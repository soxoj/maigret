"""Maigret command-line arguments parsing tests"""

from argparse import Namespace
from typing import Dict, Any

DEFAULT_ARGS: Dict[str, Any] = {
    'all_sites': False,
    'auto_disable': False,
    'connections': 100,
    'cookie_file': None,
    'csv': False,
    'db_file': 'resources/data.json',
    'debug': False,
    'diagnose': False,
    'disable_extracting': False,
    'disable_recursive_search': False,
    'folderoutput': 'reports',
    'html': False,
    'graph': False,
    'id_type': 'username',
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
    'ai_model': 'gpt-4o',
    'no_autoupdate': False,
    'force_update': False,
    'cloudflare_bypass': False,
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
