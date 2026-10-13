"""Admin create/edit/delete flows through the new Flask-WTF forms."""

import io
import os


def test_login_then_dashboard(auth_client):
    assert auth_client.get("/admin/").status_code == 200


def test_create_project(auth_client):
    response = auth_client.post(
        "/admin/projects/create",
        data={
            "title": "New Project",
            "description": "Created in a test.",
            "technologies": "Python، Flask، SQLAlchemy",
            "features": "A، B",
            "status": "completed",
            "year": "2026",
            "github": "https://github.com/example/new",
        },
    )
    assert response.status_code == 302

    from repositories.project_repository import get_projects

    projects = get_projects()
    created = next(p for p in projects if p["title"] == "New Project")

    # The Persian comma must split as well as the ASCII one.
    assert created["technologies"] == ["Python", "Flask", "SQLAlchemy"]


def test_create_project_rejects_missing_title(auth_client):
    response = auth_client.post(
        "/admin/projects/create",
        data={
            "description": "no title",
            "technologies": "Python",
            "status": "completed",
        },
    )
    assert response.status_code == 200  # re-renders with errors

    from repositories.project_repository import get_projects

    assert get_projects() == []


def test_create_project_rejects_bad_year(auth_client):
    response = auth_client.post(
        "/admin/projects/create",
        data={
            "title": "T",
            "description": "D",
            "technologies": "Python",
            "status": "completed",
            "year": "not-a-year",
        },
    )
    assert response.status_code == 200

    from repositories.project_repository import get_projects

    assert get_projects() == []


def test_create_project_rejects_invalid_status(auth_client):
    response = auth_client.post(
        "/admin/projects/create",
        data={
            "title": "T",
            "description": "D",
            "technologies": "Python",
            "status": "something-else",
        },
    )
    assert response.status_code == 200

    from repositories.project_repository import get_projects

    assert get_projects() == []


def test_edit_project(auth_client, sample_project):
    response = auth_client.post(
        "/admin/projects/{}/edit".format(sample_project["id"]),
        data={
            "title": "Renamed",
            "description": "Edited.",
            "technologies": "Python",
            "status": "in-progress",
            "year": "2025",
        },
    )
    assert response.status_code == 302

    from repositories.project_repository import get_project_by_id

    updated = get_project_by_id(sample_project["id"])
    assert updated["title"] == "Renamed"
    assert updated["status"] == "in-progress"


def test_delete_project(auth_client, sample_project):
    response = auth_client.post(
        "/admin/projects/{}/delete".format(sample_project["id"])
    )
    assert response.status_code == 302

    from repositories.project_repository import get_project_by_id

    assert get_project_by_id(sample_project["id"]) is None


def test_edit_missing_project_returns_404(auth_client):
    assert auth_client.get("/admin/projects/9999/edit").status_code == 404


def test_create_article_with_pdf(auth_client, app):
    response = auth_client.post(
        "/admin/articles/create",
        data={
            "title": "Uploaded Article",
            "abstract": "With a PDF.",
            "year": "2026",
            "language": "fa",
            "file": (io.BytesIO(b"%PDF-1.4 fake"), "my paper.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    from repositories.article_repository import get_articles

    stored = next(a for a in get_articles() if a["title"] == "Uploaded Article")

    # A random prefix is applied so two uploads cannot collide.
    assert stored["file"] != "my paper.pdf"
    assert stored["file"].endswith(".pdf")
    assert os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], stored["file"]))


def test_create_article_rejects_non_pdf(auth_client):
    response = auth_client.post(
        "/admin/articles/create",
        data={
            "title": "Bad Upload",
            "abstract": "Not a PDF.",
            "file": (io.BytesIO(b"<script>"), "evil.html"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200

    from repositories.article_repository import get_articles

    assert get_articles() == []


def test_create_article_requires_a_file(auth_client):
    response = auth_client.post(
        "/admin/articles/create",
        data={"title": "No File", "abstract": "Missing PDF."},
    )
    assert response.status_code == 200

    from repositories.article_repository import get_articles

    assert get_articles() == []


def test_edit_article_without_reupload_keeps_file(auth_client, sample_article):
    response = auth_client.post(
        "/admin/articles/{}/edit".format(sample_article["id"]),
        data={"title": "Edited Title", "abstract": "Still here.", "language": "fa"},
    )
    assert response.status_code == 302

    from repositories.article_repository import get_article_by_id

    updated = get_article_by_id(sample_article["id"])
    assert updated["title"] == "Edited Title"
    assert updated["file"] == sample_article["file"]


def test_delete_article_also_removes_its_pdf(auth_client, app):
    auth_client.post(
        "/admin/articles/create",
        data={
            "title": "Doomed",
            "abstract": "Will be deleted.",
            "file": (io.BytesIO(b"%PDF-1.4"), "doomed.pdf"),
        },
        content_type="multipart/form-data",
    )

    from repositories.article_repository import get_articles

    article = next(a for a in get_articles() if a["title"] == "Doomed")
    path = os.path.join(app.config["UPLOAD_FOLDER"], article["file"])
    assert os.path.isfile(path)

    auth_client.post("/admin/articles/{}/delete".format(article["id"]))

    # The orphaned PDF used to be left on disk forever.
    assert not os.path.exists(path)


def test_settings_update_saves_skills_as_categories(auth_client):
    response = auth_client.post(
        "/admin/settings",
        data={
            "github": "https://github.com/someone",
            "linkedin": "",
            "twitter": "",
            "skills-0-name": "Rust",
            "skills-0-category": "languages",
            "skills-1-name": "Redis",
            "skills-1-category": "databases",
        },
    )
    assert response.status_code == 302

    from repositories.settings_repository import get_settings

    skills = get_settings()["skills"]
    assert {"name": "Rust", "category": "languages"} in skills
    assert {"name": "Redis", "category": "databases"} in skills

    # No percentage level survives the migration.
    assert all("level" not in s for s in skills)


def test_settings_rejects_invalid_url(auth_client):
    response = auth_client.post(
        "/admin/settings",
        data={"github": "not a url", "linkedin": "", "twitter": ""},
    )
    assert response.status_code == 200


def test_message_read_toggle_and_delete(auth_client):
    from repositories.message_repository import create_message, get_message_by_id

    message = create_message("Tester", "t@example.com", "Hello")

    auth_client.post("/admin/messages/{}/read".format(message["id"]))
    assert get_message_by_id(message["id"])["read"] is True

    auth_client.post("/admin/messages/{}/read".format(message["id"]))
    assert get_message_by_id(message["id"])["read"] is False

    auth_client.post("/admin/messages/{}/delete".format(message["id"]))
    assert get_message_by_id(message["id"]) is None
