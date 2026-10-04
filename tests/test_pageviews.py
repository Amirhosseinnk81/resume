"""
Page-view counter tests.

The dashboard previously reported a hardcoded `"visitors": 0` that was never
incremented, so these also serve as the proof that the stat is now real.
"""

from repositories import pageview_repository as views_repo


def test_html_get_is_counted(client, app):
    client.get("/")

    with app.app_context():
        assert views_repo.total_views() == 1


def test_repeated_views_accumulate(client, app):
    for _ in range(3):
        client.get("/")

    with app.app_context():
        assert views_repo.total_views() == 3
        top = views_repo.top_pages()
        assert top[0]["path"] == "/"
        assert top[0]["views"] == 3


def test_admin_pages_are_not_counted(auth_client, app):
    auth_client.get("/admin/")
    auth_client.get("/admin/projects")

    with app.app_context():
        paths = [page["path"] for page in views_repo.top_pages()]
        assert not any(path.startswith("/admin") for path in paths)


def test_non_html_responses_are_not_counted(client, app):
    client.get("/sitemap.xml")
    client.get("/feed.xml")
    client.get("/robots.txt")
    client.get("/manifest.webmanifest")

    with app.app_context():
        assert views_repo.total_views() == 0


def test_redirects_are_not_counted(client, app):
    client.get("/toggle-lang")  # 302

    with app.app_context():
        assert views_repo.total_views() == 0


def test_404_is_not_counted(client, app):
    client.get("/definitely-not-a-page")

    with app.app_context():
        assert views_repo.total_views() == 0


def test_post_requests_are_not_counted(client, app):
    client.post(
        "/contact",
        data={"name": "A", "email": "a@b.co", "message": "hello there"},
    )

    with app.app_context():
        assert views_repo.total_views() == 0


def test_daily_series_is_zero_filled(client, app):
    client.get("/")

    with app.app_context():
        series = views_repo.daily_series(14)

        assert len(series) == 14
        # Today is the last entry and holds the hit.
        assert series[-1]["views"] == 1
        assert all(point["views"] == 0 for point in series[:-1])


def test_distinct_paths_are_tracked_separately(client, app):
    client.get("/")
    client.get("/about")
    client.get("/about")

    with app.app_context():
        by_path = {page["path"]: page["views"] for page in views_repo.top_pages()}
        assert by_path["/about"] == 2
        assert by_path["/"] == 1


def test_dashboard_reports_a_real_visitor_count(auth_client, app):
    # Generate public traffic first.
    client = app.test_client()
    for _ in range(5):
        client.get("/")

    response = auth_client.get("/admin/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    # The hardcoded zero is gone.
    assert "5" in body
