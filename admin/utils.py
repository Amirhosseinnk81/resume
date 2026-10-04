"""
Admin helpers for file uploads.

This file existed but was empty — these helpers were defined inline in
routes.py. Moving them out is what lets routes.py shrink and lets the
filename sanitiser be unit-tested directly, which matters because it is a
security boundary.
"""

import os
import re
import unicodedata
import uuid

ALLOWED_ARTICLE_EXTENSIONS = {"pdf"}

# Characters that are unsafe in a filename on Windows or in a URL path.
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_COLLAPSE = re.compile(r"[\s_]+")


def allowed_article_file(filename):
    return (
        "." in (filename or "")
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_ARTICLE_EXTENSIONS
    )


def safe_upload_filename(filename, upload_folder):
    """
    Sanitise an uploaded filename for saving to disk.

    Werkzeug's secure_filename() strips non-ASCII, which would mangle the
    Persian filenames this project actually uses. Instead:

      1. Strip directory components to block traversal ("../../etc/passwd").
      2. Normalise Unicode (NFC) so visually identical Persian names don't
         produce two different files.
      3. Remove characters that are illegal in Windows filenames or that
         would need escaping in a URL.
      4. Prefix a short random id so one upload cannot silently overwrite
         another article's file when two share a name.
      5. Re-check the resolved path still lands inside upload_folder.
    """
    base_name = os.path.basename(filename or "").strip()
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
