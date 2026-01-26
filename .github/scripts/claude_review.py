#!/usr/bin/env python3
"""Claude Code Review for GitHub PRs.

Usage: claude_review.py "file1.py file2.py ..."
Requires: ANTHROPIC_API_KEY and GITHUB_TOKEN environment variables.
"""

import os
import sys
from pathlib import Path

import httpx

# Claude API configuration
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 8192

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"


def get_file_diff(file_path: str, base_ref: str) -> str:
    """Get git diff for a file."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", f"origin/{base_ref}...HEAD", "--", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return f"# Error getting diff for {file_path}"


def get_file_content(file_path: str) -> str:
    """Get file content."""
    path = Path(file_path)
    if not path.exists():
        return f"# File not found: {file_path}"
    return path.read_text()


def review_with_claude(files: list[str]) -> str:
    """Send code to Claude for review."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "❌ Error: ANTHROPIC_API_KEY not set"

    # Build context with diffs and current file content
    context_parts = ["# Code Review Request\n"]
    context_parts.append("Review the following changes for:\n")

    base_ref = os.environ.get("GITHUB_BASE_REF", "main")

    for file_path in files:
        context_parts.append(f"\n## {file_path}\n")
        diff = get_file_diff(file_path, base_ref)
        if diff.strip():
            context_parts.append(f"### Diff\n```diff\n{diff}\n```\n")
        # Also include current file for full context
        content = get_file_content(file_path)
        context_parts.append(f"### Current Content\n```python\n{content[:2000]}\n```\n")

    context_parts.append(
        "\n# Review Instructions\n"
        "Focus on:\n"
        "1. **Security issues** - injections, unsafe patterns\n"
        "2. **Bugs** - logic errors, edge cases\n"
        "3. **Type safety** - missing types, Any usage\n"
        "4. **Code smell** - duplication, complexity\n"
        "5. **Python best practices** - PEP 8, idioms\n\n"
        "Be concise. Use bullet points. Prefix issues with severity: 🔴 Critical, "
        "⚠️ Moderate, ℹ️ Minor."
    )

    prompt = "".join(context_parts)

    try:
        response = httpx.post(
            API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        return f"❌ Error calling Claude API: {e}"


def post_github_comment(pr_number: int, body: str) -> None:
    """Post review as a comment on the PR."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print("Error: GITHUB_TOKEN or GITHUB_REPOSITORY not set")
        return

    url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={"body": body},
        timeout=30.0,
    )

    if response.status_code == 201:
        print(f"✅ Review posted to PR #{pr_number}")
    else:
        print(f"❌ Failed to post comment: {response.status_code} {response.text}")


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: claude_review.py <file1> <file2> ...")
        return 1

    files = sys.argv[1].split()
    if not files:
        print("No files to review")
        return 0

    print(f"🔍 Reviewing {len(files)} file(s)...")

    review = review_with_claude(files)

    # Post to GitHub if this is a PR
    pr_number = os.environ.get("GITHUB_PR_NUMBER")
    if pr_number:
        formatted_review = f"## 🤖 Claude Code Review\n\n{review}"
        post_github_comment(int(pr_number), formatted_review)
    else:
        print(review)

    return 0


if __name__ == "__main__":
    sys.exit(main())
