from functools import wraps

from flask import redirect, request, url_for

from .auth import is_authenticated


def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not is_authenticated():
            # Carry the requested page so login can return the admin there
            # instead of always dumping them on the dashboard.
            return redirect(url_for("admin.login", next=request.full_path))

        return func(*args, **kwargs)

    return wrapper
