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


class URLMatcher:
    _HTTP_URL_RE_STR = '^https?://(www.)?(.+)$'
    HTTP_URL_RE = re.compile(_HTTP_URL_RE_STR)
    UNSAFE_SYMBOLS = '.?'

    @classmethod
    def extract_main_part(self, url: str) -> str:
        match = self.HTTP_URL_RE.search(url)
        if match and match.group(2):
            return match.group(2).rstrip('/')

        return ''

    @classmethod
    def make_profile_url_regexp(self, url: str, username_regexp: str = ''):
        url_main_part = self.extract_main_part(url)
        for c in self.UNSAFE_SYMBOLS:
            url_main_part = url_main_part.replace(c, f'\\{c}')
        username_regexp = username_regexp or '.+?'

        url_regexp = url_main_part.replace('{username}', f'({username_regexp})')
        regexp_str = self._HTTP_URL_RE_STR.replace('(.+)', url_regexp)

        return re.compile(regexp_str)


def get_dict_ascii_tree(items, prepend='', new_line=True):
    text = ''
    for num, item in enumerate(items):
        box_symbol = '┣╸' if num != len(items) - 1 else '┗╸'

        if type(item) == tuple:
            field_name, field_value = item
            if field_value.startswith('[\''):
                is_last_item = num == len(items) - 1
                prepend_symbols = ' ' * 3 if is_last_item else ' ┃ '
                field_value = get_dict_ascii_tree(eval(field_value), prepend_symbols)
            text += f'\n{prepend}{box_symbol}{field_name}: {field_value}'
        else:
            text += f'\n{prepend}{box_symbol} {item}'

    if not new_line:
        text = text[1:]

    return text
