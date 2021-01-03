"""Maigret Database test functions"""
from maigret.sites import MaigretDatabase


EXAMPLE_DB = {
    'engines': {
        "XenForo": {
          "presenseStrs": ["XenForo"],
          "site": {
            "absenceStrs": [
              "The specified member cannot be found. Please enter a member's entire name.",
            ],
            "checkType": "message",
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
          "usernameClaimed": "adam",
          "usernameUnclaimed": "noonewouldeverusethis7"
        },
    }
}


def test_load_empty_db_from_str():
    db = MaigretDatabase()
    db.load_from_str('{"engines": {}, "sites": {}}')

    assert db.sites == []
    assert db.engines == []


def test_load_valid_db():
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    assert len(db.sites) == 1
    assert len(db.engines) == 1

    assert db.sites[0].name == 'Amperka'
    assert db.engines[0].name == 'XenForo'


def test_site_json_dump():
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    init_keys = EXAMPLE_DB['sites']['Amperka'].keys()
    # contains engine data
    obj_keys = db.sites[0].json.keys()

    assert set(init_keys).issubset(set(obj_keys))


def test_site_correct_initialization():
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    xenforo = db.engines[0]
    assert xenforo.name == 'XenForo'
    assert xenforo.site['checkType'] == 'message'

    amperka = db.sites[0]
    assert amperka.name == 'Amperka'
    assert amperka.check_type == 'message'


def test_site_strip_engine_data():
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    amperka = db.sites[0]
    amperka_stripped = amperka.strip_engine_data()

    assert amperka_stripped.json == EXAMPLE_DB['sites']['Amperka']


def test_saving_site_error():
    db = MaigretDatabase()

    DB = dict(EXAMPLE_DB)
    DB['sites']['Amperka']['errors'] = {'error1': 'text1'}

    db.load_from_json(DB)

    amperka = db.sites[0]
    assert len(amperka.errors) == 2

    assert amperka.strip_engine_data().errors == {'error1': 'text1'}
    assert amperka.strip_engine_data().json['errors'] == {'error1': 'text1'}
