"""
Unit tests for the upload filename sanitiser.

This is a security boundary, which is exactly why it belongs in its own
module rather than inline in a route where it cannot be tested directly.
"""

import os

import pytest

from admin.utils import (
    allowed_article_file,
    article_upload_exists,
    delete_article_upload,
    safe_upload_filename,
)


@pytest.fixture
def upload_dir(tmp_path):
    path = tmp_path / "uploads"
    path.mkdir()
    return str(path)


def test_persian_filenames_survive(upload_dir):
    """
    secure_filename() would strip these to nothing. The project's real
    article filenames are Persian, so they must be preserved.
    """
    name = safe_upload_filename("مقاله یادگیری ماشین.pdf", upload_dir)

    assert "مقاله" in name
    assert name.endswith(".pdf")


def test_random_prefix_prevents_collisions(upload_dir):
    first = safe_upload_filename("paper.pdf", upload_dir)
    second = safe_upload_filename("paper.pdf", upload_dir)

    assert first != second


@pytest.mark.parametrize(
    "attack",
    [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config",
        "/etc/shadow",
        "....//....//etc/passwd",
        "foo/../../bar.pdf",
    ],
)
def test_path_traversal_is_stripped(attack, upload_dir):
    name = safe_upload_filename(attack, upload_dir)

    assert ".." not in name
    assert "/" not in name
    assert "\\" not in name

    resolved = os.path.abspath(os.path.join(upload_dir, name))
    assert resolved.startswith(os.path.abspath(upload_dir) + os.sep)


@pytest.mark.parametrize("name", ["", "   ", ".", "..", "...", None])
def test_degenerate_names_get_a_safe_default(name, upload_dir):
    result = safe_upload_filename(name, upload_dir)
    assert result.endswith(".pdf")
    assert len(result) > len(".pdf")


def test_windows_separators_are_treated_as_separators(upload_dir):
    r"""
    os.path.basename is platform-dependent: on Linux a backslash is an
    ordinary filename character, so "..\..\windows\system32\config" kept its
    ".." segments and collapsed to "....windowssystem32config" instead of
    "config". Not exploitable — the containment check still held — but the
    result differed between a Windows dev machine and the Linux CI runner,
    which is how this was found.
    """
    name = safe_upload_filename(r"..\..\windows\system32\config.pdf", upload_dir)

    assert name.endswith("config.pdf")
    assert ".." not in name
    assert "\\" not in name


def test_drive_letter_path_keeps_only_the_filename(upload_dir):
    name = safe_upload_filename(r"C:\Users\me\report.pdf", upload_dir)

    assert name.endswith("report.pdf")
    assert ":" not in name


def test_windows_illegal_characters_removed(upload_dir):
    name = safe_upload_filename('a<b>c:d"e|f?g*h.pdf', upload_dir)

    for char in '<>:"|?*':
        assert char not in name


def test_very_long_name_is_truncated(upload_dir):
    name = safe_upload_filename("x" * 500 + ".pdf", upload_dir)
    # 8 hex chars + underscore + 120 + ".pdf"
    assert len(name) <= 140


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("a.pdf", True),
        ("a.PDF", True),
        ("a.pdf.exe", False),
        ("a.exe", False),
        ("noextension", False),
        ("", False),
    ],
)
def test_allowed_extensions(filename, expected):
    assert allowed_article_file(filename) is expected


def test_delete_upload_removes_the_file(upload_dir):
    target = os.path.join(upload_dir, "doomed.pdf")
    with open(target, "wb") as handle:
        handle.write(b"%PDF")

    assert article_upload_exists("doomed.pdf", upload_dir) is True
    assert delete_article_upload("doomed.pdf", upload_dir) is True
    assert article_upload_exists("doomed.pdf", upload_dir) is False


def test_delete_upload_tolerates_missing_file(upload_dir):
    assert delete_article_upload("never-existed.pdf", upload_dir) is False


def test_delete_upload_refuses_to_escape_the_folder(tmp_path, upload_dir):
    """A stored name must never be trusted enough to delete outside uploads."""
    outside = tmp_path / "important.txt"
    outside.write_text("do not delete")

    delete_article_upload("../important.txt", upload_dir)

    assert outside.exists(), "a traversal path must not delete outside the folder"
