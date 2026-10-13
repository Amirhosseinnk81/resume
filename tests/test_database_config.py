"""
Database bootstrap tests.

Production on Liara failed to boot with:

    sqlite3.OperationalError: unable to open database file

SQLite does not create missing directories, and `data/` was not present in
the deployed bundle. These cover the bootstrap paths that CI otherwise never
exercises, because locally the directory always already exists.
"""

import os

import pytest

from config import _normalise_db_url, sqlite_path

# --- URL normalisation ------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Managed Postgres add-ons still publish the postgres:// scheme,
        # which SQLAlchemy 2.x rejects outright.
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        # No driver named -> SQLAlchemy would reach for psycopg2.
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        # Already explicit: left alone.
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:////srv/data/resume.db", "sqlite:////srv/data/resume.db"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_database_url_normalisation(raw, expected):
    assert _normalise_db_url(raw) == expected


def test_normalisation_passes_through_empty():
    assert _normalise_db_url("") == ""
    assert _normalise_db_url(None) is None


def test_postgres_password_is_not_mangled():
    """A password containing '//' must survive the scheme rewrite."""
    url = "postgres://user:pa//ss@host:5432/db"
    assert _normalise_db_url(url).endswith("pa//ss@host:5432/db")


# --- sqlite path extraction -------------------------------------------


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("sqlite:////srv/data/resume.db", "/srv/data/resume.db"),
        ("sqlite:///relative/resume.db", "relative/resume.db"),
        # Nothing to create a directory for:
        ("sqlite:///:memory:", None),
        ("postgresql+psycopg://u:p@h/db", None),
        ("", None),
        (None, None),
    ],
)
def test_sqlite_path_extraction(uri, expected):
    assert sqlite_path(uri) == expected


# --- boot behaviour ----------------------------------------------------


def test_boot_creates_a_missing_sqlite_directory(tmp_path, monkeypatch):
    """
    The exact production failure: the parent directory does not exist.
    SQLite reports 'unable to open database file' rather than anything
    pointing at a missing folder.
    """
    target = tmp_path / "deep" / "nested" / "resume.db"
    assert not target.parent.exists()

    # Must be set before create_app: Flask-SQLAlchemy builds the engine from
    # the config at init time, so assigning the URI afterwards is ignored.
    # This mirrors how the host actually supplies it.
    monkeypatch.setenv("SECRET_KEY", "boot-test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(target))

    import importlib

    import config as config_module

    importlib.reload(config_module)

    import app as app_module

    importlib.reload(app_module)

    try:
        application = app_module.create_app("production")

        assert target.parent.is_dir(), "the directory should have been created"
        assert target.is_file(), "the database file should have been created"
        assert application.test_client().get("/healthz").status_code == 200
    finally:
        # Leave the module cache as the rest of the suite expects it.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        importlib.reload(config_module)
        importlib.reload(app_module)


def test_boot_raises_a_useful_error_when_the_path_is_unusable(tmp_path):
    """
    A clear message beats a hundred-line SQLAlchemy traceback in a
    container log.
    """
    from app import _prepare_database, create_app

    # A file where a directory needs to be: makedirs cannot proceed.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")

    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(
        blocker / "sub" / "resume.db"
    )

    with pytest.raises(RuntimeError) as excinfo:
        _prepare_database(app)

    message = str(excinfo.value)
    assert "DATABASE_URL" in message, "the message should name the way out"


def test_in_memory_database_needs_no_directory():
    """sqlite_path returning None must skip makedirs entirely."""
    from app import _prepare_database, create_app

    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    _prepare_database(app)  # must not raise


def test_engine_options_guard_stale_connections(app):
    """
    A managed database drops idle connections; without pool_pre_ping the
    first request after an idle night gets a dead one.
    """
    options = app.config["SQLALCHEMY_ENGINE_OPTIONS"]
    assert options["pool_pre_ping"] is True
    assert options["pool_recycle"] > 0


def test_psycopg_is_installed_so_postgres_is_a_one_variable_switch():
    """requirements.txt ships psycopg; without it a Postgres URL fails late."""
    import psycopg  # noqa: F401
