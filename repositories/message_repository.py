"""
Contact message data access.

Backed by SQLAlchemy instead of data/messages.json. This is the most
important one to have moved off a JSON file: the contact form is the only
public write path, so it was the most exposed to the lost-write race.
"""

from extensions import db
from models import ContactMessage

from ._backup import get_or_new, iso, restore_timestamps


def get_messages():
    """Newest first — the admin inbox wants the latest message on top."""
    rows = ContactMessage.query.order_by(ContactMessage.id.desc()).all()
    return [row.to_dict() for row in rows]


def get_message_by_id(message_id):
    row = db.session.get(ContactMessage, message_id)
    return row.to_dict() if row else None


def create_message(name, email, body):
    row = ContactMessage(name=name, email=email, message=body, read=False)
    db.session.add(row)
    db.session.commit()
    return row.to_dict()


def set_read(message_id, read=True):
    row = db.session.get(ContactMessage, message_id)
    if row is None:
        return None
    row.read = bool(read)
    db.session.commit()
    return row.to_dict()


def delete_message(message_id):
    row = db.session.get(ContactMessage, message_id)
    if row is None:
        return None
    data = row.to_dict()
    db.session.delete(row)
    db.session.commit()
    return data


def count_messages():
    return ContactMessage.query.count()


def count_unread():
    """
    Counted in SQL rather than by loading every message and summing in
    Python, which the admin context processor did on every single request.
    """
    return ContactMessage.query.filter_by(read=False).count()


# --- Backup -----------------------------------------------------------


def export_messages():
    rows = ContactMessage.query.order_by(ContactMessage.id).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "message": row.message,
            "read": bool(row.read),
            "created_at": iso(row.created_at),
        }
        for row in rows
    ]


def import_messages(rows, mode="merge"):
    """Does not commit — see repositories/_backup.py."""
    if mode == "replace":
        ContactMessage.query.delete()

    for item in rows:
        row = get_or_new(ContactMessage, item, mode)
        row.name = item["name"]
        row.email = item["email"]
        row.message = item["message"]
        row.read = bool(item.get("read"))
        restore_timestamps(row, item)

    db.session.flush()
    return len(rows)
