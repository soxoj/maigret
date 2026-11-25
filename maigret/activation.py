import json
import os
import os.path as path
import re
from http.cookiejar import MozillaCookieJar
from http.cookies import Morsel
from typing import Dict

from aiohttp import ClientSession, CookieJar

from .db_updater import MAIGRET_HOME


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
    async def proton(site, logger, **kwargs):
        # Proton's /api/users/available now requires an anon session: POST
        # /api/auth/v4/sessions returns UID + AccessToken which must be sent
        # as x-pm-uid and Authorization: Bearer on the availability call.
        headers = {
            k: v for k, v in site.headers.items()
            if k.lower() not in ("authorization", "x-pm-uid")
        }
        async with ClientSession(trust_env=True) as session:
            async with session.post(
                site.activation["url"],
                headers=headers,
                json={},
                timeout=kwargs.get("timeout"),
            ) as response:
                payload = await response.json(content_type=None)
        uid, token = payload.get("UID"), payload.get("AccessToken")
        if uid and token:
            site.headers["x-pm-uid"] = uid
            site.headers["Authorization"] = f"Bearer {token}"
            logger.debug("Proton activation: got session UID + token")
        else:
            logger.warning(
                f"Proton activation failed: no UID/token in {str(payload)[:120]!r}"
            )

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
    # Iterate the jar itself rather than its internal {domain: {path: {name}}}
    # mapping: picking a single path bucket per domain silently dropped every
    # cookie stored under the domain's other paths.
    for cookie in cookies_obj:
        c: Morsel = Morsel()
        # A valueless cookie ("name" with no "=value") parses as value None,
        # which used to reach the wire as the literal string "None".
        value = cookie.value or ""
        c.set(cookie.name, value, value)
        c["domain"] = cookie.domain
        c["path"] = cookie.path
        cookies_list.append((cookie.name, c))

    cookies.update_cookies(cookies_list)

    return cookies


ACTIVATION_CACHE_PATH = path.join(MAIGRET_HOME, "activation.json")


def _activation_sites(db):
    return [site for site in db.sites if site.activation]


def load_activation_cache(db, logger) -> Dict[str, Dict[str, str]]:
    """Apply per-user cached activation headers to the sites database.

    Tokens minted at runtime (guest tokens, JWTs, session cookies) are user
    state, not package data, so they are kept in the user's home instead of
    being written back into the shipped database — which is read-only on any
    system-wide install.

    Returns the pre-overlay headers, needed by :func:`save_activation_cache`
    to tell a minted value from one that simply came with the database.
    """
    baseline = {site.name: dict(site.headers) for site in _activation_sites(db)}

    try:
        with open(ACTIVATION_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
    except FileNotFoundError:
        return baseline
    except (OSError, ValueError) as e:
        logger.debug(f"Ignoring unreadable activation cache: {e}")
        return baseline

    for site in _activation_sites(db):
        cached = cache.get(site.name)
        if isinstance(cached, dict):
            # Assign rather than update: MaigretSite.headers defaults to a
            # mutable class attribute shared by every site that doesn't
            # declare its own, and updating it in place would leak these
            # tokens onto all of them.
            site.headers = {**site.headers, **cached}

    return baseline


def save_activation_cache(db, baseline: Dict[str, Dict[str, str]], logger) -> None:
    """Persist only the header values that this run actually minted.

    Storing the full header set would freeze whatever the database shipped at
    the time, so a later database update could no longer change those headers.
    """
    cache = {}
    for site in _activation_sites(db):
        was = baseline.get(site.name, {})
        minted = {k: v for k, v in site.headers.items() if was.get(k) != v}
        if minted:
            cache[site.name] = minted

    if not cache:
        return

    try:
        os.makedirs(MAIGRET_HOME, exist_ok=True)
        # These are session credentials (guest tokens, JWTs, cookies), so the
        # file is created 0600 rather than inheriting the umask.
        fd = os.open(
            ACTIVATION_CACHE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.debug(f"Could not write the activation cache: {e}")
