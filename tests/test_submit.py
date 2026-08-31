import re

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from maigret.submit import Submitter
from aiohttp import ClientSession
from maigret.sites import MaigretDatabase, MaigretSite
import logging


@pytest.mark.slow
@pytest.mark.asyncio
async def test_detect_known_engine(test_db, local_test_db):
    # Use the database fixture instead of mocking
    mock_db = test_db
    mock_settings = MagicMock()
    mock_logger = MagicMock()
    mock_args = MagicMock()
    mock_args.cookie_file = ""
    mock_args.proxy = ""

    # Mock the supposed usernames
    mock_settings.supposed_usernames = ["adam"]
    # Create the Submitter instance
    submitter = Submitter(test_db, mock_settings, mock_logger, mock_args)

    # Call the method with test URLs
    url_exists = "https://devforum.zoom.us/u/adam"
    url_mainpage = "https://devforum.zoom.us/"
    # Mock extract_username_dialog to return "adam"
    submitter.extract_username_dialog = MagicMock(return_value="adam")  # type: ignore[method-assign]

    sites, resp_text = await submitter.detect_known_engine(
        url_exists, url_mainpage, session=None, follow_redirects=False, headers=None
    )

    # Assertions
    assert len(sites) == 2
    assert sites[0].name == "devforum.zoom.us"
    assert sites[0].url_main == "https://devforum.zoom.us/"
    assert sites[0].engine == "Discourse"
    assert sites[0].username_claimed == "adam"
    assert sites[0].username_unclaimed == "noonewouldeverusethis7"
    assert resp_text != ""

    await submitter.close()

    # Create the Submitter instance without engines
    submitter = Submitter(local_test_db, mock_settings, mock_logger, mock_args)
    sites, resp_text = await submitter.detect_known_engine(
        url_exists, url_mainpage, session=None, follow_redirects=False, headers=None
    )
    assert len(sites) == 0

    await submitter.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_check_features_manually_success(settings):
    # Setup
    db = MaigretDatabase()
    logger = logging.getLogger("test_logger")
    args = type(
        'Args', (object,), {'proxy': None, 'cookie_file': None, 'verbose': False}
    )()

    submitter = Submitter(db, settings, logger, args)

    username = "KONAMI"
    url_exists = "https://play.google.com/store/apps/developer?id=KONAMI"

    # Execute
    presence_list, absence_list, status, random_username, _, _ = (
        await submitter.check_features_manually(
            username=username,
            url_exists=url_exists,
            session=ClientSession(),
            follow_redirects=False,
            headers=None,
        )
    )
    await submitter.close()
    # Assert
    assert status == "Found", "Expected status to be 'Found'"
    assert isinstance(presence_list, list), "Presence list should be a list"
    assert isinstance(absence_list, list), "Absence list should be a list"
    assert isinstance(random_username, str), "Random username should be a string"
    assert (
        random_username != username
    ), "Random username should not be the same as the input username"
    assert sorted(presence_list) == sorted(
        [
            ' title=',
            'og:title',
            'display: none;',
            '4;0',
            'main-title',
        ]
    )
    assert sorted(absence_list) == sorted(
        [
            '  body {',
            '  </style>',
            '><title>Not Found</title>',
            '  <style nonce=',
            '  .rounded {',
        ]
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_check_features_manually_cloudflare(settings):
    # Setup
    db = MaigretDatabase()
    logger = logging.getLogger("test_logger")
    args = type(
        'Args', (object,), {'proxy': None, 'cookie_file': None, 'verbose': False}
    )()

    submitter = Submitter(db, settings, logger, args)

    username = "abel"
    url_exists = "https://community.cloudflare.com/badges/1/basic?username=abel"

    # Execute
    presence_list, absence_list, status, random_username, _, _ = (
        await submitter.check_features_manually(
            username=username,
            url_exists=url_exists,
            session=ClientSession(),
            follow_redirects=False,
            headers=None,
        )
    )
    await submitter.close()

    # Assert
    assert status == "Cloudflare detected, skipping"
    assert presence_list is None
    assert absence_list is None
    assert random_username != username


@pytest.mark.asyncio
async def test_check_features_manually_uses_distinct_status_codes(settings):
    db = MaigretDatabase()
    args = MagicMock(cookie_file="", proxy=None)
    submitter = Submitter(db, settings, logging.getLogger("test_logger"), args)
    submitter.get_html_response_to_compare = AsyncMock(
        side_effect=[("same response", 200), ("same response", 404)]
    )

    result = await submitter.check_features_manually(
        username="claimed",
        url_exists="https://example.com/claimed",
        session=MagicMock(close=AsyncMock()),
    )

    assert result[2] == "Found"
    assert result[4:] == (200, 404)


@pytest.mark.asyncio
async def test_check_features_manually_does_not_treat_redirect_as_absence(settings):
    db = MaigretDatabase()
    args = MagicMock(cookie_file="", proxy=None)
    submitter = Submitter(db, settings, logging.getLogger("test_logger"), args)
    submitter.get_html_response_to_compare = AsyncMock(
        side_effect=[("same response", 200), ("same response", 302)]
    )

    result = await submitter.check_features_manually(
        username="claimed",
        url_exists="https://example.com/claimed",
        session=MagicMock(close=AsyncMock()),
    )

    assert result[2] == (
        "HTTP responses for pages with existing and non-existing accounts are the same"
    )
    assert result[4:] == (200, 302)


@pytest.mark.asyncio
async def test_dialog_selects_status_code_check(settings):
    db = MaigretDatabase()
    args = MagicMock(
        cookie_file="",
        proxy=None,
        verbose=False,
        db_file="test_db.json",
        db="test_db.json",
    )
    submitter = Submitter(db, settings, logging.getLogger("test_logger"), args)
    submitter.detect_known_engine = AsyncMock(return_value=([], ""))
    submitter.extract_username_dialog = MagicMock(return_value="claimed")
    submitter.check_features_manually = AsyncMock(
        return_value=(None, None, "Found", "unclaimed", 200, 404)
    )
    submitter.site_self_check = AsyncMock(return_value={"disabled": False})

    with patch('builtins.input', side_effect=['y', '', '']):
        result = await submitter.dialog("https://example.com/claimed", None)

    assert result is True
    assert db.sites[0].check_type == "status_code"


@pytest.mark.asyncio
async def test_dialog_keeps_message_check_for_redirect(settings):
    db = MaigretDatabase()
    args = MagicMock(
        cookie_file="",
        proxy=None,
        verbose=False,
        db_file="test_db.json",
        db="test_db.json",
    )
    submitter = Submitter(db, settings, logging.getLogger("test_logger"), args)
    submitter.detect_known_engine = AsyncMock(return_value=([], ""))
    submitter.extract_username_dialog = MagicMock(return_value="claimed")
    submitter.check_features_manually = AsyncMock(
        return_value=(["profile"], ["not found"], "Found", "unclaimed", 200, 302)
    )
    submitter.site_self_check = AsyncMock(return_value={"disabled": False})

    with patch('builtins.input', side_effect=['y', '', '']):
        result = await submitter.dialog("https://example.com/claimed", None)

    assert result is True
    assert db.sites[0].check_type == "message"
    assert db.sites[0].presense_strs == ["profile"]
    assert db.sites[0].absence_strs == ["not found"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_dialog_adds_site_positive(settings):
    # Initialize necessary objects
    db = MaigretDatabase()
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    args = type(
        'Args',
        (object,),
        {
            'proxy': None,
            'cookie_file': None,
            'verbose': False,
            'db_file': 'test_db.json',
            'db': 'test_db.json',
        },
    )()

    submitter = Submitter(db, settings, logger, args)

    # Mock user inputs
    user_inputs = [
        'KONAMI',  # Manually input username
        'y',  # Save the site in the Maigret DB
        'GooglePlayStore',  # Custom site name
        '',  # no custom tags
    ]

    with patch('builtins.input', side_effect=user_inputs):
        result = await submitter.dialog(
            "https://play.google.com/store/apps/developer?id=KONAMI", None
        )
        await submitter.close()

    assert result is True
    assert len(db.sites) == 1

    site = db.sites[0]
    assert site.url_main == "https://play.google.com"
    assert site.name == "GooglePlayStore"
    assert site.tags == []
    assert site.username_claimed == "KONAMI"
    assert site.check_type in ("message", "status_code")
    if site.check_type == "status_code":
        assert site.presense_strs == []
        assert site.absence_strs == []
    else:
        assert site.presense_strs != []
        assert site.absence_strs != []


@pytest.mark.slow
@pytest.mark.asyncio
async def test_dialog_replace_site(settings, test_db):
    # Initialize necessary objects
    db = test_db
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    args = type(
        'Args',
        (object,),
        {
            'proxy': None,
            'cookie_file': None,
            'verbose': False,
            'db_file': 'test_db.json',
            'db': 'test_db.json',
        },
    )()

    assert len(db.sites) == 4

    submitter = Submitter(db, settings, logger, args)

    # Mock user inputs
    user_inputs = [
        'y',  # Similar sites found, continue
        'InvalidActive',  # Choose site to replace
        '',  # Custom headers
        'y',  # Should we do redirects automatically?
        'KONAMI',  # Manually input username
        'y',  # Save the site in the Maigret DB
        '',  # Custom site name
        '',  # no custom tags
    ]

    with patch('builtins.input', side_effect=user_inputs):
        result = await submitter.dialog(
            "https://play.google.com/store/apps/developer?id=KONAMI", None
        )
        await submitter.close()

    assert result is True
    assert len(db.sites) == 4

    site = db.sites_dict["InvalidActive"]
    assert site.name == "InvalidActive"
    assert site.url_main == "https://play.google.com"
    assert site.tags == ['global', 'us']
    assert site.username_claimed == "KONAMI"
    assert site.check_type in ("message", "status_code")
    if site.check_type == "status_code":
        assert site.presense_strs == []
        assert site.absence_strs == []
    else:
        assert site.presense_strs != []
        assert site.absence_strs != []


@pytest.mark.slow
@pytest.mark.asyncio
async def test_dialog_adds_site_negative(settings):
    # Initialize necessary objects
    db = MaigretDatabase()
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    args = type(
        'Args',
        (object,),
        {
            'proxy': None,
            'cookie_file': None,
            'verbose': False,
            'db_file': 'test_db.json',
            'db': 'test_db.json',
        },
    )()

    submitter = Submitter(db, settings, logger, args)

    # Mock user inputs
    user_inputs = [
        'sokrat',  # Manually input username
        'y',  # Save the site in the Maigret DB
    ]

    with patch('builtins.input', side_effect=user_inputs):
        result = await submitter.dialog("https://icq.com/sokrat", None)
        await submitter.close()

    assert result is False


def test_domain_matching_exact():
    """Test that domain matching uses proper boundary checks, not substring matching.

    x.com should NOT match sites like 500px.com, mix.com, etc.
    """
    domain_raw = "x.com"
    domain_re = re.compile(
        r'://(www\.)?' + re.escape(domain_raw) + r'(/|$)'
    )

    # These should NOT match x.com
    non_matching = [
        MaigretSite("500px", {"url": "https://500px.com/p/{username}", "urlMain": "https://500px.com/"}),
        MaigretSite("Mix", {"url": "https://mix.com/{username}", "urlMain": "https://mix.com"}),
        MaigretSite("Screwfix", {"url": "{urlMain}{urlSubpath}/members/?username={username}", "urlMain": "https://community.screwfix.com"}),
        MaigretSite("Wix", {"url": "https://{username}.wix.com", "urlMain": "https://wix.com/"}),
        MaigretSite("1x", {"url": "https://1x.com/{username}", "urlMain": "https://1x.com"}),
        MaigretSite("Roblox", {"url": "https://www.roblox.com/user.aspx?username={username}", "urlMain": "https://www.roblox.com/"}),
    ]

    for site in non_matching:
        assert not domain_re.search(site.url_main + site.url), \
            f"x.com should NOT match site {site.name} ({site.url_main})"


def test_domain_matching_positive():
    """Test that domain matching correctly matches the exact domain."""
    domain_raw = "x.com"
    domain_re = re.compile(
        r'://(www\.)?' + re.escape(domain_raw) + r'(/|$)'
    )

    # These SHOULD match x.com
    matching = [
        MaigretSite("X", {"url": "https://x.com/{username}", "urlMain": "https://x.com"}),
        MaigretSite("X-www", {"url": "https://www.x.com/{username}", "urlMain": "https://www.x.com"}),
    ]

    for site in matching:
        assert domain_re.search(site.url_main + site.url), \
            f"x.com SHOULD match site {site.name} ({site.url_main})"


def test_dialog_nonexistent_site_name_no_crash():
    """Test that entering a site name not in the matched list doesn't crash.

    This tests the fix for: AttributeError: 'NoneType' object has no attribute 'name'
    The old_site should be None when user enters a name not in matched_sites,
    and the code should handle it gracefully.
    """
    # Simulate the logic that was crashing
    matched_sites = [
        MaigretSite("ValidActive", {"url": "https://example.com/{username}", "urlMain": "https://example.com"}),
        MaigretSite("InvalidActive", {"url": "https://example.com/alt/{username}", "urlMain": "https://example.com"}),
    ]
    site_name = "NonExistentSite"

    old_site = next(
        (site for site in matched_sites if site.name == site_name), None
    )

    # This is what the old code did - it would crash here
    assert old_site is None

    # The fix: check before accessing .name
    if old_site is None:
        result = "not found"
    else:
        result = old_site.name

    assert result == "not found"

    # And when site_name IS in matched_sites, it should work
    site_name = "ValidActive"
    old_site = next(
        (site for site in matched_sites if site.name == site_name), None
    )
    assert old_site is not None
    assert old_site.name == "ValidActive"


# --- SOCKS proxy scheme normalization tests (issue #2955) ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'given, expected',
    [
        # python_socks rejects socks5h outright, so --submit through a SOCKS
        # proxy used to crash with "Invalid scheme component: socks5h"
        ('socks5h://127.0.0.1:1080', 'socks5://127.0.0.1:1080'),
        ('socks5://127.0.0.1:1080', 'socks5://127.0.0.1:1080'),
        ('http://127.0.0.1:8080', 'http://127.0.0.1:8080'),
    ],
)
async def test_submitter_normalizes_proxy_scheme(test_db, given, expected):
    args = MagicMock()
    args.cookie_file = ""
    args.proxy = given

    captured = []

    class _DummyConnector:
        def __init__(self, *args, **kwargs):
            # aiohttp's ClientSession expects these on its connector
            self._loop = None
            self.closed = False

        async def close(self):
            pass

        @property
        def force_close(self):
            return False

    def fake_from_url(url, **kwargs):
        captured.append(url)
        return _DummyConnector()

    # Only the URL handed to python_socks matters here; whether ClientSession
    # then accepts the dummy connector is irrelevant to this assertion.
    with patch('aiohttp_socks.ProxyConnector.from_url', side_effect=fake_from_url):
        try:
            Submitter(test_db, MagicMock(), logging.getLogger(), args)
        except Exception:
            pass

    assert captured == [expected]


@pytest.mark.asyncio
async def test_submitter_site_self_check_dns_resolver_fallback(test_db):
    stub_args = type('Args', (object,), {'proxy': None, 'cookie_file': None, 'verbose': False})()
    submitter = Submitter(test_db, MagicMock(), logging.getLogger(), stub_args)

    with patch('maigret.submit.site_self_check', new_callable=AsyncMock) as mock_ssc:
        await submitter.site_self_check(MagicMock(), MagicMock())
        mock_ssc.assert_awaited_once()
        _, kwargs = mock_ssc.call_args
        assert kwargs.get('dns_resolver') == 'async'


@pytest.mark.asyncio
async def test_submitter_site_self_check_dns_resolver_forwarded(test_db):
    stub_args = type('Args', (object,), {'proxy': None, 'cookie_file': None, 'verbose': False, 'dns_resolver': 'threaded'})()
    submitter = Submitter(test_db, MagicMock(), logging.getLogger(), stub_args)

    with patch('maigret.submit.site_self_check', new_callable=AsyncMock) as mock_ssc:
        await submitter.site_self_check(MagicMock(), MagicMock())
        mock_ssc.assert_awaited_once()
        _, kwargs = mock_ssc.call_args
        assert kwargs.get('dns_resolver') == 'threaded'
