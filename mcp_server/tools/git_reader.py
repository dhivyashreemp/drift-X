import os
import shutil
import subprocess
import tempfile

import re

def parse_git_url(url):
    """
    Parses a GitHub URL to extract the root repo URL, branch, and subpath.
    Handles browser URLs like:
    https://github.com/user/repo/tree/branch-name/sub/folder
    """
    # Standard SSH or HTTPS URLs
    if url.endswith('.git'):
        return url, None, None
    
    # Check for GitHub browser URLs with tree or blob
    github_pattern = r"https?://github\.com/([^/]+)/([^/]+)/(tree|blob)/([^/]+)(.*)"
    match = re.match(github_pattern, url)
    
    if match:
        owner, repo, _, branch, subpath = match.groups()
        root_url = f"https://github.com/{owner}/{repo}.git"
        return root_url, branch, subpath.lstrip('/')
        
    return url, None, None

def _inject_token(url: str, token: str) -> str:
    """Insert a PAT into an HTTPS URL using oauth2 format (works for classic and fine-grained PATs)."""
    if not token or not url.startswith("https://"):
        return url
    after_scheme = url[len("https://"):]
    # Don't double-inject
    if "@" in after_scheme.split("/")[0]:
        return url
    return f"https://x-access-token:{token}@{after_scheme}"


def clone_repo(repo_url, branch=None, token=None):
    """
    Clones a git repository to a temporary directory.
    Automatically handles GitHub browser URLs by extracting the root, branch, and subpath.
    An explicit `branch` argument overrides any branch found in the URL.
    Pass `token` (GitHub PAT) to access private repositories.
    Returns the path to the specific directory requested.
    """
    clean_url, url_branch, subpath = parse_git_url(repo_url)
    if token:
        clean_url = _inject_token(clean_url, token)
    effective_branch = branch or url_branch
    temp_dir = tempfile.mkdtemp()

    try:
        command = ["git", "clone"]
        if effective_branch:
            command.extend(["--branch", effective_branch, "--single-branch"])
        command.extend([clean_url, temp_dir])

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, onerror=on_rm_error)
            stderr = result.stderr.strip()
            # Scrub token from error message before surfacing it
            if token:
                stderr = stderr.replace(token, "***")
            if result.returncode == 128:
                raise Exception(f"PRIVATE_REPO: {stderr or 'Repository not found or access denied.'}")
            raise Exception(f"Git clone failed (exit {result.returncode}): {stderr}")

        if subpath:
            target_path = os.path.join(temp_dir, subpath)
            if os.path.exists(target_path):
                return target_path

        return temp_dir
    except Exception:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=on_rm_error)
        raise

import stat

def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access error (read only file),
    it attempts to add write permission and then retries.
    If the error is for another reason it re-raises the error.
    """
    # Is the error an access error?
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)

def cleanup_repo(path):
    """
    Removes the temporary directory.
    """
    if os.path.exists(path):
        # On Windows, git files are often read-only. We need a handler.
        shutil.rmtree(path, onerror=on_rm_error)


def pull_repo(path: str) -> bool:
    """
    Fast-forward pull an already-cloned repo to pick up new commits.
    Returns True on success, False on failure.
    """
    try:
        result = subprocess.run(
            ["git", "-C", path, "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False
