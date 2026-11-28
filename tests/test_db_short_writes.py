"""A verified download must be written completely before replacing a cached DB."""

import errno
import hashlib
import json
import os
from unittest.mock import Mock

import pytest

from maigret import db_updater


@pytest.mark.parametrize('chunks', [1, 7, 31])
def test_database_download_retries_short_writes(chunks, tmp_path, monkeypatch):
    cache = tmp_path / 'data.json'
    original = b'{"sites": {}, "engines": {}, "tags": []}'
    cache.write_bytes(original)
    content = json.dumps(
        {
            'sites': {'Fixture': {'url': 'https://example.test/{username}'}},
            'engines': {},
            'tags': [],
        }
    ).encode()
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(cache))
    monkeypatch.setattr(
        db_updater.requests,
        'get',
        Mock(return_value=Mock(status_code=200, content=content)),
    )
    real_write = os.write
    writes = []

    def short_write(fd, data):
        written = real_write(fd, data[:chunks])
        writes.append(written)
        return written

    monkeypatch.setattr(db_updater.os, 'write', short_write)
    result = db_updater._download_and_verify(
        'https://example.test/data.json', hashlib.sha256(content).hexdigest()
    )
    assert result == str(cache)
    assert cache.read_bytes() == content
    assert sum(writes) == len(content)
    assert len(writes) > 1
    assert list(tmp_path.iterdir()) == [cache]


@pytest.mark.parametrize('failure', ['zero', 'disk-full'])
def test_database_download_preserves_cache_if_write_cannot_finish(
    failure, tmp_path, monkeypatch
):
    cache = tmp_path / 'data.json'
    original = b'{"sites": {}, "engines": {}, "tags": []}'
    cache.write_bytes(original)
    content = json.dumps({'sites': {'Fixture': {}}, 'engines': {}, 'tags': []}).encode()
    monkeypatch.setattr(db_updater, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(db_updater, 'CACHED_DB_PATH', str(cache))
    monkeypatch.setattr(
        db_updater.requests,
        'get',
        Mock(return_value=Mock(status_code=200, content=content)),
    )
    real_write = os.write
    calls = 0

    def failing_write(fd, data):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_write(fd, data[:7])
        if failure == 'zero':
            return 0
        raise OSError(errno.ENOSPC, 'Synthetic full disk')

    monkeypatch.setattr(db_updater.os, 'write', failing_write)
    assert (
        db_updater._download_and_verify(
            'https://example.test/data.json', hashlib.sha256(content).hexdigest()
        )
        is None
    )
    assert cache.read_bytes() == original
    assert calls == 2
    assert list(tmp_path.iterdir()) == [cache]
