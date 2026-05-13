from datetime import datetime
from db import users_col


def get_user(email: str) -> dict | None:
    doc = users_col().find_one({"email": email.lower()}, {"_id": 0})
    return doc


def email_exists(email: str) -> bool:
    return users_col().count_documents({"email": email.lower()}, limit=1) > 0


def create_user(
    email: str,
    name: str,
    hashed_password: str,
    auth_provider: str = "email",
    role: str = "developer",
) -> dict:
    user = {
        "email": email.lower(),
        "name": name,
        "hashed_password": hashed_password,
        "auth_provider": auth_provider,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "role": role,
    }
    users_col().update_one({"email": email.lower()}, {"$setOnInsert": user}, upsert=True)
    return user


def all_users() -> list[dict]:
    return list(users_col().find({}, {"_id": 0}))


def safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "hashed_password"}
