"""
Admin routes.

Reduced from 779 lines to the HTTP layer only. What moved out:

  * credential checking          -> admin/auth.py
  * upload sanitising / saving   -> admin/utils.py
  * field validation & coercion  -> admin/forms.py (Flask-WTF)

Each view now does one thing: bind a form, hand the validated data to a
repository, and redirect or re-render.
"""

import io
import os
from urllib.parse import urlparse

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from extensions import limiter
from repositories.article_repository import (
    create_article,
    delete_article,
    get_article_by_id,
    get_articles,
    update_article,
)
from repositories.message_repository import (
    count_unread,
    delete_message,
    get_message_by_id,
    get_messages,
    set_read,
)
from repositories.project_repository import (
    create_project,
    delete_project,
    get_project_by_id,
    get_projects,
    update_project,
)
from repositories.settings_repository import get_settings, update_settings

from . import admin_bp, backup_service
from .auth import current_user, login_user, logout_user, verify_credentials
from .dashboard_service import get_dashboard_stats
from .decorators import login_required
from .forms import (
    SKILL_CATEGORY_CHOICES,
    ArticleForm,
    BackupExportForm,
    BackupImportForm,
    LoginForm,
    ProjectForm,
    SettingsForm,
)
from .utils import (
    article_image_url,
    delete_article_upload,
    save_article_image,
    save_article_upload,
)


def _is_safe_next(target):
    """Only allow same-site relative redirects after login."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")


@admin_bp.context_processor
def inject_unread_messages():
    if not current_user():
        return {}
    # Counted in SQL rather than by loading and summing every message on
    # every admin request.
    return {"unread_messages": count_unread()}


@admin_bp.context_processor
def inject_admin_asset():
    """
    Static files are cached for 30 days and marked immutable, so a changed
    admin.css would otherwise not reach a returning browser. The file's
    mtime in the query string gives every deploy a fresh URL.
    """

    def admin_asset(filename):
        path = os.path.join(current_app.static_folder, "admin", filename)
        try:
            version = int(os.path.getmtime(path))
        except OSError:
            version = None
        return url_for("static", filename=f"admin/{filename}", v=version)

    return {"admin_asset": admin_asset}


# --- Auth -------------------------------------------------------------


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():

    form = LoginForm()

    if form.validate_on_submit():

        if verify_credentials(form.username.data, form.password.data):

            login_user(form.username.data)

            target = request.args.get("next") or request.form.get("next")
            if _is_safe_next(target):
                return redirect(target)

            return redirect(url_for("admin.dashboard"))

        flash("نام کاربری یا رمز عبور اشتباه است.", "danger")

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


# --- Dashboard --------------------------------------------------------


@admin_bp.route("/")
@login_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        page_title="Dashboard",
        stats=get_dashboard_stats(),
    )


# --- Projects ---------------------------------------------------------


@admin_bp.route("/projects")
@login_required
def projects():
    return render_template(
        "admin/projects.html",
        page_title="Projects",
        projects=get_projects(),
    )


@admin_bp.route("/projects/create", methods=["GET", "POST"])
@login_required
def create_project_view():

    form = ProjectForm()

    if form.validate_on_submit():
        create_project(form.to_dict())
        flash("پروژه با موفقیت اضافه شد.", "success")
        return redirect(url_for("admin.projects"))

    return render_template(
        "admin/project_form.html",
        page_title="Add Project",
        form=form,
        edit_mode=False,
    )


@admin_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):

    project = get_project_by_id(project_id)
    if project is None:
        abort(404)

    form = ProjectForm(data=project)

    if form.validate_on_submit():
        update_project(project_id, form.to_dict())
        flash("پروژه با موفقیت ویرایش شد.", "success")
        return redirect(url_for("admin.projects"))

    return render_template(
        "admin/project_form.html",
        page_title="Edit Project",
        form=form,
        project=project,
        edit_mode=True,
    )


@admin_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project_view(project_id):

    if delete_project(project_id) is None:
        flash("پروژه مورد نظر پیدا نشد.", "danger")
    else:
        flash("پروژه حذف شد.", "success")

    return redirect(url_for("admin.projects"))


# --- Articles ---------------------------------------------------------


@admin_bp.route("/articles")
@login_required
def articles():
    return render_template(
        "admin/articles.html",
        page_title="Articles",
        articles=get_articles(),
    )


def _save_article_files(form):
    """
    Store the uploaded PDF and cover image.

    Returns (pdf_name, image_name), each None when that file was not
    uploaded, or None after recording the error on the form. A failure
    leaves nothing new on disk.
    """
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    image_folder = current_app.config["ARTICLE_IMAGE_FOLDER"]

    try:
        image_name = save_article_image(form.image_file.data, image_folder)
    except ValueError as error:
        form.image_file.errors.append(str(error))
        return None

    try:
        pdf_name = save_article_upload(form.file.data, upload_folder)
    except ValueError as error:
        delete_article_upload(image_name, image_folder)
        form.file.errors.append(str(error))
        return None

    return pdf_name, image_name


@admin_bp.route("/articles/create", methods=["GET", "POST"])
@login_required
def create_article_view():

    form = ArticleForm().require_file()

    if form.validate_on_submit():

        saved = _save_article_files(form)

        if saved is not None:
            pdf_name, image_name = saved

            data = form.to_dict()
            data["file"] = pdf_name
            data["image"] = image_name or ""
            if not data["authors"]:
                data["authors"] = (current_user() or {}).get("username", "")

            create_article(data)
            flash("مقاله با موفقیت اضافه شد.", "success")
            return redirect(url_for("admin.articles"))

    return render_template(
        "admin/article_form.html",
        page_title="Add Article",
        form=form,
        edit_mode=False,
    )


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
def edit_article(article_id):

    article = get_article_by_id(article_id)
    if article is None:
        abort(404)

    # `file` is excluded: seeding a FileField with a stored filename string
    # makes form.file.data a str, which is not an upload.
    form = ArticleForm(
        data={key: value for key, value in article.items() if key != "file"}
    )

    if form.validate_on_submit():

        saved = _save_article_files(form)

        if saved is not None:
            pdf_name, image_name = saved

            data = form.to_dict()
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            image_folder = current_app.config["ARTICLE_IMAGE_FOLDER"]

            if pdf_name:
                # Replacing the PDF used to leave the previous one on disk
                # forever.
                delete_article_upload(article.get("file"), upload_folder)
                data["file"] = pdf_name
            else:
                data["file"] = article.get("file", "")

            # delete_article_upload only ever touches the uploads folder, so
            # an older cover committed under static/images is never removed.
            if image_name:
                delete_article_upload(article.get("image"), image_folder)
                data["image"] = image_name
            elif form.remove_image.data:
                delete_article_upload(article.get("image"), image_folder)
                data["image"] = ""
            else:
                data["image"] = article.get("image", "")

            update_article(article_id, data)
            flash("مقاله با موفقیت ویرایش شد.", "success")
            return redirect(url_for("admin.articles"))

    return render_template(
        "admin/article_form.html",
        page_title="Edit Article",
        form=form,
        article=article,
        cover_url=article_image_url(article.get("image")),
        edit_mode=True,
    )


@admin_bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@login_required
def delete_article_view(article_id):

    deleted = delete_article(article_id)

    if deleted is None:
        flash("مقاله مورد نظر پیدا نشد.", "danger")
    else:
        # Remove the orphaned PDF and cover too, which the old route never did.
        delete_article_upload(
            deleted.get("file"), current_app.config["UPLOAD_FOLDER"]
        )
        delete_article_upload(
            deleted.get("image"), current_app.config["ARTICLE_IMAGE_FOLDER"]
        )
        flash("مقاله حذف شد.", "success")

    return redirect(url_for("admin.articles"))


# --- Messages ---------------------------------------------------------


@admin_bp.route("/messages")
@login_required
def messages():
    return render_template(
        "admin/messages.html",
        page_title="Messages",
        messages=get_messages(),
    )


@admin_bp.route("/messages/<int:message_id>/read", methods=["POST"])
@login_required
def toggle_message_read(message_id):

    message = get_message_by_id(message_id)

    if message is None:
        flash("پیام مورد نظر پیدا نشد.", "danger")
    else:
        set_read(message_id, not message.get("read"))

    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message_view(message_id):

    if delete_message(message_id) is None:
        flash("پیام مورد نظر پیدا نشد.", "danger")
    else:
        flash("پیام حذف شد.", "success")

    return redirect(url_for("admin.messages"))


# --- Settings ---------------------------------------------------------


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    stored = get_settings()

    if request.method == "POST":
        form = SettingsForm()
    else:
        form = SettingsForm(
            data={
                "github": stored["socials"].get("github", ""),
                "linkedin": stored["socials"].get("linkedin", ""),
                "twitter": stored["socials"].get("twitter", ""),
                "skills": stored["skills"],
                "default_lang": stored["appearance"]["default_lang"],
                "default_theme": stored["appearance"]["default_theme"],
            }
        )

    if form.validate_on_submit():

        update_settings(form.to_dict())

        resume = form.resume.data
        if resume and resume.filename:
            resume.save(
                os.path.join(current_app.root_path, "myresume.pdf")
            )

        flash("تنظیمات با موفقیت ذخیره شد.", "success")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html",
        page_title="Settings",
        form=form,
        settings=stored,
        skill_category_choices=[
            {"value": value, "label": label} for value, label in SKILL_CATEGORY_CHOICES
        ],
    )


# --- Backup -----------------------------------------------------------


def _resume_path():
    return os.path.join(current_app.root_path, "myresume.pdf")


def _render_backup(export_form=None, import_form=None):
    return render_template(
        "admin/backup.html",
        page_title="Backup",
        export_form=export_form or BackupExportForm(formdata=None),
        import_form=import_form or BackupImportForm(formdata=None),
    )


@admin_bp.route("/backup")
@login_required
def backup():
    return _render_backup()


@admin_bp.route("/backup/export", methods=["POST"])
@login_required
def backup_export():

    form = BackupExportForm()

    if not form.validate_on_submit():
        return _render_backup(export_form=form)

    payload = backup_service.build_export(
        current_app.config["UPLOAD_FOLDER"],
        _resume_path(),
        include_messages=form.include_messages.data,
        image_folder=current_app.config["ARTICLE_IMAGE_FOLDER"],
    )

    return send_file(
        io.BytesIO(payload),
        mimetype="application/zip",
        as_attachment=True,
        download_name=backup_service.export_filename(),
    )


@admin_bp.route("/backup/import", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def backup_import():

    form = BackupImportForm()

    if not form.validate_on_submit():
        return _render_backup(import_form=form)

    try:
        counts = backup_service.import_backup(
            form.archive.data.stream,
            current_app.config["UPLOAD_FOLDER"],
            _resume_path(),
            mode=form.mode.data,
            tables=form.tables.data,
            image_folder=current_app.config["ARTICLE_IMAGE_FOLDER"],
        )
    except backup_service.BackupError as error:
        flash(str(error), "danger")
        return _render_backup(import_form=form)

    labels = dict(form.tables.choices)
    summary = "، ".join(f"{labels[name]}: {count}" for name, count in counts.items())
    flash(f"بازگردانی با موفقیت انجام شد ({summary}).", "success")
    return redirect(url_for("admin.backup"))
