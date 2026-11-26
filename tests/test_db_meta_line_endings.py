"""The sites database must be checked out byte for byte.

`db_meta.json` carries a sha256 of `data.json`, and both the client's
auto-update and `test_bundled_db_meta_matches_data_json` compare that hash
against the file on disk. `data.json` holds about 130 000 newlines, so a
checkout that rewrites them (`core.autocrlf=true`, the default on a Windows
install of git) produces a different hash for identical content: the client
then rejects the database it just downloaded and keeps serving its old cache.

The guard is one line in `.gitattributes`. These tests fail if it is removed,
because the symptom appears on someone else's machine and never on CI.
"""

import os
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA = os.path.join(REPO, "maigret", "resources", "data.json")


def _inside_a_git_checkout() -> bool:
    """Tests also run from an unpacked sdist, where there is no repository and
    git may not be installed at all."""
    if shutil.which("git") is None:
        return False
    out = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return out.returncode == 0 and out.stdout.strip() == "true"


def test_data_json_is_exempt_from_newline_conversion():
    """Guards the guard: this fails if the `.gitattributes` line is dropped."""
    if not _inside_a_git_checkout():
        pytest.skip("not a git checkout, nothing to ask git about")
    out = subprocess.run(
        ["git", "check-attr", "text", "--", "maigret/resources/data.json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith(": text: unset"), (
        "data.json must be marked `-text` in .gitattributes, otherwise a "
        f"checkout can rewrite its newlines and break the hash: {out.stdout!r}"
    )


def test_checked_out_data_json_has_no_crlf():
    """Names the cause that the hash check cannot name.

    `test_bundled_db_meta_matches_data_json` fails on a rewritten checkout too,
    but it blames a stale meta and tells you to regenerate it, which is the one
    thing that will not help: regenerating would record the hash of the
    rewritten bytes and ship it.
    """
    with open(DATA, "rb") as f:
        raw = f.read()
    assert b"\r\n" not in raw, (
        "this checkout rewrote the newlines of data.json, so its sha256 no "
        "longer matches db_meta.json; check core.autocrlf and .gitattributes, "
        "and do not regenerate the meta to make the error go away"
    )
