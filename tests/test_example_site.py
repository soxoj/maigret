import responses
from maigret_sites_example.example_site import check

@responses.activate
def test_found_by_html():
    url = "https://www.example.com/alice"
    # HTML fixture that includes a profile header fragment
    responses.add(responses.GET, url, body='<div class="profile-header">Alice</div>', status=200)
    result = check("alice", user_agent="test-agent")
    assert result["status"] == "found"

@responses.activate
def test_not_found_404():
    url = "https://www.example.com/bob"
    responses.add(responses.GET, url, body='Not Found', status=404)
    result = check("bob", user_agent="test-agent")
    assert result["status"] == "not_found"
