import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import json
from datetime import datetime
from mcp_server.tools.commit_analyzer import CommitAnalyzer

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
            - Subtract points for each issue found.
            - **MINIMUM SCORE IS 0**. The final score must be between 0 and 100.
            - -20: Major feature missing or incomplete.
            - -15: Violation of critical "Don't" guideline.
            - -10: Feature modified significantly without justification.
            - -10: Missing critical "Do" (security/validation).
            - -5: Minor extra feature (gold plating).
            - -5: Minor guideline deviation or code smell.
            
            **DEDUPLICATION**: If two or more issues are semantically the same (e.g., a "missing feature" and a "coverage gap" describing the same thing), merge them into a single concise item.
            
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
            response = chain.invoke({
                "requirements": requirements_text[:10000],
                "dos_donts": dos_donts_text[:5000] if dos_donts_text else "No specific guidelines provided.",
                "code_context": code_context
            })
            content = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            
            # Ensure score is within [0, 100]
            if "score" in data:
                try:
                    data["score"] = max(0.0, min(100.0, float(data["score"])))
                except:
                    data["score"] = 0.0
            return data
        except Exception as e:
            return {
                "error": str(e), 
                "score": 0, 
                "issues": [],
                "summary": f"Unified analysis failed: {str(e)}"
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
            - Subtract points for each issue found.
            - **MINIMUM SCORE IS 0**. The final score must be between 0 and 100.
            - -30: Critical feature deleted and NOT replaced.
            - -10: Feature replaced with inferior logic.
            - -5: Feature replaced with better/equivalent logic (refactor).
            
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
            response = chain.invoke({
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
            
            # Ensure feature_loss_score is within [0, 100]
            if "feature_loss_score" in result:
                try:
                    result["feature_loss_score"] = max(0.0, min(100.0, float(result["feature_loss_score"])))
                except:
                    result["feature_loss_score"] = 0.0
            
            # Add metadata
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
