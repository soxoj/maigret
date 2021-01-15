"""Maigret activation test functions"""
import pytest
from mock import Mock

from maigret.activation import ParsingActivator


@pytest.mark.slow
def test_twitter_activation(default_db):
    twitter_site = default_db.sites_dict['Twitter']
    token1 = twitter_site.headers['x-guest-token']

    ParsingActivator.twitter(twitter_site, Mock())
    token2 = twitter_site.headers['x-guest-token']

    assert token1 != token2
