"""Maigret data test functions"""

from maigret.utils import is_country_tag
from maigret.sites import SUPPORTED_TAGS


def test_tags_validity(default_db):
    unknown_tags = set()

    for site in default_db.sites:
        for tag in filter(lambda x: not is_country_tag(x), site.tags):
            if tag not in SUPPORTED_TAGS:
                unknown_tags.add(tag)

    assert unknown_tags == set()
