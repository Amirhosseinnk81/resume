"""
One-off migration: data/*.json -> the SQLAlchemy database.

Run once after upgrading:

    python scripts/migrate_json_to_db.py

Idempotent: re-running will not duplicate rows (it matches on title for
projects/articles and on name+created_at for messages). The JSON files are
left untouched so they remain a usable backup; move them out of data/ once
you have confirmed the site works.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import Article, ContactMessage, Project, Setting  # noqa: E402

DATA_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "data"
)


def _load(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        print(f"  skip {name} (not found)")
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        print(f"  !! {name} is not valid JSON ({error}) — skipped")
        return None


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def migrate_projects():
    rows = _load("projects.json")
    if not rows:
        return 0

    added = 0
    for item in rows:
        title = (item.get("title") or "").strip()
        if not title or Project.query.filter_by(title=title).first():
            continue

        db.session.add(
            Project(
                title=title,
                description=item.get("description") or "",
                technologies_raw="\n".join(item.get("technologies") or []),
                features_raw="\n".join(item.get("features") or []),
                github=item.get("github") or "",
                demo=item.get("demo") or "",
                image=item.get("image") or "",
                status=item.get("status") or "completed",
                year=item.get("year"),
            )
        )
        added += 1

    db.session.commit()
    return added


def migrate_articles():
    rows = _load("articles.json")
    if not rows:
        return 0

    added = 0
    for item in rows:
        title = (item.get("title") or "").strip()
        if not title or Article.query.filter_by(title=title).first():
            continue

        db.session.add(
            Article(
                title=title,
                abstract=item.get("abstract") or "",
                authors=item.get("authors") or "",
                year=item.get("year"),
                file=item.get("file") or "",
                language=item.get("language") or "fa",
                image=item.get("image") or "",
                # Carried over so the existing view count is not reset to 0.
                views=int(item.get("views") or 0),
            )
        )
        added += 1

    db.session.commit()
    return added


def migrate_messages():
    rows = _load("messages.json")
    if not rows:
        return 0

    added = 0
    for item in rows:
        created = _parse_dt(item.get("created_at"))
        name = item.get("name") or ""

        exists = ContactMessage.query.filter_by(
            name=name, message=item.get("message") or ""
        ).first()
        if exists:
            continue

        message = ContactMessage(
            name=name,
            email=item.get("email") or "",
            message=item.get("message") or "",
            read=bool(item.get("read")),
        )
        if created:
            message.created_at = created

        db.session.add(message)
        added += 1

    db.session.commit()
    return added


def migrate_settings():
    data = _load("settings.json")
    if not data:
        return 0

    written = 0
    for key in ("socials", "skills"):
        if key not in data:
            continue
        if Setting.query.filter_by(key=key).first():
            continue

        value = data[key]

        if key == "skills":
            # Drop the percentage levels and map each skill onto a category.
            # The repository layer also normalises on read, but writing the
            # new shape means the stored data is clean too.
            from repositories.settings_repository import _normalise_skills

            value = _normalise_skills(value)

        db.session.add(
            Setting(key=key, value=json.dumps(value, ensure_ascii=False))
        )
        written += 1

    db.session.commit()
    return written


def main():
    app = create_app()

    with app.app_context():
        db.create_all()

        print("Migrating data/*.json -> database")
        print(f"  database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"  projects: +{migrate_projects()}")
        print(f"  articles: +{migrate_articles()}")
        print(f"  messages: +{migrate_messages()}")
        print(f"  settings: +{migrate_settings()}")
        print("Done. The JSON files were left in place as a backup.")


if __name__ == "__main__":
    main()
