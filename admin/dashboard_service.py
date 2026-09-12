from repositories.project_repository import get_projects
from repositories.article_repository import get_articles
from repositories.message_repository import get_messages


def get_dashboard_stats():

    stats = {
        "projects": 0,
        "articles": 0,
        "messages": 0,
        "unread_messages": 0,
        "visitors": 0,
    }

    stats["projects"] = len(get_projects())
    stats["articles"] = len(get_articles())

    messages = get_messages()
    stats["messages"] = len(messages)
    stats["unread_messages"] = sum(1 for m in messages if not m.get("read"))

    return stats
