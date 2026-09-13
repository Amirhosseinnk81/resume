import json
import os
import threading

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROJECTS_FILE = os.path.join(BASE_DIR, "data", "projects.json")

# Guards the read-modify-write sequence in create/update/delete below so two
# concurrent requests (e.g. two admin tabs) can't race and silently drop one
# write. This only protects within a single process — if this app is ever
# deployed with multiple worker processes, use a real file lock or a database instead.
_lock = threading.Lock()


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

    with _lock:

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

    with _lock:

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

    with _lock:

        projects = get_projects()

        for index, project in enumerate(projects):

            if project.get("id") == project_id:

                deleted_project = projects.pop(index)

                with open(PROJECTS_FILE, "w", encoding="utf-8") as file:

                    json.dump(projects, file, ensure_ascii=False, indent=4)

                return deleted_project

        return None
