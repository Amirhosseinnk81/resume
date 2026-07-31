from flask import render_template, request, redirect, url_for, session, flash

import os
from . import admin_bp
from .decorators import login_required


@admin_bp.route("/")
@login_required
def dashboard():
    return render_template("admin/dashboard.html", page_title="Dashboard")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == os.getenv("ADMIN_USERNAME") and password == os.getenv(
            "ADMIN_PASSWORD"
        ):

            session["admin"] = {
                "username": username
                }

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
    return render_template("admin/projects.html", page_title="Projects")


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
