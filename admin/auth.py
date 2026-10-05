"""
Admin authentication.

This file existed but was empty — the credential check lived inline in
routes.py. Isolating it means the comparison logic is in one place and can
be tested without going through an HTTP request.
"""

import hmac

from flask import current_app, session
from werkzeug.security import check_password_hash

SESSION_KEY = "admin"


def verify_credentials(username, password):
    """
    Constant-time-ish credential check.

    Both comparisons always run so a wrong username and a wrong password take
    the same path, and `hmac.compare_digest` avoids leaking the username
    through timing. Returns False when no credentials are configured at all,
    rather than letting an empty .env authorise an empty form.
    """
    expected_user = current_app.config.get("ADMIN_USERNAME") or ""
    expected_hash = current_app.config.get("ADMIN_PASSWORD_HASH") or ""

    if not expected_user or not expected_hash:
        current_app.logger.error(
            "Admin login attempted but ADMIN_USERNAME/ADMIN_PASSWORD_HASH "
            "are not configured."
        )
        return False

    username_ok = hmac.compare_digest(str(username or ""), expected_user)

    password_ok = False
    try:
        password_ok = check_password_hash(expected_hash, password or "")
    except (ValueError, TypeError):
        # Malformed hash in the environment: treat as no valid credential.
        current_app.logger.error("ADMIN_PASSWORD_HASH is malformed.")
        password_ok = False

    return username_ok and password_ok


def login_user(username):
    session.clear()
    session[SESSION_KEY] = {"username": username}
    # Bind the session to the configured lifetime instead of lasting until
    # the browser closes.
    session.permanent = True


def logout_user():
    session.clear()


def current_user():
    return session.get(SESSION_KEY)


def is_authenticated():
    return bool(session.get(SESSION_KEY))
