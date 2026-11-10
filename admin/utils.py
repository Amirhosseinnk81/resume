"""
Admin helpers for file uploads.

This file existed but was empty — these helpers were defined inline in
routes.py. Moving them out is what lets routes.py shrink and lets the
filename sanitiser be unit-tested directly, which matters because it is a
security boundary.
"""

import io
import os
import posixpath
import re
import unicodedata
import uuid

from flask import current_app, url_for
from PIL import Image

ALLOWED_ARTICLE_EXTENSIONS = {"pdf"}

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

# The stored extension comes from what Pillow finds in the file, never from
# the uploaded name, so "cover.png" holding HTML cannot be served as HTML.
# SVG is deliberately absent: it can carry script.
_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}

MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Characters that are unsafe in a filename on Windows or in a URL path.
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_COLLAPSE = re.compile(r"[\s_]+")


def allowed_article_file(filename):
    return (
        "." in (filename or "")
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_ARTICLE_EXTENSIONS
    )


def allowed_image_file(filename):
    return (
        "." in (filename or "")
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def safe_upload_filename(filename, upload_folder):
    """
    Sanitise an uploaded filename for saving to disk.

    Werkzeug's secure_filename() strips non-ASCII, which would mangle the
    Persian filenames this project actually uses. Instead:

      1. Treat both "/" and "\\" as separators before taking the basename.
         os.path.basename is platform-dependent: on Linux a backslash is an
         ordinary filename character, so a Windows-style path uploaded to a
         Linux server kept its ".." segments ("..\\..\\etc\\passwd" became
         "....etcpasswd"). Normalising first makes the result identical on
         both platforms.
      2. Normalise Unicode (NFC) so visually identical Persian names don't
         produce two different files.
      3. Remove characters that are illegal in Windows filenames or that
         would need escaping in a URL.
      4. Prefix a short random id so one upload cannot silently overwrite
         another article's file when two share a name.
      5. Re-check the resolved path still lands inside upload_folder.
    """
    # Normalise Windows separators first so basename() behaves the same on
    # every platform, then take the final segment.
    raw = (filename or "").replace("\\", "/")
    base_name = posixpath.basename(raw).strip()
    base_name = unicodedata.normalize("NFC", base_name)

    # Reject anything that is only dots, or empty after stripping.
    if not base_name or set(base_name) <= {"."}:
        base_name = "file.pdf"

    base_name = _UNSAFE.sub("", base_name)
    base_name = _COLLAPSE.sub(" ", base_name).strip()

    if not base_name:
        base_name = "file.pdf"

    # Keep the name from growing past common filesystem limits once the
    # random prefix is added.
    root, ext = os.path.splitext(base_name)
    root = root[:120] or "file"
    ext = ext.lower() if ext else ".pdf"

    safe_name = f"{uuid.uuid4().hex[:8]}_{root}{ext}"

    resolved = os.path.abspath(os.path.join(upload_folder, safe_name))
    if not resolved.startswith(os.path.abspath(upload_folder) + os.sep):
        raise ValueError("Unsafe filename")

    return safe_name


def save_article_upload(file_storage, upload_folder):
    """
    Validate and store an uploaded article PDF.

    Returns the stored filename, or None when no file was supplied.
    Raises ValueError when the file is present but not an allowed type.
    """
    # Populating an edit form from a stored dict puts the *filename string*
    # into the field, not a FileStorage, so check for the upload interface
    # rather than mere truthiness.
    if not file_storage or not hasattr(file_storage, "filename"):
        return None

    if not file_storage.filename:
        return None

    if not allowed_article_file(file_storage.filename):
        raise ValueError("فقط فایل PDF مجاز است.")

    os.makedirs(upload_folder, exist_ok=True)

    stored_name = safe_upload_filename(file_storage.filename, upload_folder)
    file_storage.save(os.path.join(upload_folder, stored_name))

    return stored_name


def delete_article_upload(filename, upload_folder):
    """
    Remove a stored upload, ignoring a missing file.

    Deleting an article previously left its PDF behind forever, so the
    uploads directory grew without bound.
    """
    if not filename:
        return False

    # Never trust a stored name enough to skip the containment check.
    target = os.path.abspath(os.path.join(upload_folder, os.path.basename(filename)))
    if not target.startswith(os.path.abspath(upload_folder) + os.sep):
        return False

    try:
        os.remove(target)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def article_upload_exists(filename, upload_folder):
    if not filename:
        return False
    target = os.path.abspath(os.path.join(upload_folder, os.path.basename(filename)))
    if not target.startswith(os.path.abspath(upload_folder) + os.sep):
        return False
    return os.path.isfile(target)


# --- Article cover images ---------------------------------------------


def image_extension(payload):
    """
    Return the extension for an image's real format, or raise ValueError
    when the bytes are not a JPEG, PNG, WebP or GIF.
    """
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image_format = image.format
            image.verify()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        raise ValueError("فایل انتخاب‌شده یک تصویر معتبر نیست.") from error

    extension = _IMAGE_FORMATS.get(image_format)
    if extension is None:
        raise ValueError("فقط تصویر JPG، PNG، WebP یا GIF مجاز است.")

    return extension


def store_image_bytes(payload, original_name, image_folder):
    """Validate image bytes and write them under a sanitised name."""
    extension = image_extension(payload)

    os.makedirs(image_folder, exist_ok=True)

    root = os.path.splitext(original_name or "")[0] or "cover"
    stored_name = safe_upload_filename(root + extension, image_folder)

    with open(os.path.join(image_folder, stored_name), "wb") as handle:
        handle.write(payload)

    return stored_name


def save_article_image(file_storage, image_folder):
    """
    Validate and store an uploaded cover image.

    Returns the stored filename, or None when no file was supplied.
    Raises ValueError when the file is present but not an acceptable image.
    """
    if not file_storage or not hasattr(file_storage, "filename"):
        return None

    if not file_storage.filename:
        return None

    if not allowed_image_file(file_storage.filename):
        raise ValueError("فقط تصویر JPG، PNG، WebP یا GIF مجاز است.")

    payload = file_storage.read(MAX_IMAGE_BYTES + 1)
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("حجم تصویر نباید بیشتر از ۵ مگابایت باشد.")

    return store_image_bytes(payload, file_storage.filename, image_folder)


def article_image_url(filename):
    """
    URL of an article's cover image, or None when there is no usable file.

    Covers uploaded from the admin live in ARTICLE_IMAGE_FOLDER; older ones
    are committed under static/images. A name found in neither (an upload
    lost with a container's disk, say) returns None, so templates show
    their placeholder instead of a broken image.
    """
    if not filename:
        return None

    if article_upload_exists(filename, current_app.config["ARTICLE_IMAGE_FOLDER"]):
        return url_for("article_image", filename=filename)

    if article_upload_exists(filename, os.path.join(current_app.static_folder, "images")):
        return url_for("static", filename=f"images/{filename}")

    return None
