"""
Shared helpers for the backup export/import functions in each repository.

The import functions deliberately never commit: admin/backup_service.py runs
all of them inside one transaction so a failure half-way restores nothing.
"""

from datetime import date, datetime

from extensions import db

MODES = ("merge", "replace")


def iso(value):
    return value.isoformat() if value else None


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def parse_day(value):
    return date.fromisoformat(value)


def restore_timestamps(row, item):
    for field in ("created_at", "updated_at"):
        value = parse_dt(item.get(field))
        if value is not None and hasattr(row, field):
            setattr(row, field, value)


def get_or_new(model, item, mode):
    """
    Find the row an imported item refers to, or build a new one carrying the
    exported id so ids (and therefore public URLs) survive a restore.
    """
    row_id = item.get("id")

    row = db.session.get(model, row_id) if row_id is not None and mode == "merge" else None
    if row is None:
        row = model(id=row_id)
        db.session.add(row)

    return row
