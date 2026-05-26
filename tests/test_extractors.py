"""
Unit tests for username extraction helpers.
"""

from maigret.extractors import extract_usernames

from mock import Mock

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