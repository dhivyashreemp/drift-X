import os
import re
import time
import json
import boto3
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from langchain_core.prompts import PromptTemplate
from datetime import datetime
from mcp_server.tools.commit_analyzer import CommitAnalyzer

_MAX_RETRIES = 3
_RETRY_DELAY = 10


def _build_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _extract_invoke_model_text(body_bytes: bytes) -> str:
    result = json.loads(body_bytes)
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    if "content" in result:
        blocks = result["content"]
        if isinstance(blocks, list):
            return "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        return str(blocks)
    if "results" in result:
        return result["results"][0].get("outputText", "")
    return str(result)


def _call_bedrock(client, model_id: str, prompt_text: str, max_tokens: int = 8192) -> str:
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt_text}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": max_tokens},
        )
        blocks = response.get("output", {}).get("message", {}).get("content", [])
        text = "".join(b["text"] for b in blocks if isinstance(b, dict) and "text" in b)
        if text:
            return text
    except Exception:
        pass

    is_claude = "anthropic" in model_id.lower()
    if is_claude:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}],
        })
    else:
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        })
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    text = _extract_invoke_model_text(response["body"].read())
    if not text:
        raise ValueError("invoke_model returned an empty response")
    return text


def _invoke(client, model_id: str, prompt_text: str, max_tokens: int = 8192) -> str:
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            return _call_bedrock(client, model_id, prompt_text, max_tokens)
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                code in err_str for code in ["503", "UNAVAILABLE", "429", "ResourceExhausted", "overloaded", "ThrottlingException"]
            )
            if is_transient and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_DELAY * (2 ** attempt)
                time.sleep(wait)
                last_error = e
            else:
                raise
    raise last_error


def _parse_json(raw: str) -> dict:
    """Strip markdown fences and extract JSON from LLM output, repairing common issues."""
    from json_repair import repair_json
    text = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    candidate = match.group() if match else text
    try:
        return json.loads(repair_json(candidate))
    except Exception:
        raise ValueError(f"Could not parse LLM response as JSON. Raw (first 300 chars): {text[:300]}")


def _invoke_and_parse(client, model_id: str, prompt_text: str, max_tokens: int = 8192) -> dict:
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            raw = _invoke(client, model_id, prompt_text, max_tokens)
            return _parse_json(raw)
        except ValueError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2)
        except Exception:
            raise
    raise last_error


class ComplianceAgent:
    def __init__(self):
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "arn:aws:bedrock:ap-south-1:453194202893:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.client = _build_client()

    def unified_analysis(self, repo_paths, requirements_text, dos_donts_text=""):
        """
        Performs a Unified Quality Analysis across 10 dimensions:
        Requirement Drift, Feature Completeness, Security, Code Quality,
        Error Handling, Testing, Performance, Deployment Readiness,
        Observability, Dependency Health.
        """
        code_context = self._get_code_summary(repo_paths)

        prompt = PromptTemplate(
            template="""
            You are a Senior Staff Engineer and the final deployment gatekeeper. Your approval or rejection directly determines whether this code ships to production. You have seen codebases fail in production due to missed issues at review time — do not let that happen here. Be exhaustive, be strict, cite exact evidence for every finding, and provide actionable step-by-step remediation that a developer can apply immediately.

            Requirements Document:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            Implemented Code Context (entire repository — all files with line numbers):
            {code_context}

            ═══════════════════════════════════════════════
            AUDIT DIMENSIONS — analyse ALL ten, no skipping
            ═══════════════════════════════════════════════

            1. REQUIREMENT DRIFT
               - MISSING features: present in requirements but absent from code after exhaustive scan.
               - EXTRA features ("Gold Plating"): code that adds scope, complexity, or attack surface beyond what was asked.
               - MODIFIED features: implemented differently from specification in a way that changes behaviour or breaks the contract.

            2. FEATURE COMPLETENESS
               - Trace every requirement to its implementation. Partial implementations that cover the happy path but miss edge cases or secondary flows count as incomplete.
               - Assess intent, not just surface wording — if the requirement says "users can reset their password", check the full reset flow (request, token, validation, expiry, confirmation), not just the presence of a reset route.

            3. SECURITY VULNERABILITIES (highest priority — zero benefit of the doubt)
               - OWASP Top 10: SQL/command/LDAP injection, broken authentication, XSS, IDOR, security misconfiguration, sensitive data exposure, XML/deserialization attacks, broken access control, SSRF.
               - Hardcoded secrets, API keys, passwords, tokens, or connection strings anywhere in source code or config files committed to the repo.
               - Missing or bypassable authentication and authorisation checks on every sensitive endpoint.
               - Missing or incomplete input validation on ALL user-facing and API inputs — check type, length, format, and allowed value ranges.
               - Insecure HTTP methods (PUT/DELETE/PATCH) allowed where they should be restricted.
               - Verbose error messages, stack traces, or DB schema details exposed to API callers.
               - Insecure direct object references — any endpoint that takes an ID from the caller without verifying ownership.
               - Missing CSRF protection on state-changing endpoints.
               - Insecure cookie flags (missing HttpOnly, Secure, SameSite).

            4. CODE QUALITY
               - Cyclomatic complexity: functions with >4 nesting levels or >100 lines without clear sub-function extraction.
               - Duplicated logic that belongs in a shared utility — copy-pasted blocks across files are a maintenance and bug-drift risk.
               - Dead code, commented-out production code, or unreachable branches left in the codebase.
               - Misleading, abbreviated, or inconsistent naming that violates the project's conventions.
               - Any TODO/FIXME/HACK comment in a production code path — these are deferred defects.
               - Magic numbers or hardcoded configuration values that should be constants or env vars.

            5. ERROR HANDLING
               - Every external call (database, third-party API, file I/O, network, cache) must have explicit error handling.
               - Bare `except:` / `catch (e) {{}}` / `except Exception: pass` blocks that silently swallow errors are defects.
               - API endpoints must return structured, machine-readable error responses (error code + message) — not raw Python/JS exceptions.
               - Async operations must propagate rejections — unhandled promise rejections and unhandled async exceptions crash services.
               - Every caught error in a critical path must be logged with enough context (request ID, user ID, input summary) to diagnose in production without a debugger.

            6. TESTING COVERAGE
               - Zero test files anywhere in the repo = critical gap, automatic deduction.
               - Check that tests cover: authentication flows, data write paths, permission checks, payment or financial logic, and all public API endpoints.
               - Edge cases and error paths must be tested — not just happy-path flows.
               - Security-sensitive functions (input validation, auth checks, token generation) must have dedicated tests.
               - Integration tests must exercise real DB/service calls, not just mocked internals.

            7. PERFORMANCE & SCALABILITY
               - N+1 query patterns: loops that issue one DB query per iteration — must use batch queries or JOINs.
               - Missing pagination on any endpoint that returns a collection — unbounded result sets will OOM in production.
               - Synchronous blocking I/O inside async request handlers — blocks the event loop under load.
               - Missing caching on hot read paths that hit the database for every request.
               - Unbounded loops or recursion over user-controlled input size — potential DoS vector.
               - Large in-memory accumulation (building giant lists/strings without streaming).
               - Missing database indexes on columns used in WHERE clauses or JOIN conditions in hot query paths.

            8. DEPLOYMENT READINESS
               - All required environment variables must be validated at application startup — crash fast if a required var is missing, do not silently use a None/null default.
               - Health check endpoint (`/health` or `/ping`) must exist and verify critical dependencies (DB connectivity, cache, external services).
               - Database migration scripts must exist for every schema change and must be idempotent (safe to re-run).
               - Graceful shutdown handling — the app must finish in-flight requests and close DB connections on SIGTERM.
               - No hardcoded hostnames, ports, or environment-specific values in production code paths.
               - Dockerfile or deployment config must not run the service as root.
               - Static assets, secrets, and credentials must not be included in the build artifact.

            9. OBSERVABILITY & LOGGING
               - Structured logging (JSON format with consistent fields: timestamp, level, request_id, user_id, service) must be present on all critical paths.
               - Every incoming API request must be logged with method, path, status code, and latency.
               - Every outgoing external call (DB, API, cache) must log success/failure and latency.
               - Errors must be logged at ERROR level with full context — not silently swallowed or logged at DEBUG.
               - Correlation/request IDs must propagate through all service calls to enable end-to-end tracing.
               - No sensitive data (passwords, tokens, PII) may appear in log output.

            10. DEPENDENCY HEALTH
                - Check requirements.txt / package.json / go.mod / pom.xml for packages with known CVEs or that are flagged as deprecated/abandoned.
                - Unpinned dependency versions (e.g. `requests>=2.0`) in production — version drift can introduce breaking changes or vulnerabilities silently.
                - Any dependency that duplicates standard-library functionality without justification adds unnecessary attack surface.
                - Packages imported but unused in the codebase should be removed to reduce the attack surface.

            ═══════════════════════════════════════
            EXHAUSTIVE SCAN MANDATE
            ═══════════════════════════════════════
            Before raising ANY issue you MUST:
            - Traverse EVERY file in the code context: entry points, routes, controllers, services, utilities, helpers, middlewares, models, config files, test files, and dependency manifests.
            - For each requirement, trace its implementation through every function call chain, loop, conditional branch, and nested block — a feature may be implemented across multiple files or inside a utility under a different name.
            - Check ALL naming variants and equivalent patterns: "login" may appear as "authenticate", "signin", or "session_create" — treat functionally equivalent code as implemented.
            - For each security check, trace the full request path from the entry point through every middleware and handler to confirm whether a protection is truly absent or handled at a different layer.
            - Only after exhausting every file and every code path may you conclude something is absent.

            ═══════════════════════════════════════
            EVIDENCE REQUIREMENT (non-negotiable)
            ═══════════════════════════════════════
            BEFORE deducting any points:
            - Cite the exact file path and line number(s). If you cannot point to a concrete location, do NOT raise the issue.
            - Copy the verbatim lines from the code context into the evidence block.
            - "Feature not found" is not evidence — you must confirm absence after scanning all files, all loops, all branches, all utilities.
            - If a feature exists under a different name or equivalent approach, do NOT mark it missing.

            DEDUPLICATION: If two findings share the same root cause, merge into one entry. Report the minimum set of distinct, actionable issues.

            ═══════════════════════════════════════
            SCORING RUBRIC (start at 100)
            ═══════════════════════════════════════
            Apply the single best-fit deduction per confirmed issue. Do not stack deductions for the same root cause. Maximum total deduction: 75 points.

            Security (zero benefit of doubt):
              -12: Critical — hardcoded secret, SQL/command injection, broken auth, RCE risk, missing auth on sensitive endpoint.
              -8:  High — missing input validation on public endpoint, IDOR, sensitive data without masking, missing CSRF.
              -5:  Medium — verbose error exposing internals, weak token handling, insecure cookie flags, missing rate limit on auth.

            Requirement & completeness:
              -8:  Major feature completely absent — confirmed after exhaustive scan.
              -5:  Critical guideline violated (Do's & Don'ts).
              -4:  Feature partially implemented — core path works but secondary flows or edge cases are missing.
              -3:  Feature implemented differently than specified but functionally equivalent.
              -2:  Minor gold plating that adds unnecessary complexity or attack surface.
              -1:  Minor guideline deviation or low-risk smell.

            Quality & reliability:
              -6:  Zero test coverage — no test files anywhere in the codebase.
              -5:  N+1 query or unbounded collection on a production endpoint.
              -5:  Missing health check or startup env-var validation — deployment will silently misconfigure.
              -4:  Critical external call with zero error handling.
              -4:  Graceful shutdown absent — in-flight requests dropped on deploy/restart.
              -3:  Silent error swallowing (bare except / empty catch) in a production-critical path.
              -3:  High cyclomatic complexity in a critical function (>4 nesting levels or >150 lines).
              -3:  No structured logging on any critical path — incidents are undiagnosable in production.
              -2:  Missing tests for a security-sensitive function.
              -2:  Unpinned production dependency version.
              -1:  Missing public API documentation.
              -1:  TODO/FIXME in a production code path.

            ═══════════════════════════════════════
            OUTPUT FORMAT
            ═══════════════════════════════════════
            Output JSON ONLY — no markdown fences, no commentary outside the JSON object.

            deployment_verdict values: "APPROVED" (score >= 85), "CONDITIONAL" (score 65-84, fix before next release), "BLOCKED" (score < 65, must fix before any deployment).

            For EACH issue ALL five fields are mandatory — vague or one-line answers are rejected:

            type: one of — Security Vulnerability / Requirement Drift / Feature Completeness / Code Quality / Error Handling / Testing Gap / Guideline Violation / Performance Issue / Deployment Readiness / Observability Gap / Dependency Risk

            severity: one of — Critical / High / Medium / Low
              Critical: blocks deployment immediately (hardcoded secret, broken auth, RCE, missing feature entirely, N+1 on prod endpoint, no health check)
              High: must fix before next release (missing input validation, IDOR, silent error swallow on critical path, zero tests)
              Medium: should fix within current sprint (partial feature, high complexity, missing pagination on low-traffic endpoint)
              Low: fix in future sprint (minor naming, missing doc comment, low-risk smell)

            description: 2–3 sentence plain-English explanation of exactly what is wrong and what should have been done instead.

            evidence: three mandatory parts —
              1. Exact file path and line number(s), e.g. "backend/main.py:L45-L52"
              2. Verbatim lines of code copied from the context, in a code block
              3. One sentence on what specifically in those lines is the problem.

            reasoning: 2–4 sentences on real-world production impact — what attack or failure scenario does this enable, what data or service is at risk, what breaks and how.

            remediation: numbered steps (minimum 3) the developer can follow immediately. Include BEFORE/AFTER code snippets showing the exact change required.

            {{
                "score": 78,
                "deployment_verdict": "CONDITIONAL",
                "summary": "- Bullet 1: biggest risk identified\n- Bullet 2: what the code does well\n- Bullet 3: top priority fix needed\n(Write 3-5 bullet points using '- ' prefix. Do NOT write paragraph sentences.)",
                "issues": [
                    {{
                        "type": "Security Vulnerability",
                        "severity": "Critical",
                        "description": "2-3 sentence description of what is wrong and what should be done instead.",
                        "evidence": "backend/main.py:L45-L52\n```python\nexcept Exception:\n    pass\n```\nBare except silently swallows all errors with no logging or reraise.",
                        "reasoning": "2-4 sentences on the real-world production impact and failure/attack scenario.",
                        "remediation": "1. Replace bare except with specific exception type.\n2. Add structured error logging with context.\n3. Return a proper HTTP error response.\nBEFORE:\n```python\nexcept Exception:\n    pass\n```\nAFTER:\n```python\nexcept Exception as e:\n    logger.error('Operation failed', extra={{'request_id': req_id}}, exc_info=e)\n    raise HTTPException(status_code=500, detail='Internal server error')\n```"
                    }}
                ]
            }}
            """,
            input_variables=["requirements", "dos_donts", "code_context"]
        )

        prompt_text = prompt.format(
            requirements=requirements_text[:10000],
            dos_donts=dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
            code_context=code_context,
        )
        try:
            data = _invoke_and_parse(self.client, self.model_id, prompt_text)
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
            You are a Senior Staff Engineer conducting a deep-dive review of a specific software module before it ships to production. Your job is to surface every defect, gap, and risk within this module — not just surface-level issues but anything that would cause an incident, a security breach, or a deployment failure.

            Module Name: {module_name}

            Module Files (full code with line numbers):
            {module_code}

            Requirements / Specification:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            ═══════════════════════════════════════
            EXHAUSTIVE SCAN MANDATE
            ═══════════════════════════════════════
            Before raising any issue you MUST:
            - Read through EVERY function, every loop, every conditional branch, and every helper across all module files.
            - Trace each requirement through the full call chain — a requirement may be fulfilled deep inside a utility, middleware, or shared service referenced by this module.
            - Check all naming variants: "validate input" may appear as "sanitize", "check_payload", or "schema.parse" — treat functionally equivalent code as compliant.
            - Only mark something missing after confirming its complete absence across all scanned paths, all branches, and all utility references.

            ═══════════════════════════════════════
            AUDIT SCOPE FOR THIS MODULE
            ═══════════════════════════════════════
            1. MODULE PURPOSE — what it owns, its boundaries, its responsibilities.
            2. KEY COMPONENTS — every class, function, route, model, and service this module exposes or consumes.
            3. REQUIREMENT COMPLIANCE — for each requirement, confirm implemented/partial/absent with evidence.
            4. SECURITY — auth checks, input validation, data exposure, injection risks within this module's code paths.
            5. ERROR HANDLING — every external call, every failure path inside the module.
            6. PERFORMANCE — N+1 queries, unbounded loops, missing pagination, blocking I/O within module paths.
            7. OBSERVABILITY — is this module's critical logic logged with enough context to diagnose production incidents?
            8. GUIDELINE VIOLATIONS — Do's not followed, Don'ts present in this module's code.
            9. DEPLOYMENT IMPACT — does this module have any hardcoded config, missing env validation, or migration gaps?

            ═══════════════════════════════════════
            EVIDENCE REQUIREMENT (non-negotiable)
            ═══════════════════════════════════════
            For EACH issue ALL five fields are mandatory:
            - type: one of — Security Vulnerability / Requirement Drift / Feature Completeness / Code Quality / Error Handling / Testing Gap / Guideline Violation / Performance Issue / Deployment Readiness / Observability Gap
            - description: 2–3 sentences on exactly what is wrong and what should have been done.
            - evidence: exact file path + line number(s) + verbatim code snippet in a code block + one sentence on what is wrong in those specific lines.
            - reasoning: 2–4 sentences on real-world production impact — what breaks, what is at risk, what incident scenario does this enable.
            - remediation: numbered steps (minimum 3) with BEFORE/AFTER code snippets the developer can apply immediately.

            Output JSON ONLY — no markdown, no commentary outside the JSON:
            {{
                "module_purpose": "2-3 sentence description of what this module owns and is responsible for.",
                "key_components": ["ClassName", "function_name", "route /path", "..."],
                "compliance_score": 85,
                "summary": "- Bullet 1: what this module does well\n- Bullet 2: biggest gap or risk\n- Bullet 3: top fix needed before deployment\n(Write 3-5 bullet points using '- ' prefix. Do NOT write paragraph sentences.)",
                "issues": [
                    {{
                        "type": "Security Vulnerability",
                        "severity": "Critical",
                        "description": "2-3 sentence description of what is wrong and what should be done instead.",
                        "evidence": "module/file.py:L10-L15\n```python\nverbatim code\n```\nOne sentence on what is wrong in these specific lines.",
                        "reasoning": "2-4 sentences on the production impact — what breaks, what is at risk.",
                        "remediation": "1. Step one.\n2. Step two.\n3. Step three.\nBEFORE:\n```python\nbroken code\n```\nAFTER:\n```python\nfixed code\n```"
                    }}
                ]
            }}
            """,
            input_variables=["module_name", "module_code", "requirements", "dos_donts"]
        )

        prompt_text = prompt.format(
            module_name=module_name,
            module_code=module_code if module_code else "No module files found.",
            requirements=requirements_text[:8000] if requirements_text else "No requirements provided.",
            dos_donts=dos_donts_text[:3000] if dos_donts_text else "No guidelines provided.",
        )
        try:
            analysis = _invoke_and_parse(self.client, self.model_id, prompt_text)
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

    _CODE_PRIORITY = ('.py', '.ts', '.js', '.tsx', '.jsx')

    def _get_code_summary(self, repo_paths):
        """
        repo_paths: str (single path) or list of (path, label) tuples
        Returns combined code context capped at 60K chars total, 5K per file.
        Priority files (.py/.ts/.js) are included first.
        """
        if isinstance(repo_paths, str):
            entries = [(repo_paths, None)]
        else:
            entries = repo_paths

        ignore_dirs = {'.git', 'node_modules', '__pycache__', 'build', 'dist', '.next', '.venv', 'venv', 'env', '.idea', '.vscode'}
        skip_exts = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.pyc', '.exe', '.dll', '.so', '.dylib', '.pdf', '.zip', '.tar.gz', '-lock.json', '.lock', '.log')

        total_budget = 60000
        per_file_budget = 5000
        per_repo = total_budget // max(len(entries), 1)

        summary = ""
        for repo_path, label in entries:
            if label:
                summary += f"\n{'='*50}\nREPO: {label}\n{'='*50}\n"

            # Collect all eligible files, sorted by priority then path
            all_files = []
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = sorted(d for d in dirs if d not in ignore_dirs)
                for fname in sorted(files):
                    if any(fname.endswith(e) for e in skip_exts):
                        continue
                    full = os.path.join(root, fname)
                    ext = os.path.splitext(fname)[1]
                    priority = 0 if ext in self._CODE_PRIORITY else 1
                    all_files.append((priority, full, fname))

            all_files.sort(key=lambda x: (x[0], x[1]))

            repo_chars = 0
            for _, file_path, fname in all_files:
                if repo_chars >= per_repo:
                    break
                try:
                    if os.path.getsize(file_path) > 102400:
                        continue
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    content_with_lines = ""
                    current_chars = 0
                    for i, line in enumerate(lines, 1):
                        line_entry = f"{i}: {line}"
                        if current_chars + len(line_entry) > per_file_budget:
                            break
                        content_with_lines += line_entry
                        current_chars += len(line_entry)
                    rel = os.path.relpath(file_path, repo_path).replace("\\", "/")
                    chunk = f"--- {rel} ---\n{content_with_lines}\n"
                    summary += chunk
                    repo_chars += len(chunk)
                except Exception:
                    pass

        return summary[:total_budget]


    def analyze_code_structure(self, repo_paths):
        """
        LLM-powered focused audit of code-level structural issues:
        auth/authorization patterns, pipeline/concurrency safety,
        dependency risks, error handling, and observability gaps.
        Returns issues grouped by category without affecting the quality score.
        """
        code_context = self._get_code_summary(repo_paths)

        prompt = PromptTemplate(
            template="""
            You are a Senior Security and Reliability Engineer performing a targeted code structure audit. Your focus is ONLY on the following five categories — do NOT report requirement drift, feature completeness, or general quality issues (those are handled separately).

            Implemented Code Context (all files with line numbers):
            {code_context}

            ═══════════════════════════════════════
            AUDIT CATEGORIES — cover all five
            ═══════════════════════════════════════

            1. AUTH & AUTHORIZATION ISSUES
               - Missing or bypassable authentication on API endpoints (routes that modify state without auth checks).
               - JWT/session token issues: no expiry, no signature verification, tokens stored insecurely.
               - OAuth flow vulnerabilities: missing state parameter (CSRF), missing nonce, open redirects in callback handlers.
               - Role-based access control gaps: endpoints accessible to roles that should be denied.
               - Insecure password handling: plaintext storage, weak hashing (MD5/SHA1), missing salt.
               - Token leakage: credentials passed in URL query params, logged in plain text, embedded in response bodies.

            2. PIPELINE & CONCURRENCY ISSUES
               - Background thread/job safety: shared mutable state (dicts, lists, counters) accessed from multiple threads without locks.
               - No timeout on external calls (HTTP, LLM/Bedrock, DB) — a hung call blocks the thread indefinitely.
               - Resource leaks: file handles, DB connections, temp directories not cleaned up on exception path (missing try/finally or context manager).
               - Job/task state corruption: no atomic update mechanism when multiple threads update the same job record.
               - Error propagation: background threads that swallow exceptions without updating job status to "error" — jobs appear "running" forever.
               - Missing retry logic on transient failures (HTTP 429/503, DB connection timeout).

            3. DEPENDENCY & SUPPLY CHAIN ISSUES
               - Known-risky packages: outdated versions of security-sensitive libraries (auth, crypto, HTTP clients).
               - Packages imported but not used in actual code paths — dead dependency that adds attack surface.
               - Missing integrity checks or pinning strategy for production dependencies.
               - Direct use of exec(), eval(), or subprocess with user-controlled input — code injection risk.

            4. ERROR HANDLING ISSUES
               - Bare `except:` or `except Exception: pass` blocks that silently discard errors on critical paths.
               - External API/DB calls with zero error handling — any failure raises an unhandled exception to the caller.
               - Inconsistent error response format — some endpoints return raw Python exceptions, others return structured JSON.
               - Async operations where rejections/exceptions are not propagated or logged.
               - Missing structured error context in logged errors (no request_id, user_id, or input summary).

            5. OBSERVABILITY GAPS
               - No structured logging on critical code paths (analysis jobs, auth flows, external calls).
               - print() used instead of a logger in backend/production code.
               - Errors caught and logged at DEBUG level instead of ERROR level.
               - No request/job ID propagated through background work — impossible to correlate logs to a specific analysis run.
               - Sensitive data (passwords, tokens, PII) appearing in log output.

            ═══════════════════════════════════════
            EVIDENCE REQUIREMENT (non-negotiable)
            ═══════════════════════════════════════
            For EACH issue:
            - Cite exact file path and line number.
            - Copy the verbatim line(s) into the evidence block.
            - Only report issues you can point to in the code. Do NOT speculate.

            ═══════════════════════════════════════
            OUTPUT FORMAT
            ═══════════════════════════════════════
            Output JSON ONLY — no markdown fences, no text outside the JSON.
            Each issue must have: subcategory, severity (Critical/High/Medium/Low), file, line, description (2 sentences), evidence (file:line + code snippet), remediation (numbered steps with BEFORE/AFTER code).

            {{
                "auth_issues": [
                    {{
                        "subcategory": "Unprotected Endpoint",
                        "severity": "High",
                        "file": "backend/main.py",
                        "line": 45,
                        "description": "2-sentence description of exactly what is wrong.",
                        "evidence": "backend/main.py:L45\n```python\nverbatim code\n```\nOne sentence on the specific problem.",
                        "remediation": "1. Step one.\n2. Step two.\nBEFORE:\n```python\nbroken\n```\nAFTER:\n```python\nfixed\n```"
                    }}
                ],
                "pipeline_issues": [],
                "dependency_issues": [],
                "error_handling_issues": [],
                "observability_issues": [],
                "summary": "- Bullet 1: most critical structural finding\n- Bullet 2: second most important finding\n- Bullet 3: top priority fix recommended\n(Write 3-5 bullet points using '- ' prefix. Do NOT write paragraph sentences.)"
            }}
            """,
            input_variables=["code_context"]
        )

        prompt_text = prompt.format(code_context=code_context)
        try:
            data = _invoke_and_parse(self.client, self.model_id, prompt_text)
            for key in ('auth_issues', 'pipeline_issues', 'dependency_issues', 'error_handling_issues', 'observability_issues'):
                data.setdefault(key, [])
                for issue in data[key]:
                    issue.setdefault('category', key.replace('_issues', ''))
            return data
        except Exception as e:
            return {
                "error": str(e),
                "auth_issues": [],
                "pipeline_issues": [],
                "dependency_issues": [],
                "error_handling_issues": [],
                "observability_issues": [],
                "summary": f"Code structure analysis failed: {str(e)}"
            }

    def analyze_feature_loss_with_history(self, repo_entries, requirements_text, dos_donts_text="", base_commit=None, head_commit=None):
        """
        Collects commit history and diffs from ALL repos, then runs a SINGLE
        LLM call that checks every commit across every repo against the uploaded docs.
        repo_entries: str (single path) or list of (path, base_commit, head_commit) tuples.
        """
        if isinstance(repo_entries, str):
            entries = [(repo_entries, base_commit, head_commit)]
        else:
            entries = repo_entries

        # ── 1. Gather data from every repo ──────────────────────────────────
        repo_data = []
        total_commits = 0
        total_commits_with_deletions = 0

        for repo_path, base_c, head_c in entries:
            commit_analyzer = CommitAnalyzer(repo_path)
            commit_history = commit_analyzer.get_commit_history()

            if len(commit_history) < 2:
                continue

            head_c = head_c or commit_history[0]["hash"]
            base_c = base_c or commit_history[-1]["hash"]

            full_diff = commit_analyzer.get_full_diff_between_commits(base_c, head_c)
            history_context = commit_analyzer.get_feature_loss_context()

            repo_label = os.path.basename(repo_path.rstrip("/\\"))
            cwd = history_context.get("commits_with_deletions", 0)
            total_commits += len(commit_history)
            total_commits_with_deletions += cwd

            repo_data.append({
                "label": repo_label,
                "path": repo_path,
                "total_commits": len(commit_history),
                "commits_with_deletions": cwd,
                "base_commit": base_c,
                "head_commit": head_c,
                "commit_history": commit_history,         # full list
                "full_diff": full_diff,
                "history_context": history_context,
            })

        if not repo_data:
            return {"error": "No repos with enough commit history", "feature_changes": [], "feature_loss_score": 0}

        # ── 2. Build combined commit timeline for the prompt ────────────────
        # Budget: 20 000 chars for all commit timelines, split evenly per repo
        timeline_budget = 20000
        per_repo_budget = timeline_budget // len(repo_data)

        combined_timeline = ""
        combined_diffs = ""
        diff_budget = 12000
        per_diff_budget = diff_budget // len(repo_data)

        for rd in repo_data:
            label = rd["label"]
            combined_timeline += (
                f"\n=== REPO: {label} | {rd['total_commits']} commits "
                f"| base: {rd['base_commit'][:8]} → head: {rd['head_commit'][:8]} ===\n"
            )
            # Include the full deletion timeline (sorted chronologically)
            timeline_json = json.dumps(rd["history_context"], indent=2)
            combined_timeline += timeline_json[:per_repo_budget] + "\n"

            combined_diffs += f"\n=== DIFF {label}: {rd['base_commit'][:8]} → {rd['head_commit'][:8]} ===\n"
            combined_diffs += json.dumps(rd["full_diff"], indent=2)[:per_diff_budget] + "\n"

        # ── 3. Code context across all repos ────────────────────────────────
        repo_paths_labeled = [(rd["path"], rd["label"]) for rd in repo_data]
        code_context = self._get_code_summary(repo_paths_labeled)

        # ── 4. Single unified LLM call ───────────────────────────────────────
        repo_summary_line = ", ".join(
            f"{rd['label']} ({rd['total_commits']} commits)" for rd in repo_data
        )

        prompt = PromptTemplate(
            template="""
            You are a Senior Staff Engineer conducting a full commit-history audit across ALL repositories. Your role is to act as the deployment gatekeeper — you must determine whether every requirement was implemented, whether any feature was dropped between commits without a replacement, and whether the current codebase is what was actually promised in the requirements document.

            Repositories analyzed: {repo_summary}
            Total commits across all repos: {total_commits}

            Requirements Document:
            {requirements}

            Do's and Don'ts Guidelines:
            {dos_donts}

            Current Code (latest state of ALL repos — full file contents with line numbers):
            {code_context}

            Commit History & Deletion Timeline (ALL repos, ALL commits in chronological order):
            {commit_analysis}

            Full Code Diffs (base → head for each repo):
            {deletions}

            ═══════════════════════════════════════
            AUDIT TASKS — complete ALL, no skipping
            ═══════════════════════════════════════

            1. REQUIREMENT COVERAGE
               For EVERY requirement in the document, find the commit(s) that implement it and confirm the feature exists in the current code. If a requirement has no corresponding commit AND no corresponding code in the latest snapshot, flag it as Missing. A requirement implemented in commit A but refactored in commit B is only Missing if the refactor removed it entirely from the current code.

            2. FEATURE LOSS DETECTION
               For every block of code deleted in a commit, determine:
               (a) Was it replaced by equivalent logic in the same or a later commit? → "Replacement - Feature Preserved"
               (b) Was it renamed or moved to another file with no change in functionality? → "Refactor - No Loss"
               (c) Was it removed with no replacement, and is absent from the current code? → "Loss" — flag this.
               Cross-check the CURRENT code snapshot before concluding Loss. If the feature exists anywhere in the current code — even under a different name or in a different file — it is NOT lost.

            3. REGRESSION DETECTION
               Identify any feature that was fully working in an earlier commit but is now broken or degraded in the latest code — even if the code was not explicitly deleted (e.g., a refactor broke the logic, a dependency change broke an integration, a config change removed a capability).

            4. API CONTRACT CHANGES
               Identify any endpoint signatures, request/response schemas, or public interfaces that changed between commits in a breaking way — removed fields, changed types, renamed routes — and confirm whether the change is documented and intentional.

            5. CONFIGURATION DRIFT
               Identify any environment variables, feature flags, or configuration values that changed between commits in a way that could cause a silent misconfiguration in production.

            6. GUIDELINE VIOLATIONS IN COMMITS
               Flag any commit that introduced code violating the Do's & Don'ts, and confirm whether the violation is still present in the current code.

            ═══════════════════════════════════════
            EXHAUSTIVE SCAN MANDATE
            ═══════════════════════════════════════
            Before marking any feature as Lost or Missing you MUST:
            - Cross-check against the CURRENT code across EVERY file in ALL repos — a deletion in one commit may have been re-added in a later commit or moved to a different file.
            - Scan ALL function bodies, loops, conditional branches, middleware chains, and utility modules for the feature's logic — do not stop at top-level entry points.
            - Check ALL naming variants: a deleted "generateReport" may reappear as "buildPDFOutput" or "exportSummary".
            - If the feature exists anywhere in the current code, it is NOT lost — cite its current location in replacement_logic.

            ═══════════════════════════════════════
            SCORING RUBRIC (start at 100)
            ═══════════════════════════════════════
            Apply the single best-fit deduction per confirmed finding. Do not stack for the same root cause. Maximum total deduction: 60 points.
              -10: Critical requirement completely absent from commits AND from current code.
              -7:  Feature was implemented in commits but deleted with no replacement — confirmed absent from current code.
              -5:  Regression: feature worked in an earlier commit, broken or degraded in current code.
              -4:  Breaking API contract change with no documentation or versioning.
              -3:  Feature replaced with noticeably inferior logic that does not fully satisfy the requirement.
              -3:  Configuration drift that could cause a silent production misconfiguration.
              -2:  Guideline violation introduced in a commit and still present in current code.
              -0:  Refactor, rename, or structural reorganisation with no functional loss.

            IMPORTANT:
            - Only deduct for confirmed findings — cite repo name, commit hash, file, and line.
            - Do NOT stack deductions for the same root cause across multiple repos.

            ═══════════════════════════════════════
            OUTPUT FORMAT
            ═══════════════════════════════════════
            Output JSON ONLY — no markdown fences, no text outside the JSON object.
            For EACH feature_change ALL fields are mandatory — vague or one-line answers are not acceptable.

            status values: "Loss" / "Replacement - Feature Preserved" / "Refactor - No Loss" / "Missing" / "Regression" / "API Breaking Change" / "Config Drift" / "Guideline Violation"

            {{
                "feature_loss_score": 85,
                "feature_changes": [
                    {{
                        "feature_name": "Descriptive name of the feature or requirement",
                        "repo": "repo label or 'all'",
                        "status": "Loss",
                        "severity": "Critical/High/Medium/Low",
                        "evidence": "repo/file.py:L45-L52\n```python\nverbatim deleted or missing code\n```\nOne sentence on what exactly is wrong or absent.",
                        "replacement_logic": "If replaced or refactored, describe the new implementation location and logic in 2-3 sentences. If truly absent, write 'None — confirmed absent from entire current codebase.'",
                        "requirement_reference": "Exact requirement text or section this maps to",
                        "impact": "2-3 sentences on the business and user impact — what fails, what users cannot do, what data is at risk.",
                        "commit_info": "commit_hash: first 8 chars — commit message",
                        "reasoning": "2-4 sentences on production risk — what breaks in production, what failure scenario this creates, what the on-call engineer would see.",
                        "remediation": "1. Specific step one.\n2. Specific step two.\n3. Specific step three.\nBEFORE:\n```python\nmissing or broken code\n```\nAFTER:\n```python\nrestored or fixed code\n```"
                    }}
                ],
                "summary": "- Bullet 1: X requirements confirmed implemented, Y lost or missing\n- Bullet 2: most critical gap or feature loss\n- Bullet 3: overall deployment risk level and recommendation\n(Write 3-5 bullet points using '- ' prefix. Do NOT write paragraph sentences.)"
            }}
            """,
            input_variables=["repo_summary", "total_commits", "requirements", "dos_donts",
                             "code_context", "commit_analysis", "deletions"]
        )

        prompt_text = prompt.format(
            repo_summary=repo_summary_line,
            total_commits=str(total_commits),
            requirements=requirements_text[:10000],
            dos_donts=dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
            code_context=code_context[:15000],
            commit_analysis=combined_timeline[:20000],
            deletions=combined_diffs[:12000],
        )

        try:
            result = _invoke_and_parse(self.client, self.model_id, prompt_text)

            if "feature_loss_score" in result:
                try:
                    result["feature_loss_score"] = max(0.0, min(100.0, float(result["feature_loss_score"])))
                except Exception:
                    result["feature_loss_score"] = 0.0

            result["analysis_metadata"] = {
                "repos": [rd["label"] for rd in repo_data],
                "total_commits": total_commits,
                "commits_with_deletions": total_commits_with_deletions,
                "analysis_date": str(datetime.now()),
            }
            result["commits_with_deletions"] = total_commits_with_deletions
            return result

        except Exception as e:
            return {
                "error": str(e),
                "feature_loss_score": 0,
                "feature_changes": [],
                "summary": f"Feature history analysis failed: {str(e)}",
                "analysis_metadata": {
                    "total_commits": total_commits,
                    "commits_with_deletions": total_commits_with_deletions,
                },
                "commits_with_deletions": total_commits_with_deletions,
            }
