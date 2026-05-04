import json
import os
from datetime import datetime, timedelta

TEAM_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "team_history.json"
)


def _week_start() -> str:
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


def _load() -> dict:
    if not os.path.exists(TEAM_FILE):
        return {}
    try:
        with open(TEAM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    with open(TEAM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_analysis(
    email: str,
    name: str,
    repo_url: str,
    score: float,
    summary: str,
    issue_count: int = 0,
    critical_count: int = 0,
) -> None:
    data = _load()
    if email not in data:
        data[email] = {"name": name, "email": email, "analyses": []}
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "repo_url": repo_url,
        "score": score,
        "summary": summary,
        "issue_count": issue_count,
        "critical_count": critical_count,
    }
    data[email]["analyses"].insert(0, entry)
    data[email]["analyses"] = data[email]["analyses"][:50]
    _save(data)


def get_team_summary() -> list[dict]:
    data = _load()
    summary = []
    for email, record in data.items():
        analyses = record.get("analyses", [])
        latest = analyses[0] if analyses else None
        today = datetime.now().strftime("%Y-%m-%d")
        today_scores = [a["score"] for a in analyses if a.get("date") == today]
        prev = analyses[1] if len(analyses) > 1 else None
        if latest and prev:
            diff = latest["score"] - prev["score"]
            trend = "up" if diff > 2 else ("down" if diff < -2 else "flat")
        else:
            trend = None

        summary.append({
            "email": email,
            "name": record.get("name", email),
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
            "this_week_count": len([a for a in analyses if a.get("date", "") >= _week_start()]),
        })
    return sorted(summary, key=lambda x: (x["latest_score"] or -1), reverse=True)


def get_user_history(email: str) -> list[dict]:
    data = _load()
    return data.get(email, {}).get("analyses", [])
