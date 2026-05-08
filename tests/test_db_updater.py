"""Tests for the database auto-update system."""

import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from maigret.db_updater import (
    _parse_version,
    _needs_check,
    _is_version_compatible,
    _is_update_available,
    _load_state,
    _save_state,
    _best_local,
    _cached_db_path,
    _state_path,
    _now_iso,
    resolve_db_path,
    force_update,
    MAIGRET_HOME,
    BUNDLED_DB_PATH,
)


def test_parse_version():
    assert _parse_version("0.5.0") == (0, 5, 0)
    assert _parse_version("1.2.3") == (1, 2, 3)
    assert _parse_version("bad") == (0, 0, 0)
    assert _parse_version("") == (0, 0, 0)


def test_needs_check_no_state():
    assert _needs_check({}, 24) is True


def test_needs_check_recent():
    state = {"last_check_at": _now_iso()}
    assert _needs_check(state, 24) is False


def test_needs_check_expired():
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"last_check_at": old_time}
    assert _needs_check(state, 24) is True


def test_needs_check_corrupt():
    state = {"last_check_at": "not-a-date"}
    assert _needs_check(state, 24) is True


def test_version_compatible():
    with patch("maigret.db_updater.__version__", "0.5.0"):
        assert _is_version_compatible({"min_maigret_version": "0.5.0"}) is True
        assert _is_version_compatible({"min_maigret_version": "0.4.0"}) is True
        assert _is_version_compatible({"min_maigret_version": "0.6.0"}) is False
        assert _is_version_compatible({}) is True  # missing field = compatible


def test_update_available_no_cache(tmp_path):
    home = str(tmp_path)
    assert _is_update_available({"updated_at": "2026-01-01T00:00:00Z"}, {}, home) is True


def test_update_available_newer(tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write("{}")
    state = {"last_meta": {"updated_at": "2026-01-01T00:00:00Z"}}
    meta = {"updated_at": "2026-02-01T00:00:00Z"}
    assert _is_update_available(meta, state, home) is True


def test_update_available_same(tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write("{}")
    state = {"last_meta": {"updated_at": "2026-01-01T00:00:00Z"}}
    meta = {"updated_at": "2026-01-01T00:00:00Z"}
    assert _is_update_available(meta, state, home) is False


def test_load_state_missing(tmp_path):
    assert _load_state(str(tmp_path)) == {}


def test_load_state_corrupt(tmp_path):
    home = str(tmp_path)
    os.makedirs(home, exist_ok=True)
    corrupt = _state_path(home)
    with open(corrupt, "w") as f:
        f.write("not json{{{")
    assert _load_state(home) == {}


def test_save_and_load_state(tmp_path):
    home = str(tmp_path)
    _save_state({"last_check_at": "2026-01-01T00:00:00Z"}, home)
    loaded = _load_state(home)
    assert loaded["last_check_at"] == "2026-01-01T00:00:00Z"


def test_best_local_with_valid_cache(tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write('{"sites": {}, "engines": {}, "tags": []}')
    assert _best_local(home) == cache_path


def test_best_local_with_corrupt_cache(tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write("not json")
    assert _best_local(home) == BUNDLED_DB_PATH


def test_best_local_no_cache(tmp_path):
    assert _best_local(str(tmp_path)) == BUNDLED_DB_PATH


def test_resolve_db_path_custom_url():
    result = resolve_db_path("https://example.com/db.json")
    assert result == "https://example.com/db.json"


def test_resolve_db_path_custom_file(tmp_path):
    custom_db = tmp_path / "custom" / "path.json"
    custom_db.parent.mkdir(parents=True)
    custom_db.write_text("{}")
    result = resolve_db_path(str(custom_db))
    assert result.endswith(os.path.join("custom", "path.json"))


def test_resolve_db_path_no_autoupdate(tmp_path):
    home = str(tmp_path)
    result = resolve_db_path("resources/data.json", no_autoupdate=True, home=home)
    assert result == BUNDLED_DB_PATH


def test_resolve_db_path_no_autoupdate_with_cache(tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write('{"sites": {}, "engines": {}, "tags": []}')
    result = resolve_db_path("resources/data.json", no_autoupdate=True, home=home)
    assert result == cache_path


@patch("maigret.db_updater._fetch_meta")
def test_resolve_db_path_network_failure(mock_fetch, tmp_path):
    home = str(tmp_path)
    mock_fetch.return_value = None
    result = resolve_db_path("resources/data.json", home=home)
    assert result == BUNDLED_DB_PATH


# --- force_update tests ---


@patch("maigret.db_updater._fetch_meta")
def test_force_update_network_failure(mock_fetch, tmp_path):
    home = str(tmp_path)
    mock_fetch.return_value = None
    assert force_update(home=home) is False


@patch("maigret.db_updater._fetch_meta")
def test_force_update_incompatible_version(mock_fetch, tmp_path):
    home = str(tmp_path)
    mock_fetch.return_value = {"min_maigret_version": "99.0.0", "sites_count": 100}
    assert force_update(home=home) is False


@patch("maigret.db_updater._download_and_verify")
@patch("maigret.db_updater._fetch_meta")
def test_force_update_success(mock_fetch, mock_download, tmp_path):
    home = str(tmp_path)
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3200,
        "updated_at": "2099-01-01T00:00:00Z",
        "data_url": "https://example.com/data.json",
        "data_sha256": "abc123",
    }
    cache_path = _cached_db_path(home)
    mock_download.return_value = cache_path
    assert force_update(home=home) is True
    state = _load_state(home)
    assert state["last_meta"]["sites_count"] == 3200


@patch("maigret.db_updater._fetch_meta")
def test_force_update_already_up_to_date(mock_fetch, tmp_path):
    home = str(tmp_path)
    cache_path = _cached_db_path(home)
    state_path = _state_path(home)
    os.makedirs(home, exist_ok=True)
    with open(cache_path, "w") as f:
        f.write('{"sites": {}, "engines": {}, "tags": []}')
    with open(state_path, "w") as f:
        json.dump({
            "last_check_at": _now_iso(),
            "last_meta": {"updated_at": "2026-01-01T00:00:00Z", "sites_count": 3000},
        }, f)
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3000,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    assert force_update(home=home) is False


@patch("maigret.db_updater._download_and_verify")
@patch("maigret.db_updater._fetch_meta")
def test_force_update_download_fails(mock_fetch, mock_download, tmp_path):
    home = str(tmp_path)
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3200,
        "updated_at": "2099-01-01T00:00:00Z",
        "data_url": "https://example.com/data.json",
        "data_sha256": "abc123",
    }
    mock_download.return_value = None
    assert force_update(home=home) is False
