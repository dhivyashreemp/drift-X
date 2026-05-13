from datetime import datetime
from bson import ObjectId
from db import repo_history_col


def save_analysis(repo_url, analysis_type, score, summary,
                  last_commit_hash=None, full_results=None,
                  history_results=None, module_results=None):
    col = repo_history_col()
    entry = {
        "repo_url": repo_url,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": analysis_type,
        "score": score,
        "summary": summary,
        "last_commit_hash": last_commit_hash,
        "full_results": full_results or {"score": score, "summary": summary, "issues": []},
        "history_results": history_results,
        "module_results": module_results,
    }
    result = col.insert_one(entry)

    # Keep only the 20 most recent analyses per repo
    ids_to_keep = [
        doc["_id"]
        for doc in col.find({"repo_url": repo_url}, {"_id": 1}).sort("timestamp", -1).limit(20)
    ]
    col.delete_many({"repo_url": repo_url, "_id": {"$nin": ids_to_keep}})
    return str(result.inserted_id)


def get_repo_history(repo_url):
    docs = list(
        repo_history_col()
        .find(
            {"repo_url": repo_url},
            {"full_results": 0, "history_results": 0, "module_results": 0}
        )
        .sort("timestamp", -1)
        .limit(20)
    )
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
        doc.pop("repo_url", None)
    return docs


def get_analysis_full(entry_id: str):
    try:
        doc = repo_history_col().find_one({"_id": ObjectId(entry_id)})
    except Exception:
        return None
    return doc


def clear_repo_history(repo_url):
    result = repo_history_col().delete_many({"repo_url": repo_url})
    return result.deleted_count > 0
