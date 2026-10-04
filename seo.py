"""
SEO helpers: structured data, sitemap and RSS generation.

The sitemap used to be a hand-maintained static file with a `lastmod` frozen
at 2026-09-13 that listed only the five top-level pages — no project or
article URLs at all. For a site that already has a database of content,
generating it is both more correct and less work to keep correct.
"""

from datetime import UTC, date, datetime
from xml.sax.saxutils import escape

from flask import current_app, url_for

from content import EDUCATION, EXPERIENCES, NAME, PROFILE, TAGLINE


def site_url():
    return current_app.config["SITE_URL"].rstrip("/")


def absolute(path):
    return f"{site_url()}{path}"


def person_schema(settings, lang="fa"):
    """
    schema.org/Person for the site owner, embedded on every page.

    This is the cheapest meaningful SEO win available to a personal site:
    it is what lets search engines render a person result rather than a
    plain blue link.
    """
    socials = [url for url in (settings.get("socials") or {}).values() if url]

    skills = [s["name"] for s in (settings.get("skills") or [])]

    alumni = []
    for entry in EDUCATION:
        name = entry.get("university_en") or entry.get("university")
        if name and name not in alumni:
            alumni.append(name)

    works_for = None
    for entry in EXPERIENCES:
        company = entry.get("company_en") or entry.get("company")
        if company and "freelance" not in company.lower():
            works_for = company
            break

    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": PROFILE["name_en"] if lang == "en" else PROFILE["name"],
        "alternateName": PROFILE["name"] if lang == "en" else PROFILE["name_en"],
        "jobTitle": PROFILE["job_en"] if lang == "en" else PROFILE["job"],
        "description": TAGLINE,
        "email": f"mailto:{PROFILE['email']}",
        "url": site_url(),
        "image": absolute(url_for("static", filename="images/og-image.jpg")),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": PROFILE["location_en"] if lang == "en" else PROFILE["location"],
            "addressCountry": "IR",
        },
        "knowsAbout": skills,
    }

    if socials:
        schema["sameAs"] = socials
    if alumni:
        schema["alumniOf"] = [
            {"@type": "EducationalOrganization", "name": name} for name in alumni
        ]
    if works_for:
        schema["worksFor"] = {"@type": "Organization", "name": works_for}

    return schema


def breadcrumb_schema(items):
    """items: list of (name, path) tuples, outermost first."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": name,
                "item": absolute(path),
            }
            for index, (name, path) in enumerate(items)
        ],
    }


def article_schema(article):
    published = article.get("year")
    schema = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": article["title"],
        "abstract": article.get("abstract") or "",
        "inLanguage": article.get("language") or "fa",
        "author": {"@type": "Person", "name": article.get("authors") or NAME},
        "url": absolute(url_for("article_detail", article_id=article["id"])),
        "interactionStatistic": {
            "@type": "InteractionCounter",
            "interactionType": "https://schema.org/ViewAction",
            "userInteractionCount": article.get("views", 0),
        },
    }
    if published:
        schema["datePublished"] = str(published)
    if article.get("image"):
        schema["image"] = absolute(
            url_for("static", filename=f"images/{article['image']}")
        )
    return schema


def project_schema(project):
    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": project["title"],
        "description": project.get("description") or "",
        "url": absolute(url_for("project_detail", project_id=project["id"])),
        "programmingLanguage": project.get("technologies") or [],
        "author": {"@type": "Person", "name": NAME},
    }
    if project.get("github"):
        schema["codeRepository"] = project["github"]
    return schema


# --- Sitemap ----------------------------------------------------------


def _node(loc, lastmod=None, changefreq=None, priority=None):
    parts = [f"    <loc>{escape(loc)}</loc>"]
    if lastmod:
        if isinstance(lastmod, datetime):
            lastmod = lastmod.date()
        parts.append(f"    <lastmod>{lastmod.isoformat()}</lastmod>")
    if changefreq:
        parts.append(f"    <changefreq>{changefreq}</changefreq>")
    if priority is not None:
        parts.append(f"    <priority>{priority}</priority>")
    return "  <url>\n" + "\n".join(parts) + "\n  </url>"


def build_sitemap(projects, articles):
    today = date.today()

    def newest(rows):
        stamps = [r.get("updated_at") for r in rows if r.get("updated_at")]
        return max(stamps).date() if stamps else today

    nodes = [
        _node(absolute(url_for("home")), newest(projects + articles), "weekly", "1.0"),
        _node(absolute(url_for("projects")), newest(projects), "weekly", "0.9"),
        _node(absolute(url_for("articles")), newest(articles), "weekly", "0.8"),
        _node(absolute(url_for("about")), today, "monthly", "0.7"),
        _node(absolute(url_for("contact")), today, "yearly", "0.5"),
    ]

    for project in projects:
        nodes.append(
            _node(
                absolute(url_for("project_detail", project_id=project["id"])),
                project.get("updated_at") or today,
                "monthly",
                "0.7",
            )
        )

    for article in articles:
        nodes.append(
            _node(
                absolute(url_for("article_detail", article_id=article["id"])),
                article.get("updated_at") or today,
                "monthly",
                "0.6",
            )
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(nodes)
        + "\n</urlset>\n"
    )


# --- RSS --------------------------------------------------------------


def _rfc822(value):
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=UTC)
    else:
        dt = datetime.now(UTC)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def build_rss(articles, lang="fa"):
    """
    An RSS feed is how the reference sites' writing actually travels. Cheap
    to generate from data already in the database.
    """
    items = []
    for article in articles:
        link = absolute(url_for("article_detail", article_id=article["id"]))
        items.append(
            "    <item>\n"
            f"      <title>{escape(article['title'])}</title>\n"
            f"      <link>{escape(link)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(link)}</guid>\n"
            f"      <description>{escape(article.get('abstract') or '')}</description>\n"
            f"      <pubDate>{_rfc822(article.get('created_at'))}</pubDate>\n"
            "    </item>"
        )

    title = f"{NAME} — {'مقالات' if lang == 'fa' else 'Articles'}"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(site_url())}</link>\n"
        f"    <description>{escape(TAGLINE)}</description>\n"
        f"    <language>{'fa-IR' if lang == 'fa' else 'en-US'}</language>\n"
        f"    <lastBuildDate>{_rfc822(datetime.now(UTC))}</lastBuildDate>\n"
        f'    <atom:link href="{escape(absolute(url_for("rss_feed")))}" '
        'rel="self" type="application/rss+xml" />\n'
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
