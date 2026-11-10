"""
Backup export / import tests.

The container filesystem is rebuilt on every deploy, so this archive is the
only way the admin's content survives one. These tests pin the two things
that matter most: a restore gives back exactly what was exported, and a bad
archive changes nothing at all.
"""

import io
import json
import os
import zipfile
from datetime import date

import pytest

from admin import backup_service
from models import Article, ContactMessage, PageView, Project, Setting
from repositories.article_repository import create_article, get_articles
from repositories.message_repository import create_message
from repositories.project_repository import create_project, get_projects
from repositories.settings_repository import get_settings, update_settings
from seed import seed_if_empty

PDF_BYTES = b"%PDF-1.4 backup test"
SKILLS = [{"name": "Rust", "category": "languages"}]
APPEARANCE = {"default_lang": "en", "default_theme": "dark"}


@pytest.fixture(autouse=True)
def resume_path(tmp_path, monkeypatch):
    """Keep the routes away from the real myresume.pdf in the repo root."""
    path = str(tmp_path / "myresume.pdf")
    monkeypatch.setattr("admin.routes._resume_path", lambda: path)
    return path


@pytest.fixture
def populated(app, db):
    """One of everything, including a PDF on disk and a stray one."""
    upload_folder = app.config["UPLOAD_FOLDER"]

    with open(os.path.join(upload_folder, "paper.pdf"), "wb") as handle:
        handle.write(PDF_BYTES)
    with open(os.path.join(upload_folder, "orphan.pdf"), "wb") as handle:
        handle.write(b"not attached to any article")

    create_project(
        {
            "title": "Backup Project",
            "description": "desc",
            "technologies": ["Python", "Flask"],
            "features": ["one"],
            "status": "completed",
            "year": 2026,
        }
    )
    create_article(
        {
            "title": "Backup Article",
            "abstract": "abstract",
            "authors": "Tester",
            "year": 2025,
            "file": "paper.pdf",
            "views": 42,
        }
    )
    update_settings(
        {
            "socials": {"github": "https://github.com/x"},
            "skills": SKILLS,
            "appearance": APPEARANCE,
        }
    )
    create_message("Sara", "sara@example.com", "a private message")

    db.session.add(PageView(path="/", day=date(2026, 11, 1), count=7))
    db.session.commit()


def export(app, resume_path, **kwargs):
    return backup_service.build_export(app.config["UPLOAD_FOLDER"], resume_path, **kwargs)


def restore(app, resume_path, payload, **kwargs):
    return backup_service.import_backup(
        io.BytesIO(payload), app.config["UPLOAD_FOLDER"], resume_path, **kwargs
    )


def wipe(app, db):
    for model in (Project, Article, Setting, PageView, ContactMessage):
        model.query.delete()
    db.session.commit()

    for name in os.listdir(app.config["UPLOAD_FOLDER"]):
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], name))


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def valid_data(**overrides):
    data = {
        "schema_version": backup_service.SCHEMA_VERSION,
        "projects": [{"id": 1, "title": "From Archive", "technologies": [], "features": []}],
        "articles": [],
        "settings": {},
        "pageviews": [],
    }
    data.update(overrides)
    return json.dumps(data)


def snapshot(app):
    return (
        Project.query.count(),
        Article.query.count(),
        Setting.query.count(),
        PageView.query.count(),
        ContactMessage.query.count(),
        sorted(os.listdir(app.config["UPLOAD_FOLDER"])),
    )


# --- Round trip -------------------------------------------------------


def test_round_trip_restores_the_same_data(app, db, populated, resume_path):
    with open(resume_path, "wb") as handle:
        handle.write(b"%PDF resume")

    projects_before = get_projects()
    payload = export(app, resume_path, include_messages=True)

    wipe(app, db)
    os.remove(resume_path)
    restore(app, resume_path, payload, mode="replace")

    assert get_projects() == projects_before

    article = get_articles()[0]
    assert article["title"] == "Backup Article"
    assert article["views"] == 42

    # The PDF came back, under whatever name the sanitiser gave it.
    stored = os.path.join(app.config["UPLOAD_FOLDER"], article["file"])
    with open(stored, "rb") as handle:
        assert handle.read() == PDF_BYTES

    assert get_settings()["skills"] == SKILLS
    assert get_settings()["socials"] == {"github": "https://github.com/x"}
    assert get_settings()["appearance"] == APPEARANCE

    view = PageView.query.one()
    assert (view.path, view.day, view.count) == ("/", date(2026, 11, 1), 7)

    assert ContactMessage.query.one().email == "sara@example.com"

    with open(resume_path, "rb") as handle:
        assert handle.read() == b"%PDF resume"


def test_export_only_includes_pdfs_attached_to_an_article(app, populated, resume_path):
    names = zipfile.ZipFile(io.BytesIO(export(app, resume_path))).namelist()

    assert "uploads/articles/paper.pdf" in names
    assert "uploads/articles/orphan.pdf" not in names


def test_seed_if_empty_does_not_overwrite_an_import(app, db, populated, resume_path):
    payload = export(app, resume_path)
    wipe(app, db)
    restore(app, resume_path, payload, mode="replace")

    assert seed_if_empty() == {}

    assert [project["title"] for project in get_projects()] == ["Backup Project"]
    assert [article["title"] for article in get_articles()] == ["Backup Article"]
    assert get_settings()["skills"] == SKILLS


# --- Merge / replace --------------------------------------------------


def test_merge_does_not_duplicate_rows(app, populated, resume_path):
    payload = export(app, resume_path, include_messages=True)
    before = snapshot(app)[:5]

    restore(app, resume_path, payload, mode="merge")
    restore(app, resume_path, payload, mode="merge")

    assert snapshot(app)[:5] == before
    # The article's PDF was replaced, not accumulated.
    assert len(os.listdir(app.config["UPLOAD_FOLDER"])) == 2  # paper + orphan


def test_merge_keeps_rows_missing_from_the_archive(app, populated, resume_path):
    payload = export(app, resume_path)
    create_project({"title": "Added Later", "description": "", "technologies": []})

    restore(app, resume_path, payload, mode="merge")

    assert {project["title"] for project in get_projects()} == {
        "Backup Project",
        "Added Later",
    }


def test_replace_removes_previous_rows(app, populated, resume_path):
    payload = export(app, resume_path)
    create_project({"title": "Added Later", "description": "", "technologies": []})

    restore(app, resume_path, payload, mode="replace")

    assert [project["title"] for project in get_projects()] == ["Backup Project"]


def test_replace_only_touches_selected_tables(app, populated, resume_path):
    payload = make_zip({"data.json": valid_data()})

    restore(app, resume_path, payload, mode="replace", tables=["projects"])

    assert [project["title"] for project in get_projects()] == ["From Archive"]
    assert Article.query.count() == 1
    assert PageView.query.count() == 1


# --- Access control ---------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/admin/backup"), ("post", "/admin/backup/export"), ("post", "/admin/backup/import")],
)
def test_backup_routes_require_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_backup_routes_reject_a_missing_csrf_token(app, auth_client, populated):
    app.config["WTF_CSRF_ENABLED"] = True
    before = snapshot(app)

    export_response = auth_client.post("/admin/backup/export")
    import_response = auth_client.post(
        "/admin/backup/import",
        data={
            "archive": (io.BytesIO(make_zip({"data.json": valid_data()})), "backup.zip"),
            "mode": "replace",
            "tables": ["projects"],
            "confirm_replace": "y",
        },
        content_type="multipart/form-data",
    )

    assert export_response.status_code == 400
    assert import_response.status_code == 400
    assert snapshot(app) == before


def test_import_is_post_only(auth_client):
    assert auth_client.get("/admin/backup/import").status_code == 405


def test_backup_through_the_admin_routes(app, db, auth_client, populated):
    assert auth_client.get("/admin/backup").status_code == 200

    response = auth_client.post("/admin/backup/export")
    assert response.status_code == 200
    assert response.mimetype == "application/zip"

    wipe(app, db)

    response = auth_client.post(
        "/admin/backup/import",
        data={
            "archive": (io.BytesIO(response.data), "backup.zip"),
            "mode": "replace",
            "tables": ["projects", "articles", "settings", "pageviews", "messages"],
            "confirm_replace": "y",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert [project["title"] for project in get_projects()] == ["Backup Project"]
    assert get_articles()[0]["views"] == 42


def test_replace_needs_explicit_confirmation(app, auth_client, populated):
    before = snapshot(app)

    response = auth_client.post(
        "/admin/backup/import",
        data={
            "archive": (io.BytesIO(make_zip({"data.json": valid_data()})), "backup.zip"),
            "mode": "replace",
            "tables": ["projects"],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200  # re-renders the form
    assert snapshot(app) == before


# --- Hostile or broken archives ---------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        {"../evil.pdf": PDF_BYTES},
        {"uploads/articles/../../evil.pdf": PDF_BYTES},
        {"/etc/evil.pdf": PDF_BYTES},
        {"uploads\\articles\\..\\evil.pdf": PDF_BYTES},
        {"uploads/articles/shell.py": b"print('x')"},
        {"notes.txt": b"hello"},
    ],
)
def test_unsafe_archives_are_rejected_untouched(app, populated, resume_path, tmp_path, extra):
    before = snapshot(app)
    files_before = sorted(str(path) for path in tmp_path.rglob("*"))

    with pytest.raises(backup_service.BackupError):
        restore(app, resume_path, make_zip({"data.json": valid_data(), **extra}), mode="replace")

    assert snapshot(app) == before
    assert sorted(str(path) for path in tmp_path.rglob("*")) == files_before


@pytest.mark.parametrize(
    "data",
    [
        "{not json",
        valid_data(schema_version=999),
        json.dumps({"projects": []}),
        valid_data(projects="nope"),
        valid_data(projects=[{"title": ""}]),
        valid_data(pageviews=[{"path": "/", "day": "yesterday", "count": 1}]),
        valid_data(articles=[{"title": "x", "views": "many"}]),
    ],
)
def test_invalid_data_leaves_the_database_untouched(app, populated, resume_path, data):
    before = snapshot(app)

    with pytest.raises(backup_service.BackupError):
        restore(app, resume_path, make_zip({"data.json": data}), mode="replace")

    assert snapshot(app) == before
    assert [project["title"] for project in get_projects()] == ["Backup Project"]


def test_a_database_error_rolls_everything_back(app, populated, resume_path):
    """
    Valid archive, but two rows share an id: the projects are already
    deleted and the article PDF already written by the time it fails.
    """
    before = snapshot(app)
    data = valid_data(
        articles=[{"id": 5, "title": "With File", "file": "new.pdf", "views": 1}],
        pageviews=[
            {"path": "/", "day": "2026-01-01", "count": 1},
            {"path": "/a", "day": "2026-01-01", "count": 1},
        ],
        messages=[
            {"id": 9, "name": "a", "email": "a@b.co", "message": "m"},
            {"id": 9, "name": "b", "email": "b@b.co", "message": "m"},
        ],
    )
    payload = make_zip({"data.json": data, "uploads/articles/new.pdf": PDF_BYTES})

    with pytest.raises(backup_service.BackupError):
        restore(app, resume_path, payload, mode="replace")

    assert snapshot(app) == before
    assert [project["title"] for project in get_projects()] == ["Backup Project"]


def test_not_a_zip_is_rejected(app, resume_path):
    with pytest.raises(backup_service.BackupError):
        restore(app, resume_path, b"definitely not a zip")


def test_oversized_archives_are_rejected(app, resume_path, monkeypatch):
    monkeypatch.setattr(backup_service, "MAX_TOTAL_BYTES", 10)

    with pytest.raises(backup_service.BackupError):
        restore(app, resume_path, make_zip({"data.json": valid_data()}))

    monkeypatch.setattr(backup_service, "MAX_TOTAL_BYTES", 50 * 1024 * 1024)
    monkeypatch.setattr(backup_service, "MAX_FILES", 1)

    with pytest.raises(backup_service.BackupError):
        restore(
            app,
            resume_path,
            make_zip({"data.json": valid_data(), "uploads/articles/a.pdf": PDF_BYTES}),
        )


# --- Privacy ----------------------------------------------------------


def test_export_contains_no_secrets(app, populated, resume_path):
    archive = zipfile.ZipFile(io.BytesIO(export(app, resume_path, include_messages=True)))
    text = archive.read("data.json").decode("utf-8")

    for key in ("SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD_HASH", "MAIL_PASSWORD"):
        assert key not in text
        value = app.config.get(key)
        if value:
            assert str(value) not in text

    assert set(json.loads(text)) == {
        "schema_version",
        "exported_at",
        "projects",
        "articles",
        "settings",
        "pageviews",
        "messages",
    }


def test_messages_are_left_out_unless_asked_for(app, populated, resume_path):
    archive = zipfile.ZipFile(io.BytesIO(export(app, resume_path)))
    text = archive.read("data.json").decode("utf-8")

    assert "messages" not in json.loads(text)
    assert "sara@example.com" not in text
