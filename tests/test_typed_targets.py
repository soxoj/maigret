"""Offline CLI coverage for identifier values shared by different ID types."""

import importlib
import json
import logging
import signal
import sys
from unittest.mock import AsyncMock, Mock

import pytest

from maigret.settings import SETTINGS_FILES_PATHS, Settings

module = importlib.import_module('maigret.maigret')


@pytest.fixture
def cli(tmp_path, monkeypatch):
    db = tmp_path / 'data.json'
    db.write_text(
        json.dumps(
            {
                'sites': {
                    'Names': {
                        'url': 'http://127.0.0.1/users/{username}',
                        'urlMain': 'http://127.0.0.1',
                        'checkType': 'status_code',
                    },
                    'IDs': {
                        'url': 'http://127.0.0.1/id{username}',
                        'urlMain': 'http://127.0.0.1',
                        'checkType': 'status_code',
                        'type': 'vk_id',
                    },
                },
                'engines': {},
                'tags': [],
            }
        )
    )
    real_load = Settings.load
    monkeypatch.setattr(
        Settings, 'load', lambda self: real_load(self, SETTINGS_FILES_PATHS[:1])
    )
    monkeypatch.setattr(module, 'load_activation_cache', Mock(return_value={}))
    monkeypatch.setattr(module, 'save_activation_cache', Mock())
    monkeypatch.setattr(module, 'get_plaintext_report', Mock(return_value=''))
    reports = Mock(return_value={'username': '12345'})
    monkeypatch.setattr(module, 'generate_report_context', reports)
    search = AsyncMock(return_value={})
    monkeypatch.setattr(module, 'maigret', search)
    handler = signal.getsignal(signal.SIGINT)
    logger = logging.getLogger('maigret')
    level = logger.level

    async def run(args, entries=None):
        if entries is not None:
            names = tmp_path / 'ids.txt'
            names.write_text(entries)
            args = ['--input-file', str(names), *args]
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'maigret',
                '--no-autoupdate',
                '--no-color',
                '--no-progressbar',
                '--db',
                str(db),
                '-fo',
                str(tmp_path),
                *args,
            ],
        )
        await module.main()
        return [
            (c.kwargs['username'], c.kwargs['id_type'], list(c.kwargs['site_dict']))
            for c in search.call_args_list
        ]

    yield run, search, reports
    signal.signal(signal.SIGINT, handler)
    logger.setLevel(level)


async def test_batch_keeps_same_value_for_distinct_types(cli):
    run, _, reports = cli
    calls = await run([], 'username:12345\nvk_id:12345\nusername:12345\n')
    assert calls == [('12345', 'username', ['Names']), ('12345', 'vk_id', ['IDs'])]
    assert [(u, t) for u, t, _ in reports.call_args.args[0]] == [
        ('12345', 'username'),
        ('12345', 'vk_id'),
    ]


async def test_recursive_typed_value_is_not_an_already_checked_username(cli):
    run, search, _ = cli
    search.side_effect = [
        {'Synthetic': {'ids_usernames': {'12345': 'vk_id'}}},
        {'Synthetic': {'ids_usernames': {'12345': 'username'}}},
    ]
    assert await run(['12345']) == [
        ('12345', 'username', ['Names']),
        ('12345', 'vk_id', ['IDs']),
    ]


async def test_recursive_target_does_not_replace_pending_other_type(cli):
    run, search, _ = cli
    search.side_effect = [{'Synthetic': {'ids_usernames': {'12345': 'vk_id'}}}, {}, {}]
    assert await run(['alice', '12345']) == [
        ('alice', 'username', ['Names']),
        ('12345', 'username', ['Names']),
        ('12345', 'vk_id', ['IDs']),
    ]


async def test_same_type_case_insensitive_dedup_and_ordinary_filenames(
    cli, monkeypatch
):
    run, _, _ = cli
    saved = Mock()
    monkeypatch.setattr(module, 'save_csv_report', saved)
    assert await run(['Alice', 'alice', 'bob', '--csv']) == [
        ('Alice', 'username', ['Names']),
        ('bob', 'username', ['Names']),
    ]
    assert [c.args[0].rsplit('/', 1)[1] for c in saved.call_args_list] == [
        'report_Alice.csv',
        'report_bob.csv',
    ]


async def test_no_recursion_is_preserved(cli):
    run, search, _ = cli
    search.return_value = {'Synthetic': {'ids_usernames': {'12345': 'vk_id'}}}
    assert await run(['12345', '--no-recursion']) == [('12345', 'username', ['Names'])]


async def test_recursion_keeps_equal_values_extracted_from_different_sites(cli):
    run, search, _ = cli
    search.side_effect = [
        {
            'First': {'ids_usernames': {'12345': 'username'}},
            'Second': {'ids_usernames': {'12345': 'vk_id'}},
        },
        {},
        {},
    ]
    assert await run(['alice']) == [
        ('alice', 'username', ['Names']),
        ('12345', 'username', ['Names']),
        ('12345', 'vk_id', ['IDs']),
    ]


async def test_typed_input_with_no_default_username_sites_is_not_rejected(cli):
    run, _, _ = cli
    assert await run(['--site', 'IDs'], 'vk_id:12345\n') == [
        ('12345', 'vk_id', ['IDs'])
    ]


async def test_no_matching_type_still_exits_before_search(cli):
    run, search, _ = cli
    with pytest.raises(SystemExit) as error:
        await run(['alice', '--site', 'IDs'])
    assert error.value.code == 2
    search.assert_not_awaited()


async def test_ignored_value_skips_every_type(cli):
    run, _, _ = cli
    assert await run(
        ['alice', '--ignore', '12345'], 'username:12345\nvk_id:12345\n'
    ) == [('alice', 'username', ['Names'])]


async def test_recursive_links_keep_both_types(cli):
    run, search, _ = cli
    search.side_effect = [
        {
            'Synthetic': {
                'ids_links': [
                    'http://127.0.0.1/users/12345',
                    'http://127.0.0.1/id12345',
                ]
            },
        },
        {},
        {},
    ]
    assert await run(['alice']) == [
        ('alice', 'username', ['Names']),
        ('12345', 'username', ['Names']),
        ('12345', 'vk_id', ['IDs']),
    ]


def test_public_extraction_mapping_keeps_legacy_last_value_wins():
    from maigret.sites import MaigretDatabase

    results = {
        'First': {'ids_usernames': {'12345': 'username'}},
        'Second': {'ids_usernames': {'12345': 'vk_id'}},
    }
    assert module.extract_ids_from_results(results, MaigretDatabase()) == {
        '12345': 'vk_id'
    }


@pytest.mark.parametrize(
    'flag,writer',
    [
        ('--csv', 'save_csv_report'),
        ('--txt', 'save_txt_report'),
        ('--json', 'save_json_report'),
        ('--xmind', 'save_xmind_report'),
    ],
)
async def test_slash_writer_labels_keep_legacy_sanitization_without_changing_targets(
    cli, monkeypatch, flag, writer
):
    run, _, reports = cli
    saved = Mock()
    monkeypatch.setattr(module, writer, saved)
    args = [flag, 'simple'] if flag == '--json' else [flag]
    calls = await run(args, 'username:group/alice\nvk_id:group/alice\n')
    assert [(u, t) for u, t, _ in calls] == [
        ('group/alice', 'username'),
        ('group/alice', 'vk_id'),
    ]
    assert [c.args[1] for c in saved.call_args_list] == ['group_alice', 'group_alice']
    assert [(u, t) for u, t, _ in reports.call_args.args[0]] == [
        ('group/alice', 'username'),
        ('group/alice', 'vk_id'),
    ]
