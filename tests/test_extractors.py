"""
Unit tests for username extraction helpers.
"""

from maigret.utils import extract_usernames
from maigret.maigret import extract_ids_from_page

from unittest.mock import Mock, patch


def test_extract_username():
    logger = Mock()

    result = extract_usernames(
        {"profile_username": "emily"},
        logger,
    )

    assert result == ["emily"]


def test_extract_list_usernames():
    logger = Mock()

    result = extract_usernames(
        {"profile_usernames": "['emily','ashton']"},
        logger,
    )

    assert set(result) == {"emily", "ashton"}


def test_reject_invalid_username():
    logger = Mock()

    result = extract_usernames(
        {"profile_username": "https.example.com/au"},
        logger,
    )

    assert result == []


def test_ignore_invalid_username_list():
    logger = Mock()

    result = extract_usernames(
        {"profile_usernames": "not-a-list"},
        logger,
    )

    assert result == []
    assert logger.warning.called

def test_extract_ids_from_page_username_contract():
    logger = Mock()

    with patch("maigret.maigret.parse") as mock_parse, \
         patch("maigret.maigret.extract") as mock_extract, \
         patch("maigret.maigret.extract_usernames") as mock_usernames:

        # fake page fetch
        mock_parse.return_value = ("<html></html>", {})

        # no structured IDs
        mock_extract.return_value = {}

        # username detection
        mock_usernames.return_value = ["emily"]

        result = extract_ids_from_page(
            "https://example.com/profile",
            logger,
            timeout=5,
        )

    assert result == {"emily": "username"}
