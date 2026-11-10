"""
Backup export / import for the admin panel.

The host rebuilds the container filesystem on every deploy, which wipes the
SQLite database and the uploaded PDFs. This produces one ZIP holding
everything the admin can edit, and restores it again:

    data.json                    the tables, as plain JSON
    uploads/articles/<name>.pdf  the PDF of every article that has one
    myresume.pdf                 the resume served at /resume

Nothing from the app config is ever written to the archive — only rows the
repositories return.

An import is all-or-nothing. The archive is validated completely before a
single byte is written; the database work then runs in one transaction, and
any PDF already written is removed again if that transaction fails.
"""

import io
import json
import os
import posixpath
import re
import zipfile
from datetime import date, datetime, timezone

from extensions import db
from repositories._backup import MODES
from repositories.article_repository import export_articles, import_articles
from repositories.message_repository import export_messages, import_messages
from repositories.pageview_repository import export_pageviews, import_pageviews
from repositories.project_repository import export_projects, import_projects
from repositories.settings_repository import export_settings, import_settings

from .utils import allowed_article_file, delete_article_upload, safe_upload_filename

SCHEMA_VERSION = 1

DATA_FILE = "data.json"
RESUME_FILE = "myresume.pdf"
ARTICLES_DIR = "uploads/articles"

TABLES = ("projects", "articles", "settings", "pageviews", "messages")

# Guards against a zip bomb: both are checked against the sizes the archive
# declares *and* enforced again while reading.
MAX_FILES = 200
MAX_TOTAL_BYTES = 50 * 1024 * 1024

# safe_upload_filename() prefixes a random id. Stripping the previous one
# first keeps a name from growing by nine characters on every restore.
_UPLOAD_PREFIX = re.compile(r"^[0-9a-f]{8}_")


class BackupError(ValueError):
    """The archive is unusable. The message is safe to show to the admin."""


# --- Export -----------------------------------------------------------


def build_export(upload_folder, resume_path, include_messages=False):
    """Return the backup archive as bytes."""
    articles = export_articles()

    data = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "projects": export_projects(),
        "articles": articles,
        "settings": export_settings(),
        "pageviews": export_pageviews(),
    }

    # Messages hold other people's names and email addresses, so they only
    # leave the server when explicitly asked for.
    if include_messages:
        data["messages"] = export_messages()

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DATA_FILE, json.dumps(data, ensure_ascii=False, indent=2))

        # Only PDFs an article actually points at — not whatever else has
        # accumulated in the folder.
        for name in sorted({item["file"] for item in articles if item["file"]}):
            path = _contained_path(upload_folder, name)
            if path and allowed_article_file(name) and os.path.isfile(path):
                archive.write(path, f"{ARTICLES_DIR}/{name}")

        if os.path.isfile(resume_path):
            archive.write(resume_path, RESUME_FILE)

    return buffer.getvalue()


def export_filename():
    return f"backup-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.zip"


# --- Import -----------------------------------------------------------


def import_backup(stream, upload_folder, resume_path, mode="merge", tables=TABLES):
    """
    Restore an archive produced by build_export().

    Returns a dict of how many rows each table received. Raises BackupError,
    leaving the database and the disk untouched, when anything is wrong.
    """
    if mode not in MODES:
        raise BackupError("حالت بازگردانی نامعتبر است.")

    tables = [name for name in TABLES if name in tables]
    if not tables:
        raise BackupError("هیچ بخشی برای بازگردانی انتخاب نشده است.")

    try:
        archive = zipfile.ZipFile(stream)
    except (zipfile.BadZipFile, OSError) as error:
        raise BackupError("فایل انتخاب‌شده یک ZIP معتبر نیست.") from error

    with archive:
        pdf_members, resume_member = _validate_members(archive, upload_folder)
        data = _load_data(archive)
        _validate_data(data)

        written = []
        resume_tmp = None

        try:
            counts = {}
            stale_files = []

            if "projects" in tables:
                counts["projects"] = import_projects(data.get("projects", []), mode)

            if "articles" in tables:
                rows = _restore_article_files(
                    archive, data.get("articles", []), pdf_members, upload_folder, written
                )
                stale_files = import_articles(rows, mode)
                counts["articles"] = len(rows)

            if "settings" in tables:
                import_settings(data.get("settings", {}), mode)
                counts["settings"] = len(data.get("settings", {}))

                if resume_member is not None:
                    resume_tmp = resume_path + ".importing"
                    _extract(archive, resume_member, resume_tmp)

            if "pageviews" in tables:
                counts["pageviews"] = import_pageviews(data.get("pageviews", []), mode)

            if "messages" in tables and "messages" in data:
                counts["messages"] = import_messages(data["messages"], mode)

            db.session.commit()

        except Exception as error:
            db.session.rollback()

            for path in written + ([resume_tmp] if resume_tmp else []):
                _remove(path)

            if isinstance(error, BackupError):
                raise
            raise BackupError(
                "بازگردانی انجام نشد و هیچ تغییری ذخیره نشد. "
                "داده‌های فایل با ساختار پایگاه داده سازگار نیست."
            ) from error

    # Past this point the database is committed; what is left is tidying up.
    if resume_tmp:
        os.replace(resume_tmp, resume_path)

    kept = {os.path.basename(path) for path in written}
    for name in stale_files:
        if name not in kept:
            delete_article_upload(name, upload_folder)

    return counts


def _restore_article_files(archive, articles, pdf_members, upload_folder, written):
    """
    Write each article's PDF under a freshly sanitised name and point the
    row at it. Appends every path written to `written` as it goes, so the
    caller can undo them.
    """
    os.makedirs(upload_folder, exist_ok=True)

    rows = []
    for item in articles:
        row = dict(item)
        member = pdf_members.get(row.get("file") or "")

        if member is None:
            # No PDF travelled with this article. Leaving the key out keeps
            # whatever file an existing row already has.
            row.pop("file", None)
        else:
            original = _UPLOAD_PREFIX.sub("", row["file"])
            stored_name = safe_upload_filename(original, upload_folder)
            target = os.path.join(upload_folder, stored_name)
            written.append(target)
            _extract(archive, member, target)
            row["file"] = stored_name

        rows.append(row)

    return rows


# --- Archive validation -----------------------------------------------


def _contained_path(folder, name):
    """Resolve `name` inside `folder`, or None if it would escape it."""
    root = os.path.abspath(folder)
    target = os.path.abspath(os.path.join(root, name))
    if not target.startswith(root + os.sep):
        return None
    return target


def _validate_members(archive, upload_folder):
    """
    Check every entry before anything is extracted.

    Returns ({stored filename: ZipInfo}, resume ZipInfo or None).
    """
    members = [info for info in archive.infolist() if not info.is_dir()]

    if len(members) > MAX_FILES:
        raise BackupError(f"تعداد فایل‌های داخل ZIP بیش از حد مجاز ({MAX_FILES}) است.")

    if sum(info.file_size for info in members) > MAX_TOTAL_BYTES:
        raise BackupError("حجم محتوای ZIP بیش از حد مجاز (۵۰ مگابایت) است.")

    pdf_members = {}
    resume_member = None
    has_data = False

    for info in members:
        name = info.filename

        # Zip-slip: reject anything that is not a plain relative path before
        # looking at where it claims to go.
        if (
            "\\" in name
            or name.startswith("/")
            or ".." in name.split("/")
            or posixpath.normpath(name) != name
        ):
            raise BackupError("ZIP شامل مسیر غیرمجاز است.")

        if name == DATA_FILE:
            has_data = True
        elif name == RESUME_FILE:
            resume_member = info
        elif posixpath.dirname(name) == ARTICLES_DIR and allowed_article_file(name):
            base_name = posixpath.basename(name)
            if _contained_path(upload_folder, base_name) is None:
                raise BackupError("ZIP شامل مسیر غیرمجاز است.")
            pdf_members[base_name] = info
        else:
            raise BackupError("ZIP شامل فایل غیرمجاز است؛ فقط data.json و PDF پذیرفته می‌شود.")

    if not has_data:
        raise BackupError("فایل data.json در ZIP پیدا نشد.")

    return pdf_members, resume_member


def _read(archive, info):
    """Read one member without trusting the size the archive declares."""
    with archive.open(info) as handle:
        payload = handle.read(MAX_TOTAL_BYTES + 1)
    if len(payload) > MAX_TOTAL_BYTES:
        raise BackupError("حجم محتوای ZIP بیش از حد مجاز (۵۰ مگابایت) است.")
    return payload


def _extract(archive, info, target):
    payload = _read(archive, info)
    with open(target, "wb") as handle:
        handle.write(payload)


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _load_data(archive):
    try:
        return json.loads(_read(archive, archive.getinfo(DATA_FILE)).decode("utf-8"))
    except (ValueError, zipfile.BadZipFile) as error:
        raise BackupError("فایل data.json خراب است و خوانده نمی‌شود.") from error


# --- data.json validation ---------------------------------------------


def _require(condition, message):
    if not condition:
        raise BackupError(f"ساختار data.json نامعتبر است: {message}")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_rows(data, key, required):
    rows = data.get(key, [])
    _require(isinstance(rows, list), f"«{key}» باید یک فهرست باشد.")

    for row in rows:
        _require(isinstance(row, dict), f"هر مورد «{key}» باید یک شیء باشد.")

        if "id" in row and row["id"] is not None:
            _require(_is_int(row["id"]) and row["id"] > 0, f"شناسهٔ نامعتبر در «{key}».")

        for field in required:
            value = row.get(field)
            _require(
                isinstance(value, str) and value.strip(),
                f"فیلد «{field}» در «{key}» خالی یا نامعتبر است.",
            )

    return rows


def _validate_data(data):
    _require(isinstance(data, dict), "ریشهٔ فایل باید یک شیء باشد.")

    if data.get("schema_version") != SCHEMA_VERSION:
        raise BackupError(
            "نسخهٔ این فایل پشتیبان (schema_version) پشتیبانی نمی‌شود."
        )

    for project in _validate_rows(data, "projects", ("title",)):
        for field in ("technologies", "features"):
            _require(
                isinstance(project.get(field, []), list),
                f"«{field}» پروژه باید یک فهرست باشد.",
            )

    for article in _validate_rows(data, "articles", ("title",)):
        _require(isinstance(article.get("file", ""), str), "نام فایل مقاله نامعتبر است.")
        views = article.get("views", 0)
        _require(_is_int(views) and views >= 0, "تعداد بازدید مقاله نامعتبر است.")

    _validate_rows(data, "messages", ("name", "email", "message"))

    settings = data.get("settings", {})
    _require(isinstance(settings, dict), "«settings» باید یک شیء باشد.")
    _require(isinstance(settings.get("socials", {}), dict), "«socials» باید یک شیء باشد.")
    _require(isinstance(settings.get("skills", []), list), "«skills» باید یک فهرست باشد.")

    for view in _validate_rows(data, "pageviews", ("path", "day")):
        try:
            date.fromisoformat(view["day"])
        except ValueError:
            _require(False, "تاریخ بازدید نامعتبر است.")
        _require(
            _is_int(view.get("count")) and view["count"] >= 0,
            "تعداد بازدید صفحه نامعتبر است.",
        )
