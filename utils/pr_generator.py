import os
import subprocess
from openai import OpenAI
import sys
import re

def log(message):
    """Helper function for logging"""
    print(f"[DEBUG] {message}", file=sys.stderr)

def get_base_branch():
    """Get and verify base branch"""
    default_branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    base_branch = f"origin/{default_branch}"
    
    try:
        log(f"Checking base branch: {base_branch}")
        subprocess.check_output(
            ["git", "show-ref", "--verify", f"refs/remotes/{base_branch}"],
            stderr=subprocess.STDOUT,
            text=True
        )
        log(f"Using base branch: {base_branch}")
        return base_branch
    except subprocess.CalledProcessError:
        log("Base branch not found, using HEAD~1")
        return "HEAD~1"

def get_git_diff(base_branch):
    """Get git diff with safe exclusions"""
    exclude_patterns = [
        "venv/", "__pycache__/", "*.log", "config.yaml", ".env",
        "*.lock", "package-lock.json", "yarn.lock", "*.md",
        "*.json", "*.yaml", "*.yml", "node_modules/", "dist/",
        "build/", ".gitignore", ".github/"
    ]
    
    try:
        command = ["git", "diff", base_branch, "--"]
        for pattern in exclude_patterns:
            command.extend([":(exclude)", pattern])
        
        log("Getting diff with command: " + " ".join(command))
        diff = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        log(f"Diff length: {len(diff)} characters")
        return diff
    except subprocess.CalledProcessError as e:
        log(f"Git diff failed: {e.output}")
        log("Falling back to simple diff")
        return subprocess.check_output(["git", "diff", base_branch], text=True)

def truncate_diff(diff, max_length=8000):
    """Truncate diff if too long"""
    if len(diff) > max_length:
        log(f"Truncating diff from {len(diff)} to {max_length} characters")
        return diff[:max_length] + "\n... [truncated]"
    return diff

def generate_with_openai(diff):
    """Generate PR body using OpenAI API"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("OPENAI_API_KEY not found in environment")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        log("Sending request to OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer. Generate a concise PR description in markdown with: "
                               "1) Summary of Changes, 2) Key Improvements, 3) Potential Concerns. "
                               "Focus on logic changes, not formatting."
                },
                {
                    "role": "user",
                    "content": f"Analyze these code changes:\n\n{diff}"
                }
            ],
            temperature=0.2,
            max_tokens=600
        )
        
        log("Received response from OpenAI")
        return response.choices[0].message.content.strip()
    except Exception as e:
        log(f"OpenAI error: {str(e)}")
        return None

def fallback_git_info(base_branch):
    """Fallback to git info if OpenAI fails"""
    try:
        log("Generating fallback with git info")
        diff_stat = subprocess.check_output(["git", "diff", "--stat", base_branch], text=True)
        commits = subprocess.check_output(["git", "log", "--oneline", f"{base_branch}..HEAD"], text=True)
        return f"## Changes\n```\n{diff_stat}\n```\n## Commits\n{commits}"
    except Exception as e:
        log(f"Git fallback failed: {str(e)}")
        return "## Auto-generated PR\nChanges require review"

def main():
    try:
        log("Starting PR body generation")
        
        base_branch = get_base_branch()
        diff = get_git_diff(base_branch)
        truncated_diff = truncate_diff(diff)
        
        pr_body = generate_with_openai(truncated_diff)
        
        if not pr_body:
            log("OpenAI generation failed, using fallback")
            pr_body = fallback_git_info(base_branch)
        
        # Clean up output
        pr_body = re.sub(r'<!--.*?-->', '', pr_body, flags=re.DOTALL)
        pr_body = pr_body.strip()
        
        log("PR body generation successful")
        return pr_body
        
    except Exception as e:
        log(f"Critical error: {str(e)}")
        return "## Auto-generated PR\nChanges require review"

if __name__ == "__main__":
    body = main()
    print(body)