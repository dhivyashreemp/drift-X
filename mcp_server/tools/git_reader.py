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

def clone_repo(repo_url):
    """
    Clones a git repository to a temporary directory.
    Automatically handles GitHub browser URLs by extracting the root, branch, and subpath.
    Returns the path to the specific directory requested.
    """
    clean_url, branch, subpath = parse_git_url(repo_url)
    temp_dir = tempfile.mkdtemp()
    
    try:
        command = ["git", "clone"]
        if branch:
            command.extend(["--branch", branch, "--single-branch"])
        command.extend([clean_url, temp_dir])
        
        subprocess.check_call(command)
        
        # If a subpath was specified, return the path to that internal folder
        if subpath:
            target_path = os.path.join(temp_dir, subpath)
            if os.path.exists(target_path):
                return target_path
            
        return temp_dir
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=on_rm_error)
        raise Exception(f"Failed to clone repository: {e}")

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
