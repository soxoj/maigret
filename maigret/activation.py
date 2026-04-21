import json
from http.cookiejar import MozillaCookieJar
from http.cookies import Morsel

from aiohttp import CookieJar


class ParsingActivator:
    @staticmethod
    def twitter(site, logger, cookies={}, **kwargs):
        headers = dict(site.headers)
        del headers["x-guest-token"]
        import requests

        r = requests.post(site.activation["url"], headers=headers)
        logger.info(r)
        j = r.json()
        guest_token = j[site.activation["src"]]
        site.headers["x-guest-token"] = guest_token

    @staticmethod
    def vimeo(site, logger, cookies={}, **kwargs):
        headers = dict(site.headers)
        if "Authorization" in headers:
            del headers["Authorization"]
        import requests

        r = requests.get(site.activation["url"], headers=headers)
        logger.debug(f"Vimeo viewer activation: {json.dumps(r.json(), indent=4)}")
        jwt_token = r.json()["jwt"]
        site.headers["Authorization"] = "jwt " + jwt_token

    @staticmethod
    def onlyfans(site, logger, url=None, **kwargs):
        # Signing rules (static_param / checksum_indexes / checksum_constant / format / app_token)
        # live in data.json under OnlyFans.activation and rotate upstream every ~1–3 weeks.
        # If "Please refresh the page" keeps firing after activation, refresh them from:
        #   https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json
        import hashlib
        import secrets
        import time as _time
        from urllib.parse import urlparse

        import requests

        act = site.activation
        static_param = act["static_param"]
        indexes = act["checksum_indexes"]
        constant = act["checksum_constant"]
        fmt = act["format"]
        init_url = act["url"]

        user_id = site.headers.get("user-id", "0") or "0"

        def _sign(path):
            t = str(int(_time.time() * 1000))
            msg = "\n".join([static_param, t, path, user_id]).encode()
            sha = hashlib.sha1(msg).hexdigest()
            cs = sum(ord(sha[i]) for i in indexes) + constant
            return t, fmt.format(sha, abs(cs))

        if site.headers.get("x-bc", "").strip("0") == "":
            site.headers["x-bc"] = secrets.token_hex(20)

        if not site.headers.get("cookie"):
            init_path = urlparse(init_url).path
            t, sg = _sign(init_path)
            hdrs = dict(site.headers)
            hdrs["time"] = t
            hdrs["sign"] = sg
            hdrs.pop("cookie", None)
            r = requests.get(init_url, headers=hdrs, timeout=15)
            jar = "; ".join(f"{k}={v}" for k, v in r.cookies.items())
            if jar:
                site.headers["cookie"] = jar
                logger.debug(f"OnlyFans init: got cookies {list(r.cookies.keys())}")

        target_path = urlparse(url).path if url else urlparse(init_url).path
        t, sg = _sign(target_path)
        site.headers["time"] = t
        site.headers["sign"] = sg
        logger.debug(f"OnlyFans signed {target_path} time={t}")

    @staticmethod
    def weibo(site, logger, **kwargs):
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
        location = r.headers.get("Location", "")

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
    for domain in cookies_obj._cookies.values():  # type: ignore[attr-defined]
        for key, cookie in list(domain.values())[0].items():
            c: Morsel = Morsel()
            c.set(key, cookie.value, cookie.value)
            c["domain"] = cookie.domain
            c["path"] = cookie.path
            cookies_list.append((key, c))

    cookies.update_cookies(cookies_list)

    return cookies
