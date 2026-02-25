import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()
import time
import PyPDF2
from mcp_server.tools.git_reader import clone_repo, cleanup_repo
from agents.compliance_agent import ComplianceAgent
from history_manager import save_analysis, get_repo_history, clear_repo_history
from mcp_server.tools.commit_analyzer import CommitAnalyzer

st.set_page_config(
    page_title="DriftX 2.0 - Compliance Gateway", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Validate API key
if not os.getenv('GOOGLE_API_KEY'):
    st.error("⚠️ Configuration Error: GOOGLE_API_KEY not found in environment variables.")
    st.info("Please check your .env file and ensure GOOGLE_API_KEY is set.")
    st.stop()

def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
        else:
            # Assume text/md
            text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
    return text

def display_unified_analysis(results, history_results=None):
    """Display Unified Quality Analysis Results"""
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Quality Report", "🚨 Analysis Issues", "🧬 Feature Evolution", "📜 Review History"])
    
    with tab1:
        st.subheader("Unified Quality Score")
        score = results.get("score", 0)
        st.metric("Overall Compliance Score", f"{score}/100")
        
        st.write(f"**Summary**: {results.get('summary', 'Analysis completed.')}")
        
        st.divider()
        st.subheader("🏁 Quality Gate Decision")
        if score > 90:
            st.balloons()
            st.success("✅ Quality Gate Passed! Code is ready for deployment.")
            if st.button("🚀 Deploy to Production"):
                st.toast("Initiating Deployment Pipeline...", icon="🚀")
                time.sleep(2)
                st.success("Deployment Triggered Successfully!")
        elif score > 75:
            st.warning("⚠️ Quality Gate Warning. Minor improvements recommended.")
        else:
            st.error("⛔ Quality Gate Failed. Major fixes required before deployment.")

        # --- Feature Evolution Summary ---
        if history_results:
            st.divider()
            st.subheader("🕵️ Feature Evolution Summary")
            
            # Show analyzed commit range
            metadata = history_results.get("analysis_metadata", {})
            base_h = metadata.get("base_commit", "Initial")[:8]
            head_h = metadata.get("head_commit", "Now")[:8]
            st.info(f"📅 **Analyzed Range**: `{base_h}` → `{head_h}`")
            
            changes = history_results.get("feature_changes", [])
            losses = [c for c in changes if 'loss' in c.get('status', '').lower()]
            replacements = [c for c in changes if any(word in c.get('status', '').lower() for word in ['replacement', 'refactor', 'updated'])]
            
            col_x, col_y = st.columns(2)
            if losses:
                col_x.error(f"❌ {len(losses)} Feature Loss(es) Detected")
            else:
                col_x.success("✅ No Feature Loss Occurred")
                
            if replacements:
                col_y.info(f"🔄 {len(replacements)} Feature Replacements")
            else:
                col_y.info("ℹ️ No Replacements Detected")
            
            st.caption("See the **🧬 Feature Evolution** tab for the full technical breakdown.")

    with tab2:
        st.subheader("Identified Issues & AI Remediation")
        issues = results.get("issues", [])
        if not issues:
            st.success("✅ No critical issues found!")
        else:
            for issue in issues:
                issue_type = issue.get('type', '')
                is_critical = any(word in issue_type.lower() for word in ['loss', 'drift', 'violation', 'missing', 'failed'])
                
                header_text = f"**{issue_type}**: {issue.get('description')[:100]}..."
                if is_critical:
                    header_text = f"🚨 :red[{issue_type}]: {issue.get('description')[:100]}..."
                
                with st.expander(header_text):
                    if is_critical:
                        st.error(f"**Critical {issue_type} Detected**")
                    
                    st.write(f"**Full Description**: {issue.get('description')}")
                    if issue.get('evidence'):
                        st.markdown(f"**Evidence**: `{issue.get('evidence')}`")
                    st.write(f"**Reasoning**: {issue.get('reasoning')}")
                    st.info(f"🤖 **AI Remediation**: {issue.get('remediation')}")
                    st.divider()

    with tab3:
        st.subheader("🧬 Historical Feature Evolution")
        if history_results and "error" not in history_results:
            if history_results.get("feature_changes"):
                for idx, change in enumerate(history_results.get("feature_changes", []), 1):
                    feature_name = change.get('feature_name', '')
                    status = change.get('status', '')
                    is_loss = 'loss' in status.lower() or 'missing' in status.lower()
                    
                    header = f"**{feature_name}** (Status: {status})"
                    if is_loss:
                        header = f"❌ :red[{feature_name}] (Status: {status})"
                    
                    with st.expander(header):
                        if is_loss:
                            st.error(f"**Feature Loss detected in history**")
                            
                        st.write(f"**Impact**: {change.get('impact')}")
                        st.write(f"**Severity**: {change.get('severity', 'Medium')}")
                        st.write(f"**Reasoning**: {change.get('reasoning')}")
                        if change.get('status') == "Replacement":
                            st.success(f"🔄 Replacement logic found: {change.get('replacement_logic')}")
                        st.info(f"🤖 Remediation: {change.get('remediation')}")
                        if change.get('evidence'):
                            st.markdown(f"**Evidence**: `{change.get('evidence')}`")
                        st.divider()
            else:
                st.info("No specific feature changes (Losses or Replacements) detected in this commit range.")
        else:
            st.info("No evolution analysis available. Run an analysis with commit history to see results.")

    with tab4:
        st.subheader("DriftX Analysis History")
        repo_url = st.session_state.get('repo_input', "")
        history = get_repo_history(repo_url)
        
        if history:
            col_a, col_b = st.columns(2)
            col_a.metric("Latest Score", f"{history[0]['score']:.1f}/100")
            col_b.info(f"**Latest Summary**: {history[0]['summary']}")
            
            with st.expander("🕰️ View Past Analyses"):
                for entry in history:
                    st.write(f"**{entry['timestamp']}** | Score: {entry['score']:.1f}")
                    st.caption(f"Summary: {entry['summary']}")
                    st.divider()
            
            if st.button("🗑️ Reset Repository Memory", type="secondary", help="Clears history for this repo to allow a full re-analysis."):
                if clear_repo_history(repo_url):
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
            col1.metric("Critical Evolution Issues", history_results.get("critical_issues_found", 0))
            risk = history_results.get("deployment_risk", "Unknown")
            risk_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")
            col2.metric("History Risk", f"{risk_color} {risk}")
        else:
            st.info("No commit history metadata available.")

def main():
    st.title("🛡️ DriftX 2.0: Unified Quality Gateway")
    st.markdown("""
    Welcome to DriftX 2.0. This agent performs a **Unified Quality Analysis** of your project.
    We check for requirement drift, feature completeness, and coding guidelines in one comprehensive pass.
    """)
    
    # Initialize Session State for Repository
    if 'repo_path' not in st.session_state:
        st.session_state.repo_path = None
    if 'available_commits' not in st.session_state:
        st.session_state.available_commits = []
    if 'last_fetched_url' not in st.session_state:
        st.session_state.last_fetched_url = None
    
    # Add info box
    with st.expander("ℹ️ How to use DriftX 2.0"):
        st.markdown("""
        **Standard Compliance Mode:**
        - Analyzes requirement drift (missing/extra/modified features)
        - Checks code compliance against Do's and Don'ts guidelines
        - Provides AI-generated remediation for all issues
        
        **Evaluation Analysis Mode:**
        - Identifies feature loss (missing or incomplete features)
        - Analyzes coverage gaps (security, best practices, error handling)
        - Provides detailed implementation guidance
        - **Review History Tab**: View commit history analysis showing code deletions and feature loss over time
        
        **Required Inputs:**
        - Git repository URL (GitHub, GitLab, Bitbucket)
        - Requirement documents (PDF, TXT, or MD)
        - Do's and Don'ts guidelines (optional but recommended)
        
        **Scoring:**
        - 90-100: Ready for deployment ✅
        - 75-89: Minor improvements needed ⚠️
        - Below 75: Major issues to address ⛔
        """)

    # Sidebar for Inputs
    with st.sidebar:
        st.header("🚀 Configuration")
            
        repo_url = st.text_input("Git Repository URL", placeholder="https://github.com/user/repo", key="repo_input")
        uploaded_files = st.file_uploader("Upload Requirement Docs", accept_multiple_files=True, type=['pdf', 'txt', 'md'])
        dos_donts_files = st.file_uploader("Upload Do's and Don'ts Docs", accept_multiple_files=True, type=['pdf', 'txt', 'md'])
        
        # Step 1: Initialize Repo
        if st.button("🔍 Fetch Repository Details", use_container_width=True):
            if not repo_url:
                st.error("Please provide a Git URL first.")
            else:
                try:
                    with st.spinner("Initializing Repository..."):
                        # Clean up previous repo if URL changed
                        if st.session_state.repo_path:
                            cleanup_repo(st.session_state.repo_path)
                            st.session_state.repo_path = None
                        
                        st.session_state.repo_path = clone_repo(repo_url)
                        st.session_state.last_fetched_url = repo_url
                        
                        analyzer = CommitAnalyzer(st.session_state.repo_path)
                        st.session_state.available_commits = analyzer.get_commit_history(max_commits=100)
                        st.success(f"Fetched {len(st.session_state.available_commits)} commits.")
                except Exception as e:
                    st.error(f"Failed to fetch repository: {e}")

        # Step 2: Selection (Optional but dynamic)
        base_commit_hash = None
        head_commit_hash = None
        
        if st.session_state.available_commits:
            st.divider()
            st.subheader("🧬 Select Evolution Range")
            commit_options = [f"{c['hash'][:8]} | {c['message']} ({c['date'][:10]})" for c in st.session_state.available_commits]
            
            # Default head is the latest
            head_select = st.selectbox("Head Commit (Newer)", options=commit_options, index=0)
            
            # Default base is the one before head if available, or incremental
            repo_history = get_repo_history(repo_url)
            last_analyzed_hash = next((e['last_commit_hash'] for e in repo_history if e.get('last_commit_hash')), None)
            
            base_idx = len(commit_options) - 1 # Default to oldest
            if last_analyzed_hash:
                for i, c in enumerate(st.session_state.available_commits):
                    if c['hash'].startswith(last_analyzed_hash[:8]):
                        base_idx = i
                        break
            
            base_select = st.selectbox("Base Commit (Older)", options=commit_options, index=base_idx)
            
            base_commit_hash = st.session_state.available_commits[commit_options.index(base_select)]['hash']
            head_commit_hash = st.session_state.available_commits[commit_options.index(head_select)]['hash']
            
        st.divider()
        process_btn = st.button("🚀 Start Analysis", type="primary", use_container_width=True)

    if process_btn:
        if not repo_url or not uploaded_files:
            st.error("Please provide both a Git URL and Requirement Documents.")
        else:
            st.info("🔄 Initializing Agents... Please wait.")
            
            # 1. Extract Requirements
            requirements_text = ""
            for uploaded_file in uploaded_files:
                requirements_text += f"\n\n--- {uploaded_file.name} ---\n"
                requirements_text += extract_text_from_file(uploaded_file)
            
            # 2. Extract Do's and Don'ts
            dos_donts_text = ""
            if dos_donts_files:
                for uploaded_file in dos_donts_files:
                    dos_donts_text += f"\n\n--- {uploaded_file.name} ---\n"
                    dos_donts_text += extract_text_from_file(uploaded_file)
            
            repo_path = st.session_state.repo_path
            try:
                # 3. Use Ready Repository
                if not repo_path:
                    with st.spinner("Cloning Repository..."):
                        repo_path = clone_repo(repo_url)
                        st.session_state.repo_path = repo_path
                
                # Fetch history for incremental logic if no manual selection
                repo_history = get_repo_history(repo_url)
                last_analyzed_commit = None
                if repo_history:
                    # Find the latest entry that has a last_commit_hash
                    for entry in repo_history:
                        if entry.get("last_commit_hash"):
                            last_analyzed_commit = entry["last_commit_hash"]
                            break
                
                # Determine range: Use selected hashes if available, else fallback to last analyzed
                final_base = base_commit_hash if base_commit_hash else last_analyzed_commit
                final_head = head_commit_hash if head_commit_hash else None
                
                # 3. Unified Quality Analysis
                compliance_agent = ComplianceAgent()
                with st.spinner("🤖 Performing Unified Quality Analysis..."):
                    results = compliance_agent.unified_analysis(repo_path, requirements_text, dos_donts_text)
                
                with st.spinner("📜 Analyzing feature evolution..."):
                    history_results = compliance_agent.analyze_feature_loss_with_history(
                        repo_path, 
                        requirements_text, 
                        dos_donts_text,
                        base_commit=final_base,
                        head_commit=final_head
                    )
                
                # Merge critical history findings into main issues for visibility
                if history_results and history_results.get("feature_changes"):
                    main_issues = results.get("issues", [])
                    for change in history_results.get("feature_changes", []):
                        if change.get('status') == 'Loss' and change.get('severity') == 'Critical':
                            main_issues.append({
                                "type": "Critical Feature Loss",
                                "description": f"Evolution analysis detected a missing feature: {change.get('feature_name')}",
                                "evidence": change.get("evidence"),
                                "reasoning": change.get("reasoning"),
                                "remediation": change.get("remediation")
                            })
                    results["issues"] = main_issues
                
                # 4. Save to History and Display
                final_score = results.get("score", 0)
                current_head = history_results.get("analysis_metadata", {}).get("head_commit")
                
                save_analysis(
                    repo_url, 
                    "Unified", 
                    final_score, 
                    results.get("summary", "Analysis completed."),
                    last_commit_hash=current_head
                )
                display_unified_analysis(results, history_results)
                    


            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                # We don't cleanup_repo here anymore to allow multiple runs on the same fetched repo
                pass

if __name__ == "__main__":
    main()
