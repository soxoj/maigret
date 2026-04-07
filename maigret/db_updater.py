"""
Database auto-update logic for maigret.

Checks a lightweight meta file to determine if a newer site database is available,
downloads it if compatible, and caches it locally in ~/.maigret/.
"""

import hashlib
import json
import logging
import os
import os.path as path
import tempfile
from datetime import datetime, timezone
from typing import Optional

import requests
from colorama import Fore, Style

from .__version__ import __version__

logger = logging.getLogger("maigret")

_use_color = True


def _print_info(msg: str) -> None:
    text = f"[*] {msg}"
    if _use_color:
        print(Style.BRIGHT + Fore.GREEN + text + Style.RESET_ALL)
    else:
        print(text)


def _print_success(msg: str) -> None:
    text = f"[+] {msg}"
    if _use_color:
        print(Style.BRIGHT + Fore.GREEN + text + Style.RESET_ALL)
    else:
        print(text)


def _print_warning(msg: str) -> None:
    text = f"[!] {msg}"
    if _use_color:
        print(Style.BRIGHT + Fore.YELLOW + text + Style.RESET_ALL)
    else:
        print(text)


DEFAULT_META_URL = (
    "https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/db_meta.json"
)
DEFAULT_CHECK_INTERVAL_HOURS = 24
MAIGRET_HOME = path.expanduser("~/.maigret")
CACHED_DB_PATH = path.join(MAIGRET_HOME, "data.json")
STATE_PATH = path.join(MAIGRET_HOME, "autoupdate_state.json")
BUNDLED_DB_PATH = path.join(path.dirname(path.realpath(__file__)), "resources", "data.json")


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like '0.5.0' into a comparable tuple (0, 5, 0)."""
    try:
        return tuple(int(x) for x in version_str.strip().split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _ensure_maigret_home() -> None:
    os.makedirs(MAIGRET_HOME, exist_ok=True)


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    _ensure_maigret_home()
    tmp_path = STATE_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, STATE_PATH)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _needs_check(state: dict, interval_hours: int) -> bool:
    last_check = state.get("last_check_at")
    if not last_check:
        return True
    try:
        last_dt = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
        return elapsed >= interval_hours
    except (ValueError, TypeError):
        return True


def _fetch_meta(meta_url: str, timeout: int = 10) -> Optional[dict]:
    try:
        response = requests.get(meta_url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def _is_version_compatible(meta: dict) -> bool:
    min_ver = meta.get("min_maigret_version", "0.0.0")
    return _parse_version(__version__) >= _parse_version(min_ver)


def _is_update_available(meta: dict, state: dict) -> bool:
    if not path.isfile(CACHED_DB_PATH):
        return True
    remote_date = meta.get("updated_at", "")
    cached_date = state.get("last_meta", {}).get("updated_at", "")
    return remote_date > cached_date


def _download_and_verify(data_url: str, expected_sha256: str, timeout: int = 60) -> Optional[str]:
    _ensure_maigret_home()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=MAIGRET_HOME, suffix=".json")
    try:
        response = requests.get(data_url, timeout=timeout)
        if response.status_code != 200:
            return None

        content = response.content
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != expected_sha256:
            _print_warning("DB auto-update: SHA-256 mismatch, download rejected")
            return None

        # Validate JSON structure
        data = json.loads(content)
        if not all(k in data for k in ("sites", "engines", "tags")):
            _print_warning("DB auto-update: invalid database structure")
            return None

        os.write(tmp_fd, content)
        os.close(tmp_fd)
        tmp_fd = None
        os.replace(tmp_path, CACHED_DB_PATH)
        return CACHED_DB_PATH
    except Exception:
        return None
    finally:
        if tmp_fd is not None:
            os.close(tmp_fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _best_local() -> str:
    """Return cached DB if it exists and is valid, otherwise bundled."""
    if path.isfile(CACHED_DB_PATH):
        try:
            with open(CACHED_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "sites" in data:
                return CACHED_DB_PATH
        except (json.JSONDecodeError, OSError):
            pass
    return BUNDLED_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_db_path(
    db_file_arg: str,
    no_autoupdate: bool = False,
    meta_url: str = DEFAULT_META_URL,
    check_interval_hours: int = DEFAULT_CHECK_INTERVAL_HOURS,
    color: bool = True,
) -> str:
    """
    Determine which database file to use, potentially downloading an update.

    Returns the path to the database file that should be loaded.
    """
    global _use_color
    _use_color = color

    default_db_name = "resources/data.json"

    # User specified a custom DB — skip auto-update
    is_url = db_file_arg.startswith("http://") or db_file_arg.startswith("https://")
    is_default = db_file_arg == default_db_name
    if is_url:
        return db_file_arg
    if not is_default:
        # Try the path as-is (absolute or relative to cwd) first.
        if path.isfile(db_file_arg):
            return path.abspath(db_file_arg)
        # Fall back to legacy behavior: resolve relative to the maigret module dir.
        module_relative = path.join(path.dirname(path.realpath(__file__)), db_file_arg)
        if module_relative != db_file_arg and path.isfile(module_relative):
            return module_relative
        if module_relative != db_file_arg:
            raise FileNotFoundError(
                f"Custom database file not found: {db_file_arg!r} "
                f"(also tried {module_relative!r})"
            )
        raise FileNotFoundError(f"Custom database file not found: {db_file_arg!r}")

    # Auto-update disabled
    if no_autoupdate:
        return _best_local()

    # Check interval
    _ensure_maigret_home()
    state = _load_state()
    if not _needs_check(state, check_interval_hours):
        return _best_local()

    # Time to check
    _print_info("DB auto-update: checking for updates...")
    meta = _fetch_meta(meta_url)
    if meta is None:
        _print_warning("DB auto-update: could not reach update server, using local database")
        state["last_check_at"] = _now_iso()
        _save_state(state)
        return _best_local()

    # Version compatibility
    if not _is_version_compatible(meta):
        min_ver = meta.get("min_maigret_version", "?")
        _print_warning(
            f"DB auto-update: latest database requires maigret >= {min_ver}, "
            f"you have {__version__}. Please upgrade with: pip install -U maigret"
        )
        state["last_check_at"] = _now_iso()
        _save_state(state)
        return _best_local()

    # Check if update available
    if not _is_update_available(meta, state):
        sites_count = meta.get("sites_count", "?")
        _print_info(f"DB auto-update: database is up to date ({sites_count} sites)")
        state["last_check_at"] = _now_iso()
        state["last_meta"] = meta
        _save_state(state)
        return _best_local()

    # Download update
    new_count = meta.get("sites_count", "?")
    old_count = state.get("last_meta", {}).get("sites_count")
    if old_count:
        _print_info(f"DB auto-update: downloading updated database ({new_count} sites, was {old_count})...")
    else:
        _print_info(f"DB auto-update: downloading database ({new_count} sites)...")

    data_url = meta.get("data_url", "")
    expected_sha = meta.get("data_sha256", "")
    result = _download_and_verify(data_url, expected_sha)

    if result is None:
        _print_warning("DB auto-update: download failed, using local database")
        state["last_check_at"] = _now_iso()
        _save_state(state)
        return _best_local()

    _print_success(f"DB auto-update: database updated successfully ({new_count} sites)")
    state["last_check_at"] = _now_iso()
    state["last_meta"] = meta
    state["cached_db_sha256"] = expected_sha
    _save_state(state)
    return CACHED_DB_PATH


def force_update(
    meta_url: str = DEFAULT_META_URL,
    color: bool = True,
) -> bool:
    """
    Force check for database updates and download if available.

    Returns True if database was updated, False otherwise.
    """
    global _use_color
    _use_color = color

    _ensure_maigret_home()

    _print_info("DB update: checking for updates...")
    meta = _fetch_meta(meta_url)
    if meta is None:
        _print_warning("DB update: could not reach update server")
        return False

    if not _is_version_compatible(meta):
        min_ver = meta.get("min_maigret_version", "?")
        _print_warning(
            f"DB update: latest database requires maigret >= {min_ver}, "
            f"you have {__version__}. Please upgrade with: pip install -U maigret"
        )
        return False

    state = _load_state()
    new_count = meta.get("sites_count", "?")
    old_count = state.get("last_meta", {}).get("sites_count")

    if not _is_update_available(meta, state):
        _print_info(f"DB update: database is already up to date ({new_count} sites)")
        state["last_check_at"] = _now_iso()
        state["last_meta"] = meta
        _save_state(state)
        return False

    if old_count:
        _print_info(f"DB update: downloading updated database ({new_count} sites, was {old_count})...")
    else:
        _print_info(f"DB update: downloading database ({new_count} sites)...")

    data_url = meta.get("data_url", "")
    expected_sha = meta.get("data_sha256", "")
    result = _download_and_verify(data_url, expected_sha)

    if result is None:
        _print_warning("DB update: download failed")
        return False

    _print_success(f"DB update: database updated successfully ({new_count} sites)")
    state["last_check_at"] = _now_iso()
    state["last_meta"] = meta
    state["cached_db_sha256"] = expected_sha
    _save_state(state)
    return True
