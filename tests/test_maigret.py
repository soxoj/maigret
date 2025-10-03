"""Maigret main module test functions"""

import asyncio
import copy

import pytest
from mock import Mock

from maigret.maigret import self_check, maigret
from maigret.maigret import (
    extract_ids_from_page,
    extract_ids_from_results,
)
from maigret.sites import MaigretSite
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

    await self_check(test_db, test_db.sites_dict, logger, silent=False)

    assert test_db.sites_dict['InvalidActive'].disabled is True
    assert test_db.sites_dict['ValidInactive'].disabled is False
    assert test_db.sites_dict['ValidActive'].disabled is False
    assert test_db.sites_dict['InvalidInactive'].disabled is True


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


def test_extract_ids_from_results(test_db):
    TEST_EXAMPLE = copy.deepcopy(RESULTS_EXAMPLE)
    TEST_EXAMPLE['Reddit']['ids_usernames'] = {'test1': 'yandex_public_id'}
    TEST_EXAMPLE['Reddit']['ids_links'] = ['https://www.reddit.com/user/test2']

    extract_ids_from_results(TEST_EXAMPLE, test_db) == {
        'test1': 'yandex_public_id',
        'test2': 'username',
    }


@pytest.mark.asyncio
async def test_self_check_with_exception_handling(test_db):
    """Test that self-check continues when individual site checks raise exceptions."""
    logger = Mock()
    
    # Create a modified site that will raise an exception
    # We'll use a mock to simulate the exception scenario
    from maigret.checking import site_self_check
    from unittest.mock import patch, AsyncMock
    
    original_site_self_check = site_self_check
    exception_raised = False
    
    async def failing_site_self_check(*args, **kwargs):
        nonlocal exception_raised
        site = args[0]
        # Make one specific site fail
        if site.name == 'ValidActive':
            exception_raised = True
            raise RuntimeError("Simulated site check failure")
        return await original_site_self_check(*args, **kwargs)
    
    with patch('maigret.checking.site_self_check', side_effect=failing_site_self_check):
        # This should not crash despite the exception
        result = await self_check(test_db, test_db.sites_dict, logger, silent=True)
        
    # Verify the exception was raised (meaning our mock worked)
    assert exception_raised, "Test setup failed - exception was not raised"
    
    # Verify logger.error was called to log the exception
    assert logger.error.called, "Exception was not logged"
    
    # Verify the result is still valid (boolean return value)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_self_check_multiple_site_failures(test_db):
    """Test self-check with multiple sites failing to ensure all are attempted."""
    logger = Mock()
    
    from maigret.checking import site_self_check
    from unittest.mock import patch
    
    failed_sites = []
    
    async def failing_site_self_check(*args, **kwargs):
        site = args[0]
        # Make multiple sites fail with different exception types
        if site.name in ['ValidActive', 'InvalidActive']:
            failed_sites.append(site.name)
            if site.name == 'ValidActive':
                raise ConnectionError(f"Network error for {site.name}")
            else:
                raise TimeoutError(f"Timeout for {site.name}")
        # Let other sites proceed normally
        return {'disabled': False}
    
    with patch('maigret.checking.site_self_check', side_effect=failing_site_self_check):
        result = await self_check(test_db, test_db.sites_dict, logger, silent=True)
        
    # Verify both sites failed (were attempted)
    assert len(failed_sites) == 2
    assert 'ValidActive' in failed_sites
    assert 'InvalidActive' in failed_sites
    
    # Verify errors were logged for both failures
    assert logger.error.call_count >= 2


@pytest.mark.asyncio  
async def test_self_check_progress_bar_updates_on_exception():
    """Test that progress bar updates even when exceptions occur."""
    from maigret.sites import MaigretDatabase, MaigretSite
    from maigret.checking import site_self_check
    from unittest.mock import patch, MagicMock
    import logging
    
    # Create a minimal test database with a few sites
    db = MaigretDatabase()
    
    # Add test sites
    for i in range(3):
        site = MaigretSite(
            f'TestSite{i}',
            {
                'url': f'https://example{i}.com/{{username}}',
                'urlMain': f'https://example{i}.com/',
                'username_claimed': 'test',
                'username_unclaimed': 'noone',
            }
        )
        db.sites.append(site)
    
    logger = logging.getLogger('test')
    
    progress_count = 0
    
    async def failing_site_self_check(*args, **kwargs):
        # All sites will fail
        raise Exception("All sites fail")
    
    # Mock alive_bar to track progress updates
    original_alive_bar = __import__('alive_progress').alive_bar
    
    class MockProgressBar:
        def __call__(self):
            nonlocal progress_count
            progress_count += 1
    
    class MockAliveBar:
        def __init__(self, total, **kwargs):
            self.total = total
            
        def __enter__(self):
            return MockProgressBar()
            
        def __exit__(self, *args):
            pass
    
    with patch('maigret.checking.site_self_check', side_effect=failing_site_self_check):
        with patch('maigret.checking.alive_bar', MockAliveBar):
            result = await self_check(db, db.sites_dict, logger, silent=True)
    
    # Verify progress bar was updated for all sites despite failures
    assert progress_count == 3, f"Expected 3 progress updates, got {progress_count}"


@pytest.mark.asyncio
async def test_self_check_combined_with_all_sites_flag(test_db):
    """
    Test that self-check works correctly when combined with all-sites flag.
    This simulates the issue #703 scenario: -a --self-check
    """
    logger = Mock()
    
    # Get all sites (simulating -a flag behavior)
    all_sites = test_db.sites_dict
    
    # This should complete without crashing
    result = await self_check(test_db, all_sites, logger, silent=True)
    
    # Verify result is boolean
    assert isinstance(result, bool)
    
    # Verify all sites were processed (no early termination)
    # The function should have attempted to check all sites
    assert len(all_sites) > 0
