from flask import render_template, request, redirect, url_for, session, flash
from .dashboard_service import get_dashboard_stats
import os
from . import admin_bp
from .decorators import login_required
from repositories.project_repository import (
    get_projects,
    get_project_by_id,
    create_project,
    update_project,
)


@admin_bp.route("/")
@login_required
def dashboard():

    stats = get_dashboard_stats()

    return render_template("admin/dashboard.html", page_title="Dashboard", stats=stats)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == os.getenv("ADMIN_USERNAME") and password == os.getenv(
            "ADMIN_PASSWORD"
        ):

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
    return render_template("admin/projects.html", page_title="Projects" ,projects=projects)


@admin_bp.route("/projects/create", methods=["GET", "POST"])
@login_required
def create_project_view():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        technologies_raw = request.form.get("technologies", "").strip()
        github = request.form.get("github", "").strip()

        errors = []

        if not title:
            errors.append("عنوان پروژه الزامی است.")

        if not description:
            errors.append("توضیحات پروژه الزامی است.")

        technologies = [
            item.strip() for item in technologies_raw.split(",") if item.strip()
        ]

        if not technologies:
            errors.append("حداقل یک تکنولوژی وارد کنید.")

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
                },
            )

        project = {
            "title": title,
            "description": description,
            "technologies": technologies,
            "github": github,
        }

        create_project(project)

        return redirect(url_for("admin.projects"))

    return render_template(
        "admin/project_form.html", page_title="Add Project", errors=[], project={}
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

        errors = []

        if not title:
            errors.append("عنوان پروژه الزامی است.")

        if not description:
            errors.append("توضیحات پروژه الزامی است.")

        technologies = [
            item.strip() for item in technologies_raw.split(",") if item.strip()
        ]

        if not technologies:
            errors.append("حداقل یک تکنولوژی وارد کنید.")

        if errors:

            project = {
                "id": project_id,
                "title": title,
                "description": description,
                "technologies": technologies,
                "github": github,
            }

            return render_template(
                "admin/project_form.html",
                page_title="Edit Project",
                errors=errors,
                project=project,
                edit_mode=True,
            )

        updated_project = {
            "id": project_id,
            "title": title,
            "description": description,
            "technologies": technologies,
            "github": github,
        }

        update_project(project_id, updated_project)

        return redirect(url_for("admin.projects"))

    return render_template(
        "admin/project_form.html",
        page_title="Edit Project",
        errors=[],
        project=project,
        edit_mode=True,
    )


@admin_bp.route("/articles")
@login_required
def articles():
    return render_template("admin/articles.html", page_title="Articles")


@admin_bp.route("/messages")
@login_required
def messages():
    return render_template("admin/messages.html", page_title="Messages")


@admin_bp.route("/settings")
@login_required
def settings():
    return render_template("admin/settings.html", page_title="Settings")
