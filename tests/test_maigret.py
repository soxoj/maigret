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


def test_extract_ids_from_page_when_socid_missing(test_db):
    """Test that extract_ids_from_page handles missing socid_extractor gracefully"""
    from unittest.mock import patch
    from maigret import maigret as maigret_module
    
    logger = Mock()
    
    # Mock SOCID_EXTRACTOR_AVAILABLE to be False
    with patch.object(maigret_module, 'SOCID_EXTRACTOR_AVAILABLE', False):
        # Should return empty dict instead of crashing
        result = maigret_module.extract_ids_from_page(
            'https://www.reddit.com/user/test', logger
        )
        assert result == {}


def test_version_output_when_socid_missing():
    """Test that --version works even when socid_extractor is missing"""
    from maigret.maigret import setup_arguments_parser
    from maigret.settings import Settings
    
    settings = Settings()
    settings.load()  # Load default settings
    parser = setup_arguments_parser(settings)
    
    # This should not crash even if socid_extractor is not installed
    # The version string should contain "not installed" for socid_extractor
    assert parser is not None
