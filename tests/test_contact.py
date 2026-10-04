"""
Contact form tests.

The form previously had three `if not x` checks and nothing else: no length
limit, no email-shape check, and the honeypot was read straight off
request.form.
"""


def test_valid_submission_is_stored(client):
    response = client.post(
        "/contact",
        data={"name": "Ali", "email": "ali@example.com", "message": "Hello there"},
    )
    assert response.status_code == 302

    from repositories.message_repository import get_messages

    messages = get_messages()
    assert len(messages) == 1
    assert messages[0]["name"] == "Ali"
    assert messages[0]["read"] is False


def test_message_is_stored_even_when_mail_fails(client, app, monkeypatch):
    """
    A broken SMTP config must never lose a submission or 500 the visitor.
    """
    app.config["CONTACT_RECIPIENT_EMAIL"] = "owner@example.com"

    from extensions import mail

    def explode(*args, **kwargs):
        raise RuntimeError("SMTP is down")

    monkeypatch.setattr(mail, "send", explode)

    response = client.post(
        "/contact",
        data={"name": "Ali", "email": "ali@example.com", "message": "Hello there"},
    )

    assert response.status_code == 302

    from repositories.message_repository import get_messages

    assert len(get_messages()) == 1


def test_honeypot_submission_is_silently_dropped(client):
    response = client.post(
        "/contact",
        data={
            "name": "Bot",
            "email": "bot@example.com",
            "message": "spam spam spam",
            "website": "http://spam.example",
        },
    )

    # Looks successful to the bot...
    assert response.status_code == 302

    # ...but nothing was stored.
    from repositories.message_repository import get_messages

    assert get_messages() == []


def test_missing_fields_are_rejected(client):
    for payload in (
        {"name": "", "email": "a@b.co", "message": "hello there"},
        {"name": "A", "email": "", "message": "hello there"},
        {"name": "A", "email": "a@b.co", "message": ""},
    ):
        response = client.post("/contact", data=payload)
        assert response.status_code == 200, payload

    from repositories.message_repository import get_messages

    assert get_messages() == []


def test_malformed_email_is_rejected(client):
    for bad in ("not-an-email", "a b@example.com", "a@@b.com", "a@b", "@example.com"):
        response = client.post(
            "/contact", data={"name": "A", "email": bad, "message": "hello there"}
        )
        assert response.status_code == 200, bad

    from repositories.message_repository import get_messages

    assert get_messages() == []


def test_oversized_message_is_rejected(client):
    """There was no length limit at all before."""
    response = client.post(
        "/contact",
        data={"name": "A", "email": "a@b.co", "message": "x" * 6000},
    )
    assert response.status_code == 200

    from repositories.message_repository import get_messages

    assert get_messages() == []


def test_too_short_message_is_rejected(client):
    response = client.post(
        "/contact", data={"name": "A", "email": "a@b.co", "message": "hi"}
    )
    assert response.status_code == 200
