import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from radon.complexity import cc_visit
    _HAS_RADON = True
except ImportError:
    _HAS_RADON = False

_IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'build', 'dist',
    '.next', '.venv', 'venv', 'env', '.idea', '.vscode',
    'coverage', '.pytest_cache', 'migrations',
}
_CODE_EXTS = {'.py', '.js', '.ts', '.jsx', '.tsx'}

_SECRET_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\'$%\{\s]{4,}["\']', 'Hardcoded Password'),
    (r'(?i)(secret|api_key|apikey|private_key|auth_token)\s*=\s*["\'][^"\'$%\{\s]{8,}["\']', 'Hardcoded Secret'),
    (r'AKIA[A-Z0-9]{16}', 'Hardcoded AWS Access Key'),
    (r'(?i)mongodb(\+srv)?://[^@\s"\']+:[^@\s"\']+@', 'Hardcoded MongoDB URI'),
]

_SEV_ORDER = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}


def _collect_files(repo_path):
    files = []
    for root, dirs, fnames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for fname in fnames:
            if Path(fname).suffix in _CODE_EXTS:
                files.append(os.path.join(root, fname))
    return files


def _rel(repo_path, full_path):
    return os.path.relpath(full_path, repo_path).replace('\\', '/')


def _issue(category, subcategory, severity, file_path, line, description, evidence, remediation):
    return {
        'category': category,
        'subcategory': subcategory,
        'severity': severity,
        'file': file_path,
        'line': line,
        'description': description,
        'evidence': (evidence or '')[:120],
        'remediation': remediation,
    }


def _scan_secrets(content, rel_path):
    issues = []
    lines = content.splitlines()
    for pattern, label in _SECRET_PATTERNS:
        for m in re.finditer(pattern, content):
            line_no = content[:m.start()].count('\n') + 1
            line_text = lines[line_no - 1] if line_no <= len(lines) else ''
            if any(kw in line_text for kw in ('os.getenv', 'environ', 'os.environ', 'getenv')):
                continue
            issues.append(_issue(
                'auth', label, 'Critical', rel_path, line_no,
                f'{label} found in source code — will be exposed in git history',
                line_text.strip()[:80],
                'Move to environment variable. Remove from source and purge git history with git-filter-repo.'
            ))
    return issues


def _analyze_python_ast(content, rel_path):
    issues = []
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return issues

    # Bare except handlers
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is not None:
            continue
        line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
        body_is_pass = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
        issues.append(_issue(
            'pipeline', 'Bare Exception Handler',
            'Critical' if body_is_pass else 'High',
            rel_path, node.lineno,
            'Bare `except:` catches ALL exceptions including SystemExit/KeyboardInterrupt'
            + (' and silently discards them (pass)' if body_is_pass else ''),
            line_text,
            'Use specific types: `except (ValueError, IOError) as e:` and log with `logger.error(..., exc_info=e)`.'
        ))

    # Try blocks acquiring resources without finally
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if node.finalbody:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else '')
            if name in ('open', 'connect', 'clone_repo', 'acquire', 'cursor', 'socket'):
                line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                issues.append(_issue(
                    'pipeline', 'Missing Finally Block', 'Medium',
                    rel_path, node.lineno,
                    f'`try` block acquires resource via `{name}()` with no `finally` for cleanup — resource may leak on exception',
                    line_text,
                    'Add `finally: resource.close()` or use a `with` statement (context manager).'
                ))
                break

    # Long functions
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end_line = getattr(node, 'end_lineno', node.lineno)
        func_lines = end_line - node.lineno + 1
        if func_lines > 80:
            issues.append(_issue(
                'complexity', 'Long Function',
                'High' if func_lines > 150 else 'Medium',
                rel_path, node.lineno,
                f'`{node.name}` is {func_lines} lines (threshold: 80) — difficult to test, review, and maintain',
                f'def {node.name}(...)  # lines {node.lineno}–{end_line}',
                f'Decompose `{node.name}` into smaller single-responsibility functions, each under 50 lines.'
            ))

    # TODO/FIXME in production code
    for i, line in enumerate(lines, 1):
        if re.search(r'#\s*(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
            issues.append(_issue(
                'dead_code', 'TODO/FIXME in Production', 'Low',
                rel_path, i,
                'Deferred defect or missing implementation left in production code path',
                line.strip()[:80],
                'Resolve the TODO or open a tracking ticket, then remove the comment from production code.'
            ))

    return issues


def _check_auth_patterns(content, rel_path, lines):
    issues = []

    # JWT without expiry
    if re.search(r'jwt\.encode|create_access_token|create_token', content):
        if not re.search(r'\bexp\b|expires_delta|timedelta', content, re.IGNORECASE):
            issues.append(_issue(
                'auth', 'JWT Without Expiry', 'High', rel_path, 1,
                'JWT tokens are created but no expiry (`exp` claim) is visible — tokens are valid indefinitely',
                'jwt.encode / create_token without exp/timedelta',
                'Add expiry: include `"exp": datetime.utcnow() + timedelta(hours=24)` in the JWT payload.'
            ))

    # Unprotected state-changing endpoints (FastAPI style)
    for i, line in enumerate(lines, 1):
        if not re.match(r'\s*@app\.(post|put|delete|patch)\s*\(', line, re.IGNORECASE):
            continue
        context = '\n'.join(lines[i:min(i + 15, len(lines))])
        if re.search(r'require_user|_require_user|verify_token|Depends\s*\(', context):
            continue
        # Skip health/public endpoints
        if re.search(r'health|ping|webhook|callback', line, re.IGNORECASE):
            continue
        issues.append(_issue(
            'auth', 'Unprotected State-Changing Endpoint', 'High',
            rel_path, i,
            f'POST/PUT/DELETE/PATCH route at line {i} has no authentication check in the handler body',
            line.strip()[:80],
            'Add `authorization: str = Header(default="")` and call `_require_user(authorization)` at the handler start.'
        ))

    return issues


def _check_observability(content, rel_path, lines):
    issues = []
    backend_paths = ('backend/', 'agents/', 'utils/', 'mcp_server/')
    if not any(rel_path.startswith(p) for p in backend_paths):
        return issues

    print_count = 0
    for i, line in enumerate(lines, 1):
        if re.match(r'\s*print\s*\(', line):
            print_count += 1
            if print_count <= 2:
                issues.append(_issue(
                    'observability', 'print() as Logging', 'Low',
                    rel_path, i,
                    'print() used for logging — unstructured output is not queryable or filterable in production',
                    line.strip()[:80],
                    'Replace with `logger.info(...)` or `logger.error(...)` using a structured logging library.'
                ))

    return issues


def _analyze_requirements(repo_path):
    issues = []
    req_path = os.path.join(repo_path, 'requirements.txt')
    if not os.path.exists(req_path):
        return issues

    with open(req_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith(('#', '-')):
            continue
        pkg = re.split(r'[>=<!~\s\[@]', line)[0].strip()
        if not pkg:
            continue
        if '==' in line:
            continue
        elif '>=' in line or '~=' in line:
            issues.append(_issue(
                'dependencies', 'Flexible Version Constraint', 'Medium',
                'requirements.txt', i,
                f'`{pkg}` uses a flexible version constraint — can silently drift to a breaking or vulnerable release',
                line,
                f'Pin to exact version: `{pkg}==<current-version>`. Run: pip show {pkg} | grep Version'
            ))
        else:
            issues.append(_issue(
                'dependencies', 'Unpinned Dependency', 'High',
                'requirements.txt', i,
                f'`{pkg}` has no version constraint — any fresh install may pull a different or vulnerable version',
                line,
                f'Pin to exact version: `{pkg}==<current-version>`. Run: pip freeze | grep -i {pkg}'
            ))

    return issues


def _run_bandit(repo_path):
    issues = []
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'bandit', '-r', repo_path, '-f', 'json', '-q', '--exit-zero'],
            capture_output=True, text=True, timeout=60,
        )
        if not result.stdout:
            return issues
        data = json.loads(result.stdout)
        seen_keys = set()
        for item in data.get('results', []):
            sev_map = {'HIGH': 'High', 'MEDIUM': 'Medium', 'LOW': 'Low'}
            sev = sev_map.get(item.get('issue_severity', 'LOW'), 'Low')
            rel = _rel(repo_path, item.get('filename', ''))
            line_no = item.get('line_number', 0)
            test_name = item.get('test_name', 'security_issue').replace('_', ' ').title()
            key = (rel, line_no, test_name)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            issues.append(_issue(
                'security', test_name, sev, rel, line_no,
                item.get('issue_text', ''),
                (item.get('code') or '').strip()[:80],
                f"Bandit {item.get('test_id', '')}: {item.get('more_info', 'See bandit docs for remediation.')}"
            ))
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, Exception):
        pass
    return issues


def _run_radon_complexity(repo_path):
    issues = []
    if not _HAS_RADON:
        return issues
    for root, dirs, fnames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for fname in fnames:
            if not fname.endswith('.py'):
                continue
            full = os.path.join(root, fname)
            rel = _rel(repo_path, full)
            try:
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                for block in cc_visit(content):
                    if block.complexity < 10:
                        continue
                    issues.append(_issue(
                        'complexity', 'High Cyclomatic Complexity',
                        'High' if block.complexity >= 15 else 'Medium',
                        rel, block.lineno,
                        f'`{block.name}` has cyclomatic complexity {block.complexity} (threshold: 10) — {block.complexity - 1} independent paths to test',
                        f'{block.name}: CC={block.complexity}, rank={block.rank}',
                        f'Reduce branching in `{block.name}`. Extract conditional logic into well-named helper functions.'
                    ))
            except Exception:
                pass
    return issues


def _deduplicate(issues):
    seen = set()
    result = []
    for issue in issues:
        key = (issue['file'], issue['line'], issue['subcategory'])
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def analyze_repo(repo_path):
    """
    Run all static analysis passes on a single repo.
    Returns dict with by_category and by_file groupings.
    """
    all_issues = []

    for full_path in _collect_files(repo_path):
        rel = _rel(repo_path, full_path)
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue

        lines = content.splitlines()
        all_issues.extend(_scan_secrets(content, rel))
        all_issues.extend(_check_auth_patterns(content, rel, lines))
        all_issues.extend(_check_observability(content, rel, lines))
        if full_path.endswith('.py'):
            all_issues.extend(_analyze_python_ast(content, rel))

    all_issues.extend(_analyze_requirements(repo_path))
    all_issues.extend(_run_bandit(repo_path))
    all_issues.extend(_run_radon_complexity(repo_path))

    all_issues = _deduplicate(all_issues)
    all_issues.sort(key=lambda x: (_SEV_ORDER.get(x['severity'], 9), x['file'], x['line']))

    by_category = {}
    for issue in all_issues:
        by_category.setdefault(issue['category'], []).append(issue)

    by_file = {}
    for issue in all_issues:
        by_file.setdefault(issue['file'], []).append(issue)

    return {
        'total_issues': len(all_issues),
        'by_category': by_category,
        'by_file': by_file,
    }


def analyze_repos(repo_paths_labeled):
    """
    Run static analysis across multiple repos.
    repo_paths_labeled: list of (path, label) tuples.
    """
    merged_by_category = {}
    merged_by_file = {}
    total = 0

    for repo_path, label in repo_paths_labeled:
        result = analyze_repo(repo_path)
        total += result['total_issues']
        prefix = f'[{label}] ' if label else ''

        for cat, issues in result['by_category'].items():
            prefixed = [{**iss, 'file': prefix + iss['file']} for iss in issues]
            merged_by_category.setdefault(cat, []).extend(prefixed)

        for file_path, issues in result['by_file'].items():
            key = prefix + file_path
            prefixed = [{**iss, 'file': key} for iss in issues]
            merged_by_file.setdefault(key, []).extend(prefixed)

    return {
        'total_issues': total,
        'by_category': merged_by_category,
        'by_file': merged_by_file,
    }
