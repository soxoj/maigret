import re


class CaseConverter:
	@staticmethod
	def camel_to_snake(camelcased_string: str):
		return re.sub(r'(?<!^)(?=[A-Z])', '_', camelcased_string).lower()

	@staticmethod
	def snake_to_camel(snakecased_string: str):
		formatted = ''.join(word.title() for word in snakecased_string.split('_'))
		result = formatted[0].lower() + formatted[1:]
		return result
