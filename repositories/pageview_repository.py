"""
Page-view counting.

The admin dashboard previously showed a hardcoded `"visitors": 0`. This
stores an aggregate count per (path, day) — no IPs, no user agents, no
cookies, so there is nothing personally identifying to protect.
"""

from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import PageView


def record_view(path):
    """
    Increment today's counter for `path`.

    Uses an UPDATE-first strategy so the common case is a single statement
    and concurrent requests cannot lose a count. The INSERT is retried once
    behind a savepoint because two workers can race to create the same row.
    """
    today = date.today()

    updated = (
        PageView.query
        .filter_by(path=path, day=today)
        .update({PageView.count: PageView.count + 1}, synchronize_session=False)
    )

    if not updated:
        try:
            with db.session.begin_nested():
                db.session.add(PageView(path=path, day=today, count=1))
        except IntegrityError:
            # Another worker created the row first — increment it instead.
            (
                PageView.query
                .filter_by(path=path, day=today)
                .update({PageView.count: PageView.count + 1}, synchronize_session=False)
            )

    db.session.commit()


def total_views():
    return db.session.query(
        db.func.coalesce(db.func.sum(PageView.count), 0)
    ).scalar() or 0


def views_since(days=30):
    cutoff = date.today() - timedelta(days=days)
    return db.session.query(
        db.func.coalesce(db.func.sum(PageView.count), 0)
    ).filter(PageView.day >= cutoff).scalar() or 0


def top_pages(limit=5):
    rows = (
        db.session.query(
            PageView.path,
            db.func.sum(PageView.count).label("total"),
        )
        .group_by(PageView.path)
        .order_by(db.desc("total"))
        .limit(limit)
        .all()
    )
    return [{"path": path, "views": int(total)} for path, total in rows]


def daily_series(days=14):
    """Per-day totals for the dashboard sparkline, zero-filled."""
    cutoff = date.today() - timedelta(days=days - 1)

    rows = dict(
        db.session.query(PageView.day, db.func.sum(PageView.count))
        .filter(PageView.day >= cutoff)
        .group_by(PageView.day)
        .all()
    )

    series = []
    for offset in range(days):
        day = cutoff + timedelta(days=offset)
        series.append({"day": day.isoformat(), "views": int(rows.get(day, 0))})

    return series
