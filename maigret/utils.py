import ast
import difflib
import re
import random
from typing import Any


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
]


class CaseConverter:
    @staticmethod
    def camel_to_snake(camelcased_string: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", camelcased_string).lower()

    @staticmethod
    def snake_to_camel(snakecased_string: str) -> str:
        formatted = "".join(word.title() for word in snakecased_string.split("_"))
        result = formatted[0].lower() + formatted[1:]
        return result

    @staticmethod
    def snake_to_title(snakecased_string: str) -> str:
        words = snakecased_string.split("_")
        words[0] = words[0].title()
        return " ".join(words)


def is_country_tag(tag: str) -> bool:
    """detect if tag represent a country"""
    return bool(re.match("^([a-zA-Z]){2}$", tag)) or tag == "global"


def enrich_link_str(link: str) -> str:
    link = link.strip()
    if link.startswith("www.") or (link.startswith("http") and "//" in link):
        return f'<a class="auto-link" href="{link}">{link}</a>'
    return link


class URLMatcher:
    _HTTP_URL_RE_STR = "^https?://(www.)?(.+)$"
    HTTP_URL_RE = re.compile(_HTTP_URL_RE_STR)
    UNSAFE_SYMBOLS = ".?"

    @classmethod
    def extract_main_part(self, url: str) -> str:
        match = self.HTTP_URL_RE.search(url)
        if match and match.group(2):
            return match.group(2).rstrip("/")

        return ""

    @classmethod
    def make_profile_url_regexp(self, url: str, username_regexp: str = ""):
        url_main_part = self.extract_main_part(url)
        for c in self.UNSAFE_SYMBOLS:
            url_main_part = url_main_part.replace(c, f"\\{c}")
        prepared_username_regexp = (username_regexp or ".+?").lstrip('^').rstrip('$')

        url_regexp = url_main_part.replace(
            "{username}", f"({prepared_username_regexp})"
        )
        regexp_str = self._HTTP_URL_RE_STR.replace("(.+)", url_regexp)

        return re.compile(regexp_str)


def ascii_data_display(data: str) -> Any:
    return ast.literal_eval(data)


def get_dict_ascii_tree(items, prepend="", new_line=True):
    text = ""
    for num, item in enumerate(items):
        box_symbol = "┣╸" if num != len(items) - 1 else "┗╸"

        if type(item) == tuple:
            field_name, field_value = item
            if field_value.startswith("['"):
                is_last_item = num == len(items) - 1
                prepend_symbols = " " * 3 if is_last_item else " ┃ "
                data = ascii_data_display(field_value)
                field_value = get_dict_ascii_tree(data, prepend_symbols)
            text += f"\n{prepend}{box_symbol}{field_name}: {field_value}"
        else:
            text += f"\n{prepend}{box_symbol} {item}"

    if not new_line:
        text = text[1:]

    return text


def get_random_user_agent():
    return random.choice(DEFAULT_USER_AGENTS)


def get_match_ratio(base_strs: list):
    def get_match_inner(s: str):
        return round(
            max(
                [
                    difflib.SequenceMatcher(a=s.lower(), b=s2.lower()).ratio()
                    for s2 in base_strs
                ]
            ),
            2,
        )

    return get_match_inner
