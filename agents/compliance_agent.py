import os
import re
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import json
from datetime import datetime
from mcp_server.tools.commit_analyzer import CommitAnalyzer

_MAX_RETRIES = 3
_RETRY_DELAY = 10  # seconds between retries on 503


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


class ComplianceAgent:
    def __init__(self, model_name="gemini-pro"):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

    def unified_analysis(self, repo_path, requirements_text, dos_donts_text=""):
        """
        Performs a Unified Quality Analysis:
        - Requirement Drift (Missing/Extra/Modified)
        - Feature Completeness (Feature Loss)
        - Guideline Coverage (Do's & Don'ts)
        """
        code_context = self._get_code_summary(repo_path)
        
        prompt = PromptTemplate(
            template="""
            You are a Senior Quality & Compliance Auditor. 
            Perform a UNIFIED ANALYSIS of the implemented code against requirements and guidelines.
            
            Requirements Document:
            {requirements}
            
            Do's and Don'ts Guidelines:
            {dos_donts}
            
            Implemented Code Context:
            {code_context}
            
            Your Task:
            Analyze the code for THREE critical areas and provide a comprehensive report:
            
            1. **REQUIREMENT DRIFT**:
               - Detect **MISSING** features (in requirements but not in code).
               - Detect **EXTRA** features (in code but not in requirements - "Gold Plating").
               - Detect **MODIFIED** features (implemented differently than required).
               
            2. **FEATURE COMPLETENESS**:
               - Identify features from requirements that are partially implemented or missing.
               - Assess implementation quality and depth.
               
            3. **GUIDELINE COVERAGE (Do's & Don'ts)**:
               - Validate if "Do's" are followed and "Don'ts" are avoided.
               - Identify gaps in best practices, security, and error handling.
            
            Scoring Rubric (0 to 100):
            - **Start at 100 points**.
            - Subtract points for each confirmed issue found.
            - **MINIMUM SCORE IS 0, MAXIMUM TOTAL DEDUCTION IS 55 POINTS** (score cannot go below 45 unless there are 8+ critical issues with clear evidence).
            - -6: Major feature completely absent with NO equivalent implementation anywhere in the codebase.
            - -4: Violation of a critical "Don't" guideline (e.g., hardcoded secrets, SQL injection risk).
            - -3: Feature implemented differently than specified but still functional.
            - -3: Missing a critical "Do" (e.g., no input validation on a public endpoint).
            - -1: Minor extra feature (gold plating) that doesn't break anything.
            - -1: Minor guideline deviation or code smell with low risk.

            **STRICT evidence requirement — BEFORE deducting any points**:
            - You MUST cite a specific file and line number as evidence. If you cannot point to a specific file/line that proves the issue, DO NOT raise it.
            - "Feature not found" is NOT sufficient — you must confirm the feature is absent after scanning the full code context.
            - If a feature exists in a different file or with a slightly different name/approach, do NOT mark it as missing.

            **IMPORTANT scoring guidance**:
            - Give benefit of the doubt when intent is clear even if implementation differs slightly.
            - Partial implementations that cover the core use case should NOT be treated as fully missing — deduct -3 max, not -6.
            - Extra features (gold plating) are only a problem if they actively conflict with requirements; otherwise deduct minimally or skip.
            - Do NOT stack multiple deductions for the same root cause. Pick the most applicable penalty.
            - If requirements are short or high-level, be more lenient — do not invent issues where the requirements are ambiguous.
            - A score of 70-85 is healthy and expected for a typical working codebase with minor gaps.
            - If no requirements document is provided, focus only on clear code quality issues and guidelines.

            **DEDUPLICATION**: If two or more issues are semantically the same (e.g., a "missing feature" and a "coverage gap" describing the same thing), merge them into a single concise item. Aim for the minimum number of distinct issues.
            
            For EACH issue, provide:
            - **Type**: Drift/Completeness/Guideline Violation
            - **Description**: What is the issue?
            - **Evidence**: Specific file and LINE NUMBERS (e.g., app.py:L45-L50) where the issue or relevant code is found. Provide the code snippet if useful.
            - **Reasoning**: Why is this a problem?
            - **Remediation**: AI-powered instructions for the fix.
            
            Output JSON format ONLY:
            {{
                "score": 85,
                "summary": "Overall quality summary...",
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
            input_variables=["requirements", "dos_donts", "code_context"]
        )
        
        chain = prompt | self.llm
        try:
            response = _invoke_with_retry(chain, {
                "requirements": requirements_text[:10000],
                "dos_donts": dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
                "code_context": code_context
            })
            content = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

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

    def analyze_module_focus(self, repo_path, module_name, requirements_text="", dos_donts_text=""):
        """
        Performs a focused compliance analysis on a named module:
        - Identifies files that belong to the module
        - Finds where the module is referenced elsewhere
        - Runs LLM analysis on the module code vs requirements
        """
        module_files = self._find_module_files(repo_path, module_name)
        module_usages = self._find_module_usages(repo_path, module_name, module_files)
        module_code = self._get_module_code_context(
            repo_path, [mf["path"] for mf in module_files]
        )

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
            content = response.content.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(content)
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

    def _get_code_summary(self, repo_path):
        # Universal file reader
        summary = ""
        # Directories to ignore
        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'build', 'dist', '.next', '.venv', 'venv', 'env', '.idea', '.vscode'}
        
        for root, dirs, files in os.walk(repo_path):
            # Prune ignore_dirs to prevent walking into them
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            summary += f"\nDirectory: {root}\nFiles: {', '.join(files)}\n"
            for file in files:
                 # Skip known binary/system/metadata files
                 if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.pyc', '.git', '.exe', '.dll', '.so', '.dylib', '.pdf', '.zip', '.tar.gz', '-lock.json', '.lock', '.log')):
                     continue
                     
                 # Try to read every file as text with multiple encodings
                 file_path = os.path.join(root, file)
                 try:
                    # Skip files larger than 100KB to avoid filling buffer with single file
                    if os.path.getsize(file_path) > 102400:
                        continue
                        
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        # Limit characters per file but with line indexing
                        content_with_lines = ""
                        current_chars = 0
                        for i, line in enumerate(lines, 1):
                            line_entry = f"{i}: {line}"
                            if current_chars + len(line_entry) > 3000:
                                break
                            content_with_lines += line_entry
                            current_chars += len(line_entry)
                        
                        summary += f"--- {file} ---\n{content_with_lines}\n"
                 except: 
                     # Skip non-text files
                     pass
        return summary[:45000] # Slightly increased buffer for better coverage


    def analyze_feature_loss_with_history(self, repo_path, requirements_text, dos_donts_text="", base_commit=None, head_commit=None):
        """
        Analyzes feature loss by comparing commit history with requirements.
        Detects features that existed in earlier commits but were removed.
        """
        # Get commit analysis
        commit_analyzer = CommitAnalyzer(repo_path)
        commit_history = commit_analyzer.get_commit_history(max_commits=50)
        
        if len(commit_history) < 2:
            return {
                "error": "Not enough commit history to analyze feature loss",
                "score": 0
            }
        
        # Determine commit range
        if not head_commit:
            head_commit = commit_history[0]["hash"]
        
        if not base_commit:
            # If no base provided, compare against the oldest available commit
            base_commit = commit_history[-1]["hash"]
        
        # Get detailed diff between base and head
        full_diff = commit_analyzer.get_full_diff_between_commits(base_commit, head_commit)
        
        # Get commit history context for the range
        history_context = commit_analyzer.get_feature_loss_context(max_commits=50)
        
        # Get current code context
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
                        "evidence": "Describe deleted vs added code, include LINE NUMBERS if possible (e.g. from diff context)",
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
                "head_hash": head_commit[:8]
            })
            content = response.content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)

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
                "analysis_date": str(datetime.now())
            }

            return result
        except Exception as e:
            return {
                "error": str(e),
                "feature_loss_score": 0,
                "feature_changes": [],
                "summary": f"Feature history analysis failed: {str(e)}"
            }
