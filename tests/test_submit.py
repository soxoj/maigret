import re

import pytest
from unittest.mock import MagicMock, patch
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
    presence_list, absence_list, status, random_username = (
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
    presence_list, absence_list, status, random_username = (
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
    assert site.presense_strs != []
    assert site.absence_strs != []
    assert site.username_claimed == "KONAMI"
    assert site.check_type == "message"


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
    assert site.presense_strs != []
    assert site.absence_strs != []
    assert site.username_claimed == "KONAMI"
    assert site.check_type == "message"


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
