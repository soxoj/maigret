from maigret.extractors import extract_usernames

def test_extract_usernames():
    logger = type("L", (), {"debug": lambda *a, **k: None})

    result = extract_usernames(
        {"profile_username": "emily"},
        logger,
    )

    assert result == ["emily"]

def test_extract_list_usernames():
    logger = type("L", (), {"debug": lambda *a, **k: None})

    result = extract_usernames(
        {"profile_usernames": "['emily','ashton']"},
        logger,
    )


    assert set(result) == {"emily", "ashton"}

def test_reject_invalid_username():
    logger = type("L", (), {"debug": lambda *a, **k: None})

    result = extract_usernames(
        {"profile_username": "https.example.com/au"},
        logger,
    )

    assert result == []