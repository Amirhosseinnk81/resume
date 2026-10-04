"""
Flask extension instances.

Created unbound here and attached to the app inside create_app(), which is
what lets the same extension objects be reused by a test app built with a
different config.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

csrf = CSRFProtect()

db = SQLAlchemy()

mail = Mail()

# NOTE: defaults to in-memory storage, which resets on restart and is not
# shared across worker processes. Set RATELIMIT_STORAGE_URI to a Redis URL
# (e.g. redis://localhost:6379/0) when running more than one worker,
# otherwise each worker enforces the limit separately.
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per hour"],
)
