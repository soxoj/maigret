"""The sites database must be checked out byte for byte.

`db_meta.json` carries a sha256 of `data.json`, and both the client's
auto-update and the agreement test from #3419 compare that hash against the
file on disk. `data.json` holds about 130 000 newlines, so a checkout that
rewrites them (`core.autocrlf=true`, the default on a Windows install of git)
produces a different hash for identical content: the client then rejects the
database it just downloaded and keeps serving its old cache.

The guard is one line in `.gitattributes`. These tests fail if it is removed,
because the symptom appears on someone else's machine and never on CI.
"""

import hashlib
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA = os.path.join(REPO, "maigret", "resources", "data.json")
META = os.path.join(REPO, "maigret", "resources", "db_meta.json")


def test_data_json_is_exempt_from_newline_conversion():
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
    with open(DATA, "rb") as f:
        raw = f.read()
    assert b"\r\n" not in raw, (
        "this checkout rewrote the newlines of data.json, so its sha256 no "
        "longer matches db_meta.json; check core.autocrlf and .gitattributes"
    )


def test_meta_matches_the_file_on_disk():
    """What the client checks, checked here: the recorded hash against the
    bytes actually present."""
    with open(DATA, "rb") as f:
        raw = f.read()
    with open(META, encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["data_sha256"] == hashlib.sha256(raw).hexdigest()
    assert meta["sites_count"] == len(json.loads(raw)["sites"])
