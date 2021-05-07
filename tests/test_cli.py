"""Maigret command-line arguments parsing tests"""
from argparse import Namespace
from typing import Dict, Any

DEFAULT_ARGS: Dict[str, Any] = {
    'all_sites': False,
    'connections': 100,
    'cookie_file': None,
    'csv': False,
    'db_file': None,
    'debug': False,
    'disable_extracting': False,
    'disable_recursive_search': False,
    'folderoutput': 'reports',
    'html': False,
    'id_type': 'username',
    'ignore_ids_list': [],
    'info': False,
    'json': '',
    'new_site_to_submit': False,
    'no_color': False,
    'no_progressbar': False,
    'parse_url': '',
    'pdf': False,
    'print_check_errors': False,
    'print_not_found': False,
    'proxy': None,
    'retries': 1,
    'self_check': False,
    'site_list': [],
    'stats': False,
    'tags': '',
    'timeout': 30,
    'top_sites': 500,
    'txt': False,
    'use_disabled_sites': False,
    'username': [],
    'verbose': False,
    'xmind': False,
}


def test_args_search_mode(argparser):
    args = argparser.parse_args('username'.split())

    assert args.username == ['username']

    want_args = dict(DEFAULT_ARGS)
    want_args.update({'username': ['username']})

    assert args == Namespace(**want_args)


def test_args_search_mode_several_usernames(argparser):
    args = argparser.parse_args('username1 username2'.split())

    assert args.username == ['username1', 'username2']

    want_args = dict(DEFAULT_ARGS)
    want_args.update({'username': ['username1', 'username2']})

    assert args == Namespace(**want_args)


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

    assert args == Namespace(**want_args)


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

    assert args == Namespace(**want_args)
