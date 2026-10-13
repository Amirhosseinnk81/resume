"""
Repository-layer tests.

These assert the contract the routes and templates rely on: every function
returns plain dicts with the same keys the JSON implementation produced, so
the storage swap was invisible above this layer.
"""

from repositories.article_repository import (
    create_article,
    delete_article,
    get_article_by_id,
    get_articles,
    increment_views,
    total_article_views,
    update_article,
)
from repositories.message_repository import (
    count_unread,
    create_message,
    delete_message,
    get_messages,
    set_read,
)
from repositories.project_repository import (
    create_project,
    delete_project,
    get_project_by_id,
    get_projects,
    update_project,
)
from repositories.settings_repository import (
    get_settings,
    get_skills_by_category,
    update_settings,
)

# --- Projects ---------------------------------------------------------


def test_project_roundtrip_preserves_list_fields(app):
    created = create_project(
        {
            "title": "P",
            "description": "D",
            "technologies": ["Python", "Flask"],
            "features": ["One", "Two"],
            "status": "completed",
            "year": 2026,
        }
    )

    fetched = get_project_by_id(created["id"])
    assert fetched["technologies"] == ["Python", "Flask"]
    assert fetched["features"] == ["One", "Two"]


def test_projects_are_newest_first(app):
    create_project({"title": "Old", "description": "", "technologies": [], "year": 2020})
    create_project({"title": "New", "description": "", "technologies": [], "year": 2026})

    assert [p["title"] for p in get_projects()] == ["New", "Old"]


def test_project_without_year_still_lists(app):
    """nullslast() must not drop rows with no year."""
    create_project({"title": "Dated", "description": "", "technologies": [], "year": 2024})
    create_project({"title": "Undated", "description": "", "technologies": []})

    titles = [p["title"] for p in get_projects()]
    assert set(titles) == {"Dated", "Undated"}


def test_update_missing_project_returns_none(app):
    assert update_project(9999, {"title": "x"}) is None


def test_delete_missing_project_returns_none(app):
    assert delete_project(9999) is None


def test_update_project_does_not_change_id(app):
    created = create_project({"title": "A", "description": "", "technologies": []})
    updated = update_project(created["id"], {"title": "B", "technologies": []})
    assert updated["id"] == created["id"]


# --- Articles ---------------------------------------------------------


def test_increment_views_is_additive(app):
    article = create_article({"title": "A", "abstract": "", "file": "a.pdf"})
    assert article["views"] == 0

    for expected in (1, 2, 3):
        assert increment_views(article["id"])["views"] == expected


def test_increment_views_on_missing_article_returns_none(app):
    assert increment_views(9999) is None


def test_update_article_preserves_views(app):
    article = create_article({"title": "A", "abstract": "", "file": "a.pdf"})
    increment_views(article["id"])
    increment_views(article["id"])

    update_article(article["id"], {"title": "Renamed", "abstract": ""})

    assert get_article_by_id(article["id"])["views"] == 2


def test_total_article_views_sums(app):
    first = create_article({"title": "A", "abstract": "", "file": "a.pdf"})
    second = create_article({"title": "B", "abstract": "", "file": "b.pdf"})

    increment_views(first["id"])
    increment_views(second["id"])
    increment_views(second["id"])

    assert total_article_views() == 3


def test_delete_article_returns_the_deleted_row(app):
    article = create_article({"title": "Gone", "abstract": "", "file": "g.pdf"})
    deleted = delete_article(article["id"])

    assert deleted["title"] == "Gone"
    assert deleted["file"] == "g.pdf"
    assert get_articles() == []


# --- Messages ---------------------------------------------------------


def test_message_created_at_is_a_string_for_templates(app):
    message = create_message("N", "e@example.com", "Body")
    assert isinstance(message["created_at"], str)
    assert "T" in message["created_at"]


def test_unread_count(app):
    first = create_message("A", "a@example.com", "1")
    create_message("B", "b@example.com", "2")

    assert count_unread() == 2

    set_read(first["id"], True)
    assert count_unread() == 1


def test_messages_are_newest_first(app):
    create_message("First", "a@example.com", "1")
    create_message("Second", "b@example.com", "2")

    assert [m["name"] for m in get_messages()] == ["Second", "First"]


def test_delete_missing_message_returns_none(app):
    assert delete_message(9999) is None


# --- Settings ---------------------------------------------------------


def test_settings_fall_back_to_defaults(app):
    settings = get_settings()
    assert "socials" in settings
    assert settings["skills"], "defaults should not be empty"


def test_legacy_level_skills_are_migrated_to_categories(app):
    """
    An existing settings row (or a hand-edited settings.json) still uses
    {"name", "level"}. Reading must convert it, not crash or drop it.
    """
    update_settings(
        {
            "skills": [
                {"name": "Python", "level": 75},
                {"name": "Flask", "level": 55},
            ]
        }
    )

    skills = get_settings()["skills"]
    names = {s["name"] for s in skills}

    assert names == {"Python", "Flask"}
    assert all("category" in s for s in skills)
    assert all("level" not in s for s in skills)
    # Known skills land in their real category, not the fallback.
    assert next(s for s in skills if s["name"] == "Python")["category"] == "languages"


def test_unknown_skill_category_falls_back_to_tools(app):
    update_settings({"skills": [{"name": "Nmap", "category": "nonsense"}]})
    skills = get_settings()["skills"]
    assert skills[0]["category"] == "tools"


def test_skills_grouped_omits_empty_categories(app):
    update_settings({"skills": [{"name": "Python", "category": "languages"}]})

    groups = get_skills_by_category()
    assert [g["category"] for g in groups] == ["languages"]


def test_settings_ignores_unknown_keys(app):
    update_settings({"not_a_setting": "x"})
    assert "not_a_setting" not in get_settings()


def test_settings_cache_is_invalidated_on_write(app):
    """
    get_settings() memoises per request; a write in the same request must
    not keep serving the stale value.
    """
    with app.test_request_context("/"):
        first = get_settings()["socials"].get("github")
        update_settings({"socials": {"github": "https://github.com/changed"}})
        second = get_settings()["socials"].get("github")

    assert second == "https://github.com/changed"
    assert second != first
