from flask import render_template
from . import admin_bp


@admin_bp.route("/")
def dashboard():
    return render_template("admin/dashboard.html")


@admin_bp.route("/projects")
def projects():
    return render_template("admin/projects.html")


@admin_bp.route("/articles")
def articles():
    return render_template("admin/articles.html")


@admin_bp.route("/messages")
def messages():
    return render_template("admin/messages.html")


@admin_bp.route("/settings")
def settings():
    return render_template("admin/settings.html")