import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()
import time
import PyPDF2
from datetime import datetime
from mcp_server.tools.git_reader import clone_repo, cleanup_repo
from agents.compliance_agent import ComplianceAgent
from history_manager import save_analysis, get_repo_history, clear_repo_history
from mcp_server.tools.commit_analyzer import CommitAnalyzer
from utils.pdf_report import generate_pdf_report

st.set_page_config(
    page_title="DriftX 2.0 - Compliance Gateway",
    layout="wide",
    initial_sidebar_state="expanded"
)

if not os.getenv('GOOGLE_API_KEY'):
    st.error("⚠️ Configuration Error: GOOGLE_API_KEY not found in environment variables.")
    st.info("Please check your .env file and ensure GOOGLE_API_KEY is set.")
    st.stop()


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
        else:
            text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
    return text


# ── Display helpers ───────────────────────────────────────────────────────────

def display_module_analysis(module_results):
    st.subheader(f"🔍 Module: **{module_results['module_name']}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Module Files Found", module_results["file_count"])
    col2.metric("Referenced In", f"{module_results['usage_count']} file(s)")
    analysis = module_results.get("analysis", {})
    mod_score = analysis.get("compliance_score", "N/A")
    col3.metric("Module Compliance Score", f"{mod_score}/100" if isinstance(mod_score, (int, float)) else mod_score)

    # Module purpose & key components
    if analysis.get("module_purpose"):
        st.markdown(f"**Purpose:** {analysis['module_purpose']}")
    if analysis.get("key_components"):
        with st.expander("📦 Key Components"):
            for comp in analysis["key_components"]:
                st.write(f"• {comp}")

    # Files identified as part of the module
    related = module_results.get("related_files", [])
    if related:
        with st.expander(f"📂 Files identified as part of '{module_results['module_name']}' ({len(related)})"):
            for f in related:
                st.code(f, language=None)
    else:
        st.info(f"No files found matching the module name '{module_results['module_name']}'. "
                "Try a different keyword (e.g., 'leave' instead of 'leave module').")

    # Cross-reference usages
    usages = module_results.get("usage_in_files", {})
    if usages:
        with st.expander(f"🔗 Where '{module_results['module_name']}' is referenced ({len(usages)} file(s))"):
            for file_path, hits in usages.items():
                st.markdown(f"**`{file_path}`**")
                for hit in hits:
                    st.code(f"Line {hit['line']}: {hit['content']}", language=None)
    else:
        st.info("No cross-references found for this module in other files.")

    # Module-specific issues from LLM
    mod_issues = analysis.get("issues", [])
    if mod_issues:
        st.markdown("**Module-Specific Issues:**")
        for issue in mod_issues:
            issue_type = issue.get("type", "")
            is_critical = any(w in issue_type.lower() for w in ["loss", "drift", "violation", "missing", "failed"])
            with st.expander(
                f"{'🚨' if is_critical else 'ℹ️'} [{issue_type}] {issue.get('description', '')[:100]}..."
            ):
                st.write(f"**Description:** {issue.get('description', '')}")
                if issue.get("evidence"):
                    st.markdown(f"**Evidence:** `{issue.get('evidence', '')}`")
                st.write(f"**Reasoning:** {issue.get('reasoning', '')}")
                st.info(f"🤖 **Remediation:** {issue.get('remediation', '')}")
    elif analysis.get("summary"):
        st.success(f"✅ {analysis['summary']}")


def display_unified_analysis(results, history_results=None, module_results=None,
                              repo_url="", branch="", module_name=""):
    tab_labels = ["📊 Quality Report", "🚨 Issues", "🧬 Feature Evolution", "📜 History"]
    if module_results:
        tab_labels.insert(3, "🔍 Module Analysis")
    tabs = st.tabs(tab_labels)

    tab_idx = 0

    # ── Tab 1: Quality Report ─────────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.subheader("Unified Quality Score")
        score = results.get("score", 0)
        st.metric("Overall Compliance Score", f"{score}/100")
        st.write(f"**Summary**: {results.get('summary', 'Analysis completed.')}")

        st.divider()
        st.subheader("🏁 Quality Gate Decision")
        if score >= 80:
            st.balloons()
            st.success("✅ Quality Gate Passed! Code is ready for deployment.")
            if st.button("🚀 Deploy to Production"):
                st.toast("Initiating Deployment Pipeline...", icon="🚀")
                time.sleep(2)
                st.success("Deployment Triggered Successfully!")
        elif score >= 60:
            st.warning("⚠️ Quality Gate Warning. Minor improvements recommended.")
        else:
            st.error("⛔ Quality Gate Failed. Major fixes required before deployment.")

        if history_results:
            st.divider()
            st.subheader("🕵️ Feature Evolution Summary")
            metadata = history_results.get("analysis_metadata", {})
            base_h = str(metadata.get("base_commit", "Initial"))[:8]
            head_h = str(metadata.get("head_commit", "Now"))[:8]
            st.info(f"📅 **Analyzed Range**: `{base_h}` → `{head_h}`")

            changes = history_results.get("feature_changes", [])
            losses = [c for c in changes if "loss" in c.get("status", "").lower()]
            replacements = [c for c in changes if any(
                w in c.get("status", "").lower() for w in ["replacement", "refactor", "updated"]
            )]
            col_x, col_y = st.columns(2)
            col_x.error(f"❌ {len(losses)} Feature Loss(es) Detected") if losses else col_x.success("✅ No Feature Loss")
            col_y.info(f"🔄 {len(replacements)} Feature Replacement(s)") if replacements else col_y.info("ℹ️ No Replacements")
            st.caption("See the **🧬 Feature Evolution** tab for the full breakdown.")

    # ── Tab 2: Issues ─────────────────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.subheader("Identified Issues & AI Remediation")
        issues = results.get("issues", [])
        if not issues:
            st.success("✅ No critical issues found!")
        else:
            for issue in issues:
                issue_type = issue.get("type", "")
                is_critical = any(w in issue_type.lower() for w in ["loss", "drift", "violation", "missing", "failed"])
                header_text = f"**{issue_type}**: {issue.get('description', '')[:100]}..."
                if is_critical:
                    header_text = f"🚨 :red[{issue_type}]: {issue.get('description', '')[:100]}..."
                with st.expander(header_text):
                    if is_critical:
                        st.error(f"**Critical {issue_type} Detected**")
                    st.write(f"**Full Description**: {issue.get('description', '')}")
                    if issue.get("evidence"):
                        st.markdown(f"**Evidence**: `{issue.get('evidence', '')}`")
                    st.write(f"**Reasoning**: {issue.get('reasoning', '')}")
                    st.info(f"🤖 **AI Remediation**: {issue.get('remediation', '')}")
                    st.divider()

    # ── Tab 3: Feature Evolution ──────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.subheader("🧬 Historical Feature Evolution")
        if history_results and "error" not in history_results:
            if history_results.get("feature_changes"):
                for change in history_results["feature_changes"]:
                    feature_name = change.get("feature_name", "")
                    status = change.get("status", "")
                    is_loss = "loss" in status.lower() or "missing" in status.lower()
                    header = f"{'❌ :red[' if is_loss else '**'}{feature_name}{']' if is_loss else '**'} (Status: {status})"
                    with st.expander(header):
                        if is_loss:
                            st.error("**Feature Loss detected in history**")
                        st.write(f"**Impact**: {change.get('impact', '')}")
                        st.write(f"**Severity**: {change.get('severity', 'Medium')}")
                        st.write(f"**Reasoning**: {change.get('reasoning', '')}")
                        if change.get("status") == "Replacement":
                            st.success(f"🔄 Replacement: {change.get('replacement_logic', '')}")
                        st.info(f"🤖 Remediation: {change.get('remediation', '')}")
                        if change.get("evidence"):
                            st.markdown(f"**Evidence**: `{change.get('evidence', '')}`")
                        st.divider()
            else:
                st.info("No specific feature changes detected in this commit range.")
        else:
            st.info("No evolution analysis available.")

    # ── Tab 4 (optional): Module Analysis ────────────────────────────────────
    if module_results:
        with tabs[tab_idx]:
            tab_idx += 1
            display_module_analysis(module_results)

    # ── Tab: History ─────────────────────────────────────────────────────────
    with tabs[tab_idx]:
        st.subheader("DriftX Analysis History")
        repo_url_key = st.session_state.get("repo_input", "")
        history = get_repo_history(repo_url_key)

        if history:
            col_a, col_b = st.columns(2)
            col_a.metric("Latest Score", f"{history[0]['score']:.1f}/100")
            col_b.info(f"**Latest Summary**: {history[0]['summary']}")

            with st.expander("🕰️ View Past Analyses"):
                for entry in history:
                    st.write(f"**{entry['timestamp']}** | Score: {entry['score']:.1f}")
                    st.caption(f"Summary: {entry['summary']}")
                    st.divider()

            if st.button("🗑️ Reset Repository Memory", type="secondary",
                         help="Clears history to allow a full re-analysis."):
                if clear_repo_history(repo_url_key):
                    st.success("History cleared! The next analysis will perform a full audit.")
                    time.sleep(1)
                    st.rerun()

        st.divider()
        st.subheader("📜 Git Metadata & Risk")
        if history_results and "error" not in history_results:
            metadata = history_results.get("analysis_metadata", {})
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Commits Analyzed", history_results.get("total_commits_analyzed", 0))
            col2.metric("Commits with Deletions", history_results.get("commits_with_deletions", 0))
            col3.metric("Critical Evolution Issues", history_results.get("critical_issues_found", 0))
            risk = history_results.get("deployment_risk", "Unknown")
            risk_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")
            col4.metric("History Risk", f"{risk_color} {risk}")
        else:
            st.info("No commit history metadata available.")

    # ── PDF Download ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📥 Download Report")
    try:
        pdf_bytes = generate_pdf_report(
            results=results,
            history_results=history_results,
            module_results=module_results,
            repo_url=repo_url,
            branch=branch,
            module_name=module_name,
        )
        filename = f"driftx_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        st.download_button(
            label="⬇️ Download Analysis Report (PDF)",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            type="primary",
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.title("🛡️ DriftX 2.0: Unified Quality Gateway")
    st.markdown(
        "Performs a **Unified Quality Analysis** — requirement drift, feature completeness, "
        "guideline coverage, and module-level deep-dive — in one comprehensive pass."
    )

    # Session state init
    for key in ["repo_path", "available_commits", "last_fetched_url", "last_fetched_branch"]:
        if key not in st.session_state:
            st.session_state[key] = None if key != "available_commits" else []

    with st.expander("ℹ️ How to use DriftX 2.0"):
        st.markdown("""
        **Inputs:**
        - **Git Repository URL** — GitHub, GitLab, Bitbucket, etc.
        - **Branch Name** *(optional)* — leave blank to use the repo's default branch.
        - **Module Name** *(optional)* — e.g. `leave` or `leave module` for HRMS. DriftX will
          identify the files that belong to the module and show everywhere it is referenced.
        - **Requirement Docs** — PDF, TXT, or MD.
        - **Do's and Don'ts** *(optional)* — guidelines document.

        **Steps:**
        1. Enter the URL (and optional branch / module name).
        2. Click **Fetch Repository Details** to clone and list commits.
        3. Optionally pick a commit range for evolution analysis.
        4. Click **Start Analysis**.
        5. Review results and **Download the PDF report**.

        **Scoring:**  80–100 ✅ | 60–79 ⚠️ | Below 60 ⛔
        """)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("🚀 Configuration")

        repo_url = st.text_input(
            "Git Repository URL",
            placeholder="https://github.com/user/repo",
            key="repo_input"
        )

        branch_input = st.text_input(
            "Branch Name *(optional)*",
            placeholder="e.g. main, develop, feature/leave-module",
            key="branch_input",
            help="Leave blank to use the repository's default branch."
        )

        uploaded_files = st.file_uploader(
            "Upload Requirement Docs",
            accept_multiple_files=True,
            type=["pdf", "txt", "md"]
        )
        dos_donts_files = st.file_uploader(
            "Upload Do's and Don'ts Docs",
            accept_multiple_files=True,
            type=["pdf", "txt", "md"]
        )

        module_name_input = st.text_input(
            "Module Name *(optional)*",
            placeholder="e.g. leave, payroll, attendance",
            key="module_input",
            help=(
                "Enter a module name to focus the analysis on related files. "
                "DriftX will identify which files belong to the module and where it is used."
            )
        )

        # Fetch repo button
        if st.button("🔍 Fetch Repository Details", use_container_width=True):
            if not repo_url:
                st.error("Please provide a Git URL first.")
            else:
                try:
                    with st.spinner("Cloning Repository..."):
                        if st.session_state.repo_path:
                            cleanup_repo(st.session_state.repo_path)
                            st.session_state.repo_path = None

                        branch_val = branch_input.strip() or None
                        st.session_state.repo_path = clone_repo(repo_url, branch=branch_val)
                        st.session_state.last_fetched_url = repo_url
                        st.session_state.last_fetched_branch = branch_val

                        analyzer = CommitAnalyzer(st.session_state.repo_path)
                        st.session_state.available_commits = analyzer.get_commit_history(max_commits=100)
                        st.success(
                            f"✅ Fetched {len(st.session_state.available_commits)} commits"
                            + (f" from branch **{branch_val}**" if branch_val else "")
                            + "."
                        )
                except Exception as e:
                    st.error(f"Failed to fetch repository: {e}")

        # Commit range picker
        base_commit_hash = None
        head_commit_hash = None

        if st.session_state.available_commits:
            st.divider()
            st.subheader("🧬 Select Evolution Range")
            commit_options = [
                f"{c['hash'][:8]} | {c['message']} ({c['date'][:10]})"
                for c in st.session_state.available_commits
            ]

            head_select = st.selectbox("Head Commit (Newer)", options=commit_options, index=0)

            repo_history = get_repo_history(repo_url)
            last_analyzed_hash = next(
                (e["last_commit_hash"] for e in repo_history if e.get("last_commit_hash")), None
            )
            base_idx = len(commit_options) - 1
            if last_analyzed_hash:
                for i, c in enumerate(st.session_state.available_commits):
                    if c["hash"].startswith(last_analyzed_hash[:8]):
                        base_idx = i
                        break

            base_select = st.selectbox("Base Commit (Older)", options=commit_options, index=base_idx)

            base_commit_hash = st.session_state.available_commits[commit_options.index(base_select)]["hash"]
            head_commit_hash = st.session_state.available_commits[commit_options.index(head_select)]["hash"]

        st.divider()
        process_btn = st.button("🚀 Start Analysis", type="primary", use_container_width=True)

    # ── Analysis ──────────────────────────────────────────────────────────────
    if process_btn:
        if not repo_url or not uploaded_files:
            st.error("Please provide both a Git URL and Requirement Documents.")
            return

        st.info("🔄 Initializing Agents… Please wait.")

        requirements_text = ""
        for uf in uploaded_files:
            requirements_text += f"\n\n--- {uf.name} ---\n"
            requirements_text += extract_text_from_file(uf)

        dos_donts_text = ""
        for uf in (dos_donts_files or []):
            dos_donts_text += f"\n\n--- {uf.name} ---\n"
            dos_donts_text += extract_text_from_file(uf)

        repo_path = st.session_state.repo_path
        branch_used = st.session_state.get("last_fetched_branch") or branch_input.strip() or ""
        module_name = module_name_input.strip()

        try:
            if not repo_path:
                with st.spinner("Cloning Repository..."):
                    branch_val = branch_input.strip() or None
                    repo_path = clone_repo(repo_url, branch=branch_val)
                    st.session_state.repo_path = repo_path
                    branch_used = branch_val or ""

            repo_history = get_repo_history(repo_url)
            last_analyzed_commit = next(
                (e["last_commit_hash"] for e in repo_history if e.get("last_commit_hash")), None
            )
            final_base = base_commit_hash if base_commit_hash else last_analyzed_commit
            final_head = head_commit_hash if head_commit_hash else None

            compliance_agent = ComplianceAgent()

            with st.spinner("🤖 Performing Unified Quality Analysis..."):
                results = compliance_agent.unified_analysis(repo_path, requirements_text, dos_donts_text)

            with st.spinner("📜 Analyzing feature evolution..."):
                history_results = compliance_agent.analyze_feature_loss_with_history(
                    repo_path, requirements_text, dos_donts_text,
                    base_commit=final_base, head_commit=final_head
                )

            # Merge critical history losses into main issues
            if history_results and history_results.get("feature_changes"):
                main_issues = results.get("issues", [])
                for change in history_results["feature_changes"]:
                    if change.get("status") == "Loss" and change.get("severity") == "Critical":
                        main_issues.append({
                            "type": "Critical Feature Loss",
                            "description": f"Evolution analysis: missing feature — {change.get('feature_name')}",
                            "evidence": change.get("evidence"),
                            "reasoning": change.get("reasoning"),
                            "remediation": change.get("remediation"),
                        })
                results["issues"] = main_issues

            # Module-specific analysis
            module_results = None
            if module_name:
                with st.spinner(f"🔍 Analysing module '{module_name}'..."):
                    module_results = compliance_agent.analyze_module_focus(
                        repo_path, module_name, requirements_text, dos_donts_text
                    )

            final_score = results.get("score", 0)
            current_head = history_results.get("analysis_metadata", {}).get("head_commit")
            save_analysis(
                repo_url, "Unified", final_score,
                results.get("summary", "Analysis completed."),
                last_commit_hash=current_head
            )

            display_unified_analysis(
                results, history_results, module_results,
                repo_url=repo_url, branch=branch_used, module_name=module_name
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
