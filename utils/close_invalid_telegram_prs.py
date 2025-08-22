#!/usr/bin/env python3
"""
Utility script to close pull requests with titles matching "Invalid result https://t.me/..."

This script identifies and closes PRs that follow the pattern of invalid telegram results,
which are typically auto-generated or spam PRs that should not be processed.
"""

import argparse
import os
import re
import sys
from typing import List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library is required. Install with: pip install requests")
    sys.exit(1)


class GitHubAPI:
    """Simple GitHub API wrapper for managing pull requests."""
    
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_open_prs(self) -> List[dict]:
        """Get all open pull requests."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls"
        params = {"state": "open", "per_page": 100}
        
        all_prs = []
        page = 1
        
        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            prs = response.json()
            if not prs:
                break
                
            all_prs.extend(prs)
            page += 1
            
        return all_prs
    
    def close_pr(self, pr_number: int, comment: Optional[str] = None) -> bool:
        """Close a pull request with an optional comment."""
        try:
            # Add comment if provided
            if comment:
                comment_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
                comment_data = {"body": comment}
                response = requests.post(comment_url, headers=self.headers, json=comment_data)
                response.raise_for_status()
            
            # Close the PR
            close_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
            close_data = {"state": "closed"}
            response = requests.patch(close_url, headers=self.headers, json=close_data)
            response.raise_for_status()
            
            return True
        except requests.RequestException as e:
            print(f"Error closing PR #{pr_number}: {e}")
            return False


def is_invalid_telegram_pr(title: str) -> bool:
    """
    Check if a PR title matches the pattern "Invalid result https://t.me/..."
    
    Args:
        title: The PR title to check
        
    Returns:
        True if the title matches the pattern, False otherwise
    """
    # Pattern: "Invalid result https://t.me/..." (case insensitive)
    pattern = r"^invalid\s+result\s+https://t\.me/.*"
    return bool(re.match(pattern, title.strip(), re.IGNORECASE))


def find_invalid_telegram_prs(github_api: GitHubAPI) -> List[dict]:
    """
    Find all open PRs that match the invalid telegram pattern.
    
    Args:
        github_api: GitHub API wrapper instance
        
    Returns:
        List of PR dictionaries that match the pattern
    """
    all_prs = github_api.get_open_prs()
    matching_prs = []
    
    for pr in all_prs:
        if is_invalid_telegram_pr(pr["title"]):
            matching_prs.append(pr)
    
    return matching_prs


def main():
    """Main function to find and close invalid telegram PRs."""
    parser = argparse.ArgumentParser(
        description="Close pull requests with titles matching 'Invalid result https://t.me/...'"
    )
    parser.add_argument(
        "--token",
        required=False,
        help="GitHub personal access token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--owner",
        default="soxoj",
        help="Repository owner (default: soxoj)"
    )
    parser.add_argument(
        "--repo", 
        default="maigret",
        help="Repository name (default: maigret)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be closed without actually closing PRs"
    )
    parser.add_argument(
        "--comment",
        default="Automatically closing this PR as it appears to be an invalid result for a Telegram URL. "
                "If this is a legitimate PR, please reopen it with a more descriptive title.",
        help="Comment to add when closing PRs"
    )
    
    args = parser.parse_args()
    
    # Get GitHub token
    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token is required. Provide via --token or GITHUB_TOKEN env var")
        sys.exit(1)
    
    # Initialize GitHub API
    try:
        github_api = GitHubAPI(token, args.owner, args.repo)
    except Exception as e:
        print(f"Error initializing GitHub API: {e}")
        sys.exit(1)
    
    # Find matching PRs
    print(f"Searching for PRs matching pattern in {args.owner}/{args.repo}...")
    try:
        matching_prs = find_invalid_telegram_prs(github_api)
    except Exception as e:
        print(f"Error fetching PRs: {e}")
        sys.exit(1)
    
    if not matching_prs:
        print("No PRs found matching the pattern 'Invalid result https://t.me/...'")
        return
    
    print(f"Found {len(matching_prs)} PR(s) matching the pattern:")
    
    for pr in matching_prs:
        print(f"  - PR #{pr['number']}: {pr['title']}")
        print(f"    Created by: {pr['user']['login']}")
        print(f"    URL: {pr['html_url']}")
        print()
    
    if args.dry_run:
        print("Dry run mode: No PRs were actually closed.")
        return
    
    # Confirm before closing
    response = input(f"Close {len(matching_prs)} PR(s)? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Close PRs
    closed_count = 0
    for pr in matching_prs:
        print(f"Closing PR #{pr['number']}: {pr['title']}")
        if github_api.close_pr(pr['number'], args.comment):
            closed_count += 1
            print(f"  ✓ Closed successfully")
        else:
            print(f"  ✗ Failed to close")
    
    print(f"\nClosed {closed_count} out of {len(matching_prs)} PRs.")


if __name__ == "__main__":
    main()