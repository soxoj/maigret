import json
from http.cookiejar import MozillaCookieJar
from http.cookies import Morsel

from aiohttp import ClientSession, CookieJar


class ParsingActivator:
    @staticmethod
    async def twitter(site, logger, cookies={}, **kwargs):
        headers = dict(site.headers)
        headers.pop("x-guest-token", None)

        async with ClientSession(trust_env=True) as session:
            async with session.post(
                site.activation["url"],
                headers=headers,
                timeout=kwargs.get("timeout"),
            ) as response:
                logger.info(response)
                j = await response.json(content_type=None)
        guest_token = j[site.activation["src"]]
        site.headers[site.activation.get("dst", "x-guest-token")] = guest_token

    @staticmethod
    async def vimeo(site, logger, cookies={}, **kwargs):
        headers = dict(site.headers)
        headers.pop("Authorization", None)

        async with ClientSession(trust_env=True) as session:
            async with session.get(
                site.activation["url"],
                headers=headers,
                timeout=kwargs.get("timeout"),
            ) as response:
                payload = await response.json(content_type=None)
        logger.debug(f"Vimeo viewer activation: {json.dumps(payload, indent=4)}")
        jwt_token = payload["jwt"]
        site.headers["Authorization"] = "jwt " + jwt_token

    @staticmethod
    async def onlyfans(site, logger, url=None, **kwargs):
        # Signing rules (static_param / checksum_indexes / checksum_constant / format / app_token)
        # live in data.json under OnlyFans.activation and rotate upstream every ~1–3 weeks.
        # If "Please refresh the page" keeps firing after activation, refresh them from:
        #   https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json
        import hashlib
        import secrets
        import time as _time
        from urllib.parse import urlparse

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
            async with ClientSession(trust_env=True) as session:
                async with session.get(
                    init_url,
                    headers=hdrs,
                    timeout=kwargs.get("timeout", 15),
                ) as response:
                    jar = "; ".join(
                        f"{k}={getattr(v, 'value', v)}"
                        for k, v in response.cookies.items()
                    )
            if jar:
                site.headers["cookie"] = jar
                logger.debug(
                    f"OnlyFans init: got cookies {list(response.cookies.keys())}"
                )

        target_path = urlparse(url).path if url else urlparse(init_url).path
        t, sg = _sign(target_path)
        site.headers["time"] = t
        site.headers["sign"] = sg
        logger.debug(f"OnlyFans signed {target_path} time={t}")

    @staticmethod
    async def weibo(site, logger, **kwargs):
        headers = dict(site.headers)
        timeout = kwargs.get("timeout")

        async with ClientSession(trust_env=True) as session:
            # 1 stage: get the redirect URL
            async with session.get(
                "https://weibo.com/clairekuo",
                headers=headers,
                allow_redirects=False,
                timeout=timeout,
            ) as response:
                logger.debug(
                    f"1 stage: {'success' if response.status == 302 else 'no 302 redirect, fail!'}"
                )
                location = response.headers.get("Location", "")

            # 2 stage: go to passport visitor page
            headers["Referer"] = location
            async with session.get(
                location,
                headers=headers,
                timeout=timeout,
            ) as response:
                logger.debug(
                    f"2 stage: {'success' if response.status == 200 else 'no 200 response, fail!'}"
                )

            # 3 stage: gen visitor token
            headers["Referer"] = location
            async with session.post(
                "https://passport.weibo.com/visitor/genvisitor2",
                headers=headers,
                data={'cb': 'visitor_gray_callback', 'tid': '', 'from': 'weibo'},
                timeout=timeout,
            ) as response:
                cookies = response.headers.get('set-cookie')
                logger.debug(
                    f"3 stage: {'success' if response.status == 200 and cookies else 'no 200 response and cookies, fail!'}"
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
