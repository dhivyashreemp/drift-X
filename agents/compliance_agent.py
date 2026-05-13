import os
import re
import time
import boto3
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
import json
from datetime import datetime
from mcp_server.tools.commit_analyzer import CommitAnalyzer

_MAX_RETRIES = 3
_RETRY_DELAY = 10  # seconds between retries on 503


def _extract_text(response) -> str:
    """Extract plain text from a ChatBedrock response regardless of content format."""
    content = response.content
    # Some Bedrock models return a list of content blocks instead of a plain string
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content) if content is not None else ""


def _parse_json(raw: str) -> dict:
    """Strip markdown fences and extract JSON from LLM output, repairing common issues."""
    from json_repair import repair_json
    text = raw.replace("```json", "").replace("```", "").strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract first {...} block then repair
    match = re.search(r'\{.*\}', text, re.DOTALL)
    candidate = match.group() if match else text
    try:
        return json.loads(repair_json(candidate))
    except Exception:
        raise ValueError(f"Could not parse LLM response as JSON. Raw (first 300 chars): {text[:300]}")


def _invoke_with_retry(chain, inputs):
    """Invoke an LLM chain with exponential-backoff retry on transient API errors."""
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            return chain.invoke(inputs)
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                code in err_str for code in ["503", "UNAVAILABLE", "429", "ResourceExhausted", "overloaded"]
            )
            if is_transient and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_DELAY * (2 ** attempt)
                time.sleep(wait)
                last_error = e
            else:
                raise
    raise last_error


def _build_llm() -> ChatBedrock:
    model_id = os.getenv("BEDROCK_MODEL_ID", "openai.gpt-oss-120b-1:0")
    region = os.getenv("AWS_REGION", "ap-south-1")
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return ChatBedrock(
        model_id=model_id,
        client=client,
        model_kwargs={
            "temperature": 0.0,
            "seed": 42,
            "top_p": 1.0,
        },
    )


class ComplianceAgent:
    def __init__(self):
        self.llm = _build_llm()

    def unified_analysis(self, repo_paths, requirements_text, dos_donts_text=""):
        """
        Performs a Unified Quality Analysis across 6 dimensions:
        - Requirement Drift, Feature Completeness, Security Vulnerabilities,
          Code Quality, Error Handling, Testing Coverage
        """
        code_context = self._get_code_summary(repo_paths)

        prompt = PromptTemplate(
            template="""
            You are a Senior Quality & Security Auditor and strict gatekeeper for production deployments.
            Perform a COMPREHENSIVE QUALITY ANALYSIS of the implemented code against requirements, guidelines, and engineering best practices.

            Requirements Document:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            Implemented Code Context:
            {code_context}

            Your Task:
            Audit the code across SIX quality dimensions. Be thorough and strict — your goal is to surface real risks before they reach production.

            1. **REQUIREMENT DRIFT**:
               - Detect MISSING features (in requirements but not in code).
               - Detect EXTRA features in code not asked for ("Gold Plating") that add risk or complexity.
               - Detect MODIFIED features implemented differently than specified.

            2. **FEATURE COMPLETENESS**:
               - Identify requirements that are partially implemented or absent.
               - Assess whether the implementation actually fulfils the intent, not just the surface wording.

            3. **SECURITY VULNERABILITIES** (highest priority — no benefit of doubt):
               - OWASP Top 10: injection (SQL/command/LDAP), broken authentication, XSS, IDOR, security misconfiguration, sensitive data exposure, XML/deserialization attacks, broken access control.
               - Hardcoded secrets, API keys, passwords, or tokens directly in source code.
               - Missing authentication or authorization checks on sensitive endpoints.
               - Missing or inadequate input validation on all user-facing or API inputs.
               - Insecure HTTP methods allowed where they should be restricted.
               - Verbose error messages that expose internal stack traces or DB schemas.

            4. **CODE QUALITY**:
               - High cyclomatic complexity: deeply nested conditionals (>4 levels), functions longer than 100 lines.
               - Duplicated logic that should be extracted into shared utilities.
               - Dead code or unreachable branches left in production paths.
               - Naming that is misleading, overly abbreviated, or inconsistent with the project's conventions.
               - Missing or inadequate documentation on all public APIs and non-obvious logic.

            5. **ERROR HANDLING**:
               - External calls (database, third-party API, file I/O, network) must have try/catch or equivalent.
               - Bare `except:` or empty `catch {{}}` blocks that silently swallow errors are a defect.
               - API endpoints must return structured, meaningful error responses — not raw exceptions.
               - Async operations must have proper rejection/error propagation.
               - Critical failures must be logged with enough context to diagnose in production.

            6. **TESTING COVERAGE**:
               - Are there test files present? If zero tests exist, that is a critical gap.
               - Do tests cover the critical paths (auth, data writes, payment, permissions)?
               - Are edge cases and error paths tested — not just happy-path flows?
               - Are security-sensitive functions (input validation, auth checks) covered by tests?

            Scoring Rubric (0 to 100):
            - Start at 100 points.
            - Subtract EXACT points per confirmed issue — choose the single best-fit deduction, do not stack for the same root cause.
            - MAXIMUM TOTAL DEDUCTION IS 70 POINTS.

            Security deductions (no benefit of the doubt — apply if the risk exists):
              -10: Critical security flaw — hardcoded secret in source, SQL/command injection, broken authentication, RCE risk.
              -7: High security risk — missing input validation on a public endpoint, IDOR, sensitive data returned without masking.
              -5: Medium security risk — verbose error exposing internals, missing rate limiting on auth endpoints, weak token handling.

            Requirement & completeness deductions:
              -6: Major feature completely absent — confirmed missing after scanning the full code context.
              -4: Violation of a critical guideline from the Do's & Don'ts.
              -3: Feature implemented differently than specified but still functionally equivalent.
              -3: Missing a critical "Do" from the guidelines.
              -2: Partial implementation that covers the core use case but is noticeably incomplete.
              -1: Minor gold plating that doesn't conflict with requirements.
              -1: Minor guideline deviation or low-risk code smell.

            Quality deductions:
              -5: Zero test coverage — no test files found anywhere in the codebase.
              -4: Critical external calls (DB, API, file I/O) with no error handling whatsoever.
              -3: Silent error swallowing in a production-critical path (bare except / empty catch).
              -3: High cyclomatic complexity making a critical function unmaintainable (>4 nesting levels or >150 lines).
              -2: Missing tests for a security-sensitive function (auth, permissions, payments).
              -1: Missing documentation on a public API or module.

            STRICT evidence requirement — BEFORE deducting any points:
            - Cite a specific file and line number. If you cannot point to a concrete location, do NOT raise the issue.
            - "Feature not found" is insufficient — you must confirm absence after scanning the entire code context.
            - If a feature exists under a different name or equivalent approach, do NOT mark it missing.

            DEDUPLICATION: If two findings describe the same root cause, merge them into one. Aim for the minimum number of distinct, actionable issues.

            For EACH issue provide:
            - type: one of — Security Vulnerability / Requirement Drift / Feature Completeness / Code Quality / Error Handling / Testing Gap / Guideline Violation
            - description: clear, plain-English statement of the problem
            - evidence: specific file path and line numbers (e.g., backend/main.py:L45-L52) plus a short code snippet
            - reasoning: why this matters in production
            - remediation: concrete step-by-step fix the developer should apply

            Output JSON format ONLY — no markdown, no commentary outside the JSON:
            {{
                "score": 78,
                "summary": "Overall quality summary in plain English...",
                "issues": [
                    {{
                        "type": "Security Vulnerability",
                        "description": "...",
                        "evidence": "...",
                        "reasoning": "...",
                        "remediation": "..."
                    }}
                ]
            }}
            """,
            input_variables=["requirements", "dos_donts", "code_context"]
        )
        
        chain = prompt | self.llm
        try:
            response = _invoke_with_retry(chain, {
                "requirements": requirements_text[:10000],
                "dos_donts": dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
                "code_context": code_context
            })
            data = _parse_json(_extract_text(response))

            if "score" in data:
                try:
                    data["score"] = max(0.0, min(100.0, float(data["score"])))
                except Exception:
                    data["score"] = 0.0
            return data
        except Exception as e:
            return {
                "error": str(e),
                "score": 0,
                "issues": [],
                "summary": f"Unified analysis failed: {str(e)}"
            }


    # ── Module Analysis ──────────────────────────────────────────────────────

    _IGNORE_DIRS = {
        '.git', 'node_modules', '__pycache__', 'build', 'dist',
        '.next', '.venv', 'venv', 'env', '.idea', '.vscode',
        'coverage', '.pytest_cache', 'migrations',
    }
    _CODE_EXTS = {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go',
        '.rb', '.php', '.swift', '.kt', '.rs', '.scala',
        '.jsx', '.tsx', '.vue', '.html', '.css', '.scss',
    }

    def _module_keywords(self, module_name):
        """Split module name into search keywords, dropping generic words."""
        stop = {"module", "service", "component", "handler", "manager", "controller"}
        raw = re.split(r'[\s_\-/]+', module_name.strip())
        return [w.lower() for w in raw if w and w.lower() not in stop]

    def _find_module_files(self, repo_path, module_name):
        """
        Return a list of dicts {path, score} for files related to module_name.
        Score is higher when the keyword appears in the file path.
        """
        keywords = self._module_keywords(module_name)
        if not keywords:
            return []

        matches = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self._IGNORE_DIRS]
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, repo_path).replace("\\", "/")
                rel_lower = rel.lower()

                score = 0
                for kw in keywords:
                    if kw in rel_lower:
                        score += 3

                # Also scan file content if no path hit and extension matches
                if score == 0 and os.path.splitext(fname)[1] in self._CODE_EXTS:
                    try:
                        if os.path.getsize(full) < 102400:
                            with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                                snippet = fh.read(4000).lower()
                            for kw in keywords:
                                if kw in snippet:
                                    score += 1
                    except Exception:
                        pass

                if score > 0:
                    matches.append({"path": rel, "score": score})

        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def _find_module_usages(self, repo_path, module_name, module_files):
        """
        Scan all files NOT in module_files for references to the module.
        Returns {rel_path: [{line, content}, ...]} for files that reference the module.
        """
        keywords = self._module_keywords(module_name)
        if not keywords:
            return {}

        module_paths = {mf["path"] for mf in module_files}
        usages = {}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self._IGNORE_DIRS]
            for fname in files:
                if os.path.splitext(fname)[1] not in self._CODE_EXTS:
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, repo_path).replace("\\", "/")
                if rel in module_paths:
                    continue
                try:
                    if os.path.getsize(full) > 204800:
                        continue
                    with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                        lines = fh.readlines()
                    hits = []
                    for i, line in enumerate(lines, 1):
                        ll = line.lower()
                        if any(kw in ll for kw in keywords):
                            hits.append({"line": i, "content": line.rstrip()})
                            if len(hits) >= 10:
                                break
                    if hits:
                        usages[rel] = hits
                except Exception:
                    pass

        return usages

    def _get_module_code_context(self, repo_path, file_rel_paths):
        """Read code content from a list of relative file paths."""
        context = ""
        for rel in file_rel_paths[:12]:
            full = os.path.join(repo_path, rel)
            try:
                if os.path.getsize(full) > 102400:
                    continue
                with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = fh.readlines()
                snippet = ""
                chars = 0
                for i, line in enumerate(lines, 1):
                    entry = f"{i}: {line}"
                    if chars + len(entry) > 3000:
                        break
                    snippet += entry
                    chars += len(entry)
                context += f"\n--- {rel} ---\n{snippet}\n"
            except Exception:
                pass
        return context[:15000]

    def analyze_module_focus(self, repo_paths, module_name, requirements_text="", dos_donts_text=""):
        """
        Performs a focused compliance analysis on a named module across all repos.
        repo_paths: str or list of (path, label) tuples
        """
        entries = [(repo_paths, None)] if isinstance(repo_paths, str) else repo_paths

        all_module_files, all_usages, all_code = [], {}, ""
        for repo_path, label in entries:
            prefix = f"[{label}] " if label else ""
            mf = self._find_module_files(repo_path, module_name)
            mu = self._find_module_usages(repo_path, module_name, mf)
            mc = self._get_module_code_context(repo_path, [f["path"] for f in mf])
            all_module_files.extend({"path": f"{prefix}{f['path']}", "score": f["score"]} for f in mf)
            all_usages.update({f"{prefix}{k}": v for k, v in mu.items()})
            if label:
                all_code += f"\n=== REPO: {label} ===\n"
            all_code += mc

        module_files = all_module_files
        module_usages = all_usages
        module_code = all_code[:15000]

        prompt = PromptTemplate(
            template="""
            You are a Code Analyst performing a focused review of a specific software module.

            Module Name: {module_name}

            Module Files (code from files identified as part of this module):
            {module_code}

            Requirements / Specification:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            Your Tasks:
            1. Describe the module's purpose and responsibilities.
            2. List its key components (classes, functions, routes, models, etc.).
            3. Identify compliance issues specific to this module compared to requirements.
            4. Flag any guideline violations (Do's not followed / Don'ts present).
            5. Provide an overall compliance score for this module (0–100).

            Output JSON format ONLY:
            {{
                "module_purpose": "...",
                "key_components": ["...", "..."],
                "compliance_score": 85,
                "summary": "...",
                "issues": [
                    {{
                        "type": "...",
                        "description": "...",
                        "evidence": "...",
                        "reasoning": "...",
                        "remediation": "..."
                    }}
                ]
            }}
            """,
            input_variables=["module_name", "module_code", "requirements", "dos_donts"]
        )

        chain = prompt | self.llm
        try:
            response = _invoke_with_retry(chain, {
                "module_name": module_name,
                "module_code": module_code if module_code else "No module files found.",
                "requirements": requirements_text[:8000] if requirements_text else "No requirements provided.",
                "dos_donts": dos_donts_text[:3000] if dos_donts_text else "No guidelines provided.",
            })
            analysis = _parse_json(_extract_text(response))
        except Exception as e:
            analysis = {
                "module_purpose": "Analysis failed.",
                "key_components": [],
                "compliance_score": 0,
                "summary": f"Module analysis error: {str(e)}",
                "issues": []
            }

        return {
            "module_name": module_name,
            "related_files": [mf["path"] for mf in module_files],
            "usage_in_files": module_usages,
            "analysis": analysis,
            "file_count": len(module_files),
            "usage_count": len(module_usages),
        }

    def _get_code_summary(self, repo_paths):
        """
        repo_paths: str (single path) or list of (path, label) tuples
        Returns combined code context capped at 45K chars total.
        """
        if isinstance(repo_paths, str):
            entries = [(repo_paths, None)]
        else:
            entries = repo_paths

        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'build', 'dist', '.next', '.venv', 'venv', 'env', '.idea', '.vscode'}
        skip_exts = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.pyc', '.git', '.exe', '.dll', '.so', '.dylib', '.pdf', '.zip', '.tar.gz', '-lock.json', '.lock', '.log')

        # Budget chars per repo evenly
        total_budget = 45000
        per_repo = total_budget // len(entries)

        summary = ""
        for repo_path, label in entries:
            if label:
                summary += f"\n{'='*50}\nREPO: {label}\n{'='*50}\n"
            repo_chars = 0
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = sorted(d for d in dirs if d not in ignore_dirs)
                files = sorted(files)
                summary += f"\nDirectory: {root}\nFiles: {', '.join(files)}\n"
                for file in files:
                    if file.endswith(skip_exts):
                        continue
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getsize(file_path) > 102400:
                            continue
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        content_with_lines = ""
                        current_chars = 0
                        for i, line in enumerate(lines, 1):
                            line_entry = f"{i}: {line}"
                            if current_chars + len(line_entry) > 3000:
                                break
                            content_with_lines += line_entry
                            current_chars += len(line_entry)
                        chunk = f"--- {file} ---\n{content_with_lines}\n"
                        if repo_chars + len(chunk) > per_repo:
                            break
                        summary += chunk
                        repo_chars += len(chunk)
                    except Exception:
                        pass

        return summary[:total_budget]


    def analyze_feature_loss_with_history(self, repo_entries, requirements_text, dos_donts_text="", base_commit=None, head_commit=None):
        """
        Analyzes feature loss across one or more repos.
        repo_entries: str (single path, legacy) or list of (path, base_commit, head_commit) tuples.
        """
        # Normalize input
        if isinstance(repo_entries, str):
            entries = [(repo_entries, base_commit, head_commit)]
        else:
            entries = repo_entries  # [(path, base_commit, head_commit), ...]

        all_changes = []
        combined_metadata = {}
        first_result = None

        for repo_path, base_c, head_c in entries:
            result = self._analyze_single_repo_history(
                repo_path, requirements_text, dos_donts_text, base_c, head_c
            )
            if first_result is None:
                first_result = result
            all_changes.extend(result.get("feature_changes", []))
            if not combined_metadata:
                combined_metadata = result.get("analysis_metadata", {})

        if first_result is None:
            return {"error": "No repos to analyze", "feature_changes": [], "feature_loss_score": 0}

        first_result["feature_changes"] = all_changes
        first_result["analysis_metadata"] = combined_metadata
        return first_result

    def _analyze_single_repo_history(self, repo_path, requirements_text, dos_donts_text, base_commit, head_commit):
        commit_analyzer = CommitAnalyzer(repo_path)
        commit_history = commit_analyzer.get_commit_history(max_commits=50)

        if len(commit_history) < 2:
            return {"error": "Not enough commit history", "feature_changes": [], "feature_loss_score": 0, "summary": ""}

        if not head_commit:
            head_commit = commit_history[0]["hash"]
        if not base_commit:
            base_commit = commit_history[-1]["hash"]

        full_diff = commit_analyzer.get_full_diff_between_commits(base_commit, head_commit)
        history_context = commit_analyzer.get_feature_loss_context(max_commits=50)
        code_context = self._get_code_summary(repo_path)

        prompt = PromptTemplate(
            template="""
            You are a Feature Loss Detective analyzing commit history to identify removed features.

            Requirements Document:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            Current Code Context (Current Implementation):
            {code_context}

            Commit History Timeline:
            {commit_analysis}

            Full Code Diff (Between Base: {base_hash} and Head: {head_hash}):
            {deletions}

            Your Task:
            1. **Identify Feature Loss**: Find features that existed in requirements or base commits but are now altered/removed.
            2. **Detect REPLACEMENTS**: Check if code marked with '-' (deleted) was replaced by code marked with '+' (added) or exists in the Current Implementation.
               - If it was replaced by new logic performing the same feature, mark it as "Replacement - Feature Preserved".
               - If it was deleted/changed with NO equivalent code found, mark it as "Accidental Loss - Feature Missing".
            3. **Analyze Entire Evolution**: Take into account the whole commit history provided to understand the developer's intent.

            Scoring Rubric (0 to 100):
            - **Start at 100 points**.
            - Subtract points for each confirmed feature loss.
            - **MINIMUM SCORE IS 0, MAXIMUM TOTAL DEDUCTION IS 50 POINTS**.
            - -8: Critical feature deleted with NO equivalent replacement anywhere in the codebase.
            - -3: Feature replaced with noticeably inferior logic (measurable regression).
            - -0: Feature replaced with equivalent or better logic (healthy refactor — no penalty).

            **IMPORTANT scoring guidance**:
            - A refactor, rename, or restructure is NOT a feature loss. Only penalise genuine removals where the functionality is truly gone.
            - If the deleted code has a functional equivalent elsewhere in the current codebase, treat it as "Replacement - Feature Preserved" with zero deduction.
            - Do NOT stack deductions for the same deleted block across multiple findings.
            - When in doubt whether something was intentionally removed vs accidentally lost, lean toward "Replacement" status.
            - A score of 75-90 is typical for a codebase that has been actively refactored.

            Output JSON format ONLY:
            {{
                "feature_loss_score": 85,
                "base_commit": "{base_hash}",
                "head_commit": "{head_hash}",
                "feature_changes": [
                    {{
                        "feature_name": "...",
                        "status": "Loss/Replacement/Updated",
                        "severity": "Critical/High/Medium/Low",
                        "evidence": "Describe deleted vs added code, include LINE NUMBERS if possible",
                        "replacement_logic": "Explain the new logic found",
                        "requirement_reference": "...",
                        "impact": "...",
                        "commit_info": "...",
                        "reasoning": "...",
                        "remediation": "..."
                    }}
                ],
                "summary": "Full evolution summary..."
            }}
            """,
            input_variables=["requirements", "dos_donts", "code_context", "commit_analysis", "deletions", "base_hash", "head_hash"]
        )

        chain = prompt | self.llm
        try:
            response = _invoke_with_retry(chain, {
                "requirements": requirements_text[:10000],
                "dos_donts": dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
                "code_context": code_context[:15000],
                "commit_analysis": json.dumps(history_context, indent=2)[:5000],
                "deletions": json.dumps(full_diff, indent=2)[:5000],
                "base_hash": base_commit[:8],
                "head_hash": head_commit[:8],
            })
            result = _parse_json(_extract_text(response))

            if "feature_loss_score" in result:
                try:
                    result["feature_loss_score"] = max(0.0, min(100.0, float(result["feature_loss_score"])))
                except Exception:
                    result["feature_loss_score"] = 0.0

            result["analysis_metadata"] = {
                "repo_path": repo_path,
                "total_commits": len(commit_history),
                "base_commit": base_commit,
                "head_commit": head_commit,
                "analysis_date": str(datetime.now()),
            }
            return result
        except Exception as e:
            return {
                "error": str(e),
                "feature_loss_score": 0,
                "feature_changes": [],
                "summary": f"Feature history analysis failed: {str(e)}",
            }
