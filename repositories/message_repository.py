import json
import os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MESSAGES_FILE = os.path.join(BASE_DIR, "data", "messages.json")


def get_messages():

    if not os.path.exists(MESSAGES_FILE):
        return []

    with open(MESSAGES_FILE, "r", encoding="utf-8") as file:

        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def get_message_by_id(message_id):

    messages = get_messages()

    for message in messages:

        if message.get("id") == message_id:
            return message

    return None


def _save(messages):

    with open(MESSAGES_FILE, "w", encoding="utf-8") as file:

        json.dump(messages, file, ensure_ascii=False, indent=2)


def create_message(name, email, body):

    messages = get_messages()

    new_id = max((m.get("id", 0) for m in messages), default=0) + 1

    message = {
        "id": new_id,
        "name": name,
        "email": email,
        "message": body,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "read": False,
    }

    messages.append(message)

    _save(messages)

    return message


def set_read(message_id, read=True):

    messages = get_messages()

    for message in messages:

        if message.get("id") == message_id:

            message["read"] = read

            _save(messages)

            return message

    return None


def delete_message(message_id):

    messages = get_messages()

    for index, message in enumerate(messages):

        if message.get("id") == message_id:

            deleted_message = messages.pop(index)

            _save(messages)

            return deleted_message

    return None
