import subprocess
import json
import os

def run_radon(directory):
    """
    Runs Radon to compute Cyclomatic Complexity (cc) and Maintainability Index (mi).
    """
    try:
        # Cyclomatic Complexity
        cc_output = subprocess.check_output(
            ["radon", "cc", directory, "--json"], 
            text=True
        )
        cc_data = json.loads(cc_output)
        
        # Maintainability Index
        mi_output = subprocess.check_output(
            ["radon", "mi", directory, "--json"], 
            text=True
        )
        mi_data = json.loads(mi_output)
        
        return {
            "complexity": cc_data,
            "maintainability": mi_data
        }
    except Exception as e:
        return {"error": str(e)}

def run_bandit(directory):
    """
    Runs Bandit for security analysis.
    """
    try:
        # Run bandit and dump to JSON
        # -r for recursive, -f json for JSON format
        cmd = ["bandit", "-r", directory, "-f", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Bandit returns exit code 1 if issues found, so we check output mainly
        if result.stdout:
           try:
               return json.loads(result.stdout)
           except json.JSONDecodeError:
               return {"raw_output": result.stdout}
        return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test on local dir
    test_dir = "."
    print("Radon:", run_radon(test_dir))
    print("Bandit:", run_bandit(test_dir))
