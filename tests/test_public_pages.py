"""Public page smoke tests and the regressions they lock in."""

import pytest


@pytest.mark.parametrize(
    "path",
    ["/", "/projects", "/about", "/articles", "/contact", "/healthz"],
)
def test_public_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_project_detail_renders(client, sample_project):
    response = client.get(f"/projects/{sample_project['id']}")
    assert response.status_code == 200
    assert "Sample Project" in response.get_data(as_text=True)


def test_missing_project_returns_styled_404(client):
    """Was a bare `return "Project not found", 404` with no template."""
    response = client.get("/projects/9999")
    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert "404" in body
    # Proof it is the real template and not a plain string.
    assert "<html" in body.lower()


def test_missing_article_returns_404(client):
    assert client.get("/articles/9999").status_code == 404


def test_unknown_url_returns_404_template(client):
    response = client.get("/definitely-not-a-page")
    assert response.status_code == 404
    assert "<html" in response.get_data(as_text=True).lower()


def test_tampered_lang_cookie_does_not_500(client):
    """
    `translations[lang]` used to be a direct dict index in the global context
    processor, so a session with an unknown language raised KeyError on
    *every* page of the site.
    """
    with client.session_transaction() as session:
        session["lang"] = "klingon"

    assert client.get("/").status_code == 200


def test_language_toggle_round_trips(client):
    client.get("/")
    client.get("/toggle-lang")
    with client.session_transaction() as session:
        assert session["lang"] == "en"

    client.get("/toggle-lang")
    with client.session_transaction() as session:
        assert session["lang"] == "fa"


def test_lang_switch_rejects_unknown_code(client):
    client.get("/lang/zz")
    with client.session_transaction() as session:
        assert session["lang"] == "fa"


def test_open_redirect_is_not_followed(client):
    """
    switch_lang/toggle_lang redirected to `request.referrer` unchecked, so a
    crafted referrer could bounce a visitor to another origin.
    """
    response = client.get(
        "/toggle-lang", headers={"Referer": "https://evil.example/phish"}
    )
    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]


def test_article_views_increment_on_detail_view(client, sample_article):
    from repositories.article_repository import get_article_by_id

    before = get_article_by_id(sample_article["id"])["views"]
    client.get(f"/articles/{sample_article['id']}")
    after = get_article_by_id(sample_article["id"])["views"]

    assert after == before + 1
