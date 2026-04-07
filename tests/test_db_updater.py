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
    _now_iso,
    resolve_db_path,
    force_update,
    CACHED_DB_PATH,
    BUNDLED_DB_PATH,
    STATE_PATH,
    MAIGRET_HOME,
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
    with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "nonexistent.json")):
        assert _is_update_available({"updated_at": "2026-01-01T00:00:00Z"}, {}) is True


def test_update_available_newer(tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text("{}")
    with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
        state = {"last_meta": {"updated_at": "2026-01-01T00:00:00Z"}}
        meta = {"updated_at": "2026-02-01T00:00:00Z"}
        assert _is_update_available(meta, state) is True


def test_update_available_same(tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text("{}")
    with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
        state = {"last_meta": {"updated_at": "2026-01-01T00:00:00Z"}}
        meta = {"updated_at": "2026-01-01T00:00:00Z"}
        assert _is_update_available(meta, state) is False


def test_load_state_missing(tmp_path):
    with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "missing.json")):
        assert _load_state() == {}


def test_load_state_corrupt(tmp_path):
    corrupt = tmp_path / "state.json"
    corrupt.write_text("not json{{{")
    with patch("maigret.db_updater.STATE_PATH", str(corrupt)):
        assert _load_state() == {}


def test_save_and_load_state(tmp_path):
    state_file = tmp_path / "state.json"
    with patch("maigret.db_updater.STATE_PATH", str(state_file)):
        with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
            _save_state({"last_check_at": "2026-01-01T00:00:00Z"})
            loaded = _load_state()
            assert loaded["last_check_at"] == "2026-01-01T00:00:00Z"


def test_best_local_with_valid_cache(tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text('{"sites": {}, "engines": {}, "tags": []}')
    with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
        assert _best_local() == str(cache)


def test_best_local_with_corrupt_cache(tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text("not json")
    with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
        assert _best_local() == BUNDLED_DB_PATH


def test_best_local_no_cache(tmp_path):
    with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "missing.json")):
        assert _best_local() == BUNDLED_DB_PATH


def test_resolve_db_path_custom_url():
    result = resolve_db_path("https://example.com/db.json")
    assert result == "https://example.com/db.json"


def test_resolve_db_path_custom_file(tmp_path):
    custom_db = tmp_path / "custom" / "path.json"
    custom_db.parent.mkdir(parents=True)
    custom_db.write_text("{}")
    result = resolve_db_path(str(custom_db))
    assert result.endswith("custom/path.json")


def test_resolve_db_path_no_autoupdate(tmp_path):
    with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "missing.json")):
        result = resolve_db_path("resources/data.json", no_autoupdate=True)
        assert result == BUNDLED_DB_PATH


def test_resolve_db_path_no_autoupdate_with_cache(tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text('{"sites": {}, "engines": {}, "tags": []}')
    with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
        result = resolve_db_path("resources/data.json", no_autoupdate=True)
        assert result == str(cache)


@patch("maigret.db_updater._fetch_meta")
def test_resolve_db_path_network_failure(mock_fetch, tmp_path):
    mock_fetch.return_value = None
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "state.json")):
            with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "missing.json")):
                result = resolve_db_path("resources/data.json")
                assert result == BUNDLED_DB_PATH


# --- force_update tests ---


@patch("maigret.db_updater._fetch_meta")
def test_force_update_network_failure(mock_fetch, tmp_path):
    mock_fetch.return_value = None
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "state.json")):
            assert force_update() is False


@patch("maigret.db_updater._fetch_meta")
def test_force_update_incompatible_version(mock_fetch, tmp_path):
    mock_fetch.return_value = {"min_maigret_version": "99.0.0", "sites_count": 100}
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "state.json")):
            assert force_update() is False


@patch("maigret.db_updater._download_and_verify")
@patch("maigret.db_updater._fetch_meta")
def test_force_update_success(mock_fetch, mock_download, tmp_path):
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3200,
        "updated_at": "2099-01-01T00:00:00Z",
        "data_url": "https://example.com/data.json",
        "data_sha256": "abc123",
    }
    mock_download.return_value = str(tmp_path / "data.json")
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "state.json")):
            with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "missing.json")):
                assert force_update() is True
                state = _load_state()
                assert state["last_meta"]["sites_count"] == 3200


@patch("maigret.db_updater._fetch_meta")
def test_force_update_already_up_to_date(mock_fetch, tmp_path):
    cache = tmp_path / "data.json"
    cache.write_text('{"sites": {}, "engines": {}, "tags": []}')
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "last_check_at": _now_iso(),
        "last_meta": {"updated_at": "2026-01-01T00:00:00Z", "sites_count": 3000},
    }))
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3000,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(state_file)):
            with patch("maigret.db_updater.CACHED_DB_PATH", str(cache)):
                assert force_update() is False


@patch("maigret.db_updater._download_and_verify")
@patch("maigret.db_updater._fetch_meta")
def test_force_update_download_fails(mock_fetch, mock_download, tmp_path):
    mock_fetch.return_value = {
        "min_maigret_version": "0.1.0",
        "sites_count": 3200,
        "updated_at": "2099-01-01T00:00:00Z",
        "data_url": "https://example.com/data.json",
        "data_sha256": "abc123",
    }
    mock_download.return_value = None
    with patch("maigret.db_updater.MAIGRET_HOME", str(tmp_path)):
        with patch("maigret.db_updater.STATE_PATH", str(tmp_path / "state.json")):
            with patch("maigret.db_updater.CACHED_DB_PATH", str(tmp_path / "missing.json")):
                assert force_update() is False
