"""
Project data access.

Backed by SQLAlchemy instead of data/projects.json. Every public function
keeps the signature and dict-returning behaviour it had before, so routes
and templates were not changed by the migration.
"""

from extensions import db
from models import Project

# Keys the admin form submits that map onto list columns.
_LIST_FIELDS = ("technologies", "features")


def _apply(project, data):
    """Copy a plain dict (as the admin routes build it) onto a Project row."""

    for field in _LIST_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, (list, tuple)):
                value = "\n".join(str(item).strip() for item in value if str(item).strip())
            setattr(project, f"{field}_raw", value or "")

    for field in (
        "title",
        "description",
        "github",
        "demo",
        "image",
        "status",
        "metric_label",
        "metric_value",
    ):
        if field in data:
            setattr(project, field, data[field] or "")

    if "year" in data:
        try:
            project.year = int(data["year"]) if data["year"] not in (None, "") else None
        except (TypeError, ValueError):
            project.year = None

    return project


def get_projects():
    """Newest first, so the portfolio leads with recent work."""
    rows = (
        Project.query
        .order_by(Project.year.desc().nullslast(), Project.id.desc())
        .all()
    )
    return [row.to_dict() for row in rows]


def get_project_by_id(project_id):
    row = db.session.get(Project, project_id)
    return row.to_dict() if row else None


def create_project(project):
    row = _apply(Project(), project)
    db.session.add(row)
    db.session.commit()
    return row.to_dict()


def update_project(project_id, updated_data):
    row = db.session.get(Project, project_id)
    if row is None:
        return None
    _apply(row, updated_data)
    db.session.commit()
    return row.to_dict()


def delete_project(project_id):
    row = db.session.get(Project, project_id)
    if row is None:
        return None
    data = row.to_dict()
    db.session.delete(row)
    db.session.commit()
    return data


def count_projects():
    return Project.query.count()
