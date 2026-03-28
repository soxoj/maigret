"""Maigret data test functions"""

import pytest
from maigret.utils import is_country_tag


TOP_SITES_ALEXA_RANK_LIMIT = 50

KNOWN_SOCIAL_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "tiktok.com",
    "vk.com",
    "reddit.com",
    "pinterest.com",
    "snapchat.com",
    "linkedin.com",
    "tumblr.com",
    "threads.net",
    "bsky.app",
    "myspace.com",
    "weibo.com",
    "mastodon.social",
    "gab.com",
    "minds.com",
    "clubhouse.com",
]


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


@pytest.mark.slow
def test_top_sites_have_category_tag(default_db):
    """Top sites by alexaRank must have at least one category tag (not just country codes)."""
    sites_ranked = sorted(
        [s for s in default_db.sites if s.alexa_rank],
        key=lambda s: s.alexa_rank,
    )[:TOP_SITES_ALEXA_RANK_LIMIT]

    missing_category = []
    for site in sites_ranked:
        category_tags = [t for t in site.tags if not is_country_tag(t)]
        if not category_tags:
            missing_category.append(f"{site.name} (rank {site.alexa_rank})")

    assert missing_category == [], (
        f"{len(missing_category)} top-{TOP_SITES_ALEXA_RANK_LIMIT} sites have no category tag: "
        + ", ".join(missing_category[:20])
    )


@pytest.mark.slow
def test_no_unused_tags_in_registry(default_db):
    """Every tag in the registry should be used by at least one site."""
    all_used_tags = set()
    for site in default_db.sites:
        for tag in site.tags:
            if not is_country_tag(tag):
                all_used_tags.add(tag)

    registered_tags = set(default_db._tags)
    unused = registered_tags - all_used_tags

    assert unused == set(), f"Tags registered but not used by any site: {unused}"


@pytest.mark.slow
def test_social_networks_have_social_tag(default_db):
    """Known social network domains must have the 'social' tag."""
    from urllib.parse import urlparse

    missing_social = []
    for site in default_db.sites:
        url = site.url_main or ""
        try:
            hostname = urlparse(url).hostname or ""
        except Exception:
            continue
        for domain in KNOWN_SOCIAL_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                if "social" not in site.tags:
                    missing_social.append(f"{site.name} ({domain})")
                break

    assert missing_social == [], (
        f"{len(missing_social)} known social networks missing 'social' tag: "
        + ", ".join(missing_social)
    )
