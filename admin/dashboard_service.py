import csv
import json
import os
from repositories.project_repository import get_projects

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)


def get_dashboard_stats():

    stats = {
        "projects": 0,
        "articles": 0,
        "messages": 0,
        "visitors": 0,
    }

    projects = get_projects()

    stats["projects"] = len(projects)

    articles_file = os.path.join(
        BASE_DIR,
        "data",
        "articles.json",
    )

    if os.path.exists(articles_file):

        with open(
            articles_file,
            "r",
            encoding="utf-8"
        ) as f:

            articles = json.load(f)

            stats["articles"] = len(articles)

    messages_file = os.path.join(
        BASE_DIR,
        "data",
        "messages.csv",
    )

    if os.path.exists(messages_file):

        with open(
            messages_file,
            newline="",
            encoding="utf-8"
        ) as f:

            reader = csv.reader(f)

            next(reader, None)

            stats["messages"] = sum(1 for _ in reader)

    return stats