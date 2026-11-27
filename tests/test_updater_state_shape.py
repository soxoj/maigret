"""Corrupt disposable updater state must not prevent using a local database."""

import json
from unittest.mock import Mock

import pytest

from maigret import db_updater


@pytest.mark.parametrize('state', [None, [], ['last_check_at'], 'state', 7, True])
def test_non_object_state_uses_local_database(state, tmp_path, monkeypatch):
    state_file = tmp_path / 'autoupdate_state.json'
    state_file.write_text(json.dumps(state), encoding='utf-8')
    cache = tmp_path / 'data.json'
    cache.write_text('{"sites": {}, "engines": {}, "tags": []}', encoding='utf-8')
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'STATE_PATH', str(state_file))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(cache))
    monkeypatch.setattr(db_updater, '_fetch_meta', Mock(return_value=None))

    assert db_updater.resolve_db_path('resources/data.json', color=False) == str(cache)
    assert json.loads(state_file.read_text()) == {
        'last_check_at': db_updater._load_state()['last_check_at']
    }
    assert cache.read_text() == '{"sites": {}, "engines": {}, "tags": []}'


def test_invalid_utf8_state_uses_local_database(tmp_path, monkeypatch):
    state_file = tmp_path / 'autoupdate_state.json'
    state_file.write_bytes(b'{"last_check_at": "\xff"}')
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'STATE_PATH', str(state_file))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(tmp_path / 'missing.json'))
    monkeypatch.setattr(db_updater, '_fetch_meta', Mock(return_value=None))

    assert (
        db_updater.resolve_db_path('resources/data.json', color=False)
        == db_updater.BUNDLED_DB_PATH
    )
    assert isinstance(db_updater._load_state(), dict)


@pytest.mark.parametrize('state', [None, [], ['last_check_at'], 'state', 7, True])
def test_force_update_rebuilds_non_object_state(state, tmp_path, monkeypatch):
    state_file = tmp_path / 'autoupdate_state.json'
    state_file.write_text(json.dumps(state), encoding='utf-8')
    cache = tmp_path / 'data.json'
    cache.write_text('{"sites": {}, "engines": {}, "tags": []}', encoding='utf-8')
    meta = {'updated_at': '2099-01-01T00:00:00Z', 'sites_count': 1}
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'STATE_PATH', str(state_file))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(cache))
    monkeypatch.setattr(db_updater, '_fetch_meta', Mock(return_value=meta))
    download = Mock(return_value=str(cache))
    monkeypatch.setattr(db_updater, '_download_and_verify', download)

    assert db_updater.force_update(color=False) is True
    download.assert_called_once()
    assert db_updater._load_state()['last_meta'] == meta
    assert cache.read_text() == '{"sites": {}, "engines": {}, "tags": []}'


@pytest.mark.parametrize('content', [b'null', b'{"last_check_at": "\xff"}'])
@pytest.mark.asyncio
async def test_actual_cli_startup_with_corrupt_state(
    content, tmp_path, monkeypatch, capsys
):
    from maigret import maigret as cli

    state_file = tmp_path / 'autoupdate_state.json'
    state_file.write_bytes(content)
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'STATE_PATH', str(state_file))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(tmp_path / 'missing.json'))
    monkeypatch.setattr(db_updater, '_fetch_meta', Mock(return_value=None))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('sys.argv', ['maigret', '--stats', '--no-color'])

    with pytest.raises(SystemExit) as exc:
        await cli.main()
    assert exc.value.code == 0
    assert 'Using sites database:' in capsys.readouterr().out
    assert isinstance(db_updater._load_state()['last_check_at'], str)
