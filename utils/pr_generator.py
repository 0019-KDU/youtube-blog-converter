import os
import subprocess
import openai
import re

def generate_pr_body():
    # Get base branch (default to main)
    base_branch = os.getenv("BASE_BRANCH", "origin/main")
    
    # Get code diff with safe exclusions
    diff = subprocess.check_output(
        ["git", "diff", base_branch, "--", 
         ":!venv/", ":!__pycache__/", ":!*.log", ":!config.yaml"],
        text=True,
        stderr=subprocess.DEVNULL
    )
    
    # Truncate large diffs (stay within token limits)
    truncated_diff = diff[:8000] + ("..." if len(diff) > 8000 else "")
    
    # Initialize OpenAI
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # Generic prompt that won't interfere with other functionality
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a PR description with: Summary, Changes, Impact. Focus on code logic."
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
        # Fallback to simple git info
        print(f"OpenAI error: {e}")
        diff_stat = subprocess.check_output(["git", "diff", "--stat", base_branch], text=True)
        commits = subprocess.check_output(["git", "log", "--oneline", f"{base_branch}..HEAD"], text=True)
        return f"## Changes\n```\n{diff_stat}\n```\n## Commits\n{commits}"

if __name__ == "__main__":
    print(generate_pr_body())