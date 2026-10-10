"""Maigret command-line arguments parsing tests"""

import copy
import logging
import sys
from argparse import Namespace
from typing import Dict, Any
from unittest import mock

import pytest

from maigret import maigret as maigret_module
from maigret.maigret import setup_arguments_parser
from maigret.settings import SETTINGS_FILES_PATHS, Settings

DEFAULT_ARGS: Dict[str, Any] = {
    'all_sites': False,
    'auto_disable': False,
    'connections': 100,
    'cookie_file': None,
    'csv': False,
    'db_file': 'resources/data.json',
    'debug': False,
    'dns_resolver': 'async',
    'diagnose': False,
    'disable_extracting': False,
    'disable_recursive_search': False,
    'enrich': False,
    'folderoutput': 'reports',
    'html': False,
    'graph': False,
    'neo4j': False,
    'id_type': 'username',
    'input_file': None,
    'ignore_ids_list': [],
    'info': False,
    'json': '',
    'new_site_to_submit': False,
    'no_color': False,
    'no_progressbar': False,
    'parse_url': '',
    'pdf': False,
    'permute': False,
    'print_check_errors': False,
    'print_not_found': False,
    'proxy': None,
    'reports_sorting': 'default',
    'retries': 0,
    'self_check': False,
    'site_list': [],
    'stats': False,
    'tags': '',
    'exclude_tags': '',
    'timeout': 30,
    'tor_proxy': 'socks5://127.0.0.1:9050',
    'i2p_proxy': 'http://127.0.0.1:4444',
    'top_sites': 500,
    'txt': False,
    'use_disabled_sites': False,
    'username': [],
    'verbose': False,
    'web': None,
    'with_domains': False,
    'xmind': False,
    'md': False,
    'ai': False,
    'ai_model': 'gpt-5.4',
    'no_autoupdate': False,
    'force_update': False,
    'cloudflare_bypass': False,
    'keywords': [],
    'dns_resolver': 'async',
}


def test_args_search_mode(argparser):
    args = argparser.parse_args('username'.split())

    assert args.username == ['username']

    want_args = dict(DEFAULT_ARGS)
    want_args.update({'username': ['username']})

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_search_mode_several_usernames(argparser):
    args = argparser.parse_args('username1 username2'.split())

    assert args.username == ['username1', 'username2']

    want_args = dict(DEFAULT_ARGS)
    want_args.update({'username': ['username1', 'username2']})

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_input_file(argparser):
    args = argparser.parse_args('--input-file ids.txt'.split())

    assert args.username == []
    assert args.input_file == 'ids.txt'

    want_args = dict(DEFAULT_ARGS)
    want_args.update({'input_file': 'ids.txt'})

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_self_check_mode(argparser):
    args = argparser.parse_args('--self-check --site GitHub'.split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            'self_check': True,
            'site_list': ['GitHub'],
            'username': [],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_multiple_sites(argparser):
    args = argparser.parse_args(
        '--site GitHub VK --site PornHub --site Taringa,Steam'.split()
    )

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            'site_list': ['GitHub', 'PornHub', 'Taringa,Steam'],
            'username': ['VK'],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_exclude_tags(argparser):
    args = argparser.parse_args('--exclude-tags porn,dating username'.split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            'exclude_tags': 'porn,dating',
            'username': ['username'],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_tags_with_exclude_tags(argparser):
    args = argparser.parse_args('--tags coding --exclude-tags porn username'.split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            'tags': 'coding',
            'exclude_tags': 'porn',
            'username': ['username'],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_web_port(argparser):
    assert argparser.parse_args(['--web', '6000']).web == 6000


def test_args_web_without_port_uses_settings(settings):
    custom = copy.copy(settings)
    custom.web_interface_port = 8080

    assert setup_arguments_parser(custom).parse_args(['--web']).web == 8080


@pytest.fixture
def restore_maigret_log_level():
    # main() sets the 'maigret' logger level; later caplog-based tests depend on it.
    logger = logging.getLogger('maigret')
    level = logger.level
    yield
    logger.setLevel(level)


@pytest.mark.parametrize('cli_args', [['--web'], ['--web', '0']])
async def test_web_mode_runs_on_settings_port(cli_args, restore_maigret_log_level):
    real_load = Settings.load

    def load_with_custom_port(self, paths=None):
        # Only the bundled settings, so a developer's ~/.maigret/settings.json cannot interfere.
        result = real_load(self, SETTINGS_FILES_PATHS[:1])
        self.web_interface_port = 8080
        return result

    with mock.patch.object(Settings, 'load', load_with_custom_port), mock.patch.object(
        sys, 'argv', ['maigret', '--no-autoupdate', *cli_args]
    ), mock.patch('maigret.web.app.app.run') as run:
        await maigret_module.main()

    assert run.call_args.kwargs['port'] == 8080
