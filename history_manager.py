import json
import os
from datetime import datetime

HISTORY_FILE = "analysis_history.json"

def save_analysis(repo_url, analysis_type, score, summary, last_commit_hash=None):
    """Saves analysis results to the local history file."""
    history = load_all_history()
    
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": analysis_type,
        "score": score,
        "summary": summary,
        "last_commit_hash": last_commit_hash
    }
    
    if repo_url not in history:
        history[repo_url] = []
    
    # Prepend to keep latest first
    history[repo_url].insert(0, entry)
    
    # Keep only last 10 analyses per repo to save space
    history[repo_url] = history[repo_url][:10]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def load_all_history():
    """Loads all history from the local file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def get_repo_history(repo_url):
    """Gets history for a specific repository."""
    history = load_all_history()
    return history.get(repo_url, [])

def clear_repo_history(repo_url):
    """Clears history for a specific repository."""
    history = load_all_history()
    if repo_url in history:
        del history[repo_url]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        return True
    return False
