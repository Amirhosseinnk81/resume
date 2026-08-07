import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROJECTS_FILE = os.path.join(BASE_DIR, "data", "projects.json")


def get_projects():

    if not os.path.exists(PROJECTS_FILE):
        return []

    with open(PROJECTS_FILE, "r", encoding="utf-8") as file:

        return json.load(file)


def get_project_by_id(project_id):

    projects = get_projects()

    for project in projects:

        if project.get("id") == project_id:
            return project

    return None


def create_project(project):

    projects = get_projects()

    if projects:
        new_id = max(project.get("id", 0) for project in projects) + 1
    else:
        new_id = 1

    project["id"] = new_id

    projects.append(project)

    with open(PROJECTS_FILE, "w", encoding="utf-8") as file:

        json.dump(projects, file, ensure_ascii=False, indent=4)

    return project


def update_project(project_id, updated_data):

    projects = get_projects()

    for index, project in enumerate(projects):

        if project.get("id") == project_id:

            updated_data["id"] = project_id

            projects[index] = updated_data

            with open(PROJECTS_FILE, "w", encoding="utf-8") as file:

                json.dump(projects, file, ensure_ascii=False, indent=4)

            return updated_data

    return None


def delete_project(project_id):

    projects = get_projects()

    for index, project in enumerate(projects):

        if project.get("id") == project_id:

            deleted_project = projects.pop(index)

            with open(PROJECTS_FILE, "w", encoding="utf-8") as file:

                json.dump(projects, file, ensure_ascii=False, indent=4)

            return deleted_project

    return None
