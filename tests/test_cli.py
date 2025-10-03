"""Maigret command-line arguments parsing tests"""

from typing import Dict, Any

DEFAULT_ARGS: Dict[str, Any] = {
    "all_sites": False,
    "connections": 100,
    "cookie_file": None,
    "csv": False,
    "db_file": "resources/data.json",
    "debug": False,
    "disable_extracting": False,
    "disable_recursive_search": False,
    "folderoutput": "reports",
    "html": False,
    "graph": False,
    "id_type": "username",
    "ignore_ids_list": [],
    "info": False,
    "json": "",
    "new_site_to_submit": False,
    "no_color": False,
    "no_progressbar": False,
    "parse_url": "",
    "pdf": False,
    "permute": False,
    "print_check_errors": False,
    "print_not_found": False,
    "proxy": None,
    "reports_sorting": "default",
    "retries": 0,
    "self_check": False,
    "site_list": [],
    "stats": False,
    "tags": "",
    "timeout": 30,
    "tor_proxy": "socks5://127.0.0.1:9050",
    "i2p_proxy": "http://127.0.0.1:4444",
    "top_sites": 500,
    "txt": False,
    "use_disabled_sites": False,
    "username": [],
    "verbose": False,
    "web": None,
    "with_domains": False,
    "xmind": False,
}


def test_args_search_mode(argparser):
    args = argparser.parse_args("username".split())

    assert args.username == ["username"]

    want_args = dict(DEFAULT_ARGS)
    want_args.update({"username": ["username"]})

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_search_mode_several_usernames(argparser):
    args = argparser.parse_args("username1 username2".split())

    assert args.username == ["username1", "username2"]

    want_args = dict(DEFAULT_ARGS)
    want_args.update({"username": ["username1", "username2"]})

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_self_check_mode(argparser):
    args = argparser.parse_args("--self-check --site GitHub".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "self_check": True,
            "site_list": ["GitHub"],
            "username": [],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_multiple_sites(argparser):
    args = argparser.parse_args(
        "--site GitHub VK --site PornHub --site Taringa,Steam".split()
    )

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "site_list": ["GitHub", "PornHub", "Taringa,Steam"],
            "username": ["VK"],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_web_mode_default_port(argparser):
    """Test --web flag with no port argument uses default port 5000"""
    args = argparser.parse_args("--web".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "web": 5000,  # Default port when --web is used without value
            "username": [],
        }
    )

    for arg in vars(args):
        actual = getattr(args, arg)
        expected = want_args[arg]
        assert actual == expected, f"Mismatch for {arg}: {actual} != {expected}"


def test_args_web_mode_custom_port(argparser):
    """Test --web flag with custom port argument"""
    args = argparser.parse_args("--web 8080".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "web": 8080,
            "username": [],
        }
    )

    for arg in vars(args):
        actual = getattr(args, arg)
        expected = want_args[arg]
        assert actual == expected, f"Mismatch for {arg}: {actual} != {expected}"


def test_args_web_mode_alternative_port(argparser):
    """Test --web flag with alternative port"""
    args = argparser.parse_args("--web 3000".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "web": 3000,
            "username": [],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_no_web_mode(argparser):
    """Test that web is None by default when --web is not specified"""
    args = argparser.parse_args("testuser".split())

    assert args.web is None, f"Expected web to be None, got {args.web}"

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "username": ["testuser"],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_web_with_other_options(argparser):
    """Test --web flag combined with other options"""
    args = argparser.parse_args("--web 9000 --verbose".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "web": 9000,
            "verbose": True,
            "username": [],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]


def test_args_web_mode_with_db_file(argparser):
    """Test --web flag with custom database file"""
    args = argparser.parse_args("--web --db custom.json".split())

    want_args = dict(DEFAULT_ARGS)
    want_args.update(
        {
            "web": 5000,
            "db_file": "custom.json",
            "username": [],
        }
    )

    for arg in vars(args):
        assert getattr(args, arg) == want_args[arg]
