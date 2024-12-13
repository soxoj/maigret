"""Maigret activation test functions"""

import json
import yarl

import aiohttp
import pytest
from mock import Mock

from tests.conftest import LOCAL_SERVER_PORT
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
localhost	FALSE	/	FALSE	0	a	b
"""


@pytest.mark.skip("captcha")
@pytest.mark.slow
def test_vimeo_activation(default_db):
    vimeo_site = default_db.sites_dict['Vimeo']
    token1 = vimeo_site.headers['Authorization']

    ParsingActivator.vimeo(vimeo_site, Mock())
    token2 = vimeo_site.headers['Authorization']

    assert token1 != token2


@pytest.mark.slow
@pytest.mark.asyncio
async def test_import_aiohttp_cookies(cookie_test_server):
    cookies_filename = 'cookies_test.txt'
    with open(cookies_filename, 'w') as f:
        f.write(COOKIES_TXT)

    cookie_jar = import_aiohttp_cookies(cookies_filename)
    url = f'http://localhost:{LOCAL_SERVER_PORT}/cookies'

    cookies = cookie_jar.filter_cookies(yarl.URL(url))
    assert cookies['a'].value == 'b'

    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.get(url=url) as response:
            result = await response.json()
            print(f"Server response: {result}")

    assert result == {'cookies': {'a': 'b'}}
