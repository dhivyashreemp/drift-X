import json
import os
from datetime import datetime

USERS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users.json"
)


def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_user(email: str) -> dict | None:
    return _load().get(email.lower())


def email_exists(email: str) -> bool:
    return email.lower() in _load()


def create_user(
    email: str,
    name: str,
    hashed_password: str,
    auth_provider: str = "email",
    role: str = "developer",
) -> dict:
    data = _load()
    user = {
        "email": email.lower(),
        "name": name,
        "hashed_password": hashed_password,
        "auth_provider": auth_provider,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "role": role,
    }
    data[email.lower()] = user
    _save(data)
    return user


def all_users() -> list[dict]:
    return list(_load().values())


def safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "hashed_password"}
