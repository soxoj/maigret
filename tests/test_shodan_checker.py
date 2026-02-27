# tests/test_shodan_checker.py
from unittest.mock import patch, Mock
from maigret_sites_example.shodan_checker import check

def test_shodan_no_key(monkeypatch):
    monkeypatch.delenv("SHODAN_API_KEY", raising=False)
    res = check("alice")
    assert res["ids_usernames"] == {}
    assert res["parsing_enabled"] is False

def test_shodan_found(monkeypatch):
    monkeypatch.setenv("SHODAN_API_KEY", "FAKEKEY")
    fake_resp = Mock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"total": 1, "matches": [{"ip_str": "1.2.3.4"}]}
    with patch("maigret_sites_example.shodan_checker._get_with_backoff", return_value=fake_resp):
        res = check("alice")
        assert res["http_status"] == 200
        assert res["ids_usernames"] == {"alice": "username"}

def test_shodan_not_found(monkeypatch):
    monkeypatch.setenv("SHODAN_API_KEY", "FAKEKEY")
    fake_resp = Mock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"total": 0, "matches": []}
    with patch("maigret_sites_example.shodan_checker._get_with_backoff", return_value=fake_resp):
        res = check("nobody")
        assert res["ids_usernames"] == {}
