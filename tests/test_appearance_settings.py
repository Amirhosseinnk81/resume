"""
Default language and theme, set from /admin/settings.

Both are defaults only: they decide what a visitor with no choice of their
own sees. A visitor who has switched language or theme keeps their choice.
"""

from repositories.settings_repository import get_settings, update_settings


def set_appearance(app, **values):
    update_settings({"appearance": values})


def test_defaults_are_persian_and_auto(client):
    html = client.get("/").get_data(as_text=True)

    assert get_settings()["appearance"] == {"default_lang": "fa", "default_theme": "auto"}
    assert '<html lang="fa" dir="rtl"' in html
    assert 'data-default-theme="auto"' in html


def test_default_language_applies_to_a_new_visitor(app, client):
    set_appearance(app, default_lang="en")

    html = client.get("/").get_data(as_text=True)

    assert '<html lang="en" dir="ltr"' in html


def test_a_visitors_own_language_beats_the_default(app, client):
    client.get("/lang/fa")
    set_appearance(app, default_lang="en")

    html = client.get("/").get_data(as_text=True)

    assert '<html lang="fa" dir="rtl"' in html


def test_changing_the_default_does_not_move_an_existing_visitor(app, client):
    client.get("/")  # first visit: Persian is stored in the session
    set_appearance(app, default_lang="en")

    html = client.get("/").get_data(as_text=True)

    assert '<html lang="fa" dir="rtl"' in html


def test_default_theme_reaches_the_public_site_and_the_admin(app, auth_client):
    set_appearance(app, default_theme="dark")

    assert 'data-default-theme="dark"' in auth_client.get("/").get_data(as_text=True)
    assert 'data-default-theme="dark"' in auth_client.get("/admin/").get_data(as_text=True)


def test_settings_form_saves_language_and_theme(auth_client):
    response = auth_client.post(
        "/admin/settings",
        data={
            "github": "",
            "linkedin": "",
            "twitter": "",
            "default_lang": "en",
            "default_theme": "dark",
        },
    )

    assert response.status_code == 302
    assert get_settings()["appearance"] == {"default_lang": "en", "default_theme": "dark"}


def test_settings_page_shows_the_stored_choice(app, auth_client):
    set_appearance(app, default_lang="en", default_theme="light")

    html = auth_client.get("/admin/settings").get_data(as_text=True)

    assert '<option selected value="en">' in html
    assert '<option selected value="light">' in html


def test_unknown_values_are_ignored(app, auth_client):
    set_appearance(app, default_lang="en", default_theme="dark")

    auth_client.post(
        "/admin/settings",
        data={"default_lang": "xx", "default_theme": "neon"},
    )

    assert get_settings()["appearance"] == {"default_lang": "en", "default_theme": "dark"}


def test_saving_without_the_fields_keeps_the_stored_values(app, auth_client):
    set_appearance(app, default_lang="en", default_theme="dark")

    auth_client.post("/admin/settings", data={"github": "", "linkedin": "", "twitter": ""})

    assert get_settings()["appearance"] == {"default_lang": "en", "default_theme": "dark"}
