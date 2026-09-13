import json
import os
import threading

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SETTINGS_FILE = os.path.join(BASE_DIR, "data", "settings.json")

# See project_repository.py for why this lock exists (process-local only).
_lock = threading.Lock()

DEFAULT_SETTINGS = {
    "socials": {
        "github": "https://github.com/Amirhosseinnk81",
        "linkedin": "https://www.linkedin.com/in/amirhossein-naeimaei-618451374/",
        "twitter": "https://x.com/Amirnk_81",
    },
    "skills": [
        {"name": "Python", "level": 72},
        {"name": "Flask", "level": 55},
        {"name": "JavaScript", "level": 10},
        {"name": "Django", "level": 53},
        {"name": "Git&Github", "level": 44},
        {"name": "HTML/CSS", "level": 43},
    ],
}


def get_settings():

    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)

    with open(SETTINGS_FILE, "r", encoding="utf-8") as file:

        try:
            settings = json.load(file)
        except json.JSONDecodeError:
            return dict(DEFAULT_SETTINGS)

    # Fill in anything missing (e.g. file was created before a new key existed)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)

    return merged


def update_settings(new_settings):

    with _lock:

        settings = get_settings()

        settings.update(new_settings)

        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:

            json.dump(settings, file, ensure_ascii=False, indent=2)

        return settings
