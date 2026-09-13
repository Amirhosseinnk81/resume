from flask import render_template, request, redirect, url_for, session, flash, current_app
import os
import uuid
import hmac
from werkzeug.security import check_password_hash
from extensions import limiter
from . import admin_bp
from .decorators import login_required
from .dashboard_service import get_dashboard_stats
from repositories.project_repository import (
    get_projects,
    get_project_by_id,
    create_project,
    update_project,
    delete_project,
)
from repositories.article_repository import (
    get_articles,
    get_article_by_id,
    create_article,
    update_article,
    delete_article,
)
from repositories.message_repository import (
    get_messages,
    get_message_by_id,
    set_read,
    delete_message,
)
from repositories.settings_repository import get_settings, update_settings

ALLOWED_ARTICLE_EXTENSIONS = {"pdf"}


def _allowed_article_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_ARTICLE_EXTENSIONS
    )


def _safe_upload_filename(filename, upload_folder):
    """
    Sanitize an uploaded filename for saving to disk.

    Werkzeug's secure_filename() strips non-ASCII characters, which would
    mangle the Persian filenames this project actually uses. Instead we:
      1. Strip any directory components (os.path.basename) to block path
         traversal (e.g. "../../etc/passwd").
      2. Prefix with a short random id to prevent one upload silently
         overwriting another article's file when two uploads share a name.
    """
    base_name = os.path.basename(filename).strip()

    if not base_name or base_name in (".", ".."):
        base_name = "file.pdf"

    safe_name = f"{uuid.uuid4().hex[:8]}_{base_name}"

    # Defense in depth: confirm the resolved path still lands inside upload_folder.
    resolved = os.path.abspath(os.path.join(upload_folder, safe_name))
    if not resolved.startswith(os.path.abspath(upload_folder) + os.sep):
        raise ValueError("Unsafe filename")

    return safe_name


@admin_bp.context_processor
def inject_unread_messages():
    if not session.get("admin"):
        return {}
    return {"unread_messages": sum(1 for m in get_messages() if not m.get("read"))}


@admin_bp.route("/")
@login_required
def dashboard():

    stats = get_dashboard_stats()

    return render_template("admin/dashboard.html", page_title="Dashboard", stats=stats)


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        admin_username = os.getenv("ADMIN_USERNAME", "")
        admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

        username_ok = hmac.compare_digest(username, admin_username)

        password_ok = False
        if admin_password_hash:
            try:
                password_ok = check_password_hash(admin_password_hash, password)
            except ValueError:
                # Malformed hash in .env — treat as "no valid credential configured"
                password_ok = False

        if username_ok and password_ok:

            session["admin"] = {"username": username}

            return redirect(url_for("admin.dashboard"))

        flash("نام کاربری یا رمز عبور اشتباه است.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("admin.login"))


@admin_bp.route("/projects")
@login_required
def projects():
    projects = get_projects()
    return render_template(
        "admin/projects.html", page_title="Projects", projects=projects
    )


@admin_bp.route("/projects/create", methods=["GET", "POST"])
@login_required
def create_project_view():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        technologies_raw = request.form.get("technologies", "").strip()
        github = request.form.get("github", "").strip()

        image = request.form.get("image", "").strip()
        status = request.form.get("status", "completed").strip()
        year_raw = request.form.get("year", "").strip()
        features_raw = request.form.get("features", "").strip()

        errors = []


        # -----------------------------
        # Basic validation
        # -----------------------------

        if not title:
            errors.append("عنوان پروژه الزامی است.")

        if not description:
            errors.append("توضیحات پروژه الزامی است.")


        # -----------------------------
        # Technologies
        # -----------------------------

        technologies = [
            item.strip()
            for item in technologies_raw.split(",")
            if item.strip()
        ]

        if not technologies:
            errors.append("حداقل یک تکنولوژی وارد کنید.")


        # -----------------------------
        # Features
        # -----------------------------

        features = [
            item.strip()
            for item in features_raw.split(",")
            if item.strip()
        ]


        # -----------------------------
        # Year
        # -----------------------------

        year = None

        if year_raw:

            try:

                year = int(year_raw)

            except ValueError:

                errors.append("سال پروژه باید عدد باشد.")


        # -----------------------------
        # Status
        # -----------------------------

        allowed_statuses = [
            "completed",
            "in-progress",
            "planned"
        ]

        if status not in allowed_statuses:

            errors.append(
                "وضعیت پروژه نامعتبر است."
            )


        # -----------------------------
        # Validation errors
        # -----------------------------

        if errors:

            return render_template(
                "admin/project_form.html",
                page_title="Add Project",
                errors=errors,
                project={
                    "title": title,
                    "description": description,
                    "technologies": technologies,
                    "github": github,
                    "image": image,
                    "status": status,
                    "year": year_raw,
                    "features": features,
                },
                edit_mode=False,
            )


        # -----------------------------
        # New project
        # -----------------------------

        project = {

            "title": title,

            "description": description,

            "technologies": technologies,

            "github": github,

            "image": image,

            "status": status,

            "year": year,

            "features": features,
        }


        create_project(project)


        return redirect(
            url_for("admin.projects")
        )


    # -----------------------------
    # GET
    # -----------------------------

    return render_template(
        "admin/project_form.html",
        page_title="Add Project",
        errors=[],
        project={},
        edit_mode=False,
    )


@admin_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):

    project = get_project_by_id(project_id)

    if project is None:
        return "Project not found", 404

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        technologies_raw = request.form.get("technologies", "").strip()
        github = request.form.get("github", "").strip()

        image = request.form.get("image", "").strip()
        status = request.form.get("status", "completed").strip()
        year_raw = request.form.get("year", "").strip()
        features_raw = request.form.get("features", "").strip()

        errors = []

        # -----------------------------
        # Basic validation
        # -----------------------------

        if not title:
            errors.append("عنوان پروژه الزامی است.")

        if not description:
            errors.append("توضیحات پروژه الزامی است.")

        # -----------------------------
        # Technologies
        # -----------------------------

        technologies = [
            item.strip() for item in technologies_raw.split(",") if item.strip()
        ]

        if not technologies:
            errors.append("حداقل یک تکنولوژی وارد کنید.")

        # -----------------------------
        # Features
        # -----------------------------

        features = [item.strip() for item in features_raw.split(",") if item.strip()]

        # -----------------------------
        # Year
        # -----------------------------

        year = None

        if year_raw:

            try:

                year = int(year_raw)

            except ValueError:

                errors.append("سال پروژه باید عدد باشد.")

        # -----------------------------
        # Status
        # -----------------------------

        allowed_statuses = ["completed", "in-progress", "planned"]

        if status not in allowed_statuses:

            errors.append("وضعیت پروژه نامعتبر است.")

        # -----------------------------
        # Validation errors
        # -----------------------------

        if errors:

            project = {
                "id": project_id,
                "title": title,
                "description": description,
                "technologies": technologies,
                "github": github,
                "image": image,
                "status": status,
                "year": year_raw,
                "features": features,
            }

            return render_template(
                "admin/project_form.html",
                page_title="Edit Project",
                errors=errors,
                project=project,
                edit_mode=True,
            )

        # -----------------------------
        # Updated project
        # -----------------------------

        updated_project = {
            "id": project_id,
            "title": title,
            "description": description,
            "technologies": technologies,
            "github": github,
            "image": image,
            "status": status,
            "year": year,
            "features": features,
        }

        # IMPORTANT:
        # Update existing project by ID

        update_project(project_id, updated_project)

        return redirect(url_for("admin.projects"))

    # -----------------------------
    # GET
    # -----------------------------

    return render_template(
        "admin/project_form.html",
        page_title="Edit Project",
        errors=[],
        project=project,
        edit_mode=True,
    )

@admin_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project_view(project_id):

    deleted_project = delete_project(project_id)

    if deleted_project is None:
        flash("پروژه موردنظر پیدا نشد.", "danger")
        return redirect(url_for("admin.projects"))

    flash(
        f'پروژه "{deleted_project.get("title", "")}" با موفقیت حذف شد.',
        "success"
    )

    return redirect(url_for("admin.projects"))

@admin_bp.route("/articles")
@login_required
def articles():
    articles = get_articles()
    articles.sort(key=lambda a: a.get("id", 0), reverse=True)
    return render_template(
        "admin/articles.html", page_title="Articles", articles=articles
    )


@admin_bp.route("/articles/create", methods=["GET", "POST"])
@login_required
def create_article_view():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        abstract = request.form.get("abstract", "").strip()
        year_raw = request.form.get("year", "").strip()
        language = request.form.get("language", "fa").strip()
        image = request.form.get("image", "").strip()
        file = request.files.get("file")

        errors = []

        if not title:
            errors.append("عنوان مقاله الزامی است.")

        if not abstract:
            errors.append("چکیده مقاله الزامی است.")

        year = None
        if year_raw:
            try:
                year = int(year_raw)
            except ValueError:
                errors.append("سال انتشار باید عدد باشد.")

        if not file or file.filename == "":
            errors.append("فایل PDF مقاله الزامی است.")
        elif not _allowed_article_file(file.filename):
            errors.append("فقط فایل PDF مجاز است.")

        if errors:
            return render_template(
                "admin/article_form.html",
                page_title="Add Article",
                errors=errors,
                article={
                    "title": title,
                    "abstract": abstract,
                    "year": year_raw,
                    "language": language,
                    "image": image,
                },
                edit_mode=False,
            )

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        try:
            safe_filename = _safe_upload_filename(file.filename, upload_folder)
        except ValueError:
            errors.append("نام فایل نامعتبر است.")
            return render_template(
                "admin/article_form.html",
                page_title="Add Article",
                errors=errors,
                article={
                    "title": title,
                    "abstract": abstract,
                    "year": year_raw,
                    "language": language,
                    "image": image,
                },
                edit_mode=False,
            )

        file.save(os.path.join(upload_folder, safe_filename))

        create_article({
            "title": title,
            "abstract": abstract,
            "authors": session.get("admin", {}).get("username", ""),
            "year": year,
            "file": safe_filename,
            "language": language,
            "image": image,
        })

        flash("مقاله با موفقیت اضافه شد.", "success")
        return redirect(url_for("admin.articles"))

    return render_template(
        "admin/article_form.html",
        page_title="Add Article",
        errors=[],
        article={},
        edit_mode=False,
    )


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
def edit_article(article_id):

    article = get_article_by_id(article_id)

    if article is None:
        return "Article not found", 404

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        abstract = request.form.get("abstract", "").strip()
        year_raw = request.form.get("year", "").strip()
        language = request.form.get("language", "fa").strip()
        image = request.form.get("image", "").strip()
        file = request.files.get("file")

        errors = []

        if not title:
            errors.append("عنوان مقاله الزامی است.")

        if not abstract:
            errors.append("چکیده مقاله الزامی است.")

        year = None
        if year_raw:
            try:
                year = int(year_raw)
            except ValueError:
                errors.append("سال انتشار باید عدد باشد.")

        # PDF replacement is optional on edit — keep the existing file if none uploaded
        old_filename = article.get("file")
        filename = old_filename
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        new_file_uploaded = bool(file and file.filename)

        if new_file_uploaded:
            if not _allowed_article_file(file.filename):
                errors.append("فقط فایل PDF مجاز است.")
            else:
                try:
                    filename = _safe_upload_filename(file.filename, upload_folder)
                except ValueError:
                    errors.append("نام فایل نامعتبر است.")

        if errors:
            return render_template(
                "admin/article_form.html",
                page_title="Edit Article",
                errors=errors,
                article={
                    "id": article_id,
                    "title": title,
                    "abstract": abstract,
                    "year": year_raw,
                    "language": language,
                    "image": image,
                    "file": article.get("file"),
                },
                edit_mode=True,
            )

        if new_file_uploaded:
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))

            # Clean up the old PDF now that it's been replaced (best-effort)
            if old_filename and old_filename != filename:
                old_path = os.path.join(upload_folder, old_filename)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

        update_article(article_id, {
            "title": title,
            "abstract": abstract,
            "authors": article.get("authors", ""),
            "year": year,
            "file": filename,
            "language": language,
            "image": image,
        })

        flash("مقاله با موفقیت به‌روزرسانی شد.", "success")
        return redirect(url_for("admin.articles"))

    return render_template(
        "admin/article_form.html",
        page_title="Edit Article",
        errors=[],
        article=article,
        edit_mode=True,
    )


@admin_bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@login_required
def delete_article_view(article_id):

    deleted_article = delete_article(article_id)

    if deleted_article is None:
        flash("مقاله موردنظر پیدا نشد.", "danger")
        return redirect(url_for("admin.articles"))

    # Best-effort cleanup of the uploaded PDF — a missing file shouldn't block deletion
    filename = deleted_article.get("file")
    if filename:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass

    flash(f'مقاله "{deleted_article.get("title", "")}" با موفقیت حذف شد.', "success")
    return redirect(url_for("admin.articles"))


@admin_bp.route("/messages")
@login_required
def messages():
    messages = get_messages()
    messages.sort(key=lambda m: m.get("id", 0), reverse=True)
    return render_template(
        "admin/messages.html", page_title="Messages", messages=messages
    )


@admin_bp.route("/messages/<int:message_id>/read", methods=["POST"])
@login_required
def toggle_message_read(message_id):

    message = get_message_by_id(message_id)

    if message is None:
        flash("پیام موردنظر پیدا نشد.", "danger")
        return redirect(url_for("admin.messages"))

    set_read(message_id, read=not message.get("read", False))

    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message_view(message_id):

    deleted_message = delete_message(message_id)

    if deleted_message is None:
        flash("پیام موردنظر پیدا نشد.", "danger")
    else:
        flash("پیام با موفقیت حذف شد.", "success")

    return redirect(url_for("admin.messages"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    if request.method == "POST":

        github = request.form.get("github", "").strip()
        linkedin = request.form.get("linkedin", "").strip()
        twitter = request.form.get("twitter", "").strip()

        skill_names = request.form.getlist("skill_name[]")
        skill_levels = request.form.getlist("skill_level[]")

        skills = []
        errors = []

        for name, level_raw in zip(skill_names, skill_levels):
            name = name.strip()
            if not name:
                continue

            try:
                level = int(level_raw)
            except (TypeError, ValueError):
                errors.append(f'سطح مهارت "{name}" باید عدد باشد.')
                continue

            if not (0 <= level <= 100):
                errors.append(f'سطح مهارت "{name}" باید بین ۰ تا ۱۰۰ باشد.')
                continue

            skills.append({"name": name, "level": level})

        resume_file = request.files.get("resume")
        if resume_file and resume_file.filename:
            if resume_file.filename.rsplit(".", 1)[-1].lower() != "pdf":
                errors.append("فایل رزومه باید PDF باشد.")

        if errors:
            settings = get_settings()
            return render_template(
                "admin/settings.html",
                page_title="Settings",
                settings={
                    "socials": {"github": github, "linkedin": linkedin, "twitter": twitter},
                    "skills": skills or settings["skills"],
                },
                errors=errors,
            )

        update_settings({
            "socials": {"github": github, "linkedin": linkedin, "twitter": twitter},
            "skills": skills,
        })

        if resume_file and resume_file.filename:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            resume_file.save(os.path.join(base_dir, "myresume.pdf"))

        flash("تنظیمات با موفقیت ذخیره شد.", "success")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html",
        page_title="Settings",
        settings=get_settings(),
        errors=[],
    )
