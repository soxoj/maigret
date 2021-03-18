"""Maigret main module test functions"""
import asyncio

import pytest
from mock import Mock

from maigret.maigret import self_check
from maigret.sites import MaigretDatabase

EXAMPLE_DB = {
    'engines': {
    },
    'sites': {
        "GooglePlayStore": {
            "tags": [
                "global",
                "us"
            ],
            "disabled": False,
            "checkType": "status_code",
            "alexaRank": 1,
            "url": "https://play.google.com/store/apps/developer?id={username}",
            "urlMain": "https://play.google.com/store",
            "usernameClaimed": "Facebook_nosuchname",
            "usernameUnclaimed": "noonewouldeverusethis7"
        },
        "Reddit": {
            "tags": [
                "news",
                "social",
                "us"
            ],
            "checkType": "status_code",
            "presenseStrs": [
                "totalKarma"
            ],
            "disabled": True,
            "alexaRank": 17,
            "url": "https://www.reddit.com/user/{username}",
            "urlMain": "https://www.reddit.com/",
            "usernameClaimed": "blue",
            "usernameUnclaimed": "noonewouldeverusethis7"
        },
    }
}


@pytest.mark.slow
def test_self_check_db_positive_disable():
    logger = Mock()
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    assert db.sites[0].disabled == False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(self_check(db, db.sites_dict, logger, silent=True))

    assert db.sites[0].disabled == True


@pytest.mark.slow
def test_self_check_db_positive_enable():
    logger = Mock()
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    db.sites[0].disabled = True
    db.sites[0].username_claimed = 'Facebook'
    assert db.sites[0].disabled == True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(self_check(db, db.sites_dict, logger, silent=True))

    assert db.sites[0].disabled == False


@pytest.mark.slow
def test_self_check_db_negative_disabled():
    logger = Mock()
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    db.sites[0].disabled = True
    assert db.sites[0].disabled == True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(self_check(db, db.sites_dict, logger, silent=True))

    assert db.sites[0].disabled == True


@pytest.mark.slow
def test_self_check_db_negative_enabled():
    logger = Mock()
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    db.sites[0].disabled = False
    db.sites[0].username_claimed = 'Facebook'
    assert db.sites[0].disabled == False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(self_check(db, db.sites_dict, logger, silent=True))

    assert db.sites[0].disabled == False
