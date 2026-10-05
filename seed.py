"""
Seed the database from the JSON files in data/.

Those files were the storage layer before the SQLAlchemy migration. They are
still committed, so they travel with every deploy and make a useful set of
initial content: `db.create_all()` only creates empty tables, which is why
the first deploy served a site with no projects and no articles at all.

Used from two places:

  * `scripts/migrate_json_to_db.py` — the one-off local migration.
  * `create_app()` — seeds automatically when a table is empty, so a fresh
    database (a new host, or a container whose disk was wiped) comes up with
    the portfolio intact rather than blank.

Every function is idempotent: existing rows are matched and skipped, so
running this against a populated database changes nothing.
"""

import json
import os
from datetime import datetime

from extensions import db
from models import Article, ContactMessage, Project, Setting

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load(name, logger=None):
    path = os.path.join(DATA_DIR, name)

    if not os.path.exists(path):
        return None

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as error:
        if logger:
            logger.warning("Could not read %s: %s", name, error)
        return None


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def seed_projects(logger=None):
    rows = _load("projects.json", logger)
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


def seed_articles(logger=None):
    rows = _load("articles.json", logger)
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
                # Carried over so an existing view count is not reset.
                views=int(item.get("views") or 0),
            )
        )
        added += 1

    db.session.commit()
    return added


def seed_messages(logger=None):
    rows = _load("messages.json", logger)
    if not rows:
        return 0

    added = 0
    for item in rows:
        exists = ContactMessage.query.filter_by(
            name=item.get("name") or "", message=item.get("message") or ""
        ).first()
        if exists:
            continue

        message = ContactMessage(
            name=item.get("name") or "",
            email=item.get("email") or "",
            message=item.get("message") or "",
            read=bool(item.get("read")),
        )

        created = _parse_dt(item.get("created_at"))
        if created:
            message.created_at = created

        db.session.add(message)
        added += 1

    db.session.commit()
    return added


def seed_settings(logger=None):
    data = _load("settings.json", logger)
    if not data:
        return 0

    from repositories.settings_repository import _normalise_skills

    written = 0
    for key in ("socials", "skills"):
        if key not in data or Setting.query.filter_by(key=key).first():
            continue

        value = data[key]
        if key == "skills":
            # Drop the old percentage levels and map onto categories.
            value = _normalise_skills(value)

        db.session.add(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))
        written += 1

    db.session.commit()
    return written


def seed_all(logger=None):
    """Run every seeder. Returns a dict of how many rows each added."""
    return {
        "projects": seed_projects(logger),
        "articles": seed_articles(logger),
        "messages": seed_messages(logger),
        "settings": seed_settings(logger),
    }


def seed_if_empty(logger=None):
    """
    Seed only the tables that are empty.

    Called on boot. Deliberately per-table: deleting every project from the
    admin panel should not resurrect them on the next restart, but a brand
    new database should not come up blank either.

    Never raises — a seeding problem must not stop the app from serving.
    """
    added = {}

    try:
        if not Project.query.first():
            added["projects"] = seed_projects(logger)

        if not Article.query.first():
            added["articles"] = seed_articles(logger)

        if not Setting.query.first():
            added["settings"] = seed_settings(logger)

    except Exception as error:  # noqa: BLE001 - must never stop the boot
        # Deliberately broad: seeding is a convenience, and no failure
        # here is worth refusing to serve the site over.
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        if logger:
            logger.warning("Seeding skipped: %s", error)
        return {}

    added = {key: count for key, count in added.items() if count}

    if added and logger:
        logger.info(
            "Seeded an empty database from data/*.json: %s",
            ", ".join(f"{key}={count}" for key, count in sorted(added.items())),
        )

    return added
