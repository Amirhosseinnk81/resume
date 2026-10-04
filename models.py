"""
SQLAlchemy models.

Replaces the previous data/*.json storage. The JSON approach had two real
problems the repository layer could not paper over:

  1. `threading.Lock` only serialises writes *inside one process*. Under any
     real deployment (gunicorn/waitress with >1 worker) two workers could
     read-modify-write the same file concurrently and silently lose a record.
  2. Writes went straight to the destination file with no atomic rename and
     no fsync, so an interrupted write left a truncated, unparseable JSON
     file — losing every project at once.

The repository functions keep their exact previous signatures and still
return plain dicts, so routes and templates did not need to change.
"""

from datetime import UTC, datetime

from extensions import db


def _utcnow():
    return datetime.now(UTC)


class Project(db.Model):

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")

    # Optional English variants. The site is bilingual, but project and
    # article text lived only in Persian, so the English site still showed
    # Persian content. Empty means "fall back to the Persian value", so
    # filling these in is incremental rather than all-or-nothing.
    title_en = db.Column(db.String(200), default="")
    description_en = db.Column(db.Text, default="")

    # Previously JSON arrays inside the document. Kept as newline-delimited
    # text and exposed as lists by to_dict(), which keeps the template API
    # (`project.technologies`) identical.
    technologies_raw = db.Column("technologies", db.Text, default="")
    features_raw = db.Column("features", db.Text, default="")

    github = db.Column(db.String(500), default="")
    demo = db.Column(db.String(500), default="")
    image = db.Column(db.String(300), default="")
    status = db.Column(db.String(50), default="completed")
    year = db.Column(db.Integer)

    # New: lets the portfolio show a real metric per project the way
    # brittanychiang.com does ("8,281 stars", "100k+ installs") instead of
    # description text alone.
    metric_label = db.Column(db.String(100), default="")
    metric_value = db.Column(db.String(100), default="")

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    @staticmethod
    def _split(raw):
        if not raw:
            return []
        return [part.strip() for part in raw.split("\n") if part.strip()]

    @property
    def technologies(self):
        return self._split(self.technologies_raw)

    @property
    def features(self):
        return self._split(self.features_raw)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_en": self.title_en or "",
            "description": self.description or "",
            "description_en": self.description_en or "",
            "technologies": self.technologies,
            "features": self.features,
            "github": self.github or "",
            "demo": self.demo or "",
            "image": self.image or "",
            "status": self.status or "",
            "year": self.year,
            "metric_label": self.metric_label or "",
            "metric_value": self.metric_value or "",
            "updated_at": self.updated_at,
        }


class Article(db.Model):

    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    abstract = db.Column(db.Text, default="")
    authors = db.Column(db.String(300), default="")

    # See Project.title_en.
    title_en = db.Column(db.String(300), default="")
    abstract_en = db.Column(db.Text, default="")
    authors_en = db.Column(db.String(300), default="")
    year = db.Column(db.Integer)
    file = db.Column(db.String(500), default="")
    language = db.Column(db.String(10), default="fa")
    image = db.Column(db.String(300), default="")
    views = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_en": self.title_en or "",
            "abstract": self.abstract or "",
            "abstract_en": self.abstract_en or "",
            "authors": self.authors or "",
            "authors_en": self.authors_en or "",
            "year": self.year,
            "file": self.file or "",
            "language": self.language or "fa",
            "image": self.image or "",
            "views": self.views or 0,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ContactMessage(db.Model):

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(300), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        created = self.created_at
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "read": bool(self.read),
            # Templates previously received the ISO string the JSON file held.
            "created_at": created.isoformat(timespec="seconds") if created else "",
            "created_at_dt": created,
        }


class Setting(db.Model):
    """
    Key/value store for the editable site settings (socials, skills) that
    used to live in data/settings.json. Values are JSON-encoded text.
    """

    __tablename__ = "settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)


class PageView(db.Model):
    """
    Minimal, privacy-preserving hit counter.

    The admin dashboard previously reported a hardcoded `"visitors": 0` that
    was never incremented. This stores one row per path per day with a count
    — no IP addresses, no user agents, no cookies, so nothing here is
    personal data.
    """

    __tablename__ = "page_views"
    __table_args__ = (
        db.UniqueConstraint("path", "day", name="uq_pageview_path_day"),
        db.Index("ix_pageview_day", "day"),
    )

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(300), nullable=False)
    day = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
