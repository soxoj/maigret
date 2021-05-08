"""Maigret Database test functions"""
from maigret.sites import MaigretDatabase, MaigretSite

EXAMPLE_DB = {
    'engines': {
        "XenForo": {
            "presenseStrs": ["XenForo"],
            "site": {
                "absenceStrs": [
                    "The specified member cannot be found. Please enter a member's entire name.",
                ],
                "checkType": "message",
                "errors": {"You must be logged-in to do that.": "Login required"},
                "url": "{urlMain}{urlSubpath}/members/?username={username}",
            },
        },
    },
    'sites': {
        "Amperka": {
            "engine": "XenForo",
            "rank": 121613,
            "tags": ["ru"],
            "urlMain": "http://forum.amperka.ru",
            "usernameClaimed": "adam",
            "usernameUnclaimed": "noonewouldeverusethis7",
        },
    },
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


def test_site_strip_engine_data_with_site_prior_updates():
    db = MaigretDatabase()
    UPDATED_EXAMPLE_DB = dict(EXAMPLE_DB)
    UPDATED_EXAMPLE_DB['sites']['Amperka']['absenceStrs'] = ["test"]
    db.load_from_json(UPDATED_EXAMPLE_DB)

    amperka = db.sites[0]
    amperka_stripped = amperka.strip_engine_data()

    assert amperka_stripped.json == UPDATED_EXAMPLE_DB['sites']['Amperka']


def test_saving_site_error():
    db = MaigretDatabase()

    DB = dict(EXAMPLE_DB)
    DB['sites']['Amperka']['errors'] = {'error1': 'text1'}

    db.load_from_json(DB)

    amperka = db.sites[0]
    assert len(amperka.errors) == 2
    assert len(amperka.errors_dict) == 2

    assert amperka.strip_engine_data().errors == {'error1': 'text1'}
    assert amperka.strip_engine_data().json['errors'] == {'error1': 'text1'}


def test_site_url_detector():
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    assert (
        db.sites[0].url_regexp.pattern
        == r'^https?://(www.)?forum\.amperka\.ru/members/\?username=(.+?)$'
    )
    assert (
        db.sites[0].detect_username('http://forum.amperka.ru/members/?username=test')
        == 'test'
    )


def test_ranked_sites_dict():
    db = MaigretDatabase()
    db.update_site(MaigretSite('3', {'alexaRank': 1000, 'engine': 'ucoz'}))
    db.update_site(MaigretSite('1', {'alexaRank': 2, 'tags': ['forum']}))
    db.update_site(MaigretSite('2', {'alexaRank': 10, 'tags': ['ru', 'forum']}))

    # sorting
    assert list(db.ranked_sites_dict().keys()) == ['1', '2', '3']
    assert list(db.ranked_sites_dict(top=2).keys()) == ['1', '2']
    assert list(db.ranked_sites_dict(reverse=True, top=2).keys()) == ['3', '2']

    # filtering by tags
    assert list(db.ranked_sites_dict(tags=['ru'], top=2).keys()) == ['2']
    assert list(db.ranked_sites_dict(tags=['forum']).keys()) == ['1', '2']

    # filtering by engine
    assert list(db.ranked_sites_dict(tags=['ucoz']).keys()) == ['3']

    # disjunction
    assert list(db.ranked_sites_dict(names=['2'], tags=['forum']).keys()) == ['2']
    assert list(db.ranked_sites_dict(names=['2'], tags=['ucoz']).keys()) == []
    assert list(db.ranked_sites_dict(names=['4'], tags=['ru']).keys()) == []

    # reverse
    assert list(db.ranked_sites_dict(reverse=True).keys()) == ['3', '2', '1']


def test_ranked_sites_dict_names():
    db = MaigretDatabase()
    db.update_site(MaigretSite('3', {'alexaRank': 30}))
    db.update_site(MaigretSite('1', {'alexaRank': 2}))
    db.update_site(MaigretSite('2', {'alexaRank': 10}))

    # filtering by names
    assert list(db.ranked_sites_dict(names=['1', '2']).keys()) == ['1', '2']
    assert list(db.ranked_sites_dict(names=['2', '3']).keys()) == ['2', '3']


def test_ranked_sites_dict_disabled():
    db = MaigretDatabase()
    db.update_site(MaigretSite('1', {'disabled': True}))
    db.update_site(MaigretSite('2', {}))

    assert len(db.ranked_sites_dict()) == 2
    assert len(db.ranked_sites_dict(disabled=False)) == 1


def test_ranked_sites_dict_id_type():
    db = MaigretDatabase()
    db.update_site(MaigretSite('1', {}))
    db.update_site(MaigretSite('2', {'type': 'username'}))
    db.update_site(MaigretSite('3', {'type': 'gaia_id'}))

    assert len(db.ranked_sites_dict()) == 2
    assert len(db.ranked_sites_dict(id_type='username')) == 2
    assert len(db.ranked_sites_dict(id_type='gaia_id')) == 1
