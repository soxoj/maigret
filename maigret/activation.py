import json
import re
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
    async def wikimapia(site, logger, html="", **kwargs):
        # Wikimapia gates content behind a per-IP JS cookie challenge: the first
        # response is a stub that sets `ngxsession=<token>` via document.cookie and
        # refreshes. The token is deterministic per source IP, so we read it straight
        # from the challenge body the checker already fetched and merge it into the
        # request cookie before the retry (re-fetching would race a fresh challenge).
        match = re.search(r'ngxsession=([0-9a-f]+)', html or "")
        if not match:
            logger.warning(
                f"Wikimapia activation: ngxsession token not found for {site.name}"
            )
            return
        token = match.group(1)

        existing = site.headers.get("Cookie", "")
        parts = [
            p.strip()
            for p in existing.split(";")
            if p.strip() and not p.strip().startswith("ngxsession=")
        ]
        parts.append(f"ngxsession={token}")
        site.headers["Cookie"] = "; ".join(parts)

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
        # Weibo gates its ajax profile API behind an anonymous "Sina Visitor
        # System" cookie. genvisitor2 mints a fresh visitor SUB/SUBP pair and
        # returns it in the JSONP body. The previous version stored the
        # passport-domain Set-Cookie header (SVB) instead of that SUB/SUBP, so
        # the cookie never unlocked weibo.com and every check 403'd.
        headers = dict(site.headers)
        headers.pop("Cookie", None)
        timeout = kwargs.get("timeout")

        async with ClientSession(trust_env=True) as session:
            async with session.post(
                site.activation["url"],
                headers=headers,
                data={'cb': 'visitor_gray_callback', 'tid': '', 'from': 'weibo'},
                timeout=timeout,
            ) as response:
                body = await response.text()

        match = re.search(r"\{.*\}", body)
        data = json.loads(match.group(0)).get("data", {}) if match else {}
        sub, subp = data.get("sub"), data.get("subp")
        if sub and subp:
            site.headers["Cookie"] = f"SUB={sub}; SUBP={subp}"
            logger.debug("Weibo activation: visitor SUB/SUBP acquired")
        else:
            logger.warning(f"Weibo activation failed: no SUB/SUBP in {body[:120]!r}")


def import_aiohttp_cookies(cookiestxt_filename):
    cookies_obj = MozillaCookieJar(cookiestxt_filename)
    cookies_obj.load(ignore_discard=True, ignore_expires=True)

    cookies = CookieJar()

    cookies_list = []
    for domain in cookies_obj._cookies.values():  # type: ignore[attr-defined]
        for key, cookie in next(iter(domain.values())).items():
            c: Morsel = Morsel()
            c.set(key, cookie.value, cookie.value)
            c["domain"] = cookie.domain
            c["path"] = cookie.path
            cookies_list.append((key, c))

    cookies.update_cookies(cookies_list)

    return cookies
