from unittest.mock import patch
from maigret_sites_example.mastodon_api_checker import check

def test_mastodon_found():
    fake = {"status":"found","url":"https://mastodon.social/@alice"}
    with patch("maigret_sites_example.mastodon_api_resolver.resolve_mastodon_api", return_value=fake):
        res = check("alice")
        assert res["http_status"] == 200
        assert res["ids_usernames"] == {"alice": "username"}
        assert res["parsing_enabled"] is True

def test_mastodon_not_found():
    fake = {"status":"not_found"}
    with patch("maigret_sites_example.mastodon_api_resolver.resolve_mastodon_api", return_value=fake):
        res = check("nobody")
        assert res["ids_usernames"] == {}
        assert res["parsing_enabled"] is False
