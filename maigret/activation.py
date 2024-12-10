import json
from http.cookiejar import MozillaCookieJar
from http.cookies import Morsel

from aiohttp import CookieJar


class ParsingActivator:
    @staticmethod
    def twitter(site, logger, cookies={}):
        headers = dict(site.headers)
        del headers["x-guest-token"]
        import requests

        r = requests.post(site.activation["url"], headers=headers)
        logger.info(r)
        j = r.json()
        guest_token = j[site.activation["src"]]
        site.headers["x-guest-token"] = guest_token

    @staticmethod
    def vimeo(site, logger, cookies={}):
        headers = dict(site.headers)
        if "Authorization" in headers:
            del headers["Authorization"]
        import requests

        r = requests.get(site.activation["url"], headers=headers)
        logger.debug(f"Vimeo viewer activation: {json.dumps(r.json(), indent=4)}")
        jwt_token = r.json()["jwt"]
        site.headers["Authorization"] = "jwt " + jwt_token

    @staticmethod
    def spotify(site, logger, cookies={}):
        headers = dict(site.headers)
        if "Authorization" in headers:
            del headers["Authorization"]
        import requests

        r = requests.get(site.activation["url"])
        bearer_token = r.json()["accessToken"]
        site.headers["authorization"] = f"Bearer {bearer_token}"

    @staticmethod
    def weibo(site, logger):
        headers = dict(site.headers)
        import requests

        session = requests.Session()
        # 1 stage: get the redirect URL
        r = session.get(
            "https://weibo.com/clairekuo", headers=headers, allow_redirects=False
        )
        logger.debug(
            f"1 stage: {'success' if r.status_code == 302 else 'no 302 redirect, fail!'}"
        )
        location = r.headers.get("Location")

        # 2 stage: go to passport visitor page
        headers["Referer"] = location
        r = session.get(location, headers=headers)
        logger.debug(
            f"2 stage: {'success' if r.status_code == 200 else 'no 200 response, fail!'}"
        )

        # 3 stage: gen visitor token
        headers["Referer"] = location
        r = session.post(
            "https://passport.weibo.com/visitor/genvisitor2",
            headers=headers,
            data={'cb': 'visitor_gray_callback', 'tid': '', 'from': 'weibo'},
        )
        cookies = r.headers.get('set-cookie')
        logger.debug(
            f"3 stage: {'success' if r.status_code == 200 and cookies else 'no 200 response and cookies, fail!'}"
        )
        site.headers["Cookie"] = cookies


def import_aiohttp_cookies(cookiestxt_filename):
    cookies_obj = MozillaCookieJar(cookiestxt_filename)
    cookies_obj.load(ignore_discard=True, ignore_expires=True)

    cookies = CookieJar()

    cookies_list = []
    for domain in cookies_obj._cookies.values():
        for key, cookie in list(domain.values())[0].items():
            c = Morsel()
            c.set(key, cookie.value, cookie.value)
            c["domain"] = cookie.domain
            c["path"] = cookie.path
            cookies_list.append((key, c))

    cookies.update_cookies(cookies_list)

    return cookies
