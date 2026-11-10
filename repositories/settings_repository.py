"""
Site settings data access (socials, skills).

Two things changed here beyond the storage swap:

  1. Settings are read on *every* request by the global context processor and
     then again inside several views, which previously meant 2-4 file opens
     and JSON parses per page view for data that changes a few times a year.
     Reads are now memoised per request, and invalidated on write.

  2. `skills` moved from {"name", "level"} to {"name", "category"}. Percentage
     skill bars ("JavaScript 10%") are an anti-pattern none of the reference
     portfolios use, and a low number actively argues against the candidate.
     Skills are now grouped tags. Legacy rows with a `level` are migrated on
     read so an old settings.json or DB row still works.
"""

import json

from flask import g, has_app_context

from extensions import db
from models import Setting

DEFAULT_SOCIALS = {
    "github": "https://github.com/Amirhosseinnk81",
    "linkedin": "https://www.linkedin.com/in/amirhossein-naeimaei-618451374/",
    "twitter": "https://x.com/Amirnk_81",
}

# Ordered so the categories render in a deliberate sequence.
SKILL_CATEGORIES = ("languages", "frameworks", "databases", "tools")

DEFAULT_SKILLS = [
    {"name": "Python", "category": "languages"},
    {"name": "JavaScript", "category": "languages"},
    {"name": "SQL", "category": "languages"},
    {"name": "HTML/CSS", "category": "languages"},
    {"name": "Flask", "category": "frameworks"},
    {"name": "Django", "category": "frameworks"},
    {"name": "Bootstrap", "category": "frameworks"},
    {"name": "PostgreSQL", "category": "databases"},
    {"name": "SQLite", "category": "databases"},
    {"name": "Git&Github", "category": "tools"},
    {"name": "Docker", "category": "tools"},
    {"name": "Linux", "category": "tools"},
]

DEFAULT_SETTINGS = {
    "socials": DEFAULT_SOCIALS,
    "skills": DEFAULT_SKILLS,
}

_CACHE_KEY = "_settings_cache"


def _normalise_skills(skills):
    """
    Accept both the new {"name", "category"} shape and the legacy
    {"name", "level"} shape, so an existing database row or a hand-edited
    settings.json keeps working after the upgrade.
    """
    if not isinstance(skills, list):
        return list(DEFAULT_SKILLS)

    known = {entry["name"].lower(): entry["category"] for entry in DEFAULT_SKILLS}

    normalised = []
    for skill in skills:
        if not isinstance(skill, dict) or not skill.get("name"):
            continue

        name = str(skill["name"]).strip()
        category = skill.get("category")

        if category not in SKILL_CATEGORIES:
            # Legacy entry (or unknown category): infer from the known list,
            # defaulting to "tools" rather than dropping the skill.
            category = known.get(name.lower(), "tools")

        normalised.append({"name": name, "category": category})

    return normalised or list(DEFAULT_SKILLS)


def _read_raw():
    rows = {row.key: row.value for row in Setting.query.all()}

    settings = {}
    for key, default in DEFAULT_SETTINGS.items():
        raw = rows.get(key)
        if raw is None:
            settings[key] = default
            continue
        try:
            settings[key] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            settings[key] = default

    socials = settings.get("socials")
    if not isinstance(socials, dict):
        socials = dict(DEFAULT_SOCIALS)
    settings["socials"] = {k: v for k, v in socials.items() if v}

    settings["skills"] = _normalise_skills(settings.get("skills"))

    return settings


def get_settings():
    """Memoised for the duration of the request."""
    if not has_app_context():
        return {"socials": dict(DEFAULT_SOCIALS), "skills": list(DEFAULT_SKILLS)}

    cached = getattr(g, _CACHE_KEY, None)
    if cached is not None:
        return cached

    settings = _read_raw()
    setattr(g, _CACHE_KEY, settings)
    return settings


def get_skills_by_category():
    """
    Group skills for the categorised tag display that replaced the
    percentage bars. Empty categories are omitted.
    """
    skills = get_settings()["skills"]

    grouped = []
    for category in SKILL_CATEGORIES:
        members = [s for s in skills if s.get("category") == category]
        if members:
            grouped.append({"category": category, "skills": members})

    return grouped


def update_settings(new_settings):
    for key, value in new_settings.items():
        if key not in DEFAULT_SETTINGS:
            continue

        if key == "skills":
            value = _normalise_skills(value)

        payload = json.dumps(value, ensure_ascii=False)

        row = db.session.get(Setting, key)
        if row is None:
            db.session.add(Setting(key=key, value=payload))
        else:
            row.value = payload

    db.session.commit()

    # Drop the request-scoped cache so the admin sees the change immediately.
    if has_app_context() and hasattr(g, _CACHE_KEY):
        delattr(g, _CACHE_KEY)

    return get_settings()
