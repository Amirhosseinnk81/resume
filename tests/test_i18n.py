"""
Bilingual rendering tests.

The site has always advertised fa/en, but the English version served
Persian page titles, meta descriptions, navigation, buttons, job titles and
dates, because every template read the Persian key directly. These lock the
translation in.
"""

import re

import pytest

from content import TRANSLATIONS

PERSIAN = re.compile(r"[؀-ۿ]")


def strip_noise(html):
    """Drop comments, scripts and the <head> so only visible text remains."""
    body = html.split("<body", 1)[-1]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    return body


def text_nodes(html):
    return [
        " ".join(m.group(1).split())
        for m in re.finditer(r">([^<>]+)<", strip_noise(html), re.S)
        if m.group(1).strip()
    ]


def test_translation_dictionaries_have_identical_keys():
    """
    A key present in one language and missing in the other renders as an
    empty string on that language's pages.
    """
    fa = set(TRANSLATIONS["fa"])
    en = set(TRANSLATIONS["en"])

    assert fa == en, f"key mismatch: {sorted(fa ^ en)}"


def test_no_translation_value_is_empty():
    for lang, table in TRANSLATIONS.items():
        empty = [k for k, v in table.items() if not str(v).strip()]
        # HERO_SUFFIX is deliberately empty in English: Persian needs a
        # trailing "هستم." that English grammar does not.
        assert empty in ([], ["HERO_SUFFIX"]), f"{lang} has empty values: {empty}"


def test_english_translations_contain_no_persian():
    offenders = {
        key: value
        for key, value in TRANSLATIONS["en"].items()
        if PERSIAN.search(str(value))
    }
    assert not offenders, f"Persian text in the English table: {offenders}"


@pytest.mark.parametrize(
    "path", ["/", "/about", "/projects", "/contact"]
)
def test_english_chrome_has_no_persian(client, path):
    """
    These pages carry no database content, so in English they should be
    fully English. Pages that render project/article rows are excluded
    because that content is user-entered and falls back to Persian.
    """
    client.get("/toggle-lang")

    body = client.get(path).get_data(as_text=True)
    leaks = [t for t in text_nodes(body) if PERSIAN.search(t)]

    assert not leaks, f"{path} still renders Persian: {leaks[:5]}"


@pytest.mark.parametrize("path", ["/", "/about", "/projects", "/articles", "/contact"])
def test_english_head_has_no_persian(client, path):
    """<title> and <meta description> drive search results and browser tabs."""
    client.get("/toggle-lang")

    head = client.get(path).get_data(as_text=True).split("</head>")[0]

    title = re.search(r"<title>(.*?)</title>", head, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)"', head, re.S)

    assert title and not PERSIAN.search(title.group(1)), f"{path} title: {title}"
    assert desc and not PERSIAN.search(desc.group(1)), f"{path} description: {desc}"


def test_each_page_has_its_own_meta_description(client):
    """
    Child templates override {% block meta_description %} but base.html
    declared {% block description %}, so every page silently served the same
    generic site description.
    """
    descriptions = {}
    for path in ["/", "/about", "/projects", "/contact"]:
        head = client.get(path).get_data(as_text=True).split("</head>")[0]
        match = re.search(r'<meta name="description" content="(.*?)"', head, re.S)
        descriptions[path] = match.group(1)

    assert len(set(descriptions.values())) == len(descriptions), descriptions


def test_loc_filter_prefers_english_then_falls_back(app, client):
    from repositories.project_repository import create_project

    with app.app_context():
        create_project(
            {
                "title": "عنوان فارسی",
                "title_en": "English Title",
                "description": "توضیح فارسی",
                "description_en": "",  # deliberately empty -> must fall back
                "technologies": ["Python"],
                "status": "completed",
            }
        )

    client.get("/toggle-lang")  # -> en
    body = client.get("/projects").get_data(as_text=True)

    assert "English Title" in body
    assert "عنوان فارسی" not in body
    # No English description was supplied, so the Persian one still shows.
    assert "توضیح فارسی" in body


def test_persian_remains_the_default_language(client):
    body = client.get("/").get_data(as_text=True)
    assert 'lang="fa"' in body
    assert 'dir="rtl"' in body


def test_english_switches_direction_to_ltr(client):
    client.get("/toggle-lang")
    body = client.get("/").get_data(as_text=True)
    assert 'lang="en"' in body
    assert 'dir="ltr"' in body


def test_experience_dates_localise(client):
    """EXPERIENCES carries `year` ("2021 - حالا") and `year_en`."""
    client.get("/toggle-lang")
    body = client.get("/about").get_data(as_text=True)

    assert "Present" in body or "2021" in body
    assert "حالا" not in strip_noise(body)
