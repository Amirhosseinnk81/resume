"""
Dashboard statistics.

Counts are now done in SQL instead of loading every row and measuring the
list in Python, and `visitors` is a real number: it was previously
initialised to 0 and never incremented, so the dashboard always claimed
zero visitors.
"""

from repositories import pageview_repository as views_repo
from repositories.article_repository import count_articles, total_article_views
from repositories.message_repository import count_messages, count_unread
from repositories.project_repository import count_projects


def get_dashboard_stats():

    return {
        "projects": count_projects(),
        "articles": count_articles(),
        "messages": count_messages(),
        "unread_messages": count_unread(),
        "article_views": total_article_views(),
        "visitors": views_repo.total_views(),
        "visitors_30d": views_repo.views_since(30),
        "top_pages": views_repo.top_pages(5),
        "views_series": views_repo.daily_series(14),
    }
