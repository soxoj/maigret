# Invalid Telegram PR Auto-Closer

This repository includes an automated solution to identify and close pull requests with titles matching the pattern "Invalid result https://t.me/...". These PRs are typically auto-generated or spam submissions that should not be processed.

## Components

### 1. Python Script (`utils/close_invalid_telegram_prs.py`)

A utility script that:
- Searches for open PRs matching the pattern "Invalid result https://t.me/..."
- Optionally closes them with a descriptive comment
- Supports dry-run mode for testing
- Uses the GitHub API to interact with the repository

#### Usage

```bash
# Dry run (show what would be closed without closing)
python utils/close_invalid_telegram_prs.py --dry-run

# Close matching PRs interactively
python utils/close_invalid_telegram_prs.py

# Close PRs with custom comment
python utils/close_invalid_telegram_prs.py --comment "Custom closure message"

# Use with different repository
python utils/close_invalid_telegram_prs.py --owner username --repo repository
```

#### Requirements

- Python 3.6+
- `requests` library: `pip install requests`
- GitHub personal access token with repository access

#### Authentication

Set your GitHub token via:
- Command line: `--token YOUR_TOKEN`
- Environment variable: `export GITHUB_TOKEN=YOUR_TOKEN`

### 2. GitHub Actions Workflow (`.github/workflows/close-invalid-telegram-prs.yml`)

An automated workflow that:
- Runs daily at 2 AM UTC (in dry-run mode by default)
- Can be manually triggered with option to actually close PRs
- Uses the repository's `GITHUB_TOKEN` for authentication

#### Manual Trigger

1. Go to the Actions tab in your GitHub repository
2. Select "Close Invalid Telegram PRs" workflow
3. Click "Run workflow"
4. Choose whether to run in dry-run mode or actually close PRs

### 3. Tests (`tests/test_close_invalid_telegram_prs.py`)

Unit tests that verify:
- Correct identification of matching PR titles
- Proper rejection of non-matching titles
- Case-insensitive pattern matching
- Whitespace handling

Run tests with:
```bash
python tests/test_close_invalid_telegram_prs.py
```

## Pattern Detection

The script identifies PRs with titles matching:
- `Invalid result https://t.me/...` (case insensitive)
- Various whitespace and formatting variations
- Any Telegram URL after the pattern

### Examples of Matching Titles

- "Invalid result https://t.me/someuser"
- "INVALID RESULT https://t.me/channel123"
- "Invalid Result https://t.me/bot_name"
- "  Invalid result https://t.me/user/123  " (with whitespace)

### Examples of Non-Matching Titles

- "Valid result https://t.me/someuser" (not "Invalid")
- "Invalid results https://t.me/someuser" (plural "results")
- "Fix invalid result https://t.me/someuser" (extra words)
- "Invalid result http://t.me/someuser" (http instead of https)

## Security

- The GitHub Actions workflow only has the minimum required permissions
- The script requires explicit confirmation before closing PRs (except in automated mode)
- All actions are logged and can be audited
- Dry-run mode is available for testing

## Customization

You can customize the behavior by:
- Modifying the regex pattern in `is_invalid_telegram_pr()` function
- Changing the default comment message
- Adjusting the GitHub Actions schedule
- Adding additional validation logic

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your GitHub token has the required permissions
2. **No PRs Found**: This is normal if there are no matching PRs
3. **Rate Limiting**: The script handles GitHub API rate limits automatically

### Debug Mode

Run with verbose output:
```bash
python utils/close_invalid_telegram_prs.py --dry-run
```

This will show exactly which PRs match the pattern without closing them.