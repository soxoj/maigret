import copy
import logging
from unittest.mock import Mock

import pytest

from maigret.checking import make_site_result
from maigret.sites import MaigretDatabase, MaigretEngine, MaigretSite


@pytest.mark.parametrize(
    'field, attribute',
    [
        ('headers', 'headers'),
        ('errors', 'errors'),
        ('requestPayload', 'request_payload'),
        ('getParams', 'get_params'),
    ],
)
def test_engine_dict_reaches_site_when_field_is_omitted(field, attribute):
    engine = MaigretEngine('ExampleEngine', {'site': {field: {'key': 'value'}}})
    site = MaigretSite('Example', {'url': 'https://example.test/{username}'})

    site.update_from_engine(engine)

    assert getattr(site, attribute) == {'key': 'value'}
    assert getattr(site, attribute) is not engine.site[field]
    assert field not in site.strip_engine_data().json


@pytest.mark.parametrize('field', ['headers', 'errors', 'requestPayload', 'getParams'])
def test_inherited_engine_dict_is_not_shared_with_other_sites(field):
    engine = MaigretEngine('ExampleEngine', {'site': {field: {'key': 'value'}}})
    first = MaigretSite('First', {'url': 'https://first.test/{username}'})
    second = MaigretSite('Second', {'url': 'https://second.test/{username}'})
    first.update_from_engine(engine)
    second.update_from_engine(engine)
    attribute = {'requestPayload': 'request_payload', 'getParams': 'get_params'}.get(
        field, field
    )

    getattr(first, attribute)['local'] = 'first-only'

    assert getattr(second, attribute) == {'key': 'value'}
    assert engine.site[field] == {'key': 'value'}


def test_engine_headers_and_payload_reach_checker_without_network():
    engine = MaigretEngine(
        'ExampleEngine',
        {
            'site': {
                'url': '{urlMain}/{username}',
                'requestMethod': 'POST',
                'headers': {'X-Engine': 'required'},
                'requestPayload': {'username': '{username}'},
            }
        },
    )
    site = MaigretSite('Example', {'urlMain': 'https://example.test'})
    site.update_from_engine(engine)
    checker = Mock()
    options = {
        'id_type': 'username',
        'parsing': False,
        'timeout': 1,
        'forced': False,
        'checkers': {'': lambda: checker},
    }

    make_site_result(site, 'alice', options, logging.getLogger(__name__))

    checker.prepare.assert_called_once()
    prepared = checker.prepare.call_args.kwargs
    assert prepared['headers']['X-Engine'] == 'required'
    assert prepared['payload'] == {'username': 'alice'}
    assert prepared['method'] == 'post'
    assert engine.site['requestPayload'] == {'username': '{username}'}


def test_inherited_engine_dict_round_trip_preserves_site_entries(tmp_path):
    data = {
        'engines': {
            'ExampleEngine': {
                'site': {
                    'url': '{urlMain}/{username}',
                    'headers': {'X-Engine': 'required'},
                }
            }
        },
        'sites': {
            'Example': {'engine': 'ExampleEngine', 'urlMain': 'https://example.test'}
        },
        'tags': [],
    }
    db = MaigretDatabase().load_from_json(copy.deepcopy(data))
    site = db.sites[0]
    site.headers['X-Local'] = 'retained'
    output = tmp_path / 'database.json'

    db.save_to_file(str(output))
    reloaded = MaigretDatabase().load_from_file(str(output))

    assert reloaded.sites[0].headers == {'X-Engine': 'required', 'X-Local': 'retained'}
    assert db.sites[0].headers == reloaded.sites[0].headers
    assert db.engines[0].site['headers'] == {'X-Engine': 'required'}
