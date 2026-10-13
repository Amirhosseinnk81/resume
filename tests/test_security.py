"""Tests for the security boundaries the audit touched."""

import io

import pytest


def test_admin_pages_require_login(client):
    for path in (
        "/admin/",
        "/admin/projects",
        "/admin/articles",
        "/admin/messages",
        "/admin/settings",
    ):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/admin/login" in response.headers["Location"], path


def test_admin_write_actions_require_login(client, sample_project):
    response = client.post(f"/admin/projects/{sample_project['id']}/delete")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]

    # And the project is still there.
    from repositories.project_repository import get_project_by_id

    assert get_project_by_id(sample_project["id"]) is not None


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/admin/login", data={"username": "testadmin", "password": "wrong"}
    )
    assert response.status_code == 200  # re-renders the form
    with client.session_transaction() as session:
        assert "admin" not in session


def test_login_rejects_blank_credentials_when_unconfigured(app, client):
    """An unset ADMIN_USERNAME must not let an empty form through."""
    app.config.update(ADMIN_USERNAME="", ADMIN_PASSWORD_HASH="")
    client.post("/admin/login", data={"username": "", "password": ""})
    with client.session_transaction() as session:
        assert "admin" not in session


def test_login_next_parameter_cannot_leave_the_site(auth_client):
    """An absolute `next` must not be honoured after login."""
    response = auth_client.get("/admin/logout")
    assert response.status_code == 302

    response = auth_client.post(
        "/admin/login?next=https://evil.example/",
        data={"username": "testadmin", "password": "testpass"},
    )
    assert "evil.example" not in response.headers["Location"]


def test_csrf_is_enforced_when_enabled(app):
    """
    The testing config disables CSRF so other tests can POST plainly; this
    one re-enables it to prove the protection is actually wired up.
    """
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()

    response = client.post(
        "/contact",
        data={"name": "A", "email": "a@b.co", "message": "hello there"},
    )
    # CSRFError handler redirects with 400.
    assert response.status_code == 400


def test_article_download_rejects_unknown_filename(client):
    """
    download_article passed any name straight to send_from_directory. It now
    only serves files an article actually references.
    """
    assert client.get("/articles/download/anything.pdf").status_code == 404


def test_article_download_rejects_path_traversal(client):
    for attempt in (
        "/articles/download/../../.env",
        "/articles/download/..%2F..%2F.env",
    ):
        assert client.get(attempt).status_code in (301, 308, 404), attempt


def test_security_headers_are_present(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Referrer-Policy" in headers


def test_admin_pages_are_not_cacheable(auth_client):
    response = auth_client.get("/admin/")
    assert "no-store" in response.headers.get("Cache-Control", "")


def test_public_pages_send_cache_headers(client):
    """Public pages previously sent no Cache-Control at all."""
    response = client.get("/")
    assert "Cache-Control" in response.headers
    assert "s-maxage" in response.headers["Cache-Control"]


def test_robots_disallows_admin(client):
    body = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin" in body
