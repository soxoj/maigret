"""Settings JSON must be an object before its values are applied."""

import json

import pytest

from maigret.settings import Settings


@pytest.mark.parametrize(
    'value', [None, [], ['timeout'], 'timeout', 7, 1.5, True, False]
)
def test_nonobject_settings_return_existing_error_contract(tmp_path, value):
    filename = tmp_path / 'settings.json'
    filename.write_text(json.dumps(value), encoding='utf-8')
    settings = Settings()

    loaded, error = settings.load([str(filename)])

    assert loaded is False
    assert isinstance(error, ValueError)
    assert str(filename) in str(error)
    assert 'object' in str(error)
    assert settings.json == {}


def test_pair_array_cannot_silently_override_settings(tmp_path):
    filename = tmp_path / 'settings.json'
    filename.write_text('[["timeout", 0], ["max_connections", 0]]', encoding='utf-8')
    settings = Settings()
    settings.timeout = 30
    settings.max_connections = 10

    loaded, error = settings.load([str(filename)])

    assert loaded is False
    assert isinstance(error, ValueError)
    assert settings.json == {'timeout': 30, 'max_connections': 10}


@pytest.mark.parametrize('value', [{}, {'timeout': 10}, {'arbitrary': ['a', 'b']}])
def test_object_settings_keep_existing_behavior(tmp_path, value):
    filename = tmp_path / 'settings.json'
    filename.write_text(json.dumps(value), encoding='utf-8')
    settings = Settings()

    loaded, _ = settings.load([str(filename)])

    assert loaded is bool(value)
    assert settings.json == value
