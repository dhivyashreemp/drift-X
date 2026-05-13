from datetime import datetime
from db import repo_history_col


def save_analysis(repo_url, analysis_type, score, summary, last_commit_hash=None):
    col = repo_history_col()
    entry = {
        "repo_url": repo_url,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": analysis_type,
        "score": score,
        "summary": summary,
        "last_commit_hash": last_commit_hash,
    }
    col.insert_one(entry)

    # Keep only the 10 most recent analyses per repo
    ids_to_keep = [
        doc["_id"]
        for doc in col.find({"repo_url": repo_url}, {"_id": 1}).sort("timestamp", -1).limit(10)
    ]
    col.delete_many({"repo_url": repo_url, "_id": {"$nin": ids_to_keep}})


def get_repo_history(repo_url):
    docs = list(
        repo_history_col()
        .find({"repo_url": repo_url}, {"_id": 0, "repo_url": 0})
        .sort("timestamp", -1)
        .limit(10)
    )
    return docs


def clear_repo_history(repo_url):
    result = repo_history_col().delete_many({"repo_url": repo_url})
    return result.deleted_count > 0
