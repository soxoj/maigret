# Standard library imports
import ast
import asyncio
import logging
import os
import random
import re
import ssl
import sys
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock
from urllib.parse import quote

# Third party imports
import aiodns
from alive_progress import alive_bar
from aiohttp import ClientSession, TCPConnector, http_exceptions
from aiohttp.resolver import ThreadedResolver
from aiohttp.client_exceptions import (
    ClientConnectorDNSError,
    ClientConnectorError,
    ServerDisconnectedError,
)
from python_socks import _errors as proxy_errors
from socid_extractor import extract  # type: ignore[import-not-found]

# Local imports
from . import errors
from .activation import ParsingActivator, import_aiohttp_cookies
from .error_detection import detect_error_page
from .errors import CheckError
from .executors import AsyncioQueueGeneratorExecutor
from .result import MaigretCheckResult, MaigretCheckStatus, KeywordMatchStatus, SiteResult
from .sites import MaigretDatabase, MaigretSite
from .utils import ascii_data_display, get_random_user_agent, is_plausible_username


_DNS_ERROR_MARKERS = (
    "could not contact dns servers",  # aiohttp + aiodns wording
    "name or service not known",       # glibc getaddrinfo
    "nodename nor servname",           # macOS getaddrinfo
    "temporary failure in name resolution",  # glibc EAI_AGAIN
    "getaddrinfo failed",              # generic socket error
)


def _is_dns_error(exc: Exception) -> bool:
    """Classify a ClientConnectorError as DNS-class or not.

    Prefers the typed aiohttp subclass; falls back to substring matching on
    the exception text for resolver/getaddrinfo errors that don't surface as
    ClientConnectorDNSError. The substrings are the OS/aiodns wordings
    observed in the wild.
    """
    if isinstance(exc, ClientConnectorDNSError):
        return True
    text = str(exc).lower()
    return any(m in text for m in _DNS_ERROR_MARKERS)


SUPPORTED_IDS = (
    "username",
    "yandex_public_id",
    "gaia_id",
    "vk_id",
    "ok_id",
    "wikimapia_uid",
    "steam_id",
    "uidme_uguid",
    "yelp_userid",
    "orcid",
)

BAD_CHARS = "#"


def build_cloudflare_bypass_config(
    settings_obj: Optional[Any], force_enable: bool = False
) -> Optional[Dict[str, Any]]:
    """Resolve Cloudflare webgate config from settings + CLI flag.

    Returns ``None`` when bypass is inactive or no usable module is configured.
    Otherwise returns a dict consumed by ``CloudflareWebgateChecker``:

      - ``trigger_protection``: list of ``site.protection`` values that
        activate the bypass (e.g. ``["cf_js_challenge", "cf_firewall", "webgate"]``)
      - ``modules``: ordered list of backend modules to try; each entry has
        ``name``, ``method`` (``json_api`` for FlareSolverr, ``url_rewrite``
        for CloudflareBypassForScraping), and a method-specific ``url`` plus
        optional ``max_timeout_ms``.
      - ``session_prefix``: prefix for FlareSolverr session reuse.
    """
    raw = {}
    if settings_obj is not None:
        raw = getattr(settings_obj, "cloudflare_bypass", {}) or {}
    enabled = bool(force_enable) or bool(raw.get("enabled", False))
    if not enabled:
        return None

    modules_raw = raw.get("modules") or []
    valid_modules: List[Dict[str, Any]] = []
    for module in modules_raw:
        method = module.get("method")
        url = module.get("url")
        if method == "json_api" and url:
            valid_modules.append(dict(module))
        elif method == "url_rewrite" and url and "{url}" in url:
            valid_modules.append(dict(module))
    if not valid_modules:
        return None

    trigger = raw.get("trigger_protection") or [
        "cf_js_challenge",
        "cf_firewall",
        "webgate",
    ]
    return {
        "trigger_protection": list(trigger),
        "modules": valid_modules,
        "session_prefix": raw.get("session_prefix", "maigret"),
    }


class CheckerBase:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', Mock())
        # Defaults for the request fields populated by .prepare(). Set here
        # so subclasses with a partial prepare() (e.g. AiodnsDomainResolver
        # only assigns url) still have predictable attribute access.
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        self.payload = None


class SimpleAiohttpChecker(CheckerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy = kwargs.get('proxy')
        self.cookie_jar = kwargs.get('cookie_jar')
        # 'async' (default) uses aiohttp's DefaultResolver, which is AsyncResolver
        # (powered by aiodns / c-ares) when aiodns is installed. 'threaded' uses
        # ThreadedResolver, which wraps the OS getaddrinfo via a threadpool —
        # slower for high concurrency, but respects the system DNS config
        # (resolv.conf, Windows network adapter settings) instead of having
        # aiodns rediscover it. See issue #2688: aiodns can fail to find any
        # DNS server on Windows / VPN / corporate networks, producing
        # "Could not contact DNS servers" for every site.
        self.dns_resolver = kwargs.get('dns_resolver', 'async')

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        self.url = url
        self.headers = headers
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.method = method
        self.payload = payload
        return None

    async def close(self):
        pass

    async def _make_request(
        self, session, url, headers, allow_redirects, timeout, method, logger, payload=None
    ) -> Tuple[Optional[str], int, Optional[CheckError]]:
        try:
            if method.lower() == 'get':
                request_method = session.get
            elif method.lower() == 'post':
                request_method = session.post
            elif method.lower() == 'head':
                request_method = session.head
            else:
                request_method = session.get

            kwargs = {
                'url': url,
                'headers': headers,
                'allow_redirects': allow_redirects,
                'timeout': timeout,
            }
            if payload and method.lower() == 'post':
                if headers and headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    kwargs['data'] = payload
                else:
                    kwargs['json'] = payload

            async with request_method(**kwargs) as response:
                status_code = response.status
                response_content = await response.content.read()
                charset = response.charset or "utf-8"
                decoded_content = response_content.decode(charset, "ignore")

                error = CheckError("Connection lost") if status_code == 0 else None
                logger.debug(decoded_content)

                return decoded_content, status_code, error

        except asyncio.TimeoutError as e:
            return None, 0, CheckError("Request timeout", str(e))
        except ClientConnectorError as e:
            err_type = "Connecting failure (DNS)" if _is_dns_error(e) else "Connecting failure"
            return None, 0, CheckError(err_type, str(e))
        except ServerDisconnectedError as e:
            return None, 0, CheckError("Server disconnected", str(e))
        except http_exceptions.BadHttpMessage as e:
            return None, 0, CheckError("HTTP", str(e))
        except proxy_errors.ProxyError as e:
            return None, 0, CheckError("Proxy", str(e))
        except KeyboardInterrupt:
            return None, 0, CheckError("Interrupted")
        except Exception as e:
            if sys.version_info.minor > 6 and (
                isinstance(e, ssl.SSLCertVerificationError)
                or isinstance(e, ssl.SSLError)
            ):
                return None, 0, CheckError("SSL", str(e))
            else:
                logger.debug(e, exc_info=True)
                return None, 0, CheckError("Unexpected", str(e))

    async def check(self) -> Tuple[Optional[str], int, Optional[CheckError]]:
        from aiohttp_socks import ProxyConnector

        # Use a real SSL context instead of ssl=False to avoid TLS fingerprinting
        # blocks by Cloudflare and similar WAFs. Certificate verification is
        # disabled to handle sites with invalid/expired certs.
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Build the TCPConnector with an explicit resolver when 'threaded' is
        # requested. ProxyConnector takes its own resolver kwarg too, so apply
        # the same setting on both code paths.
        resolver = ThreadedResolver() if self.dns_resolver == 'threaded' else None
        if self.proxy:
            connector = ProxyConnector.from_url(self.proxy, resolver=resolver) if resolver else ProxyConnector.from_url(self.proxy)
        else:
            connector = TCPConnector(ssl=ssl_context, resolver=resolver) if resolver else TCPConnector(ssl=ssl_context)

        async with ClientSession(
            connector=connector,
            trust_env=True,
            cookie_jar=self.cookie_jar if self.cookie_jar else None,
        ) as session:
            html_text, status_code, error = await self._make_request(
                session,
                self.url,
                self.headers,
                self.allow_redirects,
                self.timeout,
                self.method,
                self.logger,
                self.payload,
            )

            if error and str(error) == "Invalid proxy response":
                self.logger.debug(error, exc_info=True)

            return str(html_text) if html_text else '', status_code, error


class ProxiedAiohttpChecker(SimpleAiohttpChecker):
    pass


class AiodnsDomainResolver(CheckerBase):
    if sys.platform == 'win32':  # Temporary workaround for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        loop = asyncio.get_event_loop()
        self.resolver = aiodns.DNSResolver(loop=loop)

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        self.url = url
        return None

    async def check(self) -> Tuple[Optional[str], int, Optional[CheckError]]:
        status = 404
        error = None
        text = ''

        try:
            res = await self.resolver.query(self.url, 'A')
            text = str(res[0].host)
            status = 200
        except aiodns.error.DNSError:
            pass
        except Exception as e:
            self.logger.error(e, exc_info=True)
            error = CheckError('DNS resolve error', str(e))

        return text, status, error


from curl_cffi.requests import AsyncSession as CurlCffiAsyncSession


class CurlCffiChecker(CheckerBase):
    """Checker using curl_cffi to emulate browser TLS fingerprint and bypass WAF."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser_emulate = kwargs.get('browser_emulate', 'chrome')
        self.proxy = kwargs.get('proxy')

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        self.url = url
        self.headers = headers
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.method = method
        self.payload = payload
        return None

    async def close(self):
        pass

    async def check(self) -> Tuple[Optional[str], int, Optional[CheckError]]:
        try:
            session_kwargs = {}
            if self.proxy:
                session_kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
            async with CurlCffiAsyncSession(**session_kwargs) as session:
                # Strip the User-Agent so curl_cffi can use the impersonated browser's
                # matching UA. Mixing a random UA with a Chrome TLS fingerprint trips
                # composite bot scoring (e.g. Cloudflare returns a JS challenge for
                # "Chrome 91 UA + Chrome 131 TLS"). Keep any site-specific custom headers.
                headers = {k: v for k, v in (self.headers or {}).items()
                           if k.lower() not in ('user-agent', 'connection')}
                kwargs = {
                    'url': self.url,
                    'headers': headers or None,
                    'allow_redirects': self.allow_redirects,
                    'timeout': self.timeout if self.timeout else 10,
                    'impersonate': self.browser_emulate,
                }
                if self.payload and self.method.lower() == 'post':
                    kwargs['json'] = self.payload

                if self.method.lower() == 'post':
                    response = await session.post(**kwargs)
                elif self.method.lower() == 'head':
                    response = await session.head(**kwargs)
                else:
                    response = await session.get(**kwargs)

                status_code = response.status_code
                decoded_content = response.text

                self.logger.debug(decoded_content)

                error = CheckError("Connection lost") if status_code == 0 else None
                return decoded_content, status_code, error

        except asyncio.TimeoutError as e:
            return None, 0, CheckError("Request timeout", str(e))
        except KeyboardInterrupt:
            return None, 0, CheckError("Interrupted")
        except Exception as e:
            self.logger.debug(e, exc_info=True)
            return None, 0, CheckError("Unexpected", str(e))


class CloudflareWebgateChecker(CheckerBase):
    """Sends checks through a Cloudflare-bypass proxy.

    Supports two backends, selected by ``modules[0].method`` in settings:

    - ``json_api`` (FlareSolverr): POST to ``/v1`` with ``cmd: request.get``.
      Preserves real upstream status_code, headers and final URL — drop-in
      replacement for SimpleAiohttpChecker.
    - ``url_rewrite`` (CloudflareBypassForScraping ``/html`` endpoint):
      legacy mode. Returns rendered HTML only. Real upstream status is
      lost (proxy answers 200 on success). status_code / response_url
      check types degrade to "200 if HTML returned, AVAILABLE otherwise".
    """

    SESSION_PREFIX_DEFAULT = "maigret"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = kwargs.get('config') or {}
        self._modules: List[Dict[str, Any]] = []
        for raw in config.get('modules') or []:
            module = dict(raw)
            module.setdefault('method', 'json_api')
            module.setdefault('name', module.get('method'))
            self._modules.append(module)
        if not self._modules:
            raise ValueError("CloudflareWebgateChecker requires at least one module")
        # Session ID is computed per-request from the target host. Sharing a
        # single session across hosts caused FlareSolverr to break in
        # practice (TLS state / cookies leaking between domains), so each
        # host gets its own Chrome instance.
        self._session_prefix = (
            f"{config.get('session_prefix', self.SESSION_PREFIX_DEFAULT)}-{os.getpid()}"
        )
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        self.payload = None

    @property
    def session_id(self) -> str:
        """FlareSolverr session ID, scoped per target host."""
        from urllib.parse import urlparse

        host = urlparse(self.url or "").hostname or "default"
        host_safe = re.sub(r"[^a-zA-Z0-9.-]", "_", host)
        return f"{self._session_prefix}-{host_safe}"

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        self.url = url
        self.headers = headers or {}
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.method = method
        self.payload = payload
        return None

    async def close(self):
        pass

    async def check(self) -> Tuple[Optional[str], int, Optional[CheckError]]:
        attempts: List[str] = []
        last_error: Optional[CheckError] = None
        for module in self._modules:
            method = module.get('method')
            module_name = module.get('name', method or '?')
            if method == 'json_api':
                result = await self._check_flaresolverr(module)
            elif method == 'url_rewrite':
                result = await self._check_url_rewrite(module)
            else:
                self.logger.warning(
                    f"Webgate module '{module_name}' has unknown method "
                    f"'{method}', skipping"
                )
                attempts.append(f"{module_name}:unknown-method")
                continue
            body, status, err = result
            if err is None:
                return result
            last_error = err
            attempts.append(f"{module_name}:{err.type}")
            self.logger.info(
                f"Webgate module '{module_name}' failed for {self.url}: "
                f"{err.type}: {err.desc}. Trying next module if any."
            )
        # All modules failed. The most common case is "user opted into
        # cloudflare_bypass but the solver isn't running" — every per-module
        # attempt ends with "Webgate unreachable" (TCP refused / DNS fail at
        # the configured URL). Detect that case and emit a clear, actionable
        # message; fall back to a generic summary otherwise.
        primary = self._modules[0]
        primary_url = primary.get('url', '?')
        primary_method = primary.get('method', '?')
        start_hint = (
            "docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest"
            if primary_method == 'json_api'
            else "start the local proxy container"
        )
        all_unreachable = bool(attempts) and all(
            a.endswith(":Webgate unreachable") for a in attempts
        )
        if all_unreachable:
            desc = (
                "cloudflare_bypass is enabled (settings.json or "
                f"--cloudflare-bypass), but the configured solver at "
                f"{primary_url} is not reachable [{', '.join(attempts)}]. "
                f"Either start the solver ({start_hint}) or disable "
                "cloudflare_bypass in settings.json"
            )
        else:
            last_desc = last_error.desc if last_error else "unknown"
            desc = (
                f"all {len(self._modules)} module(s) failed "
                f"[{', '.join(attempts)}]. Last error: {last_desc}. "
                f"Is the solver running at {primary_url}? (hint: {start_hint})"
            )
        return None, 0, CheckError("Webgate unavailable", desc)

    async def _check_flaresolverr(
        self, module: Dict[str, Any]
    ) -> Tuple[Optional[str], int, Optional[CheckError]]:
        endpoint = module.get('url') or 'http://localhost:8191/v1'
        max_timeout_ms = int(module.get('max_timeout_ms', 60000))
        post_method = self.method.lower() == 'post'
        cmd = "request.post" if post_method else "request.get"

        body: Dict[str, Any] = {
            "cmd": cmd,
            "url": self.url,
            "maxTimeout": max_timeout_ms,
            "session": self.session_id,
        }

        proxy = module.get('proxy')
        if isinstance(proxy, str) and proxy:
            body["proxy"] = {"url": proxy}
        elif isinstance(proxy, dict) and proxy.get("url"):
            body["proxy"] = {k: v for k, v in proxy.items() if k in ("url", "username", "password")}

        if post_method and self.payload is not None:
            # FlareSolverr expects postData as urlencoded string for form data,
            # but if site.request_payload is JSON we still send it.
            body["postData"] = (
                "&".join(f"{k}={quote(str(v))}" for k, v in self.payload.items())
            )

        timeout = max(int(self.timeout) if self.timeout else 30, max_timeout_ms / 1000 + 5)

        try:
            async with ClientSession() as session:
                async with session.post(
                    endpoint, json=body, timeout=timeout
                ) as resp:
                    if resp.status >= 500:
                        return None, 0, CheckError(
                            "Webgate", f"FlareSolverr {resp.status}"
                        )
                    data = await resp.json()
        except (ClientConnectorError, ServerDisconnectedError) as e:
            return None, 0, CheckError("Webgate unreachable", str(e))
        except asyncio.TimeoutError:
            return None, 0, CheckError("Webgate timeout", endpoint)
        except Exception as e:
            self.logger.debug(e, exc_info=True)
            return None, 0, CheckError("Webgate", str(e))

        if data.get("status") != "ok":
            return None, 0, CheckError("Webgate", data.get("message", "unknown"))

        solution = data.get("solution") or {}
        upstream_status = int(solution.get("status") or 0)
        response_text = solution.get("response") or ""

        # Diagnostic: warn if FlareSolverr returned the CF challenge page
        # itself (challenge not fully solved) rather than the real content.
        # When this happens with sites that have weak presenseStrs/absenceStrs,
        # maigret's default-true presence rule produces false CLAIMED.
        cf_markers = ("Just a moment", "_cf_chl_opt", "cf-mitigated", "challenges.cloudflare.com")
        if response_text and any(m in response_text for m in cf_markers):
            self.logger.warning(
                f"Webgate response from {self.url} still contains CF challenge "
                f"markers (status={upstream_status}, body={len(response_text)}b). "
                f"FlareSolverr likely did not solve the challenge — site checks "
                f"with weak markers may produce false CLAIMED."
            )

        self.logger.info(
            f"Webgate response: url={self.url} status={upstream_status} "
            f"body_len={len(response_text)}"
        )
        return response_text, upstream_status, None

    async def _check_url_rewrite(
        self, module: Dict[str, Any]
    ) -> Tuple[Optional[str], int, Optional[CheckError]]:
        url_template = module.get('url') or ''
        if "{url}" not in url_template:
            return None, 0, CheckError(
                "Webgate", f"module '{module.get('name')}' url has no {{url}} placeholder"
            )
        from urllib.parse import quote_plus

        proxy_url = url_template.format(url=quote_plus(self.url))
        timeout = self.timeout if self.timeout else 30
        try:
            async with ClientSession() as session:
                async with session.get(proxy_url, timeout=timeout) as resp:
                    if resp.status >= 500:
                        return None, 0, CheckError(
                            "Webgate", f"url_rewrite proxy {resp.status}"
                        )
                    body = await resp.text()
        except (ClientConnectorError, ServerDisconnectedError) as e:
            return None, 0, CheckError("Webgate unreachable", str(e))
        except asyncio.TimeoutError:
            return None, 0, CheckError("Webgate timeout", proxy_url)
        except Exception as e:
            self.logger.debug(e, exc_info=True)
            return None, 0, CheckError("Webgate", str(e))

        # url_rewrite mode CANNOT recover the upstream HTTP status.
        # We assume 200 when HTML is returned; status_code/response_url
        # check types will misfire (see docs).
        return body, 200, None


class CheckerMock:
    def __init__(self, *args, **kwargs):
        pass

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        return None

    async def check(self) -> Tuple[Optional[str], int, Optional[CheckError]]:
        await asyncio.sleep(0)
        return '', 0, None

    async def close(self):
        return


def make_protocol_checker(options: Dict[str, Any], protocol: str):
    checker_factory = options["checkers"][protocol]
    if callable(checker_factory):
        return checker_factory()
    return checker_factory


def debug_response_logging(url, html_text, status_code, check_error):
    with open("debug.log", "a") as f:
        status = status_code or "No response"
        f.write(f"url: {url}\nerror: {check_error}\nr: {status}\n")
        if html_text:
            f.write(f"code: {status}\nresponse: {str(html_text)}\n")


def process_site_result(
    response, query_notify, logger, results_info: SiteResult, site: MaigretSite
):
    if not response:
        return results_info

    fulltags = site.tags

    # Retrieve other site information again
    username = results_info["username"]
    is_parsing_enabled = results_info["parsing_enabled"]
    url = results_info.get("url_user")
    url_probe = results_info.get("url_probe") or url
    if url_probe != url:
        logger.info(f"{url_probe} (display: {url})")
    else:
        logger.info(url)

    status = results_info.get("status")
    if status is not None:
        # We have already determined the user doesn't exist here
        return results_info

    # Get the expected check type
    check_type = site.check_type

    html_text, status_code, check_error = response

    response_time = None

    if logger.level == logging.DEBUG:
        debug_response_logging(url, html_text, status_code, check_error)

    # additional check for errors
    if status_code and not check_error:
        check_error = detect_error_page(
            html_text,
            status_code,
            site.errors_dict,
            site.ignore403,
        )

    site_name = site.pretty_name
    # presence flags
    # True by default
    presense_flags = site.presense_strs
    is_presense_detected = False

    if html_text:
        if not presense_flags:
            if check_type == "message" and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Site %s uses checkType message with empty presenseStrs; "
                    "presence is treated as true for any page.",
                    site.name,
                )
            is_presense_detected = True
            site.stats["presense_flag"] = None
        else:
            for presense_flag in presense_flags:
                if presense_flag in html_text:
                    is_presense_detected = True
                    site.stats["presense_flag"] = presense_flag
                    logger.debug(presense_flag)
                    break


    # Keyword detection logic
    keywords = results_info.get("keywords", [])
    keyword_match_status = None
    
    if keywords and html_text:
        keywords_found = []
        for keyword in keywords:
            if keyword.lower() in html_text.lower():
                keywords_found.append(keyword)
        
        if keywords_found:
            keyword_match_status = KeywordMatchStatus.KEYWORD_FOUND
            logger.debug(f"Keywords found in {site.name}: {keywords_found}")
        else:
            keyword_match_status = KeywordMatchStatus.KEYWORDS_NOT_FOUND
            logger.debug(f"No keywords found in {site.name}")
    else:
        keyword_match_status = KeywordMatchStatus.NO_KEYWORDS

    def build_result(status, **kwargs):
        return MaigretCheckResult(
            username,
            site_name,
            url,
            status,
            query_time=response_time,
            tags=fulltags,
            keywords=keywords,
            keyword_match_status=keyword_match_status,
            **kwargs,
        )

    if check_error:
        logger.warning(check_error)
        result = build_result(
            MaigretCheckStatus.UNKNOWN,
            error=check_error,
            context=str(check_error),
        )
    elif check_type == "message":
        # Checks if the error message is in the HTML
        is_absence_detected = any(
            [(absence_flag in html_text) for absence_flag in site.absence_strs]
        )
        if not is_absence_detected and is_presense_detected:
            result = build_result(MaigretCheckStatus.CLAIMED)
        else:
            result = build_result(MaigretCheckStatus.AVAILABLE)
    elif check_type == "status_code":
        # Checks if the status code of the response is 2XX
        if 200 <= status_code < 300:
            result = build_result(MaigretCheckStatus.CLAIMED)
        else:
            result = build_result(MaigretCheckStatus.AVAILABLE)
    elif check_type == "response_url":
        # For this detection method, we have turned off the redirect.
        # So, there is no need to check the response URL: it will always
        # match the request.  Instead, we will ensure that the response
        # code indicates that the request was successful (i.e. no 404, or
        # forward to some odd redirect).
        if 200 <= status_code < 300 and is_presense_detected:
            result = build_result(MaigretCheckStatus.CLAIMED)
        else:
            result = build_result(MaigretCheckStatus.AVAILABLE)
    else:
        # It should be impossible to ever get here...
        raise ValueError(
            f"Unknown check type '{check_type}' for " f"site '{site.name}'"
        )

    extracted_ids_data = {}

    if is_parsing_enabled and result.status == MaigretCheckStatus.CLAIMED:
        extracted_ids_data = extract_ids_data(html_text, logger, site)
        if extracted_ids_data:
            new_usernames = parse_usernames(extracted_ids_data, logger)
            results_info = update_results_info(
                results_info, extracted_ids_data, new_usernames
            )
            result.ids_data = extracted_ids_data

    # Save status of request
    results_info["status"] = result

    # Save results from request
    results_info["http_status"] = status_code
    results_info["is_similar"] = site.similar_search
    # results_site['response_text'] = html_text
    results_info["rank"] = site.alexa_rank
    return results_info


def make_site_result(
    site: MaigretSite, username: str, options: Dict[str, Any], logger, *args, **kwargs
) -> SiteResult:
    results_site: SiteResult = {}

    # Record URL of main site and username
    results_site["site"] = site
    results_site["username"] = username
    results_site["keywords"] = kwargs.get('keywords', [])
    results_site["parsing_enabled"] = options["parsing"]
    results_site["url_main"] = site.url_main
    results_site["cookies"] = (
        options.get("cookie_jar")
        and options["cookie_jar"].filter_cookies(site.url_main)
        or None
    )

    headers = {
        "User-Agent": get_random_user_agent(),
        # tell server that we want to close connection after request
        "Connection": "close",
    }

    headers.update(site.headers)

    if "url" not in site.__dict__:
        logger.error("No URL for site %s", site.name)

    if kwargs.get('retry') and hasattr(site, "mirrors"):
        site.url_main = random.choice(site.mirrors)
        logger.info(f"Use {site.url_main} as a main url of site {site}")

    # URL of user on site (if it exists)
    url = site.url.format(
        urlMain=site.url_main, urlSubpath=site.url_subpath, username=quote(username)
    )

    # workaround to prevent slash errors
    url = re.sub("(?<!:)/+", "/", url)

    # Select checker. Order of precedence:
    # 1. Cloudflare webgate (FlareSolverr / CloudflareBypassForScraping) when
    #    bypass is active and site.protection requests it.
    # 2. curl_cffi for sites requiring TLS impersonation.
    # 3. Default protocol-specific checker (aiohttp).
    cf_bypass = options.get("cloudflare_bypass")
    needs_webgate = bool(cf_bypass) and any(
        p in cf_bypass["trigger_protection"] for p in site.protection
    )
    needs_impersonation = 'tls_fingerprint' in site.protection

    if needs_webgate:
        checker = CloudflareWebgateChecker(logger=logger, config=cf_bypass)
        logger.info(
            f"Using Cloudflare webgate for {site.name} "
            f"(protection: {list(site.protection)})"
        )
    elif needs_impersonation:
        checker = CurlCffiChecker(
            logger=logger,
            browser_emulate='chrome',
            proxy=options.get('proxy'),
        )
    else:
        checker = make_protocol_checker(options, site.protocol)

    # site check is disabled
    if site.disabled and not options['forced']:
        logger.debug(f"Site {site.name} is disabled, skipping...")
        results_site["status"] = MaigretCheckResult(
            username,
            site.name,
            url,
            MaigretCheckStatus.ILLEGAL,
            error=CheckError("Check is disabled"),
        )
    # current username type could not be applied
    elif site.type != options["id_type"]:
        results_site["status"] = MaigretCheckResult(
            username,
            site.name,
            url,
            MaigretCheckStatus.ILLEGAL,
            error=CheckError('Unsupported identifier type', f'Want "{site.type}"'),
        )
    # username is not allowed.
    elif site.regex_check and re.search(site.regex_check, username) is None:
        results_site["status"] = MaigretCheckResult(
            username,
            site.name,
            url,
            MaigretCheckStatus.ILLEGAL,
            error=CheckError(
                'Unsupported username format', f'Want "{site.regex_check}"'
            ),
        )
        results_site["url_user"] = ""
        results_site["http_status"] = ""
        results_site["response_text"] = ""
        # query_notify.update(results_site["status"])
    else:
        # URL of user on site (if it exists)
        results_site["url_user"] = url
        url_probe = site.url_probe
        if url_probe is None:
            # Probe URL is normal one seen by people out on the web.
            url_probe = url
        else:
            # There is a special URL for probing existence separate
            # from where the user profile normally can be found.
            url_probe = url_probe.format(
                urlMain=site.url_main,
                urlSubpath=site.url_subpath,
                username=username,
            )

        for k, v in site.get_params.items():
            url_probe += f"&{k}={v}"

        results_site["url_probe"] = url_probe

        if site.request_method:
            request_method = site.request_method.lower()
        elif site.check_type == "status_code" and site.request_head_only:
            # In most cases when we are detecting by status code,
            # it is not necessary to get the entire body:  we can
            # detect fine with just the HEAD response.
            request_method = 'head'
        else:
            # Either this detect method needs the content associated
            # with the GET response, or this specific website will
            # not respond properly unless we request the whole page.
            request_method = 'get'

        payload = None
        if site.request_payload:
            payload = {}
            for k, v in site.request_payload.items():
                if isinstance(v, str):
                    payload[k] = v.format(username=username)
                else:
                    payload[k] = v

        if site.check_type == "response_url":
            # Site forwards request to a different URL if username not
            # found.  Disallow the redirect so we can capture the
            # http status from the original URL request.
            allow_redirects = False
        else:
            # Allow whatever redirect that the site wants to do.
            # The final result of the request will be what is available.
            allow_redirects = True

        future = checker.prepare(
            method=request_method,
            url=url_probe,
            headers=headers,
            allow_redirects=allow_redirects,
            timeout=options['timeout'],
            payload=payload,
        )

        # Store future request object in the results object
        results_site["future"] = future

    results_site["checker"] = checker

    return results_site


async def check_site_for_username(
    site, username, options: Dict[str, Any], logger, query_notify, *args, **kwargs
) -> Tuple[str, SiteResult]:
    keywords = kwargs.get('keywords')
    default_result = make_site_result(
        site, username, options, logger, retry=kwargs.get('retry'), keywords=keywords
    )
    # future = default_result.get("future")
    # if not future:
    # return site.name, default_result

    checker = default_result.get("checker")
    if not checker:
        print(f"error, no checker for {site.name}")
        return site.name, default_result

    response = await checker.check()
    html_text = response[0] if response and response[0] else ""

    # Retry once after token-style activation (e.g. Twitter guest token refresh).
    act = site.activation
    if act and html_text:
        marks = act.get("marks") or []
        if marks and any(m in html_text for m in marks):
            method = act["method"]
            try:
                activate_fun = getattr(ParsingActivator(), method)
                await activate_fun(
                    site,
                    logger,
                    url=checker.url,
                    timeout=options['timeout'],
                )
            except AttributeError:
                logger.warning(
                    f"Activation method {method} for site {site.name} not found!",
                    exc_info=True,
                )
            except Exception as e:
                logger.warning(
                    f"Failed activation {method} for site {site.name}: {str(e)}",
                    exc_info=True,
                )
            else:
                merged = dict(checker.headers or {})
                merged.update(site.headers)
                checker.prepare(
                    url=checker.url,
                    headers=merged,
                    allow_redirects=checker.allow_redirects,
                    timeout=checker.timeout,
                    method=checker.method,
                    payload=getattr(checker, 'payload', None),
                )
                response = await checker.check()

    response_result = process_site_result(
        response, query_notify, logger, default_result, site
    )

    query_notify.update(response_result['status'], site.similar_search)

    return site.name, response_result


async def debug_ip_request(checker, logger):
    checker.prepare(url="https://icanhazip.com")
    ip, status, check_error = await checker.check()
    if ip:
        logger.debug(f"My IP is: {ip.strip()}")
    else:
        logger.debug(f"IP requesting {check_error.type}: {check_error.desc}")


def get_failed_sites(results: Dict[str, SiteResult]) -> List[str]:
    sites = []
    for sitename, r in results.items():
        status = r.get('status')
        if status and status.error:
            if errors.is_permanent(status.error.type):
                continue
            sites.append(sitename)
    return sites


async def maigret(
    username: str,
    site_dict: Dict[str, MaigretSite],
    logger,
    query_notify=None,
    proxy=None,
    tor_proxy=None,
    i2p_proxy=None,
    timeout=3,
    is_parsing_enabled=False,
    id_type="username",
    debug=False,
    forced=False,
    max_connections=100,
    no_progressbar=False,
    cookies=None,
    retries=0,
    check_domains=False,
    cloudflare_bypass: Optional[Dict[str, Any]] = None,
    keywords=None,
    dns_resolver: str = 'async',
    output_container: Optional[Dict[str, SiteResult]] = None,
    *args,
    **kwargs,
) -> Dict[str, SiteResult]:
    """Main search func

    Checks for existence of username on certain sites.

    Keyword Arguments:
    username               -- Username string will be used for search.
    site_dict              -- Dictionary containing sites data in MaigretSite objects.
    query_notify           -- Notifier object (e.g. QueryNotifyPrint) used to
                              report query progress and results.
    logger                 -- Standard Python logger object.
    timeout                -- Time in seconds to wait before timing out request.
                              Default is 3 seconds.
    is_parsing_enabled     -- Extract additional info from account pages.
    id_type                -- Type of username to search.
                              Default is 'username', see all supported here:
                              https://maigret.readthedocs.io/en/latest/supported-identifier-types.html
    max_connections        -- Maximum number of concurrent connections allowed.
                              Default is 100.
    no_progressbar         -- Displaying of ASCII progressbar during scanner.
    cookies                -- Filename of a cookie jar file to use for each request.
    keywords               -- List of keywords to search for in HTML content.
                              Default is None.
    *args, **kwargs        -- Additional arguments.

    Return Value:
    Dictionary containing results from report. Key of dictionary is the name
    of the social network site, and the value is another dictionary with
    the following keys:
        url_main:      URL of main site.
        url_user:      URL of user on site (if account exists).
        status:        QueryResult() object indicating results of test for
                       account existence.
        http_status:   HTTP status code of query which checked for existence on
                       site.
        response_text: Text that came back from request.  May be None if
                       there was an HTTP error when checking for existence.
    """

    # notify caller that we are starting the query.
    if not query_notify:
        query_notify = Mock()

    query_notify.start(username, id_type)

    cookie_jar = None
    if cookies:
        logger.debug(f"Using cookies jar file {cookies}")
        cookie_jar = import_aiohttp_cookies(cookies)

    def clearweb_checker():
        return SimpleAiohttpChecker(
            proxy=proxy, cookie_jar=cookie_jar, logger=logger, dns_resolver=dns_resolver
        )

    def tor_checker():
        if not tor_proxy:
            return CheckerMock()
        return ProxiedAiohttpChecker(  # type: ignore
            proxy=tor_proxy, cookie_jar=cookie_jar, logger=logger, dns_resolver=dns_resolver
        )

    def i2p_checker():
        if not i2p_proxy:
            return CheckerMock()
        return ProxiedAiohttpChecker(  # type: ignore
            proxy=i2p_proxy, cookie_jar=cookie_jar, logger=logger, dns_resolver=dns_resolver
        )

    def dns_checker():
        if not check_domains:
            return CheckerMock()
        return AiodnsDomainResolver(logger=logger)  # type: ignore

    if logger.level == logging.DEBUG:
        await debug_ip_request(clearweb_checker(), logger)

    # setup parallel executor
    executor = AsyncioQueueGeneratorExecutor(
        logger=logger,
        in_parallel=max_connections,
        timeout=timeout + 0.5,
        *args,
        **kwargs,
    )

    # make options objects for all the requests
    options: Dict[str, Any] = {}
    options["cookies"] = cookie_jar
    options["checkers"] = {
        '': clearweb_checker,
        'tor': tor_checker,
        'dns': dns_checker,
        'i2p': i2p_checker,
    }
    options["parsing"] = is_parsing_enabled
    options["timeout"] = timeout
    options["id_type"] = id_type
    options["forced"] = forced
    options["cloudflare_bypass"] = cloudflare_bypass
    options["proxy"] = proxy

    # results from analysis of all sites
    # When the caller wants to read partial results after a Ctrl+C
    # cancellation, they pass a dict; we mutate it in place so the partial
    # state remains visible after this coroutine raises CancelledError.
    all_results: Dict[str, SiteResult] = (
        output_container if output_container is not None else {}
    )

    sites = list(site_dict.keys())

    attempts = retries + 1
    while attempts:
        tasks_dict = {}

        for sitename, site in site_dict.items():
            if sitename not in sites:
                continue
            default_result: SiteResult = {
                'site': site,
                'status': MaigretCheckResult(
                    username,
                    sitename,
                    '',
                    MaigretCheckStatus.UNKNOWN,
                    error=CheckError('Request failed'),
                ),
            }
            tasks_dict[sitename] = (
                check_site_for_username,
                [site, username, options, logger, query_notify],
                {
                    'default': (sitename, default_result),
                    'retry': retries - attempts + 1,
                    'keywords': keywords,
                },
            )

        cur_results = []
        # ctrl_c=False is critical: alive_progress's default Ctrl+C handler
        # silently absorbs the first SIGINT (it draws a "⚠" mark on the bar
        # and keeps going), so the user has to press it twice. With
        # ctrl_c=False the signal propagates immediately to asyncio, which
        # cancels the main task — caught in maigret.maigret.main() as
        # CancelledError so the search loop falls through to report
        # generation. See issue: "ctrl+c needs two presses + traceback".
        try:
            with alive_bar(
                len(tasks_dict), title="Searching", force_tty=True,
                disable=no_progressbar, ctrl_c=False,
            ) as progress:
                async for result in executor.run(list(tasks_dict.values())):  # type: ignore[arg-type]
                    cur_results.append(result)
                    # `all_results` may be an output container supplied by
                    # the caller — flush each completed site check into it
                    # immediately, so partial progress survives a Ctrl+C
                    # cancellation (issue #2688 follow-up). dict.update
                    # accepts an iterable of (k, v) 2-tuples, which is what
                    # the executor yields, so this is equivalent to the
                    # post-loop update but visible to the caller mid-flight.
                    all_results.update([result])
                    progress()
        except asyncio.CancelledError:
            # Re-raise so the caller's `except CancelledError` runs. The
            # partial `all_results` is already visible to the caller via the
            # output_container kwarg.
            query_notify.finish()
            raise

        all_results.update(cur_results)

        # rerun for failed sites
        sites = get_failed_sites(dict(cur_results))
        attempts -= 1

        if not sites:
            break

        if attempts:
            query_notify.warning(
                f'Restarting checks for {len(sites)} sites... ({attempts} attempts left)'
            )

    # notify caller that all queries are finished
    query_notify.finish()

    return all_results


def timeout_check(value):
    """Check Timeout Argument.

    Checks timeout for validity.

    Keyword Arguments:
    value                  -- Time in seconds to wait before timing out request.

    Return Value:
    Floating point number representing the time (in seconds) that should be
    used for the timeout.

    NOTE:  Will raise an exception if the timeout in invalid.
    """
    from argparse import ArgumentTypeError

    try:
        timeout = float(value)
    except ValueError:
        raise ArgumentTypeError(f"Timeout '{value}' must be a number.")
    if timeout <= 0:
        raise ArgumentTypeError(f"Timeout '{value}' must be greater than 0.0s.")
    return timeout


async def site_self_check(
    site: MaigretSite,
    logger: logging.Logger,
    semaphore,
    db: MaigretDatabase,
    silent=False,
    proxy=None,
    tor_proxy=None,
    i2p_proxy=None,
    skip_errors=False,
    cookies=None,
    auto_disable=False,
    diagnose=False,
    cloudflare_bypass: Optional[Dict[str, Any]] = None,
):
    """
    Self-check a site configuration.

    Args:
        auto_disable: If True, automatically disable sites that fail checks.
                     If False (default), only report issues without disabling.
        diagnose: If True, print detailed diagnosis information.
    """
    changes: Dict[str, Any] = {
        "disabled": False,
        "issues": [],
        "recommendations": [],
    }

    try:
        check_data = [
            (site.username_claimed, MaigretCheckStatus.CLAIMED),
            (site.username_unclaimed, MaigretCheckStatus.AVAILABLE),
        ]

        logger.info(f"Checking {site.name}...")

        results_cache = {}

        for username, status in check_data:
            async with semaphore:
                results_dict = await maigret(
                    username=username,
                    site_dict={site.name: site},
                    logger=logger,
                    timeout=30,
                    id_type=site.type,
                    forced=True,
                    no_progressbar=True,
                    retries=1,
                    proxy=proxy,
                    tor_proxy=tor_proxy,
                    i2p_proxy=i2p_proxy,
                    cookies=cookies,
                    cloudflare_bypass=cloudflare_bypass,
                )

                # don't disable entries with other ids types
                if site.name not in results_dict:
                    logger.info(results_dict)
                    changes["issues"].append(f"Site {site.name} not in results (wrong id_type?)")
                    if auto_disable:
                        changes["disabled"] = True
                    continue

                logger.debug(results_dict)

                result = results_dict[site.name]["status"]
                results_cache[username] = results_dict[site.name]

            if result.error and 'Cannot connect to host' in result.error.desc:
                changes["issues"].append("Cannot connect to host")
                if auto_disable:
                    changes["disabled"] = True

            site_status = result.status

            if site_status != status:
                if site_status == MaigretCheckStatus.UNKNOWN:
                    msgs = site.absence_strs
                    etype = site.check_type
                    error_msg = f"Error checking {username}: {result.context}"
                    changes["issues"].append(error_msg)
                    logger.warning(
                        f"Error while searching {username} in {site.name}: {result.context}, {msgs}, type {etype}"
                    )
                    # don't disable sites after the error
                    # meaning that the site could be available, but returned error for the check
                    # e.g. many sites protected by cloudflare and available in general
                    if skip_errors:
                        pass
                    # don't disable in case of available username
                    elif status == MaigretCheckStatus.CLAIMED and auto_disable:
                        changes["disabled"] = True
                elif status == MaigretCheckStatus.CLAIMED:
                    changes["issues"].append(f"Claimed user '{username}' not detected as claimed")
                    logger.warning(
                        f"Not found `{username}` in {site.name}, must be claimed"
                    )
                    logger.info(results_dict[site.name])
                    if auto_disable:
                        changes["disabled"] = True
                else:
                    changes["issues"].append(f"Unclaimed user '{username}' detected as claimed")
                    logger.warning(f"Found `{username}` in {site.name}, must be available")
                    logger.info(results_dict[site.name])
                    if auto_disable:
                        changes["disabled"] = True

        logger.info(f"Site {site.name} checking is finished")

        # Generate recommendations based on issues
        if changes["issues"] and len(results_cache) == 2:
            claimed_result = results_cache.get(site.username_claimed, {})
            unclaimed_result = results_cache.get(site.username_unclaimed, {})

            claimed_http = claimed_result.get("http_status")
            unclaimed_http = unclaimed_result.get("http_status")

            if claimed_http and unclaimed_http:
                if claimed_http != unclaimed_http and site.check_type != "status_code":
                    changes["recommendations"].append(
                        f"Consider checkType: status_code (HTTP {claimed_http} vs {unclaimed_http})"
                    )

        # Print diagnosis if requested
        if diagnose and changes["issues"]:
            print(f"\n--- {site.name} DIAGNOSIS ---")
            print(f"  Check type: {site.check_type}")
            print("  Issues:")
            for issue in changes["issues"]:
                print(f"    - {issue}")
            if changes["recommendations"]:
                print("  Recommendations:")
                for rec in changes["recommendations"]:
                    print(f"    -> {rec}")

        # Only modify site if auto_disable is enabled
        if auto_disable and changes["disabled"] != site.disabled:
            site.disabled = changes["disabled"]
            logger.info(f"Switching property 'disabled' for {site.name} to {site.disabled}")
            db.update_site(site)
            if not silent:
                action = "Disabled" if site.disabled else "Enabled"
                print(f"{action} site {site.name}...")
        elif changes["issues"] and not silent and not diagnose:
            # Report issues without disabling
            print(f"Issues found in {site.name}: {len(changes['issues'])} (not auto-disabled)")

        # remove service tag "unchecked"
        if "unchecked" in site.tags:
            site.tags.remove("unchecked")
            db.update_site(site)

    except Exception as e:
        logger.warning(
            f"Self-check of {site.name} failed with unexpected error: {e}",
            exc_info=True,
        )
        changes["issues"].append(f"Unexpected error: {e}")
        if auto_disable and not site.disabled:
            changes["disabled"] = True
            site.disabled = True
            db.update_site(site)
            if not silent:
                print(f"Disabled site {site.name} (unexpected error)...")

    return changes


async def self_check(
    db: MaigretDatabase,
    site_data: dict,
    logger: logging.Logger,
    silent=False,
    max_connections=10,
    proxy=None,
    tor_proxy=None,
    i2p_proxy=None,
    auto_disable=False,
    diagnose=False,
    no_progressbar=False,
    cloudflare_bypass: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Run self-check on sites.

    Args:
        auto_disable: If True, automatically disable sites that fail checks.
                     If False (default), only report issues without disabling.
        diagnose: If True, print detailed diagnosis for each failing site.

    Returns:
        dict with 'needs_update' bool and 'results' list of check results
    """
    sem = asyncio.Semaphore(max_connections)
    tasks = []
    all_sites = site_data
    all_results = []

    def disabled_count(lst):
        return len(list(filter(lambda x: x.disabled, lst)))

    unchecked_old_count = len(
        [site for site in all_sites.values() if "unchecked" in site.tags]
    )
    disabled_old_count = disabled_count(all_sites.values())

    for _, site in all_sites.items():
        check_coro = site_self_check(
            site, logger, sem, db, silent, proxy, tor_proxy, i2p_proxy,
            skip_errors=True, auto_disable=auto_disable, diagnose=diagnose,
            cloudflare_bypass=cloudflare_bypass,
        )
        future = asyncio.ensure_future(check_coro)
        tasks.append((site.name, future))

    if tasks:
        with alive_bar(len(tasks), title='Self-checking', force_tty=True,
                       disable=no_progressbar, ctrl_c=False) as progress:
            for site_name, f in tasks:
                try:
                    result = await f
                except Exception as e:
                    logger.warning(
                        f"Self-check task for {site_name} raised unexpected error: {e}",
                        exc_info=True,
                    )
                    result = {
                        "disabled": False,
                        "issues": [f"Unexpected error: {e}"],
                        "recommendations": [],
                    }
                result['site_name'] = site_name
                all_results.append(result)
                progress()  # Update the progress bar

    unchecked_new_count = len(
        [site for site in all_sites.values() if "unchecked" in site.tags]
    )
    disabled_new_count = disabled_count(all_sites.values())
    total_disabled = disabled_new_count - disabled_old_count

    # Count issues
    total_issues = sum(1 for r in all_results if r.get('issues'))

    if auto_disable and total_disabled:
        if total_disabled >= 0:
            message = "Disabled"
        else:
            message = "Enabled"
            total_disabled *= -1

        if not silent:
            print(
                f"{message} {total_disabled} ({disabled_old_count} => {disabled_new_count}) checked sites. "
                "Run with `--info` flag to get more information"
            )
    elif total_issues and not silent:
        print(f"\nFound issues in {total_issues} sites (auto-disable is OFF)")
        print("Use --auto-disable to automatically disable failing sites")
        print("Use --diagnose to see detailed diagnosis for each site")

    if unchecked_new_count != unchecked_old_count:
        print(f"Unchecked sites verified: {unchecked_old_count - unchecked_new_count}")

    needs_update = total_disabled != 0 or unchecked_new_count != unchecked_old_count

    return {
        'needs_update': needs_update,
        'results': all_results,
        'total_issues': total_issues,
    }


def extract_ids_data(html_text, logger, site) -> Dict:
    try:
        return extract(html_text)
    except Exception as e:
        logger.warning(f"Error while parsing {site.name}: {e}", exc_info=True)
        return {}


def parse_usernames(extracted_ids_data, logger) -> Dict:
    new_usernames = {}
    for k, v in extracted_ids_data.items():
        if "username" in k and not "usernames" in k:
            if is_plausible_username(v):
                new_usernames[v] = "username"
            else:
                logger.debug(
                    f"Rejected non-username value extracted under key {k!r}: {v!r}"
                )
        elif "usernames" in k:
            try:
                tree = ast.literal_eval(v)
                if isinstance(tree, list):
                    for n in tree:
                        if is_plausible_username(n):
                            new_usernames[n] = "username"
                        else:
                            logger.debug(
                                f"Rejected non-username item from list under key {k!r}: {n!r}"
                            )
            except Exception as e:
                logger.warning(e)
        if k in SUPPORTED_IDS:
            new_usernames[v] = k
    return new_usernames


def update_results_info(results_info, extracted_ids_data, new_usernames):
    results_info["ids_usernames"] = new_usernames
    links = ascii_data_display(extracted_ids_data.get("links", "[]"))
    if "website" in extracted_ids_data:
        links.append(extracted_ids_data["website"])
    results_info["ids_links"] = links
    return results_info
