"""
Application configuration.

Split into classes so the app factory can be built with a different config
per environment. Previously every setting was assigned directly onto a
module-level `app` object in app.py, which made it impossible to create the
app with test settings (and therefore impossible to write tests at all).
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _normalise_db_url(url):
    """
    Accept the URL shapes hosting providers hand out.

    Managed Postgres add-ons (Liara, Heroku, Render) still publish
    `postgres://`, which SQLAlchemy 2.x no longer recognises, and they do not
    name a driver. Rewriting here means DATABASE_URL can be pasted from the
    provider's panel unchanged.
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]

    return url


def sqlite_path(database_uri):
    """
    Filesystem path behind a sqlite:// URI, or None for any other backend.

    Used to create the parent directory before SQLAlchemy opens the file —
    SQLite will not create missing directories and reports the far less
    obvious "unable to open database file" instead.
    """
    if not database_uri or not database_uri.startswith("sqlite:"):
        return None

    path = database_uri.split("sqlite:///", 1)[-1]

    if not path or path == ":memory:" or path.startswith(":memory:"):
        return None

    return path


class BaseConfig:

    # --- Core ---------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # Public origin, used for absolute URLs in the sitemap, RSS feed,
    # JSON-LD and canonical tags. Without this they silently fall back to
    # whatever Host header the request carried.
    SITE_URL = os.getenv("SITE_URL", "https://amirhosseinnk.ir").rstrip("/")

    # --- Database -----------------------------------------------------
    # Defaults to SQLite next to the project; set DATABASE_URL to move to
    # PostgreSQL without touching any code.
    SQLALCHEMY_DATABASE_URI = _normalise_db_url(
        os.getenv("DATABASE_URL")
        or "sqlite:///" + os.path.join(BASE_DIR, "data", "resume.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Recycle pooled connections before a managed database drops them, and
    # check liveness on checkout. Without this, a container that has been
    # idle overnight serves its first request a dead connection.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # --- Uploads ------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "articles")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB

    # --- Mail ---------------------------------------------------------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    CONTACT_RECIPIENT_EMAIL = os.getenv("CONTACT_RECIPIENT_EMAIL")

    # --- Admin credentials -------------------------------------------
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

    # --- Sessions -----------------------------------------------------
    # The admin session cookie previously had no hardening at all.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours

    # --- Caching ------------------------------------------------------
    # How long browsers/CDNs may cache public pages. Content changes rarely,
    # and the admin panel is excluded from caching entirely.
    PUBLIC_CACHE_SECONDS = int(os.getenv("PUBLIC_CACHE_SECONDS", "300"))
    STATIC_CACHE_SECONDS = int(os.getenv("STATIC_CACHE_SECONDS", str(60 * 60 * 24 * 30)))

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SEND_FILE_MAX_AGE_DEFAULT = 0


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Requires HTTPS. The site is served over TLS, so the session cookie
    # should never travel in cleartext.
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(BaseConfig):
    TESTING = True
    # In-memory DB: tests never touch data/resume.db.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # CSRF tokens would make every test POST a two-step dance; the protection
    # itself is covered by a dedicated test that re-enables it.
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "testing-secret-key"
    SITE_URL = "https://example.test"
    RATELIMIT_ENABLED = False
    ADMIN_USERNAME = "testadmin"
    # werkzeug hash of "testpass", generated at import time so no secret is
    # committed and the test credential can never work in production.
    MAIL_SUPPRESS_SEND = True


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name=None):
    """Resolve a config class from a name or the FLASK_ENV/APP_ENV variable."""
    key = (name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    return CONFIG_MAP.get(key, DevelopmentConfig)
