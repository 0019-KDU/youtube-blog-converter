import os
import subprocess
from openai import OpenAI
import sys

def generate_pr_body():
    # Get base branch from environment or use default
    default_branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    base_branch = os.getenv("BASE_BRANCH", f"origin/{default_branch}")
    
    # Verify if base branch exists
    try:
        subprocess.check_output(
            ["git", "show-ref", "--verify", f"refs/remotes/{base_branch}"],
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError:
        print(f"Base branch {base_branch} not found. Using HEAD~1 instead")
        base_branch = "HEAD~1"  # Fallback to previous commit
    
    # Get code diff with safe exclusions
    try:
        # Build exclusion patterns
        exclude_patterns = [
            "venv/",
            "__pycache__/",
            "*.log",
            "config.yaml"
        ]
        
        command = ["git", "diff", base_branch, "--"]
        for pattern in exclude_patterns:
            command.extend([":(exclude)", pattern])
        
        diff = subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print(f"Git diff failed: {e.output}")
        # Fallback to simple diff
        diff = subprocess.check_output(
            ["git", "diff", base_branch],
            text=True
        )
    
    # Truncate large diffs
    truncated_diff = diff[:8000] + ("..." if len(diff) > 8000 else "")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # Generate PR body using AI
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Generate PR description: Summary, Changes, Impact"
                },
                {
                    "role": "user",
                    "content": f"Code changes:\n\n{truncated_diff}"
                }
            ],
            temperature=0.2,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Fallback to git info
        diff_stat = subprocess.check_output(["git", "diff", "--stat", base_branch], text=True)
        commits = subprocess.check_output(["git", "log", "--oneline", f"{base_branch}..HEAD"], text=True)
        return f"## Changes\n```\n{diff_stat}\n```\n## Commits\n{commits}"

if __name__ == "__main__":
    try:
        print(generate_pr_body())
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)