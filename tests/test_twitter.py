"""Tests for the Twitter / X site entry and GraphQL probe."""

import re

import pytest
import requests

from maigret.sites import MaigretSite


def _twitter_site(site: MaigretSite) -> None:
    assert site.name == "Twitter"
    assert site.disabled is False
    assert site.check_type == "message"
    assert site.url_probe and "{username}" in site.url_probe
    assert "UserByScreenName" in site.url_probe or "graphql" in site.url_probe
    assert site.regex_check
    assert re.fullmatch(site.regex_check, site.username_claimed)
    assert re.fullmatch(site.regex_check, site.username_unclaimed)
    assert site.absence_strs
    assert site.activation.get("method") == "twitter"
    assert site.activation.get("url")
    assert "authorization" in {k.lower() for k in site.headers.keys()}


def test_twitter_site_entry_config(default_db):
    """Twitter entry in data.json must define probe URL, regex, and activation."""
    site = default_db.sites_dict["Twitter"]
    assert isinstance(site, MaigretSite)
    _twitter_site(site)


@pytest.mark.slow
def test_twitter_graphql_probe_claimed_vs_unclaimed(default_db):
    """
    Live check: guest activation + UserByScreenName GraphQL returns a user for
    usernameClaimed and no user for usernameUnclaimed (same flow as urlProbe).
    """
    site = default_db.sites_dict["Twitter"]
    _twitter_site(site)

    headers = dict(site.headers)
    headers.pop("x-guest-token", None)

    act = requests.post(site.activation["url"], headers=headers, timeout=45)
    assert act.status_code == 200, act.text[:500]
    body = act.json()
    assert "guest_token" in body
    headers["x-guest-token"] = body["guest_token"]

    def fetch(username: str) -> dict:
        url = site.url_probe.format(username=username)
        resp = requests.get(url, headers=headers, timeout=45)
        resp.raise_for_status()
        return resp.json()

    claimed_json = fetch(site.username_claimed)
    assert "data" in claimed_json
    assert claimed_json["data"].get("user") is not None

    unclaimed_json = fetch(site.username_unclaimed)
    data = unclaimed_json.get("data") or {}
    assert data == {} or data.get("user") is None
