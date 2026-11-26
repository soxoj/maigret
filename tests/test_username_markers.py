"""{username} placeholders in presenseStrs / absenceStrs."""

from unittest.mock import Mock

from maigret.checking import _marker_in, process_site_result
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


def _site(**overrides):
    data = {
        "url": "https://x/{username}",
        "urlMain": "https://x",
        "checkType": "message",
        "usernameClaimed": "a",
        "usernameUnclaimed": "b",
    }
    data.update(overrides)
    return MaigretSite("TestSite", data)


def _check(site, username, html):
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": f"https://x/{username}",
    }
    out = process_site_result((html, 200, None), Mock(), Mock(), info, site)
    return out["status"].status


def test_marker_in_keeps_json_braces():
    assert _marker_in('{"value":"{username}"}', '[{"value":"jor"}]', "jor")
    assert _marker_in('{"error":"not-found"}', '{"error":"not-found"}', "jor")


def test_marker_in_placeholder_is_case_insensitive():
    assert _marker_in('"value":"{username}"', '"value":"jori"', "Jori")


def test_marker_in_plain_marker_stays_case_sensitive():
    assert not _marker_in("Profile-Card", "profile-card", "bob")


def test_marker_in_without_username_is_literal():
    assert _marker_in("{username}", "literal {username}", "")


def test_presence_requires_exact_name_not_prefix():
    # Autocomplete endpoints match by prefix: a lookup for "jor" also lists "joriz".
    site = _site(presenseStrs=['"value":"{username}"'])
    prefix_only = '[{"id":1,"value":"joriz"}]'
    exact = '[{"id":2,"value":"jor"},{"id":1,"value":"joriz"}]'
    assert _check(site, "jor", prefix_only) == MaigretCheckStatus.AVAILABLE
    assert _check(site, "jor", exact) == MaigretCheckStatus.CLAIMED
    assert _check(site, "JOR", exact) == MaigretCheckStatus.CLAIMED


def test_absence_marker_with_username():
    site = _site(absenceStrs=["No user named {username}"], presenseStrs=["profile"])
    assert (
        _check(site, "bob", "profile page. No user named bob")
        == MaigretCheckStatus.AVAILABLE
    )
    assert (
        _check(site, "bob", "profile page. No user named alice")
        == MaigretCheckStatus.CLAIMED
    )


def test_markers_without_placeholder_unchanged():
    site = _site(presenseStrs=["profile-card"])
    assert _check(site, "bob", "<div class=profile-card>") == MaigretCheckStatus.CLAIMED
    assert _check(site, "bob", "<div>nothing</div>") == MaigretCheckStatus.AVAILABLE
