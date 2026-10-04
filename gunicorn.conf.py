"""
Gunicorn configuration.

IMPORTANT: with workers > 1 and the default in-memory rate-limit storage,
each worker enforces its own limit (so "5 per minute" effectively becomes
5 x workers). Set RATELIMIT_STORAGE_URI to a Redis URL when scaling up.

The same applies to SQLite: one file with several worker processes is fine
for this read-heavy site, but switch DATABASE_URL to PostgreSQL if writes
ever become frequent.
"""

import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Default to 2 workers rather than the usual (2 x cores + 1): the site is
# backed by a single SQLite file, and the rate limiter is per-process.
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))

worker_class = "gthread"

timeout = 30
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# Trust the reverse proxy's forwarded headers so request.remote_addr (used
# by the rate limiter) is the real client IP, not the proxy's.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
