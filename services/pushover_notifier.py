import os
import requests


PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


def send_pushover_notification(title, message):
    user_key = os.environ.get("PUSHOVER_USER_KEY", "").strip()
    app_token = os.environ.get("PUSHOVER_APP_TOKEN", "").strip()

    if not user_key:
        raise ValueError("Missing PUSHOVER_USER_KEY environment variable.")

    if not app_token:
        raise ValueError("Missing PUSHOVER_APP_TOKEN environment variable.")

    response = requests.post(
        PUSHOVER_API_URL,
        data={
            "token": app_token,
            "user": user_key,
            "title": title,
            "message": message,
            "priority": 0,
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Pushover failed: {response.status_code} {response.text}")

    payload = response.json()

    if payload.get("status") != 1:
        raise RuntimeError(f"Pushover rejected message: {response.text}")

    return payload
