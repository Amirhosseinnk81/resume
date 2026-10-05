"""
SEO output tests: sitemap, RSS, robots, structured data, meta tags.

The sitemap in particular was a hand-maintained static file listing only
five URLs with a lastmod frozen at 2026-09-13; these tests assert it is now
generated from the actual content.
"""

import json
import re
from xml.etree import ElementTree


def test_sitemap_is_well_formed_xml(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers["Content-Type"]

    # Raises on malformed XML.
    ElementTree.fromstring(response.data)


def test_sitemap_includes_detail_pages(client, sample_project, sample_article):
    body = client.get("/sitemap.xml").get_data(as_text=True)

    assert "/projects/{}".format(sample_project["id"]) in body
    assert "/articles/{}".format(sample_article["id"]) in body


def test_sitemap_uses_configured_site_url(client, app):
    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert app.config["SITE_URL"] in body


def test_sitemap_lastmod_is_not_hardcoded(client, sample_project):
    """The old static file had every lastmod pinned to 2026-09-13."""
    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "2026-09-13" not in body
    assert re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", body)


def test_rss_feed_is_well_formed(client, sample_article):
    response = client.get("/feed.xml")
    assert response.status_code == 200

    root = ElementTree.fromstring(response.data)
    titles = [item.findtext("title") for item in root.iter("item")]
    assert "Sample Article" in titles


def test_robots_points_at_the_generated_sitemap(client, app):
    body = client.get("/robots.txt").get_data(as_text=True)
    assert "Sitemap: {}/sitemap.xml".format(app.config["SITE_URL"]) in body


def test_person_json_ld_is_present_and_valid(client):
    body = client.get("/").get_data(as_text=True)

    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S
    )
    assert blocks, "no JSON-LD found"

    schemas = [json.loads(block) for block in blocks]
    types = {schema.get("@type") for schema in schemas}
    assert "Person" in types

    person = next(s for s in schemas if s.get("@type") == "Person")
    assert person["@context"] == "https://schema.org"
    assert person["name"]
    assert person["url"].startswith("http")


def test_detail_pages_add_their_own_schema(client, sample_article):
    body = client.get("/articles/{}".format(sample_article["id"])).get_data(as_text=True)

    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S
    )
    types = {json.loads(block).get("@type") for block in blocks}

    assert "ScholarlyArticle" in types
    assert "BreadcrumbList" in types


def test_canonical_and_hreflang_present(client):
    body = client.get("/about").get_data(as_text=True)

    assert '<link rel="canonical"' in body
    assert 'hreflang="fa"' in body
    assert 'hreflang="en"' in body
    assert 'hreflang="x-default"' in body


def test_canonical_does_not_vary_with_language(client):
    """fa and en must not be indexed as duplicate content."""

    def canonical_of(path):
        body = client.get(path).get_data(as_text=True)
        return re.search(r'<link rel="canonical" href="([^"]+)"', body).group(1)

    first = canonical_of("/about")
    client.get("/toggle-lang")
    second = canonical_of("/about")

    assert first == second


def test_og_image_is_the_social_card(client):
    body = client.get("/").get_data(as_text=True)
    assert "og-image.jpg" in body
    assert '<meta property="og:image:width" content="1200">' in body


def test_error_pages_are_noindex(client):
    body = client.get("/nope").get_data(as_text=True)
    assert 'name="robots"' in body
    assert "noindex" in body


def test_manifest_is_valid_json(client):
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200

    manifest = json.loads(response.data)
    assert manifest["name"]
    assert manifest["icons"]


def test_two_font_weights_only(client):
    """
    The head requested 5 Vazirmatn weights (400;500;600;700;800), which maps
    to 15 woff2 files and ~200 KB of font data.
    """
    body = client.get("/").get_data(as_text=True)
    match = re.search(r"family=Vazirmatn:wght@([0-9;]+)", body)

    assert match, "Vazirmatn link not found"
    assert match.group(1) == "400;700"


def test_no_aos_cdn_reference(client):
    """AOS was replaced by an IntersectionObserver in main.js."""
    body = client.get("/").get_data(as_text=True)
    assert "unpkg.com/aos" not in body
    assert "aos.js" not in body
