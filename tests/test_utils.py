"""Maigret utils test functions"""
import itertools
import re
from maigret.utils import CaseConverter, is_country_tag, enrich_link_str, URLMatcher


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

def test_is_country_tag():
	assert is_country_tag('ru') == True
	assert is_country_tag('FR') == True

	assert is_country_tag('a1') == False
	assert is_country_tag('dating') == False

	assert is_country_tag('global') == True

def test_enrich_link_str():
	assert enrich_link_str('test') == 'test'
	assert enrich_link_str(' www.flickr.com/photos/alexaimephotography/') == '<a class="auto-link" href="www.flickr.com/photos/alexaimephotography/">www.flickr.com/photos/alexaimephotography/</a>'

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
