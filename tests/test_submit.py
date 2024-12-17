import pytest
from unittest.mock import MagicMock, patch
from maigret.submit import Submitter
from aiohttp import ClientSession
from maigret.sites import MaigretDatabase
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
    submitter.extract_username_dialog = MagicMock(return_value="adam")

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
async def test_check_features_manually_success(settings):
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
        result = await submitter.dialog("https://icq.im/sokrat", None)
        await submitter.close()

    assert result is False
