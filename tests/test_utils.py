"""Maigret utils test functions"""

import itertools
import re

from markupsafe import Markup

from maigret.utils import (
    CaseConverter,
    is_country_tag,
    enrich_link_str,
    URLMatcher,
    get_dict_ascii_tree,
    get_match_ratio,
    is_plausible_username,
)


def test_case_convert_camel_to_snake():
    a = 'SnakeCasedString'
    b = CaseConverter.camel_to_snake(a)

    assert b == 'snake_cased_string'


def test_case_convert_snake_to_camel():
    a = 'camel_cased_string'
    b = CaseConverter.snake_to_camel(a)

    assert b == 'camelCasedString'


def test_case_convert_snake_to_title():
    a = 'camel_cased_string'
    b = CaseConverter.snake_to_title(a)

    assert b == 'Camel cased string'


def test_case_convert_camel_with_digits_to_snake():
    a = 'ignore403'
    b = CaseConverter.camel_to_snake(a)

    assert b == 'ignore403'


def test_is_country_tag():
    assert is_country_tag('ru') is True
    assert is_country_tag('FR') is True

    assert is_country_tag('a1') is False
    assert is_country_tag('dating') is False

    assert is_country_tag('global') is True


def test_is_country_tag_field_names_are_not_country_codes():
    """The field names 'country' and 'locale' must not be mistaken for ISO codes.

    generate_report_context iterates ids_data and for keys 'country'/'locale'
    decides whether to use direct alpha_2 lookup (is_country_tag(v)) or fuzzy
    search. A previous bug passed the key name k instead of the value v, so
    is_country_tag('country') was always False and the direct lookup path was
    dead code.
    """
    assert is_country_tag('country') is False
    assert is_country_tag('locale') is False
    # Values that should trigger the direct lookup
    assert is_country_tag('US') is True
    assert is_country_tag('ru') is True


def test_enrich_link_str():
    assert enrich_link_str('test') == 'test'
    assert (
        enrich_link_str(' www.flickr.com/photos/alexaimephotography/')
        == '<a class="auto-link" href="www.flickr.com/photos/alexaimephotography/">www.flickr.com/photos/alexaimephotography/</a>'
    )


def test_enrich_link_str_escapes_payload():
    # markup inside a link must be escaped while the <a> wrapper is preserved
    payload = 'http://evil.example/"><img src=x onerror=alert(1)>'
    result = enrich_link_str(payload)

    assert isinstance(result, Markup)
    assert '<img' not in result
    assert '&lt;img' in result
    assert '"><img' not in result
    assert result.startswith('<a class="auto-link" href="')


def test_enrich_link_str_non_link_is_plain_str():
    # non-link values stay plain str so template autoescaping neutralizes them
    payload = '<script>alert(1)</script>'
    result = enrich_link_str(payload)

    assert not isinstance(result, Markup)
    assert result == payload


def test_url_extract_main_part_negative():
    url_main_part = 'None'
    assert URLMatcher.extract_main_part(url_main_part) == ''


def test_url_extract_main_part():
    url_main_part = 'flickr.com/photos/alexaimephotography'

    parts = [
        ['http://', 'https://'],
        ['www.', ''],
        [url_main_part],
        ['/', ''],
    ]

    url_regexp = re.compile(r'^https?://(www\.)?flickr.com/photos/(.+?)$')
    # combine parts variations
    for url_parts in itertools.product(*parts):
        url = ''.join(url_parts)
        # ensure all combinations give valid main part
        assert URLMatcher.extract_main_part(url) == url_main_part
        assert not url_regexp.match(url) is None


def test_url_make_profile_url_regexp():
    url_main_part = 'flickr.com/photos/{username}'

    parts = [
        ['http://', 'https://'],
        ['www.', ''],
        [url_main_part],
        ['/', ''],
    ]

    # combine parts variations
    for url_parts in itertools.product(*parts):
        url = ''.join(url_parts)
        # ensure all combinations match pattern
        assert (
            URLMatcher.make_profile_url_regexp(url).pattern
            == r'^https?://(www.|m.)?flickr\.com/photos/(.+?)$'
        )


def test_get_dict_ascii_tree():
    data = {
        'uid': 'dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==',
        'legacy_id': '26403415',
        'username': 'alexaimephotographycars',
        'name': 'Alex Aimé',
        'links': "['www.instagram.com/street.reality.photography/']",
        'created_at': '2018-05-04T10:17:01.000+0000',
        'image': 'https://drscdn.500px.org/user_avatar/26403415/q%3D85_w%3D300_h%3D300/v2?webp=true&v=2&sig=0235678a4f7b65e007e864033ebfaf5ef6d87fad34f80a8639d985320c20fe3b',
        'image_bg': 'https://drscdn.500px.org/user_cover/26403415/q%3D65_m%3D2048/v2?webp=true&v=1&sig=bea411fb158391a4fdad498874ff17088f91257e59dfb376ff67e3a44c3a4201',
        'website': 'www.instagram.com/street.reality.photography/',
        'facebook_link': ' www.instagram.com/street.reality.photography/',
        'instagram_username': 'Street.Reality.Photography',
        'twitter_username': 'Alexaimephotogr',
    }

    ascii_tree = get_dict_ascii_tree(data.items(), prepend=" ")

    assert (
        ascii_tree
        == """
 ├─uid: dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==
 ├─legacy_id: 26403415
 ├─username: alexaimephotographycars
 ├─name: Alex Aimé
 ├─links: 
 │ └─ www.instagram.com/street.reality.photography/
 ├─created_at: 2018-05-04T10:17:01.000+0000
 ├─image: https://drscdn.500px.org/user_avatar/26403415/q%3D85_w%3D300_h%3D300/v2?webp=true&v=2&sig=0235678a4f7b65e007e864033ebfaf5ef6d87fad34f80a8639d985320c20fe3b
 ├─image_bg: https://drscdn.500px.org/user_cover/26403415/q%3D65_m%3D2048/v2?webp=true&v=1&sig=bea411fb158391a4fdad498874ff17088f91257e59dfb376ff67e3a44c3a4201
 ├─website: www.instagram.com/street.reality.photography/
 ├─facebook_link:  www.instagram.com/street.reality.photography/
 ├─instagram_username: Street.Reality.Photography
 └─twitter_username: Alexaimephotogr"""
    )


def test_get_match_ratio():
    fun = get_match_ratio(["test", "maigret", "username"])

    assert fun("test") == 1


# Regression tests for #1403 — Gravatar URL leaking into next-iteration username.
# Extractor schemes occasionally store URLs/emails under '*_username' keys; without
# validation these were fed back into the search loop and produced cascades of false
# errors. See maigret/utils.py::is_plausible_username.
def test_is_plausible_username_accepts_bare_usernames():
    assert is_plausible_username("alice")
    assert is_plausible_username("alice.bob")
    assert is_plausible_username("alice_bob-42")
    assert is_plausible_username("Алиса")


def test_is_plausible_username_rejects_urls():
    assert not is_plausible_username("https://gravatar.com/alice")
    assert not is_plausible_username("http://example.com/user/alice")
    assert not is_plausible_username("//example.com/alice")
    assert not is_plausible_username("www.facebook.com/zuck")


def test_is_plausible_username_accepts_http_prefixed_handles():
    """Don't over-match: bare names that just happen to start with 'http' or 'www'
    are legitimate (e.g. the httpie CLI maintainer's handle)."""
    assert is_plausible_username("httpie")
    assert is_plausible_username("http_user")
    assert is_plausible_username("wwwsuperstar")


def test_is_plausible_username_rejects_path_like():
    assert not is_plausible_username("user/alice")
    assert not is_plausible_username("alice/")


def test_is_plausible_username_rejects_emails():
    assert not is_plausible_username("alice@example.com")
    assert not is_plausible_username("user@maigret.io")


def test_is_plausible_username_rejects_whitespace_and_empty():
    assert not is_plausible_username("")
    assert not is_plausible_username("   ")
    assert not is_plausible_username("alice bob")
    assert not is_plausible_username("alice\nbob")


def test_is_plausible_username_rejects_non_strings():
    assert not is_plausible_username(None)
    assert not is_plausible_username(42)
    assert not is_plausible_username(["alice"])
