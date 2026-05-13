import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection

_client: MongoClient | None = None
_DB_NAME = "driftx"


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI environment variable is not set.")
        _client = MongoClient(uri)
    return _client


def get_db():
    return _get_client()[_DB_NAME]


def users_col() -> Collection:
    col = get_db()["users"]
    col.create_index("email", unique=True)
    return col


def analyses_col() -> Collection:
    col = get_db()["analyses"]
    col.create_index([("email", ASCENDING), ("timestamp", DESCENDING)])
    return col


def repo_history_col() -> Collection:
    col = get_db()["repo_history"]
    col.create_index([("repo_url", ASCENDING), ("timestamp", DESCENDING)])
    return col
