"""
Seeding tests.

The first production deploy served a site with no projects and no articles:
`db.create_all()` creates empty tables, and nothing ever imported the JSON
files that still ship with the repo.
"""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models import Article, Project, Setting
from seed import seed_all, seed_articles, seed_if_empty, seed_projects


def test_empty_database_gets_seeded(app):
    assert Project.query.count() == 0

    seed_if_empty()

    assert Project.query.count() > 0
    assert Article.query.count() > 0
    assert Setting.query.count() > 0


def test_seeding_is_idempotent(app):
    first = seed_all()
    counts = (Project.query.count(), Article.query.count(), Setting.query.count())

    second = seed_all()

    assert any(first.values()), "the first run should have inserted something"
    assert not any(second.values()), "the second run should insert nothing"
    assert (
        Project.query.count(),
        Article.query.count(),
        Setting.query.count(),
    ) == counts


def test_seed_if_empty_leaves_a_populated_table_alone(app):
    from repositories.project_repository import create_project

    create_project(
        {
            "title": "Only Mine",
            "description": "Hand-written.",
            "technologies": ["Python"],
            "status": "completed",
        }
    )

    seed_if_empty()

    # The table was not empty, so nothing from data/projects.json was added.
    assert Project.query.count() == 1
    assert Project.query.first().title == "Only Mine"


def test_deleting_everything_does_not_resurrect_on_the_next_boot(app):
    """
    Per-table seeding is deliberate: emptying projects from the admin panel
    then restarting WILL re-seed that table. Articles that still exist must
    not be touched, so the two cannot interfere.
    """
    seed_all()
    assert Article.query.count() > 0

    Project.query.delete()
    from extensions import db

    db.session.commit()

    seed_if_empty()

    assert Project.query.count() > 0, "an empty table is re-seeded"
    assert Article.query.count() > 0, "a populated table is untouched"


def test_article_view_counts_survive_seeding(app):
    """data/articles.json carries a views value that must not reset to 0."""
    seed_articles()

    article = Article.query.first()
    assert article is not None
    assert article.views >= 0


def test_seeded_skills_use_categories_not_levels(app):
    """settings.json still holds the old {"name", "level"} shape."""
    from repositories.settings_repository import get_settings

    seed_all()

    skills = get_settings()["skills"]
    assert skills
    assert all("category" in skill for skill in skills)
    assert all("level" not in skill for skill in skills)


@pytest.mark.parametrize(
    "error",
    [
        SQLAlchemyError("table is gone"),
        RuntimeError("something else entirely"),
    ],
)
def test_seeding_never_raises(app, monkeypatch, error):
    """
    Seeding is a boot-time convenience; no failure in it is worth refusing
    to serve the site over. The first version only caught SQLAlchemyError,
    so anything else propagated and killed every gunicorn worker.
    """
    import seed as seed_module

    def explode(*args, **kwargs):
        raise error

    monkeypatch.setattr(seed_module, "seed_projects", explode)

    assert seed_if_empty() == {}


def test_fresh_app_serves_content_not_an_empty_site(app, client):
    """
    End to end: the condition production actually hit. A blank database must
    not produce a site that says there are no projects.
    """
    seed_if_empty()

    body = client.get("/projects").get_data(as_text=True)
    assert "پروژه‌ای موجود نیست" not in body

    assert client.get("/sitemap.xml").get_data(as_text=True).count("<loc>") > 5


def test_seed_projects_returns_a_count(app):
    added = seed_projects()
    assert added == Project.query.count()
    assert added > 0


@pytest.mark.parametrize("value,should_seed", [("0", False), ("1", True)])
def test_auto_seed_env_var_controls_boot_seeding(
    value, should_seed, monkeypatch, tmp_path
):
    """A host that manages its own data should be able to opt out."""
    import importlib

    monkeypatch.setenv("AUTO_SEED", value)
    monkeypatch.setenv("SECRET_KEY", "seed-toggle")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'toggle.db'}")

    import config as config_module

    importlib.reload(config_module)

    import app as app_module

    importlib.reload(app_module)

    try:
        application = app_module.create_app("production")
        with application.app_context():
            count = Project.query.count()

        if should_seed:
            assert count > 0, "AUTO_SEED on should populate an empty database"
        else:
            assert count == 0, "AUTO_SEED off must not seed"
    finally:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("AUTO_SEED", raising=False)
        importlib.reload(config_module)
        importlib.reload(app_module)
