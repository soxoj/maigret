"""Maigret utils test functions"""
import itertools
import re

from maigret.utils import CaseConverter, is_country_tag, enrich_link_str, URLMatcher, get_dict_ascii_tree


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
    assert is_country_tag('ru') == True
    assert is_country_tag('FR') == True

    assert is_country_tag('a1') == False
    assert is_country_tag('dating') == False

    assert is_country_tag('global') == True


def test_enrich_link_str():
    assert enrich_link_str('test') == 'test'
    assert enrich_link_str(
        ' www.flickr.com/photos/alexaimephotography/') == '<a class="auto-link" href="www.flickr.com/photos/alexaimephotography/">www.flickr.com/photos/alexaimephotography/</a>'


def test_url_extract_main_part():
    url_main_part = 'flickr.com/photos/alexaimephotography'

    parts = [
        ['http://', 'https://'],
        ['www.', ''],
        [url_main_part],
        ['/', ''],
    ]

    url_regexp = re.compile('^https?://(www.)?flickr.com/photos/(.+?)$')
    for url_parts in itertools.product(*parts):
        url = ''.join(url_parts)
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

    for url_parts in itertools.product(*parts):
        url = ''.join(url_parts)
        assert URLMatcher.make_profile_url_regexp(url).pattern == r'^https?://(www.)?flickr\.com/photos/(.+?)$'


def test_get_dict_ascii_tree():
    data = {'uid': 'dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==', 'legacy_id': '26403415', 'username': 'alexaimephotographycars', 'name': 'Alex Aimé', 'created_at': '2018-05-04T10:17:01.000+0000', 'image': 'https://drscdn.500px.org/user_avatar/26403415/q%3D85_w%3D300_h%3D300/v2?webp=true&v=2&sig=0235678a4f7b65e007e864033ebfaf5ef6d87fad34f80a8639d985320c20fe3b', 'image_bg': 'https://drscdn.500px.org/user_cover/26403415/q%3D65_m%3D2048/v2?webp=true&v=1&sig=bea411fb158391a4fdad498874ff17088f91257e59dfb376ff67e3a44c3a4201', 'website': 'www.instagram.com/street.reality.photography/', 'facebook_link': ' www.instagram.com/street.reality.photography/', 'instagram_username': 'Street.Reality.Photography', 'twitter_username': 'Alexaimephotogr'}

    ascii_tree = get_dict_ascii_tree(data.items())

    assert ascii_tree == """
┣╸uid: dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==
┣╸legacy_id: 26403415
┣╸username: alexaimephotographycars
┣╸name: Alex Aimé
┣╸created_at: 2018-05-04T10:17:01.000+0000
┣╸image: https://drscdn.500px.org/user_avatar/26403415/q%3D85_w%3D300_h%3D300/v2?webp=true&v=2&sig=0235678a4f7b65e007e864033ebfaf5ef6d87fad34f80a8639d985320c20fe3b
┣╸image_bg: https://drscdn.500px.org/user_cover/26403415/q%3D65_m%3D2048/v2?webp=true&v=1&sig=bea411fb158391a4fdad498874ff17088f91257e59dfb376ff67e3a44c3a4201
┣╸website: www.instagram.com/street.reality.photography/
┣╸facebook_link:  www.instagram.com/street.reality.photography/
┣╸instagram_username: Street.Reality.Photography
┗╸twitter_username: Alexaimephotogr"""