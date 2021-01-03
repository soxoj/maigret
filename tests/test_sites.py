"""Maigret Database test functions"""
from maigret.sites import MaigretDatabase


def test_load_empty_db_from_str():
    db = MaigretDatabase()
    db.load_from_str('{"engines": {}, "sites": {}}')

    assert db.sites == []
    assert db.engines == []


def test_load_valid_db():
    db = MaigretDatabase()
    db.load_from_json({
        'engines': {
            "XenForo": {
              "presenseStrs": ["XenForo"],
              "site": {
                "errorMsg": [
                  "The specified member cannot be found. Please enter a member's entire name.",
                ],
                "errorType": "message",
                "errors": {
                  "You must be logged-in to do that.": "Login required"
                },
                "url": "{urlMain}{urlSubpath}/members/?username={username}"
              }
            },
        },
        'sites': {
            "Amperka": {
              "engine": "XenForo",
              "rank": 121613,
              "tags": [
                "ru"
              ],
              "urlMain": "http://forum.amperka.ru",
              "username_claimed": "adam",
              "username_unclaimed": "noonewouldeverusethis7"
            },
        }
    })

    assert len(db.sites) == 1
    assert len(db.engines) == 1

    assert db.sites[0].name == 'Amperka'
    assert db.engines[0].name == 'XenForo'
