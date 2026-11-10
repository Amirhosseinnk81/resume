"""
Article cover images uploaded from the admin.

Covers used to be a filename typed by hand that had to already exist under
static/images. They are now uploaded like the PDF, which makes the upload
a security boundary: only real images are stored, under an extension taken
from their content rather than from the uploaded name.
"""

import io
import json
import os
import zipfile

import pytest
from flask import url_for
from PIL import Image

from admin import backup_service
from repositories.article_repository import create_article, get_article_by_id, get_articles

PDF = (b"%PDF-1.4 fake", "paper.pdf")


def png_bytes(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, "PNG")
    return buffer.getvalue()


def image_path(app, name):
    return os.path.join(app.config["ARTICLE_IMAGE_FOLDER"], name)


def stored_images(app):
    folder = app.config["ARTICLE_IMAGE_FOLDER"]
    return os.listdir(folder) if os.path.isdir(folder) else []


def create(auth_client, **files):
    data = {"title": "With Cover", "abstract": "Has an image.", "language": "fa"}
    for key, (payload, name) in {"file": PDF, **files}.items():
        data[key] = (io.BytesIO(payload), name)
    return auth_client.post("/admin/articles/create", data=data, content_type="multipart/form-data")


def edit(auth_client, article_id, **extra):
    data = {"title": "With Cover", "abstract": "Has an image.", "language": "fa"}
    for key, value in extra.items():
        data[key] = (io.BytesIO(value[0]), value[1]) if isinstance(value, tuple) else value
    return auth_client.post(
        f"/admin/articles/{article_id}/edit", data=data, content_type="multipart/form-data"
    )


@pytest.fixture
def article_with_cover(app, auth_client):
    assert create(auth_client, image_file=(png_bytes(), "جلد مقاله.png")).status_code == 302
    return get_articles()[0]


# --- Upload -----------------------------------------------------------


def test_cover_is_stored_and_shown(app, client, article_with_cover):
    name = article_with_cover["image"]

    assert name.endswith(".png") and name != "جلد مقاله.png"
    assert os.path.isfile(image_path(app, name))

    html = client.get(f"/articles/{article_with_cover['id']}").get_data(as_text=True)
    with app.test_request_context():
        assert url_for("article_image", filename=name) in html

    response = client.get(f"/articles/images/{name}")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_extension_comes_from_the_content(app, auth_client):
    """A PNG uploaded as .jpg is stored as .png."""
    create(auth_client, image_file=(png_bytes(), "cover.jpg"))

    assert get_articles()[0]["image"].endswith(".png")


@pytest.mark.parametrize(
    ("payload", "name"),
    [
        (b"<script>alert(1)</script>", "cover.png"),  # not an image at all
        (png_bytes(), "cover.svg"),  # extension not allowed
        (b"GIF89a but not really", "cover.gif"),
    ],
)
def test_bad_images_are_rejected_and_nothing_is_kept(app, auth_client, payload, name):
    response = create(auth_client, image_file=(payload, name))

    assert response.status_code == 200
    assert get_articles() == []
    assert not os.listdir(app.config["UPLOAD_FOLDER"])
    assert stored_images(app) == []


def test_a_bad_pdf_does_not_leave_the_cover_behind(app, auth_client):
    response = create(
        auth_client,
        file=(b"<html>", "evil.html"),
        image_file=(png_bytes(), "cover.png"),
    )

    assert response.status_code == 200
    assert get_articles() == []
    assert stored_images(app) == []


def test_oversized_image_is_rejected(app, auth_client, monkeypatch):
    monkeypatch.setattr("admin.utils.MAX_IMAGE_BYTES", 10)

    assert create(auth_client, image_file=(png_bytes(), "cover.png")).status_code == 200
    assert get_articles() == []


def test_article_without_cover_still_works(app, auth_client):
    assert create(auth_client).status_code == 302
    assert get_articles()[0]["image"] == ""


# --- Edit / delete ----------------------------------------------------


def test_editing_without_a_new_image_keeps_the_cover(app, auth_client, article_with_cover):
    edit(auth_client, article_with_cover["id"])

    assert get_article_by_id(article_with_cover["id"])["image"] == article_with_cover["image"]
    assert os.path.isfile(image_path(app, article_with_cover["image"]))


def test_replacing_the_cover_deletes_the_old_file(app, auth_client, article_with_cover):
    old = article_with_cover["image"]

    edit(auth_client, article_with_cover["id"], image_file=(png_bytes("blue"), "new.png"))

    new = get_article_by_id(article_with_cover["id"])["image"]
    assert new != old
    assert os.path.isfile(image_path(app, new))
    assert not os.path.exists(image_path(app, old))


def test_remove_image_clears_the_cover(app, auth_client, article_with_cover):
    edit(auth_client, article_with_cover["id"], remove_image="y")

    assert get_article_by_id(article_with_cover["id"])["image"] == ""
    assert not os.path.exists(image_path(app, article_with_cover["image"]))


def test_deleting_the_article_deletes_the_cover(app, auth_client, article_with_cover):
    auth_client.post(f"/admin/articles/{article_with_cover['id']}/delete")

    assert not os.path.exists(image_path(app, article_with_cover["image"]))


def test_edit_form_shows_the_current_cover(auth_client, article_with_cover):
    html = auth_client.get(f"/admin/articles/{article_with_cover['id']}/edit").get_data(
        as_text=True
    )

    assert "article-cover-preview" in html
    assert "حذف تصویر فعلی" in html


# --- Older covers and serving -----------------------------------------


def test_covers_committed_under_static_images_still_work(app, client):
    article = create_article(
        {"title": "Old Cover", "abstract": "x", "image": "article-ml-architecture.jpg"}
    )

    html = client.get(f"/articles/{article['id']}").get_data(as_text=True)

    assert "/static/images/article-ml-architecture.jpg" in html


def test_a_missing_cover_falls_back_to_the_placeholder(app, client):
    create_article({"title": "Lost Cover", "abstract": "x", "image": "gone.png"})

    html = client.get("/articles").get_data(as_text=True)

    assert "gone.png" not in html
    assert "/static/images/default.png" in html


def test_only_referenced_images_are_served(app, client, article_with_cover):
    stray = image_path(app, "stray.png")
    with open(stray, "wb") as handle:
        handle.write(png_bytes())

    assert client.get("/articles/images/stray.png").status_code == 404
    assert client.get("/articles/images/../uploads/x.png").status_code == 404


# --- Backup -----------------------------------------------------------


def test_backup_carries_uploaded_covers(app, db, article_with_cover, tmp_path):
    resume = str(tmp_path / "resume.pdf")
    payload = backup_service.build_export(
        app.config["UPLOAD_FOLDER"], resume, image_folder=app.config["ARTICLE_IMAGE_FOLDER"]
    )

    names = zipfile.ZipFile(io.BytesIO(payload)).namelist()
    assert f"uploads/images/{article_with_cover['image']}" in names

    os.remove(image_path(app, article_with_cover["image"]))
    backup_service.import_backup(
        io.BytesIO(payload),
        app.config["UPLOAD_FOLDER"],
        resume,
        mode="replace",
        image_folder=app.config["ARTICLE_IMAGE_FOLDER"],
    )

    restored = get_articles()[0]["image"]
    with open(image_path(app, restored), "rb") as handle:
        assert handle.read() == png_bytes()


def test_backup_rejects_a_fake_image_and_writes_nothing(app, tmp_path):
    data = {
        "schema_version": backup_service.SCHEMA_VERSION,
        "articles": [{"id": 1, "title": "x", "image": "cover.png", "views": 0}],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("data.json", json.dumps(data))
        archive.writestr("uploads/images/cover.png", b"<html>not an image</html>")

    with pytest.raises(backup_service.BackupError):
        backup_service.import_backup(
            io.BytesIO(buffer.getvalue()),
            app.config["UPLOAD_FOLDER"],
            str(tmp_path / "resume.pdf"),
            mode="replace",
            image_folder=app.config["ARTICLE_IMAGE_FOLDER"],
        )

    assert get_articles() == []
    assert stored_images(app) == []
