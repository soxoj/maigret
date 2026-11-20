"""Valid JSON with the wrong cache root shape must not abort startup."""

import importlib
import json
import logging
from unittest.mock import Mock, patch

import pytest

from maigret import activation
from maigret.sites import MaigretDatabase, MaigretSite


@pytest.mark.parametrize(
    'cache', [None, [], ['unexpected'], '', 'unexpected', 0, 1, False, True]
)
def test_activation_cache_ignores_non_object_root(cache, tmp_path, monkeypatch):
    target = tmp_path / 'activation.json'
    target.write_text(json.dumps(cache), encoding='utf-8')
    monkeypatch.setattr(activation, 'ACTIVATION_CACHE_PATH', str(target))
    db = MaigretDatabase()
    site = MaigretSite(
        'Fixture',
        {'activation': {'method': 'twitter'}, 'headers': {'accept': 'text/html'}},
    )
    db.update_site(site)
    logger = Mock()
    before = dict(site.headers)
    baseline = activation.load_activation_cache(db, logger)
    assert baseline == {'Fixture': before}
    assert site.headers == before
    assert json.loads(target.read_text(encoding='utf-8')) == cache
    logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_cli_self_check_continues_after_non_object_cache(tmp_path, monkeypatch):
    cli = importlib.import_module('maigret.maigret')
    cache = tmp_path / 'activation.json'
    cache.write_text('null', encoding='utf-8')
    monkeypatch.setattr(activation, 'ACTIVATION_CACHE_PATH', str(cache))
    db = tmp_path / 'database.json'
    db.write_text(
        json.dumps(
            {
                'sites': {
                    'Fixture': {
                        'url': 'https://example.test/{username}',
                        'activation': {'method': 'twitter'},
                    }
                },
                'engines': {},
                'tags': [],
            }
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        'sys.argv',
        [
            'maigret',
            '--db',
            str(db),
            '--self-check',
            '--no-autoupdate',
            '--no-progressbar',
            '--no-color',
        ],
    )
    with patch(
        'maigret.maigret.self_check', return_value={'needs_update': False}
    ) as check:
        with pytest.raises(SystemExit) as exc:
            await cli.main()
    assert exc.value.code == 0
    check.assert_awaited_once()


@pytest.mark.parametrize(
    'cache,expected',
    [
        ({}, {'accept': 'text/html'}),
        ({'Other': {'x-fixture': 'cached'}}, {'accept': 'text/html'}),
        ({'Fixture': None}, {'accept': 'text/html'}),
        ({'Fixture': []}, {'accept': 'text/html'}),
        (
            {'Fixture': {'x-fixture': 'cached'}},
            {'accept': 'text/html', 'x-fixture': 'cached'},
        ),
    ],
)
def test_activation_cache_object_semantics_unchanged(
    cache, expected, tmp_path, monkeypatch
):
    target = tmp_path / 'activation.json'
    target.write_text(json.dumps(cache), encoding='utf-8')
    monkeypatch.setattr(activation, 'ACTIVATION_CACHE_PATH', str(target))
    db = MaigretDatabase()
    site = MaigretSite(
        'Fixture',
        {'activation': {'method': 'twitter'}, 'headers': {'accept': 'text/html'}},
    )
    db.update_site(site)
    plain = MaigretSite('Plain', {'headers': {'accept': 'text/plain'}})
    db.update_site(plain)
    baseline = activation.load_activation_cache(db, Mock())
    assert baseline == {'Fixture': {'accept': 'text/html'}}
    assert site.headers == expected
    assert plain.headers == {'accept': 'text/plain'}


def test_non_object_cache_without_activation_sites(tmp_path, monkeypatch):
    target = tmp_path / 'activation.json'
    target.write_text('null', encoding='utf-8')
    monkeypatch.setattr(activation, 'ACTIVATION_CACHE_PATH', str(target))
    assert activation.load_activation_cache(MaigretDatabase(), Mock()) == {}
