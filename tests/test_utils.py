"""Maigret utils test functions"""
from maigret.utils import CaseConverter


def test_case_convert_camel_to_snake():
	a = 'SnakeCasedString'
	b = CaseConverter.camel_to_snake(a)

	assert b == 'snake_cased_string'

def test_case_convert_snake_to_camel():
	a = 'camel_cased_string'
	b = CaseConverter.snake_to_camel(a)

	assert b == 'camelCasedString'
