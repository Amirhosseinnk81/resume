"""
Shared pytest fixtures.

None of this was possible before: `app` was created at import time in
app.py, so there was no way to build it with test settings. The app factory
is what unlocked the whole test suite.
"""

import os
import sys

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402

ADMIN_USERNAME = "testadmin"
ADMIN_PASSWORD = "testpass"


@pytest.fixture
def app(tmp_path):
    application = create_app("testing")

    # A real file DB per test keeps the in-memory connection from being
    # discarded between requests, while still being thrown away afterwards.
    application.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}",
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        ADMIN_USERNAME=ADMIN_USERNAME,
        ADMIN_PASSWORD_HASH=generate_password_hash(ADMIN_PASSWORD),
    )

    os.makedirs(application.config["UPLOAD_FOLDER"], exist_ok=True)

    with application.app_context():
        _db.drop_all()
        _db.create_all()
        yield application
        _db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def auth_client(client):
    """A client already logged into the admin panel."""
    response = client.post(
        "/admin/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 302, "login fixture failed"
    return client


@pytest.fixture
def sample_project(app):
    from repositories.project_repository import create_project

    return create_project(
        {
            "title": "Sample Project",
            "description": "A project used by the tests.",
            "technologies": ["Python", "Flask"],
            "features": ["Feature one"],
            "github": "https://github.com/example/sample",
            "status": "completed",
            "year": 2026,
        }
    )


@pytest.fixture
def sample_article(app):
    from repositories.article_repository import create_article

    return create_article(
        {
            "title": "Sample Article",
            "abstract": "An article used by the tests.",
            "authors": "Tester",
            "year": 2025,
            "file": "sample.pdf",
            "language": "fa",
        }
    )
