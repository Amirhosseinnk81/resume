"""
WSGI entry point for production servers.

    gunicorn  -c gunicorn.conf.py wsgi:app     # Linux / Docker
    waitress-serve --port=8000 wsgi:app        # Windows

Running `python app.py` starts Flask's development server, which is
single-threaded and not meant to face the internet.
"""

from app import create_app

app = create_app("production")
