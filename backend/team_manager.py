from datetime import datetime, timedelta
from db import analyses_col


def _week_start() -> str:
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


def record_analysis(
    email: str,
    name: str,
    repo_url: str,
    score: float,
    summary: str,
    issue_count: int = 0,
    critical_count: int = 0,
) -> None:
    col = analyses_col()
    entry = {
        "email": email,
        "name": name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "repo_url": repo_url,
        "score": score,
        "summary": summary,
        "issue_count": issue_count,
        "critical_count": critical_count,
    }
    col.insert_one(entry)

    # Keep only the 50 most recent analyses per user
    ids_to_keep = [
        doc["_id"]
        for doc in col.find({"email": email}, {"_id": 1}).sort("timestamp", -1).limit(50)
    ]
    col.delete_many({"email": email, "_id": {"$nin": ids_to_keep}})


def get_team_summary() -> list[dict]:
    col = analyses_col()
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$email",
                "name": {"$first": "$name"},
                "analyses": {"$push": "$$ROOT"},
            }
        },
    ]
    records = list(col.aggregate(pipeline))
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = _week_start()

    summary = []
    for record in records:
        analyses = record["analyses"]
        latest = analyses[0] if analyses else None
        prev = analyses[1] if len(analyses) > 1 else None

        if latest and prev:
            diff = latest["score"] - prev["score"]
            trend = "up" if diff > 2 else ("down" if diff < -2 else "flat")
        else:
            trend = None

        today_scores = [a["score"] for a in analyses if a.get("date") == today]

        summary.append({
            "email": record["_id"],
            "name": record["name"],
            "latest_score": latest["score"] if latest else None,
            "prev_score": prev["score"] if prev else None,
            "score_trend": trend,
            "last_active": latest["timestamp"] if latest else None,
            "last_repo": latest["repo_url"] if latest else None,
            "last_summary": latest.get("summary", "") if latest else "",
            "last_issue_count": latest.get("issue_count", 0) if latest else 0,
            "last_critical_count": latest.get("critical_count", 0) if latest else 0,
            "analyses_count": len(analyses),
            "today_scores": today_scores,
            "today_avg": round(sum(today_scores) / len(today_scores), 1) if today_scores else None,
            "this_week_count": len([a for a in analyses if a.get("date", "") >= week_start]),
        })

    return sorted(summary, key=lambda x: (x["latest_score"] or -1), reverse=True)


def get_user_history(email: str) -> list[dict]:
    docs = list(
        analyses_col()
        .find({"email": email}, {"_id": 0, "email": 0, "name": 0})
        .sort("timestamp", -1)
        .limit(50)
    )
    return docs
