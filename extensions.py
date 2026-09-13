from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()

# NOTE: uses in-memory storage, which is fine for a single-process personal
# site but resets on restart and isn't shared across multiple worker
# processes. If this is ever deployed with multiple gunicorn/waitress
# workers, point storage_uri at a shared backend (e.g. Redis) instead.
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per hour"],
)
