import re


class CaseConverter:
    @staticmethod
    def camel_to_snake(camelcased_string: str) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camelcased_string).lower()

    @staticmethod
    def snake_to_camel(snakecased_string: str) -> str:
        formatted = ''.join(word.title() for word in snakecased_string.split('_'))
        result = formatted[0].lower() + formatted[1:]
        return result

    @staticmethod
    def snake_to_title(snakecased_string: str) -> str:
        words = snakecased_string.split('_')
        words[0] = words[0].title()
        return ' '.join(words)


def is_country_tag(tag: str) -> bool:
    """detect if tag represent a country"""
    return bool(re.match("^([a-zA-Z]){2}$", tag)) or tag == 'global'


def enrich_link_str(link: str) -> str:
    link = link.strip()
    if link.startswith('www.') or (link.startswith('http') and '//' in link):
        return f'<a class="auto-link" href="{link}">{link}</a>'
    return link