"""Maigret Database test functions"""

import json
from typing import Any, Dict

from maigret.sites import MaigretDatabase, MaigretSite

EXAMPLE_DB: Dict[str, Any] = {
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


def _write_db(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding='utf-8')
    return str(p)


def test_extra_db_new_site(tmp_path):
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)
    assert len(db.sites) == 1

    extra = {
        'engines': {},
        'sites': {
            'ExampleExtra': {
                'tags': ['us'],
                'checkType': 'status_code',
                'url': 'https://example.com/{username}',
                'urlMain': 'https://example.com/',
                'usernameClaimed': 'test',
                'usernameUnclaimed': 'noonewouldeverusethis7',
            }
        },
        'tags': ['us'],
    }
    db.load_extra_from_path(_write_db(tmp_path, 'extra.json', extra))

    assert len(db.sites) == 2
    assert set(db.sites_dict.keys()) == {'Amperka', 'ExampleExtra'}
    assert len(db._sites) == len(db.sites_dict)


def test_extra_db_site_override_last_wins(tmp_path):
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)
    assert db.sites_dict['Amperka'].url_main == 'http://forum.amperka.ru'

    extra = {
        'engines': {},
        'sites': {
            'Amperka': {
                'engine': 'XenForo',
                'rank': 1,
                'tags': ['overridden'],
                'urlMain': 'https://overridden.example',
                'usernameClaimed': 'adam',
                'usernameUnclaimed': 'noonewouldeverusethis7',
            }
        },
        'tags': [],
    }
    db.load_extra_from_path(_write_db(tmp_path, 'extra.json', extra))

    assert len(db.sites) == 1
    amperka = db.sites_dict['Amperka']
    assert amperka.url_main == 'https://overridden.example'
    assert 'overridden' in amperka.tags


def test_extra_db_engine_override(tmp_path):
    main = {
        'engines': {
            'Proto': {
                'presenseStrs': ['orig'],
                'site': {
                    'absenceStrs': ['original absence'],
                    'checkType': 'message',
                    'url': '{urlMain}/orig/{username}',
                },
            }
        },
        'sites': {
            'MainSite': {
                'engine': 'Proto',
                'rank': 1,
                'tags': [],
                'urlMain': 'https://main.example',
                'usernameClaimed': 'a',
                'usernameUnclaimed': 'noonewouldeverusethis7',
            }
        },
        'tags': [],
    }
    db = MaigretDatabase()
    db.load_from_json(main)

    extra = {
        'engines': {
            'Proto': {
                'presenseStrs': ['overridden'],
                'site': {
                    'absenceStrs': ['overridden absence'],
                    'checkType': 'message',
                    'url': '{urlMain}/overridden/{username}',
                },
            }
        },
        'sites': {
            'ExtraSite': {
                'engine': 'Proto',
                'rank': 10,
                'tags': [],
                'urlMain': 'https://extra.example',
                'usernameClaimed': 'a',
                'usernameUnclaimed': 'noonewouldeverusethis7',
            }
        },
        'tags': [],
    }
    db.load_extra_from_path(_write_db(tmp_path, 'extra.json', extra))

    assert len(db._engines) == 1
    assert db.engines_dict['Proto'].presenseStrs == ['overridden']
    extra_site = db.sites_dict['ExtraSite']
    assert extra_site.absence_strs == ['overridden absence']
    main_site = db.sites_dict['MainSite']
    assert main_site.absence_strs == ['original absence']


def test_extra_db_tag_dedup(tmp_path):
    db = MaigretDatabase()
    db.load_from_json({'engines': {}, 'sites': {}, 'tags': ['forum', 'ru']})

    extra = {'engines': {}, 'sites': {}, 'tags': ['forum', 'us']}
    db.load_extra_from_path(_write_db(tmp_path, 'extra.json', extra))

    assert db._tags.count('forum') == 1
    assert sorted(db._tags) == ['forum', 'ru', 'us']


def test_extra_db_chain_last_wins(tmp_path):
    db = MaigretDatabase()
    db.load_from_json(EXAMPLE_DB)

    def site_with_url(url):
        return {
            'engines': {},
            'sites': {
                'Amperka': {
                    'engine': 'XenForo',
                    'rank': 1,
                    'tags': ['ru'],
                    'urlMain': url,
                    'usernameClaimed': 'adam',
                    'usernameUnclaimed': 'noonewouldeverusethis7',
                }
            },
            'tags': [],
        }

    db.load_extra_from_path(_write_db(tmp_path, 'a.json', site_with_url('https://a')))
    db.load_extra_from_path(_write_db(tmp_path, 'b.json', site_with_url('https://b')))

    assert len(db.sites) == 1
    assert db.sites_dict['Amperka'].url_main == 'https://b'


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
        == r'^https?://(www.|m.)?forum\.amperka\.ru/members/\?username=(.+?)$'
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


def test_ranked_sites_dict_excluded_tags():
    db = MaigretDatabase()
    db.update_site(MaigretSite('3', {'alexaRank': 1000, 'engine': 'ucoz'}))
    db.update_site(MaigretSite('1', {'alexaRank': 2, 'tags': ['forum']}))
    db.update_site(MaigretSite('2', {'alexaRank': 10, 'tags': ['ru', 'forum']}))

    # excluding by tag
    assert list(db.ranked_sites_dict(excluded_tags=['ru']).keys()) == ['1', '3']
    assert list(db.ranked_sites_dict(excluded_tags=['forum']).keys()) == ['3']

    # excluding by engine
    assert list(db.ranked_sites_dict(excluded_tags=['ucoz']).keys()) == ['1', '2']

    # combining include and exclude tags
    assert list(db.ranked_sites_dict(tags=['forum'], excluded_tags=['ru']).keys()) == ['1']

    # excluding non-existent tag has no effect
    assert list(db.ranked_sites_dict(excluded_tags=['nonexistent']).keys()) == ['1', '2', '3']

    # exclude all
    assert list(db.ranked_sites_dict(excluded_tags=['forum', 'ucoz']).keys()) == []


def test_ranked_sites_dict_excluded_tags_with_top():
    """Excluded tags should also prevent mirrors from being included."""
    db = MaigretDatabase()
    db.update_site(
        MaigretSite('Parent', {'alexaRank': 1, 'tags': ['forum'], 'type': 'username'})
    )
    db.update_site(
        MaigretSite('Mirror', {'alexaRank': 999999, 'source': 'Parent', 'tags': ['forum'], 'type': 'username'})
    )
    db.update_site(
        MaigretSite('Other', {'alexaRank': 2, 'tags': ['coding'], 'type': 'username'})
    )

    # Without exclusion, mirror should be included
    result = db.ranked_sites_dict(top=1, id_type='username')
    assert 'Parent' in result
    assert 'Mirror' in result

    # With exclusion of 'forum', both Parent and Mirror should be excluded
    result = db.ranked_sites_dict(top=2, excluded_tags=['forum'], id_type='username')
    assert 'Parent' not in result
    assert 'Mirror' not in result
    assert 'Other' in result


def test_ranked_sites_dict_mirrors_disabled_parent():
    """Mirror is included when parent ranks in top N but parent is disabled."""
    db = MaigretDatabase()
    db.update_site(
        MaigretSite(
            'ParentPlatform',
            {'alexaRank': 5, 'disabled': True, 'type': 'username'},
        )
    )
    db.update_site(
        MaigretSite(
            'OtherSite',
            {'alexaRank': 100, 'type': 'username'},
        )
    )
    db.update_site(
        MaigretSite(
            'MirrorSite',
            {
                'alexaRank': 99999999,
                'source': 'ParentPlatform',
                'type': 'username',
            },
        )
    )

    result = db.ranked_sites_dict(top=1, disabled=False, id_type='username')
    assert list(result.keys()) == ['OtherSite', 'MirrorSite']


def test_ranked_sites_dict_mirrors_no_extra_without_parent_in_top():
    db = MaigretDatabase()
    db.update_site(MaigretSite('A', {'alexaRank': 1, 'type': 'username'}))
    db.update_site(
        MaigretSite(
            'B',
            {'alexaRank': 2, 'source': 'NotInDb', 'type': 'username'},
        )
    )

    assert list(db.ranked_sites_dict(top=1, id_type='username').keys()) == ['A']


def test_get_url_template():
    site = MaigretSite(
        "test",
        {
            "urlMain": "https://ya.ru/",
            "url": "{urlMain}{urlSubpath}/members/?username={username}",
        },
    )
    assert (
        site.get_url_template()
        == "{urlMain}{urlSubpath}/members/?username={username} (no engine)"
    )

    site = MaigretSite(
        "test",
        {
            "urlMain": "https://ya.ru/",
            "url": "https://{username}.ya.ru",
        },
    )
    assert site.get_url_template() == "SUBDOMAIN"


def test_has_site_url_or_name(default_db):
    # by the same url or partial match
    assert default_db.has_site("https://aback.com.ua/user/") == True
    assert default_db.has_site("https://aback.com.ua") == True

    # acceptable partial match
    assert default_db.has_site("https://aback.com.ua/use") == True
    assert default_db.has_site("https://aback.com") == True

    # by name
    assert default_db.has_site("Aback") == True

    # false
    assert default_db.has_site("https://aeifgoai3h4g8a3u4g5") == False
    assert default_db.has_site("aeifgoai3h4g8a3u4g5") == False
