import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ARTICLES_FILE = os.path.join(BASE_DIR, "data", "articles.json")


def get_articles():

    if not os.path.exists(ARTICLES_FILE):
        return []

    with open(ARTICLES_FILE, "r", encoding="utf-8") as file:

        articles = json.load(file)

    # Backfill "views" for older entries so templates never see a missing key
    for article in articles:
        article.setdefault("views", 0)

    return articles


def get_article_by_id(article_id):

    articles = get_articles()

    for article in articles:

        if article.get("id") == article_id:
            return article

    return None


def _save(articles):

    with open(ARTICLES_FILE, "w", encoding="utf-8") as file:

        json.dump(articles, file, ensure_ascii=False, indent=2)


def create_article(article):

    articles = get_articles()

    if articles:
        new_id = max(a.get("id", 0) for a in articles) + 1
    else:
        new_id = 1

    article["id"] = new_id
    article.setdefault("views", 0)

    articles.append(article)

    _save(articles)

    return article


def update_article(article_id, updated_data):

    articles = get_articles()

    for index, article in enumerate(articles):

        if article.get("id") == article_id:

            updated_data["id"] = article_id
            updated_data.setdefault("views", article.get("views", 0))

            articles[index] = updated_data

            _save(articles)

            return updated_data

    return None


def delete_article(article_id):

    articles = get_articles()

    for index, article in enumerate(articles):

        if article.get("id") == article_id:

            deleted_article = articles.pop(index)

            _save(articles)

            return deleted_article

    return None


def increment_views(article_id):

    articles = get_articles()

    for article in articles:

        if article.get("id") == article_id:

            article["views"] = article.get("views", 0) + 1

            _save(articles)

            return article

    return None
