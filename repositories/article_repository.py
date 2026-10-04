"""
Article data access.

Backed by SQLAlchemy instead of data/articles.json. Signatures match the
previous JSON implementation.
"""

from extensions import db
from models import Article


def _apply(article, data):

    for field in ("title", "abstract", "authors", "file", "language", "image"):
        if field in data:
            setattr(article, field, data[field] or "")

    if "year" in data:
        try:
            article.year = int(data["year"]) if data["year"] not in (None, "") else None
        except (TypeError, ValueError):
            article.year = None

    if "views" in data and data["views"] is not None:
        try:
            article.views = int(data["views"])
        except (TypeError, ValueError):
            pass

    return article


def get_articles():
    rows = (
        Article.query
        .order_by(Article.year.desc().nullslast(), Article.id.desc())
        .all()
    )
    return [row.to_dict() for row in rows]


def get_article_by_id(article_id):
    row = db.session.get(Article, article_id)
    return row.to_dict() if row else None


def create_article(article):
    row = _apply(Article(), article)
    if row.views is None:
        row.views = 0
    db.session.add(row)
    db.session.commit()
    return row.to_dict()


def update_article(article_id, updated_data):
    row = db.session.get(Article, article_id)
    if row is None:
        return None
    _apply(row, updated_data)
    db.session.commit()
    return row.to_dict()


def delete_article(article_id):
    row = db.session.get(Article, article_id)
    if row is None:
        return None
    data = row.to_dict()
    db.session.delete(row)
    db.session.commit()
    return data


def increment_views(article_id):
    """
    Atomic increment. The JSON version did read-modify-write under a
    process-local lock, so two workers could both read `views = 5` and both
    write `6`, losing a view. This pushes the arithmetic into the database.
    """
    row = db.session.get(Article, article_id)
    if row is None:
        return None

    Article.query.filter_by(id=article_id).update(
        {Article.views: Article.views + 1},
        synchronize_session=False,
    )
    db.session.commit()
    db.session.refresh(row)
    return row.to_dict()


def count_articles():
    return Article.query.count()


def total_article_views():
    return db.session.query(db.func.coalesce(db.func.sum(Article.views), 0)).scalar() or 0
