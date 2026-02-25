import sys
import os
import argparse
from dotenv import load_dotenv
from mcp_server.tools.git_reader import clone_repo, cleanup_repo
from agents.compliance_agent import ComplianceAgent
from history_manager import save_analysis, get_repo_history

# Load env immediately
load_dotenv()

import json

def main():
    parser = argparse.ArgumentParser(description="DriftX 2.0 CI/CD Gate")
    parser.add_argument("--repo", required=True, help="Git Repository URL")
    parser.add_argument("--requirements", required=True, help="Path to requirements document (txt/md)")
    parser.add_argument("--dos-donts", help="Path to do's and don'ts document (txt/md)")
    parser.add_argument("--mode", choices=["standard", "evaluation"], default="standard", 
                        help="Analysis mode: standard (compliance) or evaluation (feature/coverage with history)")
    parser.add_argument("--threshold", type=int, default=90, help="Minimum score to pass (default: 90)")
    parser.add_argument("--json", help="Path to save results as JSON")
    args = parser.parse_args()

    repo_url = args.repo
    requirements_path = args.requirements
    dos_donts_path = args.dos_donts
    
    print(f"🚀 Starting DriftX 2.0 Gate Analysis for {repo_url}")
    print(f"📋 Mode: {args.mode.upper()}")
    
    # Read requirements
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            requirements_text = f.read()
    except Exception as e:
        print(f"❌ Error reading requirements file: {e}")
        sys.exit(1)
    
    # Read do's and don'ts if provided
    dos_donts_text = ""
    if dos_donts_path:
        try:
            with open(dos_donts_path, 'r', encoding='utf-8') as f:
                dos_donts_text = f.read()
            print(f"✅ Loaded Do's and Don'ts guidelines")
        except Exception as e:
            print(f"⚠️ Warning: Could not read do's and don'ts file: {e}")

    repo_path = None
    try:
        print("🔄 Cloning repository...")
        repo_path = clone_repo(repo_url)
        
        # 3. Unified Quality Analysis
        print("🤖 Running Unified Quality Analysis...")
        comp_agent = ComplianceAgent()
        results = comp_agent.unified_analysis(repo_path, requirements_text, dos_donts_text)
        
        # 4. History / Feature Loss Analysis (Incremental)
        repo_history = get_repo_history(repo_url)
        last_analyzed_commit = None
        if repo_history:
            for entry in repo_history:
                if entry.get("last_commit_hash"):
                    last_analyzed_commit = entry["last_commit_hash"]
                    break
                    
        print("📜 Analyzing feature evolution history...")
        history_results = comp_agent.analyze_feature_loss_with_history(
            repo_path, requirements_text, dos_donts_text, base_commit=last_analyzed_commit
        )
        
        final_score = results.get("score", 0)
        current_head = history_results.get("analysis_metadata", {}).get("head_commit")
        
        print(f"\n🏁 Final Score: {final_score:.1f}/100 (Threshold: {args.threshold})")
        
        if final_score >= args.threshold:
            print("✅ Quality Gate Passed!")
        else:
            print("⛔ Quality Gate Failed.")
            print("\n--- Compliance Issues ---")
            for issue in results.get("issues", []):
                issue_type = issue.get('type', '')
                is_critical = any(word in issue_type.lower() for word in ['loss', 'drift', 'violation', 'missing', 'failed'])
                color_start = "\033[91m" if is_critical else ""
                color_end = "\033[0m" if is_critical else ""
                
                print(f"{color_start}[{issue_type}]{color_end} {issue.get('description')}")
                if issue.get('evidence'):
                    print(f"   {color_start}Evidence:{color_end} {issue.get('evidence')}")
        
        if history_results.get("feature_changes"):
            print("\n--- Feature Evolution (Loss/Replacement) ---")
            for change in history_results.get("feature_changes", []):
                status = change.get('status', '')
                is_loss = 'loss' in status.lower() or 'missing' in status.lower()
                status_icon = "❌" if is_loss else "🔄"
                color_start = "\033[91m" if is_loss else ""
                color_end = "\033[0m" if is_loss else ""
                
                print(f"{status_icon} {color_start}{change.get('feature_name')} ({status}){color_end}")
                print(f"   Impact: {change.get('impact')}")
                if change.get('replacement_logic'):
                    print(f"   Replacement: {change.get('replacement_logic')}")
                if change.get('evidence'):
                    print(f"   {color_start}Evidence:{color_end} {change.get('evidence')}")
        
        # Save to history with last commit hash
        save_analysis(
            repo_url, 
            "Unified", 
            final_score, 
            results.get("summary", "CLI Analysis completed."),
            last_commit_hash=current_head
        )
        
        if final_score < args.threshold:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        sys.exit(1)

    finally:
        if 'args' in locals() and args.json:
            try:
                results_json = {"repo": args.repo, "score": final_score if 'final_score' in locals() else 0}
                with open(args.json, 'w') as f:
                    json.dump(results_json, f, indent=4)
                print(f"✅ Saved results to {args.json}")
            except Exception as e:
                print(f"⚠️ Warning: Could not save results to JSON: {e}")
        if repo_path:
            cleanup_repo(repo_path)

if __name__ == "__main__":
    main()
