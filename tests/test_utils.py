"""Maigret utils test functions"""
from maigret.utils import CaseConverter, is_country_tag


def test_case_convert_camel_to_snake():
	a = 'SnakeCasedString'
	b = CaseConverter.camel_to_snake(a)

	assert b == 'snake_cased_string'

def test_case_convert_snake_to_camel():
	a = 'camel_cased_string'
	b = CaseConverter.snake_to_camel(a)

	assert b == 'camelCasedString'

def test_is_country_tag():
	assert is_country_tag('ru') == True

	assert is_country_tag('a1') == False
	assert is_country_tag('dating') == False
