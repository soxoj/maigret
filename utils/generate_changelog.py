"""Fill the CHANGELOG.md "What's Changed" section for a release.

Reproduces exactly what the GitHub "Generate release notes" button produces
(``* <PR title> by @<author> in <url>`` bullets, plus New Contributors and the
Full Changelog footer) and drops it under a ``## [<version>] - <date>`` heading
at the top of CHANGELOG.md — the same shape every prior release entry uses.

The notes are fetched via the GitHub REST API through the ``gh`` CLI, so it uses
your existing ``gh auth`` credentials (or GITHUB_TOKEN in CI). No PR data is
invented locally: the source of truth is GitHub, identical to how the section
was produced before.

Usage:
    python utils/generate_changelog.py                 # version from __version__.py, prev tag auto
    python utils/generate_changelog.py --version 0.6.2 --previous-tag v0.6.1
    python utils/generate_changelog.py --print         # print notes, don't touch CHANGELOG.md
"""

import argparse
import json
import os.path as path
import re
import subprocess
from datetime import date as date_cls
from typing import Optional

REPO_ROOT = path.dirname(path.dirname(path.abspath(__file__)))
VERSION_FILE = path.join(REPO_ROOT, "maigret", "__version__.py")
CHANGELOG_PATH = path.join(REPO_ROOT, "CHANGELOG.md")


def get_current_version() -> str:
    """Read __version__ from maigret/__version__.py."""
    with open(VERSION_FILE) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("'\"")
    raise RuntimeError(f"__version__ not found in {VERSION_FILE}")


def _run(cmd: list) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def get_repo_slug() -> str:
    """Return 'owner/repo' parsed from the origin remote."""
    url = _run(["git", "-C", REPO_ROOT, "remote", "get-url", "origin"]).strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        raise RuntimeError(f"Cannot parse GitHub repo from remote url: {url}")
    return m.group(1)


def get_latest_tag() -> Optional[str]:
    """Latest v* tag by creation date, or None if there are no version tags."""
    out = _run(["git", "-C", REPO_ROOT, "tag", "--list", "v*", "--sort=-creatordate"])
    tags = [t for t in out.splitlines() if t.strip()]
    return tags[0] if tags else None


def fetch_release_notes(repo: str, tag_name: str, previous_tag: Optional[str], commitish: str) -> str:
    """Fetch GitHub auto-generated release notes body for the given tag range.

    Works even when ``tag_name`` does not exist yet by pinning ``target_commitish``.
    """
    cmd = [
        "gh", "api", "--method", "POST",
        f"repos/{repo}/releases/generate-notes",
        "-f", f"tag_name={tag_name}",
        "-f", f"target_commitish={commitish}",
    ]
    if previous_tag:
        cmd += ["-f", f"previous_tag_name={previous_tag}"]
    body = json.loads(_run(cmd))["body"].strip()
    return body


def build_section(version: str, release_date: str, notes_body: str) -> str:
    """Assemble one CHANGELOG entry: '## [version] - date' + the notes body."""
    return f"## [{version}] - {release_date}\n\n{notes_body.strip()}\n"


# Matches a version heading like "## [0.6.2] - 2026-07-01" up to (not including)
# the next version heading or end of file.
_SECTION_RE_TMPL = r"^## \[{version}\][^\n]*\n.*?(?=^## \[|\Z)"


def upsert_section(changelog: str, version: str, section: str) -> str:
    """Insert ``section`` for ``version`` into ``changelog``.

    If an entry for ``version`` already exists (e.g. an empty placeholder left by
    the version bump) it is replaced; otherwise the section is inserted directly
    after the top-level '# Changelog' title. Idempotent.
    """
    section = section.rstrip("\n") + "\n"
    pattern = re.compile(_SECTION_RE_TMPL.format(version=re.escape(version)), re.DOTALL | re.MULTILINE)
    if pattern.search(changelog):
        return pattern.sub(lambda _: section + "\n", changelog, count=1)

    # No existing entry: insert after the "# Changelog" header.
    title = re.compile(r"^# Changelog[^\n]*\n", re.MULTILINE)
    m = title.search(changelog)
    if not m:
        return section + "\n" + changelog
    idx = m.end()
    return changelog[:idx] + "\n" + section + "\n" + changelog[idx:].lstrip("\n")


def main():
    parser = argparse.ArgumentParser(description="Fill CHANGELOG.md What's Changed from GitHub release notes")
    parser.add_argument("--version", default=None, help="Release version (default: read from __version__.py)")
    parser.add_argument("--previous-tag", default=None, help="Previous git tag (default: latest v* tag)")
    parser.add_argument("--date", default=None, help="Release date YYYY-MM-DD (default: today)")
    parser.add_argument("--commitish", default="HEAD", help="Target commit/branch for the release (default: HEAD)")
    parser.add_argument("--repo", default=None, help="owner/repo (default: parsed from origin remote)")
    parser.add_argument("--print", dest="print_only", action="store_true", help="Print notes only; do not edit CHANGELOG.md")
    args = parser.parse_args()

    version = args.version or get_current_version()
    tag_name = f"v{version}"
    previous_tag = args.previous_tag or get_latest_tag()
    release_date = args.date or date_cls.today().isoformat()
    repo = args.repo or get_repo_slug()

    notes = fetch_release_notes(repo, tag_name, previous_tag, args.commitish)
    section = build_section(version, release_date, notes)

    if args.print_only:
        print(section)
        return

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        changelog = f.read()
    updated = upsert_section(changelog, version, section)
    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    n_prs = notes.count("\n* ") + (1 if notes.lstrip().startswith("* ") else 0)
    print(f"Updated {CHANGELOG_PATH}: {version} ({previous_tag or 'start'}..{tag_name}), ~{n_prs} entries")


if __name__ == "__main__":
    main()
