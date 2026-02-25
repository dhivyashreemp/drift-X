import os
import subprocess
import json
from datetime import datetime

class CommitAnalyzer:
    """
    Analyzes commit history to detect feature loss across commits.
    Tracks code deletions that may represent removed features.
    """
    
    def __init__(self, repo_path):
        self.repo_path = repo_path
    
    def get_commit_history(self, max_commits=50):
        """
        Get commit history with metadata.
        Returns list of commits with hash, message, date, author.
        """
        try:
            cmd = [
                "git", "-C", self.repo_path, "log",
                f"--max-count={max_commits}",
                "--pretty=format:%H|%s|%ai|%an"
            ]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='ignore')
            
            commits = []
            for line in result.strip().split('\n'):
                if line:
                    hash_val, message, date, author = line.split('|', 3)
                    commits.append({
                        "hash": hash_val,
                        "message": message,
                        "date": date,
                        "author": author
                    })
            return commits
        except subprocess.CalledProcessError as e:
            return []
    
    def get_full_diff_between_commits(self, old_commit, new_commit):
        """
        Get all changes (additions and deletions) between two commits.
        Returns dict with file paths and diff lines.
        """
        try:
            cmd = [
                "git", "-C", self.repo_path, "diff",
                old_commit, new_commit,
                "--unified=0"  # No context lines
            ]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='ignore')
            
            changes = {}
            current_file = None
            
            for line in result.split('\n'):
                if line.startswith('+++ b/'):
                    current_file = line[6:]
                elif (line.startswith('-') or line.startswith('+')) and not (line.startswith('---') or line.startswith('+++')):
                    if current_file and self._is_code_file(current_file):
                        if current_file not in changes:
                            changes[current_file] = []
                        changes[current_file].append(line)
            
            return changes
        except subprocess.CalledProcessError:
            return {}
    
    def analyze_feature_loss(self, initial_commit_index=0, recent_commit_index=-1):
        """
        Analyze feature loss between initial and recent commits.
        Returns structured data about deleted code.
        """
        commits = self.get_commit_history()
        
        if len(commits) < 2:
            return {
                "error": "Not enough commits to analyze",
                "commits_found": len(commits)
            }
        
        # Get initial and recent commits
        initial_commit = commits[initial_commit_index]["hash"]
        recent_commit = commits[recent_commit_index]["hash"]
        
        changes = self.get_full_diff_between_commits(initial_commit, recent_commit)
        # Filter for deletions for this specific legacy method
        deletions = {fp: [l[1:] for l in lines if l.startswith('-')] for fp, lines in changes.items()}
        
        # Analyze deletions
        analysis = {
            "initial_commit": {
                "hash": commits[initial_commit_index]["hash"][:8],
                "message": commits[initial_commit_index]["message"],
                "date": commits[initial_commit_index]["date"]
            },
            "recent_commit": {
                "hash": commits[recent_commit_index]["hash"][:8],
                "message": commits[recent_commit_index]["message"],
                "date": commits[recent_commit_index]["date"]
            },
            "total_commits_analyzed": len(commits),
            "files_with_deletions": len(deletions),
            "deletions": {}
        }
        
        # Categorize deletions by file
        for file_path, deleted_lines in deletions.items():
            # Filter out non-code files
            if self._is_code_file(file_path):
                analysis["deletions"][file_path] = {
                    "lines_deleted": len(deleted_lines),
                    "sample_deletions": deleted_lines[:10]  # First 10 lines as sample
                }
        
        return analysis
    
    def get_commit_diff_summary(self, commit_hash):
        """
        Get summary of changes in a specific commit.
        """
        try:
            cmd = [
                "git", "-C", self.repo_path, "show",
                commit_hash,
                "--stat"
            ]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='ignore')
            return result
        except subprocess.CalledProcessError:
            return ""
    
    def _is_code_file(self, file_path):
        """
        Check if file is a code file (not binary, config, etc.)
        """
        code_extensions = [
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go',
            '.rb', '.php', '.swift', '.kt', '.rs', '.scala', '.r',
            '.jsx', '.tsx', '.vue', '.html', '.css', '.scss'
        ]
        return any(file_path.endswith(ext) for ext in code_extensions)
    
    def get_feature_loss_context(self, max_commits=20):
        """
        Get comprehensive context about potential feature loss.
        Analyzes recent commits for patterns of deletion.
        """
        commits = self.get_commit_history(max_commits)
        
        if len(commits) < 2:
            return {"error": "Not enough commits"}
        
        # Analyze each consecutive commit pair
        deletion_timeline = []
        
        for i in range(len(commits) - 1):
            newer = commits[i]
            older = commits[i + 1]
            
            changes = self.get_full_diff_between_commits(older["hash"], newer["hash"])
            # Filter for deletions
            deletions = {fp: [l[1:] for l in lines if l.startswith('-')] for fp, lines in changes.items()}
            
            if deletions:
                code_deletions = {k: v for k, v in deletions.items() if self._is_code_file(k)}
                
                if code_deletions:
                    deletion_timeline.append({
                        "commit": {
                            "hash": newer["hash"][:8],
                            "message": newer["message"],
                            "date": newer["date"],
                            "author": newer["author"]
                        },
                        "files_modified": list(code_deletions.keys()),
                        "total_lines_deleted": sum(len(lines) for lines in code_deletions.values())
                    })
        
        return {
            "total_commits_analyzed": len(commits),
            "commits_with_deletions": len(deletion_timeline),
            "deletion_timeline": deletion_timeline,
            "oldest_commit": {
                "hash": commits[-1]["hash"][:8],
                "date": commits[-1]["date"]
            },
            "newest_commit": {
                "hash": commits[0]["hash"][:8],
                "date": commits[0]["date"]
            }
        }
