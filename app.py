"""
Application factory and public routes.

Previously this file created a module-level `app` object and assigned every
setting onto it directly, which made it impossible to build the app with a
different config — and therefore impossible to test. Content constants
(translations, experience, education) moved to content.py; SEO generation
moved to seo.py.
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_mail import Message
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import OperationalError

# Load .env before any config class reads an environment variable.
load_dotenv()

from admin import admin_bp  # noqa: E402
from admin.forms import ContactForm  # noqa: E402
from admin.utils import article_upload_exists  # noqa: E402
from config import get_config, sqlite_path  # noqa: E402
from content import (  # noqa: E402
    BUILT_WITH,
    DEFAULT_LANG,
    EDUCATION,
    EXPERIENCES,
    NAME,
    PROFILE,
    SITE_TITLE,
    TAGLINE,
    TRANSLATIONS,
    get_skill_icon,
)
from extensions import csrf, db, limiter, mail  # noqa: E402
from repositories import pageview_repository as views_repo  # noqa: E402
from repositories.article_repository import (  # noqa: E402
    get_article_by_id,
    get_articles,
    increment_views,
)
from repositories.message_repository import create_message  # noqa: E402
from repositories.project_repository import get_project_by_id, get_projects  # noqa: E402
from repositories.settings_repository import (  # noqa: E402
    get_settings,
    get_skills_by_category,
)
from seed import seed_if_empty  # noqa: E402
from seo import (  # noqa: E402
    article_schema,
    breadcrumb_schema,
    build_rss,
    build_sitemap,
    person_schema,
    project_schema,
)


def create_app(config_name=None):

    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    _init_extensions(app)
    _register_jinja(app)
    _register_hooks(app)
    _register_routes(app)
    _register_errors(app)

    app.register_blueprint(admin_bp)

    _prepare_database(app)

    return app


def _prepare_database(app):
    """
    Create the schema, making sure a SQLite file has a directory to live in.

    SQLite does not create missing directories; it reports "unable to open
    database file", which on a fresh host looks like a permissions problem
    rather than a missing folder. Creating it here means the app boots on a
    host where `data/` was not part of the deployed bundle.
    """
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_path = sqlite_path(uri)

    if db_path:
        directory = os.path.dirname(os.path.abspath(db_path))
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as error:
            raise RuntimeError(
                f"Cannot create the database directory {directory!r}: {error}. "
                "Set DATABASE_URL to a writable location (or a managed "
                "Postgres URL), or mount a writable disk there."
            ) from error

    with app.app_context():
        # create_all is enough for a single-file schema of this size.
        # Introduce Alembic/Flask-Migrate once the schema starts changing
        # against data you cannot afford to rebuild.
        try:
            db.create_all()

            # create_all only makes empty tables, so the first deploy served
            # a site with no projects and no articles. The JSON files in
            # data/ ship with every deploy and are the initial content.
            # Controlled by AUTO_SEED=0 for a host that manages its own data.
            if app.config.get("AUTO_SEED", True):
                seed_if_empty(app.logger)

        except OperationalError as error:
            target = db_path or uri
            raise RuntimeError(
                f"Cannot open the database at {target!r}: {error.orig}. "
                "On a container host the application directory is often "
                "read-only or wiped between deploys — set DATABASE_URL to a "
                "managed Postgres database, or mount a persistent disk and "
                "point DATABASE_URL at a file on it."
            ) from error


# --- Wiring -----------------------------------------------------------


def _init_extensions(app):
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    limiter.init_app(app)


def _register_jinja(app):
    app.jinja_env.filters["skill_icon"] = get_skill_icon

    @app.template_filter("thousands")
    def thousands(value):
        """1234 -> 1,234 for the view counters."""
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return value

    @app.template_filter("loc")
    def localized(entry, field):
        """
        Pick the language-appropriate variant of a content field.

        content.py carries both `role` and `role_en` (and the same for
        company, desc, degree, university, year). The templates only ever
        read the Persian key, so the English site rendered Persian job
        titles, employers and dates. Falls back to the Persian value when no
        translation exists.
        """
        if not isinstance(entry, dict):
            return entry

        if session.get("lang", DEFAULT_LANG) == "en":
            translated = entry.get(f"{field}_en")
            if translated:
                return translated

        return entry.get(field, "")


def _register_hooks(app):

    @app.before_request
    def set_lang():
        if session.get("lang") not in TRANSLATIONS:
            session["lang"] = DEFAULT_LANG

    @app.after_request
    def count_view(response):
        """
        Record a hit for successful HTML GETs on public pages only. Skips
        the admin panel, static files, bots fetching feeds, and anything
        that is not a 2xx HTML response.
        """
        if (
            request.method != "GET"
            or response.status_code >= 300
            or request.blueprint == "admin"
            or request.endpoint in (None, "static")
            or "text/html" not in response.content_type
        ):
            return response

        try:
            views_repo.record_view(request.path)
        except Exception:  # pragma: no cover - never fail a page over stats
            db.session.rollback()
            current_app.logger.exception("Failed to record page view")

        return response

    @app.after_request
    def set_cache_headers(response):
        """
        Public pages previously shipped no Cache-Control at all, so every
        visit re-rendered and re-downloaded everything. The admin panel and
        anything with a session flash stay uncacheable.
        """
        if request.blueprint == "admin":
            response.headers.setdefault("Cache-Control", "no-store, private")
            return response

        if request.endpoint == "static":
            seconds = current_app.config["STATIC_CACHE_SECONDS"]
            response.headers.setdefault(
                "Cache-Control", f"public, max-age={seconds}, immutable"
            )
            return response

        if request.method == "GET" and response.status_code == 200:
            seconds = current_app.config["PUBLIC_CACHE_SECONDS"]
            response.headers.setdefault(
                "Cache-Control", f"public, max-age=0, s-maxage={seconds}, must-revalidate"
            )

        return response

    @app.after_request
    def set_security_headers(response):
        """Baseline hardening headers the site previously sent none of."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response

    @app.teardown_request
    def rollback_on_error(exception):
        # Leaves no half-finished transaction behind if a view raised.
        if exception is not None:
            db.session.rollback()

    @app.context_processor
    def inject_globals():
        lang = session.get("lang", DEFAULT_LANG)
        # .get() guards the KeyError that a tampered or stale session cookie
        # could raise on *every* page.
        translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])

        settings = get_settings()
        now = datetime.now()

        site_url = current_app.config["SITE_URL"].rstrip("/")
        canonical_url = site_url + (request.path if request else "/")

        return dict(
            SITE_TITLE=SITE_TITLE,
            NAME=NAME,
            TAGLINE=TAGLINE,
            PROFILE=PROFILE,
            SOCIALS=settings["socials"],
            BUILT_WITH=BUILT_WITH,
            year=now.year,
            current_year=now.year,
            t=translations,
            lang=lang,
            canonical_url=canonical_url,
            person_schema=person_schema(settings, lang),
        )


# --- Routes -----------------------------------------------------------


def _register_routes(app):

    @app.route("/")
    def home():
        return render_template(
            "index.html",
            skills=get_settings()["skills"],
            skill_groups=get_skills_by_category(),
            projects=get_projects(),
            articles=get_articles(),
            profile=PROFILE,
        )

    @app.route("/projects")
    def projects():
        return render_template("projects.html", projects=get_projects())

    @app.route("/projects/<int:project_id>")
    def project_detail(project_id):
        project = get_project_by_id(project_id)

        if project is None:
            # Was a bare `return "Project not found", 404` with no template.
            abort(404)

        return render_template(
            "project_detail.html",
            project=project,
            page_schema=project_schema(project),
            breadcrumbs=breadcrumb_schema(
                [
                    ("Home", url_for("home")),
                    ("Projects", url_for("projects")),
                    (project["title"], url_for("project_detail", project_id=project_id)),
                ]
            ),
        )

    @app.route("/about")
    def about():
        return render_template(
            "about.html",
            experiences=EXPERIENCES,
            education=EDUCATION,
            skills=get_settings()["skills"],
            skill_groups=get_skills_by_category(),
        )

    @app.route("/articles")
    def articles():
        return render_template("articles.html", articles=get_articles())

    @app.route("/articles/<int:article_id>")
    def article_detail(article_id):
        article = get_article_by_id(article_id)

        if not article:
            abort(404)

        article = increment_views(article_id)

        return render_template(
            "article_detail.html",
            article=article,
            page_schema=article_schema(article),
            breadcrumbs=breadcrumb_schema(
                [
                    ("Home", url_for("home")),
                    ("Articles", url_for("articles")),
                    (article["title"], url_for("article_detail", article_id=article_id)),
                ]
            ),
        )

    @app.route("/articles/download/<path:filename>")
    def download_article(filename):
        """
        Only serves a file that an article actually references, and only
        from the uploads directory. Previously any name was passed straight
        to send_from_directory, which 500'd on a miss and was not restricted
        to real article files.
        """
        known = {
            article["file"]
            for article in get_articles()
            if article.get("file")
        }

        if filename not in known:
            abort(404)

        upload_folder = current_app.config["UPLOAD_FOLDER"]

        if not article_upload_exists(filename, upload_folder):
            current_app.logger.warning(
                "Article file missing from disk: %s", filename
            )
            abort(404)

        return send_from_directory(upload_folder, filename, as_attachment=True)

    @app.route("/contact", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def contact():

        form = ContactForm()

        if form.validate_on_submit():

            # Honeypot: a bot filled the hidden field — pretend success and
            # store nothing.
            if (form.website.data or "").strip():
                flash(TRANSLATIONS[session.get("lang", DEFAULT_LANG)]["MSG_SUCCESS"], "success")
                return redirect(url_for("contact"))

            # Store first, so a submission is never lost to an SMTP failure.
            create_message(
                form.name.data.strip(),
                form.email.data.strip(),
                form.message.data.strip(),
            )

            recipient = current_app.config.get("CONTACT_RECIPIENT_EMAIL")

            if recipient:
                try:
                    mail.send(
                        Message(
                            subject=f"پیام جدید از {form.name.data.strip()}",
                            recipients=[recipient],
                            body=(
                                f"From: {form.name.data.strip()} "
                                f"<{form.email.data.strip()}>\n\n"
                                f"{form.message.data.strip()}"
                            ),
                        )
                    )
                except Exception:
                    current_app.logger.exception(
                        "Failed to send contact-form notification email"
                    )
            else:
                current_app.logger.warning(
                    "CONTACT_RECIPIENT_EMAIL is not set; message stored only."
                )

            flash(TRANSLATIONS[session.get("lang", DEFAULT_LANG)]["MSG_SUCCESS"], "success")
            return redirect(url_for("contact"))

        return render_template("contact.html", form=form)

    # --- Language -----------------------------------------------------

    def _safe_referrer():
        """Only follow a same-origin referrer."""
        referrer = request.referrer or ""
        if referrer.startswith(request.host_url):
            return referrer
        return url_for("home")

    @app.route("/lang/<code>")
    def switch_lang(code):
        if code in TRANSLATIONS:
            session["lang"] = code
        return redirect(_safe_referrer())

    @app.route("/toggle-lang")
    def toggle_lang():
        session["lang"] = "en" if session.get("lang", DEFAULT_LANG) == "fa" else "fa"
        return redirect(_safe_referrer())

    # --- Files & feeds ------------------------------------------------

    @app.route("/resume")
    def download_resume():
        return send_from_directory(
            app.root_path, "myresume.pdf", as_attachment=True
        )

    @app.route("/robots.txt")
    def robots_txt():
        """
        Generated so the Sitemap line always matches SITE_URL, and so the
        admin panel is explicitly excluded from crawling.
        """
        site_url = current_app.config["SITE_URL"].rstrip("/")
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin\n"
            "Disallow: /articles/download/\n"
            f"Sitemap: {site_url}{url_for('sitemap_xml')}\n"
        )
        return Response(body, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        """
        Built from the database. The old static file listed only the five
        top-level pages and had a lastmod frozen at 2026-09-13.
        """
        return Response(
            build_sitemap(get_projects(), get_articles()),
            mimetype="application/xml",
        )

    @app.route("/feed.xml")
    def rss_feed():
        return Response(
            build_rss(get_articles(), session.get("lang", DEFAULT_LANG)),
            mimetype="application/rss+xml",
        )

    @app.route("/manifest.webmanifest")
    def manifest():
        """Minimal PWA manifest so the site is installable on mobile."""
        return Response(
            json.dumps(
                {
                    "name": f"{NAME} — {TAGLINE}",
                    "short_name": NAME,
                    "start_url": url_for("home"),
                    "display": "standalone",
                    "background_color": "#0b1120",
                    "theme_color": "#0f172a",
                    "icons": [
                        {
                            "src": url_for(
                                "static", filename="images/apple-touch-icon.png"
                            ),
                            "sizes": "180x180",
                            "type": "image/png",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            mimetype="application/manifest+json",
        )

    @app.route("/healthz")
    def healthz():
        """Liveness probe for the container / reverse proxy."""
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            return {"status": "error"}, 503
        return {"status": "ok"}


# --- Errors -----------------------------------------------------------


def _register_errors(app):

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("نشست شما منقضی شده یا نامعتبر است، لطفاً دوباره تلاش کنید.", "danger")
        return redirect(request.referrer or url_for("home")), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(error):
        flash("حجم فایل ارسالی بیش از حد مجاز (۲۰ مگابایت) است.", "danger")
        return redirect(request.referrer or url_for("home")), 413

    @app.errorhandler(429)
    def rate_limited(error):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def server_error(error):
        # Re-raise HTTP errors so their own handlers/status codes stand.
        from werkzeug.exceptions import HTTPException

        if isinstance(error, HTTPException):
            return error

        db.session.rollback()
        current_app.logger.exception("Unhandled application error")
        return render_template("errors/500.html"), 500


# Module-level app for `flask run` and for gunicorn via wsgi.py.
app = create_app()


if __name__ == "__main__":
    # FLASK_DEBUG must be explicitly "1" to enable the interactive debugger,
    # which is remote code execution if ever exposed. For real deployment
    # use gunicorn/waitress via wsgi.py rather than this server.
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
