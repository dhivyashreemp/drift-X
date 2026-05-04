import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
sys.path.insert(0, _ROOT_DIR)     # drift-X/ — for agents/, mcp_server/, history_manager, etc.
sys.path.insert(0, _BACKEND_DIR)  # drift-X/backend/ — for auth, user_manager, team_manager, microsoft_auth

import uuid
import threading
import io
from datetime import datetime
from typing import List, Optional

import PyPDF2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(os.path.join(_ROOT_DIR, ".env"))

from mcp_server.tools.git_reader import clone_repo, cleanup_repo
from mcp_server.tools.commit_analyzer import CommitAnalyzer
from agents.compliance_agent import ComplianceAgent
from history_manager import save_analysis, get_repo_history, clear_repo_history
from utils.pdf_report import generate_pdf_report
from auth import create_token, verify_token, hash_password, verify_password
from user_manager import get_user, email_exists, create_user, all_users, safe_user
from team_manager import record_analysis, get_team_summary, get_user_history
from microsoft_auth import is_configured as ms_configured, get_auth_url as ms_auth_url
from microsoft_auth import exchange_code_for_token, get_ms_user

ALLOWED_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "")
MANAGER_INVITE_CODE = os.getenv("MANAGER_INVITE_CODE", "")

app = FastAPI(title="Drift-X API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_repo_cache: dict = {}
_jobs: dict = {}
_results_cache: dict = {}


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _current_user(authorization: str = "") -> dict | None:
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    email = verify_token(token)
    if not email:
        return None
    return get_user(email)


def _require_user(authorization: str) -> dict:
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _check_domain(email: str) -> None:
    if ALLOWED_DOMAIN and not email.lower().endswith(f"@{ALLOWED_DOMAIN.lstrip('@')}"):
        raise HTTPException(
            status_code=400,
            detail=f"Only @{ALLOWED_DOMAIN} email addresses are allowed.",
        )


# ── Auth endpoints ────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: str
    name: str
    password: str
    invite_code: str = ""


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register")
def register(body: RegisterBody):
    email = body.email.strip().lower()
    _check_domain(email)
    if email_exists(email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    role = "developer"
    if MANAGER_INVITE_CODE and body.invite_code.strip() == MANAGER_INVITE_CODE:
        role = "manager"
    user = create_user(email, body.name.strip(), hash_password(body.password), role=role)
    token = create_token(email)
    return {"token": token, "user": safe_user(user)}


@app.post("/api/auth/login")
def login(body: LoginBody):
    email = body.email.strip().lower()
    user = get_user(email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_token(email)
    return {"token": token, "user": safe_user(user)}


@app.get("/api/auth/me")
def me(authorization: str = Header(default="")):
    user = _require_user(authorization)
    return safe_user(user)


@app.get("/api/auth/microsoft")
def microsoft_login():
    if not ms_configured():
        raise HTTPException(
            status_code=400,
            detail="Microsoft OAuth is not configured. Set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, and MICROSOFT_TENANT_ID.",
        )
    return {"url": ms_auth_url()}


@app.get("/api/auth/microsoft/callback")
async def microsoft_callback(code: str = "", error: str = "", error_description: str = ""):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    if error:
        msg = error_description or error
        return RedirectResponse(f"{frontend_url}?auth_error={msg[:120]}")

    try:
        token_data = await exchange_code_for_token(code)
        access_token = token_data.get("access_token", "")
        ms_user = await get_ms_user(access_token)

        email = (ms_user.get("mail") or ms_user.get("userPrincipalName") or "").strip().lower()
        name = ms_user.get("displayName") or email.split("@")[0]

        if not email:
            return RedirectResponse(f"{frontend_url}?auth_error=Microsoft+did+not+return+an+email")

        _check_domain(email)

        if not email_exists(email):
            create_user(email, name, "", auth_provider="microsoft")

        jwt = create_token(email)
        return RedirectResponse(f"{frontend_url}?token={jwt}")
    except HTTPException as he:
        return RedirectResponse(f"{frontend_url}?auth_error={he.detail[:120]}")
    except Exception as exc:
        return RedirectResponse(f"{frontend_url}?auth_error={str(exc)[:120]}")


# ── Team endpoints ────────────────────────────────────────────────────────────

@app.get("/api/team")
def team(authorization: str = Header(default="")):
    _require_user(authorization)
    summary = get_team_summary()
    analyzed_emails = {m["email"] for m in summary}
    for u in all_users():
        if u["email"] in analyzed_emails or u.get("role") == "manager":
            continue
        summary.append({
            "email": u["email"],
            "name": u["name"],
            "latest_score": None,
            "prev_score": None,
            "score_trend": None,
            "last_active": None,
            "last_repo": None,
            "last_summary": "",
            "last_issue_count": 0,
            "last_critical_count": 0,
            "analyses_count": 0,
            "today_scores": [],
            "today_avg": None,
            "this_week_count": 0,
        })
    return summary


@app.get("/api/team/me/history")
def my_history(authorization: str = Header(default="")):
    user = _require_user(authorization)
    return get_user_history(user["email"])


@app.get("/api/team/{email}/history")
def member_history(email: str, authorization: str = Header(default="")):
    user = _require_user(authorization)
    if user.get("role") != "manager" and user["email"] != email:
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_user_history(email)


# ── Core analysis endpoints ───────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_set": bool(os.getenv("GOOGLE_API_KEY"))}


@app.get("/api/auth/providers")
def auth_providers():
    return {"microsoft": ms_configured()}


def _extract_text(file_bytes: bytes, filename: str) -> str:
    try:
        if filename.lower().endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            return "".join(p.extract_text() or "" for p in reader.pages)
        return file_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        return f"[Error reading {filename}: {exc}]"


@app.post("/api/fetch-repo")
async def fetch_repo(
    repo_url: str = Form(...),
    branch: str = Form(""),
    git_token: str = Form(""),
    authorization: str = Header(default=""),
):
    _require_user(authorization)
    branch_val = branch.strip() or None
    token_val = git_token.strip() or None
    cache_key = (repo_url.strip(), branch_val)
    try:
        if cache_key in _repo_cache:
            try:
                cleanup_repo(_repo_cache[cache_key])
            except Exception:
                pass
        repo_path = clone_repo(repo_url.strip(), branch=branch_val, token=token_val)
        _repo_cache[cache_key] = repo_path
        analyzer = CommitAnalyzer(repo_path)
        commits = analyzer.get_commit_history(max_commits=100)
        return {"success": True, "commits": commits, "count": len(commits)}
    except Exception as exc:
        detail = str(exc)
        is_private = detail.startswith("PRIVATE_REPO:")
        raise HTTPException(
            status_code=401 if is_private else 400,
            detail=detail.replace("PRIVATE_REPO: ", "") if is_private else detail,
        )


def _run_job(
    job_id: str,
    repo_url: str,
    branch_val: Optional[str],
    token_val: Optional[str],
    requirements_text: str,
    dos_donts_text: str,
    module_name: str,
    base_commit: Optional[str],
    head_commit: Optional[str],
    user_email: str,
    user_name: str,
):
    try:
        _jobs[job_id].update(status="running", progress="Preparing repository…")

        cache_key = (repo_url, branch_val)
        if cache_key not in _repo_cache:
            repo_path = clone_repo(repo_url, branch=branch_val, token=token_val)
            _repo_cache[cache_key] = repo_path
        repo_path = _repo_cache[cache_key]

        agent = ComplianceAgent()

        _jobs[job_id]["progress"] = "Running unified quality analysis…"
        results = agent.unified_analysis(repo_path, requirements_text, dos_donts_text)

        _jobs[job_id]["progress"] = "Analyzing feature evolution…"
        history_results = agent.analyze_feature_loss_with_history(
            repo_path, requirements_text, dos_donts_text,
            base_commit=base_commit, head_commit=head_commit,
        )

        if history_results and history_results.get("feature_changes"):
            issues = results.get("issues", [])
            for change in history_results["feature_changes"]:
                if change.get("status") == "Loss" and change.get("severity") == "Critical":
                    issues.append({
                        "type": "Critical Feature Loss",
                        "description": f"Evolution: missing — {change.get('feature_name')}",
                        "evidence": change.get("evidence", ""),
                        "reasoning": change.get("reasoning", ""),
                        "remediation": change.get("remediation", ""),
                    })
            results["issues"] = issues

        module_results = None
        if module_name:
            _jobs[job_id]["progress"] = f"Analysing module '{module_name}'…"
            module_results = agent.analyze_module_focus(
                repo_path, module_name, requirements_text, dos_donts_text,
            )

        final_score = results.get("score", 0)
        current_head = (history_results or {}).get("analysis_metadata", {}).get("head_commit")
        save_analysis(repo_url, "Unified", final_score, results.get("summary", ""), last_commit_hash=current_head)

        if user_email:
            all_issues = results.get("issues", [])
            critical = [i for i in all_issues if any(
                w in i.get("type", "").lower()
                for w in ["loss", "drift", "violation", "missing", "failed"]
            )]
            record_analysis(
                user_email, user_name, repo_url, final_score,
                results.get("summary", ""),
                issue_count=len(all_issues),
                critical_count=len(critical),
            )

        _results_cache[job_id] = dict(
            results=results,
            history_results=history_results,
            module_results=module_results,
            repo_url=repo_url,
            branch=branch_val or "",
            module_name=module_name,
        )

        _jobs[job_id] = {
            "status": "complete",
            "progress": "Analysis complete.",
            "result": {
                "results": results,
                "history_results": history_results,
                "module_results": module_results,
            },
        }
    except Exception as exc:
        err_str = str(exc)
        is_private = err_str.startswith("PRIVATE_REPO:")
        clean = err_str.replace("PRIVATE_REPO: ", "") if is_private else err_str
        _jobs[job_id] = {
            "status": "error",
            "progress": clean,
            "error": clean,
            "private_repo": is_private,
        }


@app.post("/api/analyze")
async def start_analysis(
    repo_url: str = Form(...),
    branch: str = Form(""),
    git_token: str = Form(""),
    module_name: str = Form(""),
    base_commit: str = Form(""),
    head_commit: str = Form(""),
    requirements_files: List[UploadFile] = File(...),
    dos_donts_files: Optional[List[UploadFile]] = File(default=None),
    authorization: str = Header(default=""),
):
    user = _require_user(authorization)

    req_text = ""
    for f in requirements_files:
        data = await f.read()
        req_text += f"\n\n--- {f.filename} ---\n{_extract_text(data, f.filename)}"

    dos_text = ""
    for f in (dos_donts_files or []):
        data = await f.read()
        dos_text += f"\n\n--- {f.filename} ---\n{_extract_text(data, f.filename)}"

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "progress": "Queued…"}

    threading.Thread(
        target=_run_job,
        args=(
            job_id,
            repo_url.strip(),
            branch.strip() or None,
            git_token.strip() or None,
            req_text,
            dos_text,
            module_name.strip(),
            base_commit.strip() or None,
            head_commit.strip() or None,
            user["email"],
            user["name"],
        ),
        daemon=True,
    ).start()

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, authorization: str = Header(default="")):
    _require_user(authorization)
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/history")
def get_history(repo_url: str, authorization: str = Header(default="")):
    _require_user(authorization)
    return get_repo_history(repo_url)


@app.delete("/api/history")
def delete_history(repo_url: str, authorization: str = Header(default="")):
    _require_user(authorization)
    return {"success": clear_repo_history(repo_url)}


@app.post("/api/report/{job_id}")
def download_report(job_id: str, authorization: str = Header(default="")):
    _require_user(authorization)
    cached = _results_cache.get(job_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Results not found for this job")
    try:
        pdf_bytes = generate_pdf_report(**cached)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="driftx_report_{ts}.pdf"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")


# ── Serve React frontend (must be mounted LAST) ───────────────────────────────

_DIST = os.path.join(_ROOT_DIR, "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
