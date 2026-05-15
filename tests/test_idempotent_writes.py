"""Tests for the 'don't rewrite files unless content actually changed' logic
in utils.generate_db_meta and utils.update_site_data. The point is to keep
sites.md and db_meta.json untouched when only the embedded timestamp/date
would change — so a precommit hook doesn't end up staging a no-op diff
every time someone runs the updater.
"""

import json
from datetime import datetime, timezone

from utils.generate_db_meta import (
    build_meta,
    meta_payload_equals,
    write_meta_if_changed,
)
from utils.update_site_data import (
    sites_md_payload_equals,
    write_sites_md_if_changed,
)


# ---------------------------------------------------------------------------
# generate_db_meta
# ---------------------------------------------------------------------------


def _write_data_json(path, sites):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sites": sites}, f)


def test_meta_payload_equals_ignores_timestamp():
    a = {"sites_count": 10, "data_sha256": "abc", "updated_at": "2026-01-01T00:00:00Z"}
    b = {"sites_count": 10, "data_sha256": "abc", "updated_at": "2027-12-31T23:59:59Z"}
    assert meta_payload_equals(a, b)


def test_meta_payload_equals_detects_real_change():
    a = {"sites_count": 10, "data_sha256": "abc", "updated_at": "2026-01-01T00:00:00Z"}
    b = {"sites_count": 11, "data_sha256": "abc", "updated_at": "2026-01-01T00:00:00Z"}
    assert not meta_payload_equals(a, b)


def test_write_meta_creates_file_when_missing(tmp_path):
    data_path = tmp_path / "data.json"
    meta_path = tmp_path / "db_meta.json"
    _write_data_json(data_path, {"GitHub": {}})

    meta, written = write_meta_if_changed(
        str(data_path), str(meta_path), "0.6.0", "https://example/data.json"
    )

    assert written is True
    assert meta_path.exists()
    on_disk = json.loads(meta_path.read_text())
    assert on_disk["sites_count"] == 1
    assert on_disk["updated_at"] == meta["updated_at"]


def test_write_meta_skips_when_only_timestamp_would_change(tmp_path):
    data_path = tmp_path / "data.json"
    meta_path = tmp_path / "db_meta.json"
    _write_data_json(data_path, {"GitHub": {}})

    # First write seeds the file with an old timestamp.
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _, written_first = write_meta_if_changed(
        str(data_path), str(meta_path), "0.6.0", "https://example/data.json", now=old
    )
    assert written_first is True
    seeded_bytes = meta_path.read_bytes()

    # Second call with a NEW `now` but identical data.json — must be a no-op.
    new = datetime(2027, 6, 15, tzinfo=timezone.utc)
    _, written_second = write_meta_if_changed(
        str(data_path), str(meta_path), "0.6.0", "https://example/data.json", now=new
    )
    assert written_second is False
    # File on disk is byte-for-byte the same — including the OLD timestamp.
    assert meta_path.read_bytes() == seeded_bytes
    on_disk = json.loads(meta_path.read_text())
    assert on_disk["updated_at"] == "2026-01-01T00:00:00Z"


def test_write_meta_writes_when_data_sha256_changes(tmp_path):
    data_path = tmp_path / "data.json"
    meta_path = tmp_path / "db_meta.json"

    _write_data_json(data_path, {"GitHub": {}})
    write_meta_if_changed(
        str(data_path),
        str(meta_path),
        "0.6.0",
        "https://example/data.json",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    # Real change to data.json — sha256 + sites_count both move.
    _write_data_json(data_path, {"GitHub": {}, "GitLab": {}})
    new_now = datetime(2027, 6, 15, tzinfo=timezone.utc)
    meta, written = write_meta_if_changed(
        str(data_path), str(meta_path), "0.6.0", "https://example/data.json", now=new_now
    )

    assert written is True
    on_disk = json.loads(meta_path.read_text())
    assert on_disk["sites_count"] == 2
    assert on_disk["updated_at"] == "2027-06-15T00:00:00Z"


def test_write_meta_writes_when_min_version_changes(tmp_path):
    data_path = tmp_path / "data.json"
    meta_path = tmp_path / "db_meta.json"
    _write_data_json(data_path, {"GitHub": {}})

    write_meta_if_changed(
        str(data_path),
        str(meta_path),
        "0.5.0",
        "https://example/data.json",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    _, written = write_meta_if_changed(
        str(data_path),
        str(meta_path),
        "0.6.0",  # bumped
        "https://example/data.json",
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert written is True
    on_disk = json.loads(meta_path.read_text())
    assert on_disk["min_maigret_version"] == "0.6.0"


def test_write_meta_writes_when_existing_file_is_corrupt(tmp_path):
    data_path = tmp_path / "data.json"
    meta_path = tmp_path / "db_meta.json"
    _write_data_json(data_path, {"GitHub": {}})
    meta_path.write_text("this is not valid json")

    _, written = write_meta_if_changed(
        str(data_path), str(meta_path), "0.6.0", "https://example/data.json"
    )

    assert written is True
    json.loads(meta_path.read_text())  # now parseable


def test_build_meta_uses_provided_now(tmp_path):
    data_path = tmp_path / "data.json"
    _write_data_json(data_path, {"GitHub": {}})
    fixed = datetime(2030, 7, 4, 12, 0, 0, tzinfo=timezone.utc)

    meta = build_meta(str(data_path), "0.6.0", "https://example/data.json", now=fixed)

    assert meta["updated_at"] == "2030-07-04T12:00:00Z"


# ---------------------------------------------------------------------------
# update_site_data
# ---------------------------------------------------------------------------


_SITES_MD_TEMPLATE = (
    "## List of supported sites (search methods): total 1\n\n"
    "Rank data fetched from Majestic Million by domains.\n\n"
    "1. [GitHub](https://github.com/)*: top 100*\n"
    "\nThe list was updated at ({date})\n"
    "## Statistics\n\n"
    "Some stats.\n"
)


def test_sites_md_payload_equals_ignores_date():
    a = _SITES_MD_TEMPLATE.format(date="2026-01-01")
    b = _SITES_MD_TEMPLATE.format(date="2027-12-31")
    assert sites_md_payload_equals(a, b)


def test_sites_md_payload_equals_detects_body_change():
    a = _SITES_MD_TEMPLATE.format(date="2026-01-01")
    b = a.replace("GitHub", "GitLab")
    assert not sites_md_payload_equals(a, b)


def test_write_sites_md_creates_file_when_missing(tmp_path):
    target = tmp_path / "sites.md"
    content = _SITES_MD_TEMPLATE.format(date="2026-05-15")

    written = write_sites_md_if_changed(content, str(target))

    assert written is True
    assert target.read_text() == content


def test_write_sites_md_skips_when_only_date_would_change(tmp_path):
    target = tmp_path / "sites.md"
    seeded = _SITES_MD_TEMPLATE.format(date="2026-01-01")
    target.write_text(seeded)

    # New content has a different date but identical body.
    new_content = _SITES_MD_TEMPLATE.format(date="2027-12-31")
    written = write_sites_md_if_changed(new_content, str(target))

    assert written is False
    # File untouched, including the OLD date.
    assert target.read_text() == seeded


def test_write_sites_md_writes_when_body_changes(tmp_path):
    target = tmp_path / "sites.md"
    target.write_text(_SITES_MD_TEMPLATE.format(date="2026-01-01"))

    new_content = _SITES_MD_TEMPLATE.format(date="2026-01-01").replace(
        "GitHub", "GitLab"
    )
    written = write_sites_md_if_changed(new_content, str(target))

    assert written is True
    assert "GitLab" in target.read_text()
    assert "GitHub" not in target.read_text()
