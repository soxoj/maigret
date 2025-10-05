import responses
from maigret_sites_example.mastodon_resolver import resolve_mastodon

@responses.activate
def test_resolve_with_instance_hint_found():
    instance = "example.social"
    url = f"https://{instance}/@alice"
    responses.add(responses.GET, url, body="OK", status=200)
    res = resolve_mastodon("alice", instance_hint=instance)
    assert res["status"] == "found"
    assert res["url"] == url

@responses.activate
def test_resolve_with_common_instances_not_found():
    # Simulate 404 on common instances
    responses.add(responses.GET, "https://mastodon.social/@bob", status=404)
    responses.add(responses.GET, "https://fosstodon.org/@bob", status=404)
    responses.add(responses.GET, "https://mstdn.social/@bob", status=404)
    responses.add(responses.GET, "https://chaos.social/@bob", status=404)
    res = resolve_mastodon("bob")
    assert res["status"] == "not_found"

@responses.activate
def test_resolve_explicit_nick_at_instance_found():
    url = "https://custom.instance/@charlie"
    responses.add(responses.GET, url, status=200)
    res = resolve_mastodon("@charlie@custom.instance")
    assert res["status"] == "found"
    assert res["url"] == url
