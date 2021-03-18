from http.cookiejar import MozillaCookieJar
from http.cookies import Morsel

import requests
from aiohttp import CookieJar


class ParsingActivator:
    @staticmethod
    def twitter(site, logger, cookies={}):
        headers = dict(site.headers)
        del headers['x-guest-token']
        r = requests.post(site.activation['url'], headers=headers)
        logger.info(r)
        j = r.json()
        guest_token = j[site.activation['src']]
        site.headers['x-guest-token'] = guest_token

    @staticmethod
    def vimeo(site, logger, cookies={}):
        headers = dict(site.headers)
        if 'Authorization' in headers:
            del headers['Authorization']
        r = requests.get(site.activation['url'], headers=headers)
        jwt_token = r.json()['jwt']
        site.headers['Authorization'] = 'jwt ' + jwt_token

    @staticmethod
    def spotify(site, logger, cookies={}):
        headers = dict(site.headers)
        if 'Authorization' in headers:
            del headers['Authorization']
        r = requests.get(site.activation['url'])
        bearer_token = r.json()['accessToken']
        site.headers['authorization'] = f'Bearer {bearer_token}'

    @staticmethod
    def xssis(site, logger, cookies={}):
        if not cookies:
            logger.debug('You must have cookies to activate xss.is parsing!')
            return

        headers = dict(site.headers)
        post_data = {
            '_xfResponseType': 'json',
            '_xfToken': '1611177919,a2710362e45dad9aa1da381e21941a38'
        }
        headers['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        r = requests.post(site.activation['url'], headers=headers, cookies=cookies, data=post_data)
        csrf = r.json()['csrf']
        site.get_params['_xfToken'] = csrf


async def import_aiohttp_cookies(cookiestxt_filename):
    cookies_obj = MozillaCookieJar(cookiestxt_filename)
    cookies_obj.load(ignore_discard=True, ignore_expires=True)

    cookies = CookieJar()

    cookies_list = []
    for domain in cookies_obj._cookies.values():
        for key, cookie in list(domain.values())[0].items():
            c = Morsel()
            c.set(key, cookie.value, cookie.value)
            c['domain'] = cookie.domain
            c['path'] = cookie.path
            cookies_list.append((key, c))

    cookies.update_cookies(cookies_list)

    return cookies
