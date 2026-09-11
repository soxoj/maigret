"""Shared Mastodon engine: lookup urlProbe lives on the engine, inside site."""

from unittest.mock import Mock

from maigret.checking import make_site_result
from maigret.sites import MaigretEngine, MaigretSite

# Hosts that use the same /@{username} profile URL shape but are not Mastodon.
# Verified by GET /api/v1/instance — they do not return an instance document.
URL_SHAPE_LOOKALIKES = ("TikTok", "Threads", "Figma")

# Pychess uses /@/{username} (note the extra slash) and is issue #3100 — leave it.
PYCHESS_URL = "https://www.pychess.org/@/{username}"


def _mastodon_engine() -> MaigretEngine:
    return MaigretEngine(
        "Mastodon",
        {
            "name": "Mastodon",
            "site": {
                "checkType": "status_code",
                "url": "{urlMain}/@{username}",
                "urlProbe": "{urlMain}/api/v1/accounts/lookup?acct={username}",
            },
        },
    )


def test_engine_fields_live_inside_site():
    """update_from_engine copies engine.site only. A sibling key is ignored.

    That is how 34 vBulletin sites ended up with empty presenseStrs: the
    strings were declared next to "site", not inside it.
    """
    engine = _mastodon_engine()
    assert list(engine.site.keys()) == ["checkType", "url", "urlProbe"]
    assert "urlProbe" not in {k for k in engine.json if k != "site"}
    assert engine.site["url"] == "{urlMain}/@{username}"
    assert engine.site["urlProbe"] == "{urlMain}/api/v1/accounts/lookup?acct={username}"


def test_site_inherits_lookup_urlprobe_from_engine():
    site = MaigretSite(
        "ExampleMastodon",
        {
            "engine": "Mastodon",
            "urlMain": "https://example.social",
            "usernameClaimed": "alice",
            "usernameUnclaimed": "noonewouldeverusethis7",
        },
    )
    site.update_from_engine(_mastodon_engine())

    assert site.check_type == "status_code"
    assert site.url == "{urlMain}/@{username}"
    assert site.url_probe == "{urlMain}/api/v1/accounts/lookup?acct={username}"

    stripped = site.strip_engine_data().json
    assert stripped["engine"] == "Mastodon"
    assert "url" not in stripped
    assert "urlProbe" not in stripped
    assert "checkType" not in stripped


def test_make_site_result_uses_lookup_probe_and_profile_url():
    site = MaigretSite(
        "ExampleMastodon",
        {"urlMain": "https://example.social"},
    )
    site.update_from_engine(_mastodon_engine())

    checker = Mock()
    checker.prepare.return_value = None
    results = make_site_result(
        site,
        "alice",
        {
            "id_type": "username",
            "parsing": False,
            "timeout": 1,
            "forced": False,
            "checkers": {"": lambda: checker},
        },
        Mock(),
    )

    assert results["url_user"] == "https://example.social/@alice"
    assert (
        results["url_probe"]
        == "https://example.social/api/v1/accounts/lookup?acct=alice"
    )


def test_shipped_engine_matches_template(default_db):
    engine = default_db.engines_dict["Mastodon"]
    assert engine.site == _mastodon_engine().site
    # nothing inherited except through site — no stray top-level check fields
    assert list(engine.site.keys()) == ["checkType", "url", "urlProbe"]


def test_confirmed_instances_use_engine(default_db):
    mastodon_sites = [s for s in default_db.sites if s.engine == "Mastodon"]
    assert len(mastodon_sites) >= 70
    names = {s.name for s in mastodon_sites}

    for expected in (
        "mastodon.social",
        "social.tchncs.de",
        "Framapiaf",
        "infosec.exchange",
        "hachyderm.io",
        "foxes.day",
        "Fosstodon",
        "fuzzies.wtf",
    ):
        assert expected in names
        site = default_db.sites_dict[expected]
        assert site.check_type == "status_code"
        assert site.url == "{urlMain}/@{username}"
        assert site.url_probe == "{urlMain}/api/v1/accounts/lookup?acct={username}"
        assert not site.url_main.endswith("/")

    # disabled instance still moved so a later re-enable gets the probe
    assert default_db.sites_dict["fuzzies.wtf"].disabled is True

    # urlMain used to point at chaos.social; the engine templates need the
    # host from the profile URL.
    assert default_db.sites_dict["mastodon.social"].url_main == (
        "https://mastodon.social"
    )


def test_lookalikes_and_pychess_are_not_on_the_engine(default_db):
    for name in URL_SHAPE_LOOKALIKES:
        site = default_db.sites_dict[name]
        assert site.engine != "Mastodon"
        assert "/@{username}" in site.url
        assert not (site.url_probe or "").endswith("accounts/lookup?acct={username}")

    pychess = default_db.sites_dict["Pychess"]
    assert pychess.engine != "Mastodon"
    assert pychess.url == PYCHESS_URL

    # unverified /api/v1/instance (TLS failure from this environment)
    chaos = default_db.sites_dict["chaos.social"]
    assert chaos.engine != "Mastodon"
