"""Maigret data test functions"""

import pytest
from maigret.utils import is_country_tag


@pytest.mark.slow
def test_tags_validity(default_db):
    unknown_tags = set()

    tags = default_db._tags

    for site in default_db.sites:
        for tag in filter(lambda x: not is_country_tag(x), site.tags):
            if tag not in tags:
                unknown_tags.add(tag)

    # make sure all tags are known
    # if you see "unchecked" tag error, please, do
    # maigret --db `pwd`/maigret/resources/data.json --self-check --tag unchecked --use-disabled-sites
    assert unknown_tags == set()
