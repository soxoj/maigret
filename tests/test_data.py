"""Maigret data test functions"""

import pytest
from maigret.result import MaigretCheckStatus
from maigret.utils import is_country_tag


TOP_SITES_ALEXA_RANK_LIMIT = 50

KNOWN_SOCIAL_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "tiktok.com",
    "vk.com",
    "reddit.com",
    "pinterest.com",
    "snapchat.com",
    "linkedin.com",
    "tumblr.com",
    "threads.net",
    "bsky.app",
    "myspace.com",
    "weibo.com",
    "mastodon.social",
    "gab.com",
    "minds.com",
    "clubhouse.com",
]


@pytest.mark.slow
def test_tags_validity(default_db):
    unknown_tags = set()

    tags = default_db._tags

    for site in default_db.sites:
        for tag in filter(lambda x: not is_country_tag(x), site.tags):
            if tag not in tags:
                unknown_tags.add(tag)

    # make sure all tags are known
    # if you see "unchecked" tag error, please, do
    # maigret --db `pwd`/maigret/resources/data.json --self-check --tag unchecked --use-disabled-sites
    assert unknown_tags == set()


@pytest.mark.slow
def test_top_sites_have_category_tag(default_db):
    """Top sites by alexaRank must have at least one category tag (not just country codes)."""
    sites_ranked = sorted(
        [s for s in default_db.sites if s.alexa_rank],
        key=lambda s: s.alexa_rank,
    )[:TOP_SITES_ALEXA_RANK_LIMIT]

    missing_category = []
    for site in sites_ranked:
        category_tags = [t for t in site.tags if not is_country_tag(t)]
        if not category_tags:
            missing_category.append(f"{site.name} (rank {site.alexa_rank})")

    assert missing_category == [], (
        f"{len(missing_category)} top-{TOP_SITES_ALEXA_RANK_LIMIT} sites have no category tag: "
        + ", ".join(missing_category[:20])
    )


@pytest.mark.slow
def test_no_unused_tags_in_registry(default_db):
    """Every tag in the registry should be used by at least one site."""
    all_used_tags = set()
    for site in default_db.sites:
        for tag in site.tags:
            if not is_country_tag(tag):
                all_used_tags.add(tag)

    registered_tags = set(default_db._tags)
    unused = registered_tags - all_used_tags

    assert unused == set(), f"Tags registered but not used by any site: {unused}"


@pytest.mark.slow
def test_social_networks_have_social_tag(default_db):
    """Known social network domains must have the 'social' tag."""
    from urllib.parse import urlparse

    missing_social = []
    for site in default_db.sites:
        url = site.url_main or ""
        try:
            hostname = urlparse(url).hostname or ""
        except Exception:
            continue
        for domain in KNOWN_SOCIAL_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                if "social" not in site.tags:
                    missing_social.append(f"{site.name} ({domain})")
                break

    assert missing_social == [], (
        f"{len(missing_social)} known social networks missing 'social' tag: "
        + ", ".join(missing_social)
    )


def test_planetaexcel_does_not_pin_bot_user_agent(default_db):
    """Planetaexcel is filtered by an Anubis bot rule that serves an HTTP 200
    'Access Denied' page to the python-requests User-Agent, which a
    status_code check reads as a found account for every username (#3191).
    The check must rely on Maigret's default browser User-Agent instead."""
    site = default_db.sites_dict["Planetaexcel"]
    assert not (site.headers or {}).get("User-Agent")


def test_cgtrader_disabled_behind_aws_waf(default_db):
    """CGTrader answers every profile URL, real or not, with an AWS WAF
    challenge (HTTP 202, empty body, x-amzn-waf-action: challenge), which a
    status_code check reads as a found account (#3163)."""
    site = default_db.sites_dict["CGTrader"]
    assert site.disabled is True
    assert "aws_waf_js_challenge" in site.protection


def _officiating_status(default_db, body, http_status, username):
    from unittest.mock import Mock
    from maigret.checking import process_site_result

    site = default_db.sites_dict["officiating"]
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": site.url.format(username=username),
    }
    out = process_site_result((body, http_status, None), Mock(), Mock(), info, site)
    return out["status"].status


def test_officiating_profile_url_follows_forum_migration(default_db):
    """The forum moved profiles from /members/<name>.html to /u/<name>; the old
    path now redirects for real accounts and answers a JSON 404 for the rest."""
    site = default_db.sites_dict["officiating"]
    assert site.url == "https://forum.officiating.com/u/{username}"


def test_officiating_missing_user_is_not_claimed(default_db):
    """A missing user gets an HTTP 404 JSON error with no HTML, so a body-marker
    check read it as a found account for every username (#3302)."""
    body = '{"errors":[{"status":"404","code":"not_found"}]}'
    assert (
        _officiating_status(default_db, body, 404, "zyiub6")
        == MaigretCheckStatus.AVAILABLE
    )


def test_officiating_existing_user_is_claimed(default_db):
    body = "<!doctype html><title>Rich - The Official Forum</title>"
    assert _officiating_status(default_db, body, 200, "rich") == MaigretCheckStatus.CLAIMED


def _bambu_status(default_db, body, http_status, username):
    from unittest.mock import Mock

    from maigret.checking import process_site_result

    site = default_db.sites_dict["Bambu Lab Forum"]
    fields = dict(
        urlMain=site.url_main,
        urlSubpath=site.url_subpath,
        username=username,
    )
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": site.url.format(**fields),
        "url_probe": site.url_probe.format(**fields),
    }
    out = process_site_result((body, http_status, None), Mock(), Mock(), info, site)
    return out["status"].status


def test_bambu_missing_user_is_not_claimed(default_db):
    """A missing user answers the .json probe with a compact not_found JSON;
    the inherited status_code check read any soft 200 as a found account (#3363)."""
    body = '{"errors":["The requested URL or resource could not be found."],"error_type":"not_found"}'
    assert (
        _bambu_status(default_db, body, 200, "Ttd") == MaigretCheckStatus.AVAILABLE
    )


def test_bambu_missing_user_with_spaced_json_is_not_claimed(default_db):
    body = '{ "errors": [ "The requested URL or resource could not be found." ], "error_type": "not_found" }'
    assert (
        _bambu_status(default_db, body, 200, "Ttd") == MaigretCheckStatus.AVAILABLE
    )


def test_bambu_existing_user_is_claimed(default_db):
    body = '{"user_badges":[],"user":{"id":1,"username":"grandpa","avatar_template":"/user_avatar/forum.bambulab.com/grandpa/{size}/1_2.png"}}'
    assert _bambu_status(default_db, body, 200, "grandpa") == MaigretCheckStatus.CLAIMED


def test_bambu_hidden_profile_is_claimed(default_db):
    """A hidden profile's .json answer carries the basic user fields but no
    user_badges array at all, so the marker must not depend on it."""
    body = '{"user":{"id":170222,"username":"test","name":"Test","avatar_template":"/user_avatar/forum.bambulab.com/test/{size}/167737_2.png","profile_hidden":true}}'
    assert _bambu_status(default_db, body, 200, "test") == MaigretCheckStatus.CLAIMED


def test_bambu_unrecognized_body_is_not_claimed(default_db):
    """An unexpected soft 200 (a bot-wall page served to datacenter clients)
    carries no profile marker, so it must not read as a found account; the
    honest verdict for it stays out of scope of the substring check (#3363)."""
    body = "<html><body>checking your browser</body></html>"
    assert _bambu_status(default_db, body, 200, "Ttd") != MaigretCheckStatus.CLAIMED


def test_bambu_probe_url_is_json_endpoint(default_db):
    site = default_db.sites_dict["Bambu Lab Forum"]
    assert (
        site.url_probe.format(urlMain=site.url_main, username="grandpa")
        == "https://forum.bambulab.com/u/grandpa.json"
    )


def _filmweb_status(default_db, body, http_status, username):
    from unittest.mock import Mock

    from maigret.checking import process_site_result

    site = default_db.sites_dict["FilmWeb"]
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": site.url.format(username=username),
    }
    out = process_site_result((body, http_status, None), Mock(), Mock(), info, site)
    return out["status"].status


def test_filmweb_missing_user_is_not_claimed(default_db):
    """A missing profile answers HTTP 404 without the old body marker, so the
    message check reported every username as claimed (#3286)."""
    body = "<!doctype html><title>Nie znaleziono strony o podanym adresie.</title>"
    assert (
        _filmweb_status(default_db, body, 404, "noonewouldeverusethis7")
        == MaigretCheckStatus.AVAILABLE
    )


def test_filmweb_existing_user_is_claimed(default_db):
    body = "<!doctype html><title>Adam - profil w Filmweb</title>"
    assert _filmweb_status(default_db, body, 200, "adam") == MaigretCheckStatus.CLAIMED


def test_filmweb_check_type_is_status_code(default_db):
    """The site no longer renders the JS redirect marker the absence check
    relied on, so the check must not depend on page body content."""
    site = default_db.sites_dict["FilmWeb"]
    assert site.check_type == "status_code"


def test_filmweb_main_url_is_site_root(default_db):
    """urlMain pointed at a user profile page instead of the site root."""
    site = default_db.sites_dict["FilmWeb"]
    assert site.url_main == "https://www.filmweb.pl"


def _weforum_status(default_db, body, http_status, username):
    from unittest.mock import Mock

    from maigret.checking import process_site_result

    site = default_db.sites_dict["Weforum"]
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": site.url.format(username=username),
    }
    out = process_site_result((body, http_status, None), Mock(), Mock(), info, site)
    return out["status"].status


def test_weforum_existing_profile_is_claimed(default_db):
    body = (
        '<script id="content-structured-data" type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Person","name":"Klaus Schwab"}'
        '</script>'
    )
    assert (
        _weforum_status(default_db, body, 200, "klaus-schwab")
        == MaigretCheckStatus.CLAIMED
    )


def test_weforum_missing_profile_is_not_claimed(default_db):
    """A synthetic HTTP 200 without the Person marker must not be claimed (#3364)."""
    body = "<!doctype html><title>Page not found | World Economic Forum</title>"
    assert (
        _weforum_status(default_db, body, 200, "noonewouldeverusethis7")
        == MaigretCheckStatus.AVAILABLE
    )


def test_weforum_404_not_found_page_is_not_claimed(default_db):
    body = "<!doctype html><title>Page not found | World Economic Forum</title>"
    assert (
        _weforum_status(default_db, body, 404, "noonewouldeverusethis7")
        == MaigretCheckStatus.AVAILABLE
    )


def test_weforum_akamai_403_is_unknown_not_available(default_db):
    body = (
        "<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD>"
        "<BODY><H1>Access Denied</H1></BODY></HTML>"
    )
    assert (
        _weforum_status(default_db, body, 403, "noonewouldeverusethis7")
        == MaigretCheckStatus.UNKNOWN
    )


def test_weforum_check_type_is_message(default_db):
    site = default_db.sites_dict["Weforum"]
    assert site.check_type == "message"
    assert '"@type":"Person"' in site.presense_strs
    assert "tls_fingerprint" in site.protection


def test_weforum_organization_jsonld_is_not_claimed(default_db):
    """An Organization block in the same structured-data script must not read
    as a person profile: only the Person marker tells the pages apart."""
    body = (
        '<script id="content-structured-data" type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization","name":"World Economic Forum"}'
        '</script>'
    )
    assert (
        _weforum_status(default_db, body, 200, "noonewouldeverusethis7")
        == MaigretCheckStatus.AVAILABLE
    )


def test_weforum_claimed_username_is_current(default_db):
    """The old adam-leismark profile now returns Page not found."""
    site = default_db.sites_dict["Weforum"]
    assert site.username_claimed == "klaus-schwab"


def test_engine_entries_do_not_override_check_type_blindly():
    """An entry on an engine must not swap the engine's check for another one
    without bringing its own markers.

    On forum engines the probe URL is a member search that answers 200 for
    anyone, so "status_code" on top of the engine's "message" claims every
    username. 318 entries got there through a saved constructor default
    (#3346, #3347). An entry that really needs another check type has to say
    how it tells the pages apart.
    """
    import json
    import os

    import maigret

    path = os.path.join(os.path.dirname(maigret.__file__), 'resources', 'data.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    engines = data['engines']

    blind = sorted(
        name
        for name, site in data['sites'].items()
        if site.get('engine')
        and 'checkType' in site
        and site['checkType'] != engines[site['engine']]['site'].get('checkType')
        and not site.get('presenseStrs')
        and not site.get('absenceStrs')
    )
    assert not blind, (
        f"{len(blind)} engine entries override checkType without their own "
        f"markers: {', '.join(blind)}. Drop checkType so the engine's check "
        f"applies, or add presenseStrs/absenceStrs that tell the pages apart."
    )
