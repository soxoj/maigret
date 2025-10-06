import pytest
from unittest.mock import Mock, patch
from maigret_sites_example.newsite import check

def test_newsite_found():
    mock_resp = Mock(status_code=200)
    with patch("maigret_sites_example.newsite.requests.get", return_value=mock_resp):
        res = check("alice")
        assert res["http_status"] == 200
        assert res["ids_usernames"] == {"alice": "username"}

def test_newsite_not_found():
    mock_resp = Mock(status_code=404)
    with patch("maigret_sites_example.newsite.requests.get", return_value=mock_resp):
        res = check("nobody")
        assert res["http_status"] == 404
        assert res["ids_usernames"] == {}
