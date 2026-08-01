import json
import os


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

PROJECTS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "projects.json"
)


def get_projects():

    if not os.path.exists(PROJECTS_FILE):
        return []

    with open(
        PROJECTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def get_project_by_id(project_id):

    projects = get_projects()

    for project in projects:

        if project.get("id") == project_id:
            return project

    return None