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
from maigret.result import QueryResult, QueryStatus


RESULTS_EXAMPLE = {
    'Reddit': {
        'cookies': None,
        'parsing_enabled': False,
        'url_main': 'https://www.reddit.com/',
        'username': 'Facebook',
    },
    'GooglePlayStore': {
        'cookies': None,
        'http_status': 200,
        'is_similar': False,
        'parsing_enabled': False,
        'rank': 1,
        'url_main': 'https://play.google.com/store',
        'url_user': 'https://play.google.com/store/apps/developer?id=Facebook',
        'username': 'Facebook',
    },
}


@pytest.mark.slow
def test_self_check_db_positive_disable(test_db):
    logger = Mock()
    assert test_db.sites[0].disabled is False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        self_check(test_db, test_db.sites_dict, logger, silent=True)
    )

    assert test_db.sites[0].disabled is True


@pytest.mark.slow
def test_self_check_db_positive_enable(test_db):
    logger = Mock()

    test_db.sites[0].disabled = True
    test_db.sites[0].username_claimed = 'Facebook'
    assert test_db.sites[0].disabled is True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        self_check(test_db, test_db.sites_dict, logger, silent=True)
    )

    assert test_db.sites[0].disabled is False


@pytest.mark.slow
def test_self_check_db_negative_disabled(test_db):
    logger = Mock()

    test_db.sites[0].disabled = True
    assert test_db.sites[0].disabled is True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        self_check(test_db, test_db.sites_dict, logger, silent=True)
    )

    assert test_db.sites[0].disabled is True


@pytest.mark.slow
def test_self_check_db_negative_enabled(test_db):
    logger = Mock()

    test_db.sites[0].disabled = False
    test_db.sites[0].username_claimed = 'Facebook'
    assert test_db.sites[0].disabled is False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        self_check(test_db, test_db.sites_dict, logger, silent=True)
    )

    assert test_db.sites[0].disabled is False


@pytest.mark.slow
def test_maigret_results(test_db):
    logger = Mock()

    username = 'Facebook'
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
    assert isinstance(reddit_status, QueryResult)
    assert reddit_status.status == QueryStatus.ILLEGAL

    playstore_status = results['GooglePlayStore']['status']
    assert isinstance(playstore_status, QueryResult)
    assert playstore_status.status == QueryStatus.CLAIMED

    del results['Reddit']['status']
    del results['GooglePlayStore']['status']

    assert results['Reddit'].get('future') is None
    del results['GooglePlayStore']['future']
    del results['GooglePlayStore']['checker']

    assert results == RESULTS_EXAMPLE


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
