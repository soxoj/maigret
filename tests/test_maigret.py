"""Maigret main module test functions"""

import asyncio
import copy
from unittest.mock import Mock, patch

import pytest

from maigret.maigret import self_check, maigret
from maigret.maigret import (
    extract_ids_from_page,
    extract_ids_from_results,
)
from maigret.checking import site_self_check
from maigret.sites import MaigretSite, MaigretDatabase
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from tests.conftest import RESULTS_EXAMPLE


@pytest.mark.slow
@pytest.mark.asyncio
async def test_self_check_db(test_db):
    # initalize logger to debug
    logger = Mock()

    assert test_db.sites_dict['InvalidActive'].disabled is False
    assert test_db.sites_dict['ValidInactive'].disabled is True
    assert test_db.sites_dict['ValidActive'].disabled is False
    assert test_db.sites_dict['InvalidInactive'].disabled is True

    await self_check(
        test_db, test_db.sites_dict, logger, silent=False, auto_disable=True
    )

    assert test_db.sites_dict['InvalidActive'].disabled is True
    assert test_db.sites_dict['ValidInactive'].disabled is False
    assert test_db.sites_dict['ValidActive'].disabled is False
    assert test_db.sites_dict['InvalidInactive'].disabled is True


@pytest.mark.slow
@pytest.mark.asyncio
async def test_self_check_no_progressbar(test_db):
    """Verify that no_progressbar=True disables the alive_bar in self_check."""
    logger = Mock()

    with patch('maigret.checking.alive_bar') as mock_alive_bar:
        mock_bar = Mock()
        mock_alive_bar.return_value.__enter__ = Mock(return_value=mock_bar)
        mock_alive_bar.return_value.__exit__ = Mock(return_value=False)

        await self_check(
            test_db, test_db.sites_dict, logger, silent=True,
            no_progressbar=True,
        )

        # First call is the self-check progress bar; subsequent calls are
        # from inner search() invocations.
        self_check_call = mock_alive_bar.call_args_list[0]
        _, kwargs = self_check_call
        assert kwargs.get('title') == 'Self-checking'
        assert kwargs.get('disable') is True


@pytest.mark.slow
@pytest.mark.asyncio
async def test_self_check_progressbar_enabled_by_default(test_db):
    """Verify that alive_bar is enabled by default (no_progressbar=False)."""
    logger = Mock()

    with patch('maigret.checking.alive_bar') as mock_alive_bar:
        mock_bar = Mock()
        mock_alive_bar.return_value.__enter__ = Mock(return_value=mock_bar)
        mock_alive_bar.return_value.__exit__ = Mock(return_value=False)

        await self_check(
            test_db, test_db.sites_dict, logger, silent=True,
        )

        self_check_call = mock_alive_bar.call_args_list[0]
        _, kwargs = self_check_call
        assert kwargs.get('title') == 'Self-checking'
        assert kwargs.get('disable') is False


@pytest.mark.asyncio
async def test_site_self_check_handles_exception(test_db):
    """Verify that site_self_check catches unexpected exceptions and returns a valid result."""
    logger = Mock()
    sem = asyncio.Semaphore(1)
    site = test_db.sites_dict['ValidActive']

    with patch('maigret.checking.maigret', side_effect=RuntimeError("test crash")):
        result = await site_self_check(site, logger, sem, test_db)

    assert isinstance(result, dict)
    assert "issues" in result
    assert len(result["issues"]) > 0
    assert any("Unexpected error" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_self_check_handles_task_exception(test_db):
    """Verify that self_check continues when individual site checks raise exceptions."""
    logger = Mock()

    with patch('maigret.checking.maigret', side_effect=RuntimeError("test crash")):
        result = await self_check(
            test_db, test_db.sites_dict, logger, silent=True,
            no_progressbar=True,
        )

    assert isinstance(result, dict)
    assert 'results' in result
    assert len(result['results']) == len(test_db.sites_dict)
    for r in result['results']:
        assert 'site_name' in r
        assert 'issues' in r


@pytest.mark.slow
@pytest.mark.skip(reason="broken, fixme")
def test_maigret_results(test_db):
    logger = Mock()

    username = 'Skyeng'
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        maigret(username, site_dict=test_db.sites_dict, logger=logger, timeout=30)
    )

    assert isinstance(results, dict)

    reddit_site = results['Reddit']['site']
    assert isinstance(reddit_site, MaigretSite)

    assert reddit_site.json == {
        'tags': ['news', 'social', 'us'],
        'checkType': 'status_code',
        'presenseStrs': ['totalKarma'],
        'disabled': True,
        'alexaRank': 17,
        'url': 'https://www.reddit.com/user/{username}',
        'urlMain': 'https://www.reddit.com/',
        'usernameClaimed': 'blue',
        'usernameUnclaimed': 'noonewouldeverusethis7',
    }

    del results['Reddit']['site']
    del results['GooglePlayStore']['site']

    reddit_status = results['Reddit']['status']
    assert isinstance(reddit_status, MaigretCheckResult)
    assert reddit_status.status == MaigretCheckStatus.ILLEGAL

    playstore_status = results['GooglePlayStore']['status']
    assert isinstance(playstore_status, MaigretCheckResult)
    assert playstore_status.status == MaigretCheckStatus.CLAIMED

    del results['Reddit']['status']
    del results['GooglePlayStore']['status']

    assert results['Reddit'].get('future') is None
    del results['GooglePlayStore']['future']
    del results['GooglePlayStore']['checker']

    assert results == RESULTS_EXAMPLE


@pytest.mark.slow
def test_extract_ids_from_url(default_db):
    assert default_db.extract_ids_from_url('https://www.reddit.com/user/test') == {
        'test': 'username'
    }
    assert default_db.extract_ids_from_url('https://vk.com/id123') == {'123': 'vk_id'}
    assert default_db.extract_ids_from_url('https://vk.com/ida123') == {
        'ida123': 'username'
    }
    assert default_db.extract_ids_from_url(
        'https://my.mail.ru/yandex.ru/dipres8904/'
    ) == {'dipres8904': 'username'}
    assert default_db.extract_ids_from_url(
        'https://reviews.yandex.ru/user/adbced123'
    ) == {'adbced123': 'yandex_public_id'}


@pytest.mark.slow
def test_extract_ids_from_page(test_db):
    logger = Mock()
    extract_ids_from_page('https://www.reddit.com/user/test', logger) == {
        'test': 'username'
    }


def test_extract_ids_from_results_aggregates_usernames_and_links(default_db):
    """Covers the recursive ID-extraction path flagged at maigret.py:946
    (`# TODO: tests`, `if recursive_search_enabled: extract_ids_from_results(...)`).

    The previous incarnation of this test was a bare expression
    (`extract_ids_from_results(...) == {...}`) with no `assert`, so it silently
    passed regardless of the return value. It also pinned the result against
    `test_db` (tests/db.json), whose site set never matched the Reddit URL and
    thus returned `{'test1': ...}` — silently dropping `test2`. Restored here as
    a real assertion against `default_db`, which carries the Reddit URL pattern.
    """
    TEST_EXAMPLE: dict = copy.deepcopy(RESULTS_EXAMPLE)
    TEST_EXAMPLE['Reddit']['ids_usernames'] = {'test1': 'yandex_public_id'}
    TEST_EXAMPLE['Reddit']['ids_links'] = ['https://www.reddit.com/user/test2']

    assert extract_ids_from_results(TEST_EXAMPLE, default_db) == {
        'test1': 'yandex_public_id',
        'test2': 'username',
    }


def test_extract_ids_from_results_merges_ids_usernames_across_sites(default_db):
    """ids_usernames from every site must be merged into the result dict,
    keyed by username with the per-site id type as the value."""
    example = {
        'SiteA': {'ids_usernames': {'alice': 'username', 'bob': 'telegram'}},
        'SiteB': {'ids_usernames': {'carol': 'username'}},
    }
    assert extract_ids_from_results(example, default_db) == {
        'alice': 'username',
        'bob': 'telegram',
        'carol': 'username',
    }


def test_extract_ids_from_results_skips_empty_site_entry(default_db):
    """A site whose result dict is empty (`{}`) must be skipped via
    `if not dictionary: continue` rather than raising on the subsequent
    `.get('ids_usernames')` / `.get('ids_links')` calls."""
    example = {
        'EmptySite': {},
        'SiteA': {'ids_usernames': {'alice': 'username'}},
    }
    assert extract_ids_from_results(example, default_db) == {'alice': 'username'}


def test_extract_ids_from_results_empty_input_returns_empty(default_db):
    """No sites searched → no extracted ids. Guards against accidental
    KeyError / iteration over None."""
    assert extract_ids_from_results({}, default_db) == {}


# -----------------------------------------------------------------------------
# Ctrl+C handling (https://github.com/soxoj/maigret/issues from
# "two presses needed to exit + traceback"). The contract:
#
#   1. First Ctrl+C during a running search → cancel that search but proceed
#      to report generation with whatever was collected.
#   2. Any KeyboardInterrupt that escapes to __main__.py (e.g. second Ctrl+C
#      during the report write, or interrupt before the search loop runs)
#      must exit with the conventional SIGINT code (130) and a one-line
#      message — never a Python traceback.
# -----------------------------------------------------------------------------


def test_main_entrypoint_handles_top_level_keyboard_interrupt_cleanly():
    """Verify the __main__.py wrapper around asyncio.run catches
    KeyboardInterrupt and exits with code 130 + a clean message. We can't
    SIGINT the test process itself without disrupting pytest's signal
    handlers, so we drive __main__.py in a subprocess with asyncio.run
    monkey-patched to raise KeyboardInterrupt directly."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    script = (
        "import asyncio, sys, runpy\n"
        # Simulate the second-Ctrl+C-during-asyncio.run path:
        "def _raise(*a, **kw):\n"
        "    raise KeyboardInterrupt()\n"
        "asyncio.run = _raise\n"
        # run_module executes maigret/__main__.py with __name__ == '__main__'
        "runpy.run_module('maigret', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    # 130 is the conventional SIGINT exit code (128 + SIGINT=2)
    assert result.returncode == 130, (
        f"expected exit 130, got {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # The user-facing message replaces the traceback
    assert "Maigret interrupted" in result.stderr
    # No Python traceback may leak through
    assert "Traceback" not in result.stderr
    assert "KeyboardInterrupt" not in result.stderr
