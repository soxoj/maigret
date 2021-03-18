"""Maigret activation test functions"""
import json

import aiohttp
import pytest
from mock import Mock

from maigret.activation import ParsingActivator, import_aiohttp_cookies

COOKIES_TXT = """# HTTP Cookie File downloaded with cookies.txt by Genuinous @genuinous
# This file can be used by wget, curl, aria2c and other standard compliant tools.
# Usage Examples:
#   1) wget -x --load-cookies cookies.txt "https://xss.is/search/"
#   2) curl --cookie cookies.txt "https://xss.is/search/"
#   3) aria2c --load-cookies cookies.txt "https://xss.is/search/"
#
xss.is	FALSE	/	TRUE	0	xf_csrf	test
xss.is	FALSE	/	TRUE	1642709308	xf_user	tset
.xss.is	TRUE	/	FALSE	0	muchacho_cache	test
.xss.is	TRUE	/	FALSE	1924905600	132_evc	test
httpbin.org	FALSE	/	FALSE	0	a	b
"""


@pytest.mark.slow
def test_twitter_activation(default_db):
    twitter_site = default_db.sites_dict['Twitter']
    token1 = twitter_site.headers['x-guest-token']

    ParsingActivator.twitter(twitter_site, Mock())
    token2 = twitter_site.headers['x-guest-token']

    assert token1 != token2


@pytest.mark.asyncio
async def test_import_aiohttp_cookies():
    cookies_filename = 'cookies_test.txt'
    with open(cookies_filename, 'w') as f:
        f.write(COOKIES_TXT)

    cookie_jar = await import_aiohttp_cookies(cookies_filename)
    assert list(cookie_jar._cookies.keys()) == ['xss.is', 'httpbin.org']

    url = 'https://httpbin.org/cookies'
    connector = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(connector=connector, trust_env=True,
                                    cookie_jar=cookie_jar)

    response = await session.get(url=url)
    result = json.loads(await response.content.read())
    await session.close()

    assert result == {'cookies': {'a': 'b'}}
