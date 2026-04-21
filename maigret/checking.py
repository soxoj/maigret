# Standard library imports
import ast
import asyncio
import logging
import random
import re
import ssl
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

# Third party imports
import aiodns
from alive_progress import alive_bar
from aiohttp import ClientSession, TCPConnector, http_exceptions
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError
from python_socks import _errors as proxy_errors
from socid_extractor import extract  # type: ignore[import-not-found]

try:
    from mock import Mock
except ImportError:
    from unittest.mock import Mock

# Local imports
from . import errors
from .activation import ParsingActivator, import_aiohttp_cookies
from .errors import CheckError
from .executors import AsyncioQueueGeneratorExecutor
from .result import MaigretCheckResult, MaigretCheckStatus
from .sites import MaigretDatabase, MaigretSite
from .types import QueryOptions, QueryResultWrapper
from .utils import ascii_data_display, get_random_user_agent


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
)

BAD_CHARS = "#"


class CheckerBase:
    pass


class SimpleAiohttpChecker(CheckerBase):
    def __init__(self, *args, **kwargs):
        self.proxy = kwargs.get('proxy')
        self.cookie_jar = kwargs.get('cookie_jar')
        self.logger = kwargs.get('logger', Mock())
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        self.payload = None

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
            return None, 0, CheckError("Connecting failure", str(e))
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

        connector = (
            ProxyConnector.from_url(self.proxy)
            if self.proxy
            else TCPConnector(ssl=ssl_context)
        )

        async with ClientSession(
            connector=connector,
            trust_env=True,
            # TODO: tests
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
    def __init__(self, *args, **kwargs):
        self.proxy = kwargs.get('proxy')
        self.cookie_jar = kwargs.get('cookie_jar')
        self.logger = kwargs.get('logger', Mock())


class AiodnsDomainResolver(CheckerBase):
    if sys.platform == 'win32':  # Temporary workaround for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def __init__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        self.logger = kwargs.get('logger', Mock())
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


try:
    from curl_cffi.requests import AsyncSession as CurlCffiAsyncSession

    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


class CurlCffiChecker(CheckerBase):
    """Checker using curl_cffi to emulate browser TLS fingerprint and bypass WAF."""

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', Mock())
        self.browser_emulate = kwargs.get('browser_emulate', 'chrome')
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        self.payload = None

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
            async with CurlCffiAsyncSession() as session:
                kwargs = {
                    'url': self.url,
                    'headers': self.headers,
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


# TODO: move to separate class
def detect_error_page(
    html_text, status_code, fail_flags, ignore_403
) -> Optional[CheckError]:
    # Detect service restrictions such as a country restriction
    for flag, msg in fail_flags.items():
        if flag in html_text:
            return CheckError("Site-specific", msg)

    # Detect common restrictions such as provider censorship and bot protection
    err = errors.detect(html_text)
    if err:
        return err

    # Detect common site errors
    if status_code == 403 and not ignore_403:
        return CheckError("Access denied", "403 status code, use proxy/vpn")

    elif status_code == 999:
        # LinkedIn anti-bot / HTTP 999 workaround. It shouldn't trigger an infrastructure
        # Server Error because it represents a valid "Not Found / Blocked" state for the username.
        pass

    elif status_code >= 500:
        return CheckError("Server", f"{status_code} status code")

    return None


def debug_response_logging(url, html_text, status_code, check_error):
    with open("debug.log", "a") as f:
        status = status_code or "No response"
        f.write(f"url: {url}\nerror: {check_error}\nr: {status}\n")
        if html_text:
            f.write(f"code: {status}\nresponse: {str(html_text)}\n")


def process_site_result(
    response,
    query_notify,
    logger,
    results_info: QueryResultWrapper,
    site: MaigretSite,
    response_time: Optional[float] = None,
):
    if not response:
        return results_info

    fulltags = site.tags

    # Retrieve other site information again
    username = results_info["username"]
    is_parsing_enabled = results_info["parsing_enabled"]
    url = results_info.get("url_user")
    logger.info(url)

    status = results_info.get("status")
    if status is not None:
        # We have already determined the user doesn't exist here
        return results_info

    # Get the expected check type
    check_type = site.check_type

    # TODO: refactor
    if not response:
        logger.error(f"No response for {site.name}")
        return results_info

    html_text, status_code, check_error = response

    if logger.level == logging.DEBUG:
        debug_response_logging(url, html_text, status_code, check_error)

    # additional check for errors
    if status_code and not check_error:
        check_error = detect_error_page(
            html_text, status_code, site.errors_dict, site.ignore403
        )

    # parsing activation
    is_need_activation = any(
        [s for s in site.activation.get("marks", []) if s in html_text]
    )

    if site.activation and html_text and is_need_activation:
        logger.debug(f"Activation for {site.name}")
        method = site.activation["method"]
        try:
            activate_fun = getattr(ParsingActivator(), method)
            # TODO: async call
            activate_fun(site, logger)
        except AttributeError as e:
            logger.warning(
                f"Activation method {method} for site {site.name} not found!",
                exc_info=True,
            )
        except Exception as e:
            logger.warning(
                f"Failed activation {method} for site {site.name}: {str(e)}",
                exc_info=True,
            )
        # TODO: temporary check error

    site_name = site.pretty_name
    # presense flags
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

    def build_result(status, **kwargs):
        return MaigretCheckResult(
            username,
            site_name,
            url,
            status,
            query_time=response_time,
            tags=fulltags,
            **kwargs,
        )

    if check_error:
        logger.warning(check_error)
        result = MaigretCheckResult(
            username,
            site_name,
            url,
            MaigretCheckStatus.UNKNOWN,
            query_time=response_time,
            error=check_error,
            context=str(CheckError),
            tags=fulltags,
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
    site: MaigretSite, username: str, options: QueryOptions, logger, *args, **kwargs
) -> QueryResultWrapper:
    results_site: QueryResultWrapper = {}

    # Record URL of main site and username
    results_site["site"] = site
    results_site["username"] = username
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

    # Select checker: use curl_cffi for sites requiring TLS impersonation
    needs_impersonation = 'tls_fingerprint' in site.protection
    if needs_impersonation and CURL_CFFI_AVAILABLE:
        checker = CurlCffiChecker(logger=logger, browser_emulate='chrome')
    elif needs_impersonation and not CURL_CFFI_AVAILABLE:
        logger.warning(
            f"Site {site.name} requires TLS impersonation (curl_cffi) but it's not installed. "
            "Install with: pip install curl_cffi"
        )
        checker = options["checkers"][site.protocol]
    else:
        checker = options["checkers"][site.protocol]

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
    site, username, options: QueryOptions, logger, query_notify, *args, **kwargs
) -> Tuple[str, QueryResultWrapper]:
    default_result = make_site_result(
        site, username, options, logger, retry=kwargs.get('retry')
    )
    # future = default_result.get("future")
    # if not future:
    # return site.name, default_result

    checker = default_result.get("checker")
    if not checker:
        print(f"error, no checker for {site.name}")
        return site.name, default_result

    elapsed = 0.0
    t0 = time.perf_counter()
    response = await checker.check()
    elapsed += time.perf_counter() - t0
    html_text = response[0] if response and response[0] else ""

    # Retry once after token-style activation (e.g. Twitter guest token refresh).
    act = site.activation
    if act and html_text:
        marks = act.get("marks") or []
        if marks and any(m in html_text for m in marks):
            method = act["method"]
            try:
                activate_fun = getattr(ParsingActivator(), method)
                activate_fun(site, logger)
            except AttributeError as e:
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
                t1 = time.perf_counter()
                response = await checker.check()
                elapsed += time.perf_counter() - t1

    response_result = process_site_result(
        response, query_notify, logger, default_result, site,
        response_time=elapsed,
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


def get_failed_sites(results: Dict[str, QueryResultWrapper]) -> List[str]:
    sites = []
    for sitename, r in results.items():
        status = r.get('status', {})
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
    *args,
    **kwargs,
) -> QueryResultWrapper:
    """Main search func

    Checks for existence of username on certain sites.

    Keyword Arguments:
    username               -- Username string will be used for search.
    site_dict              -- Dictionary containing sites data in MaigretSite objects.
    query_notify           -- Object with base type of QueryNotify().
                              This will be used to notify the caller about
                              query results.
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

    clearweb_checker = SimpleAiohttpChecker(
        proxy=proxy, cookie_jar=cookie_jar, logger=logger
    )

    # TODO
    tor_checker = CheckerMock()
    if tor_proxy:
        tor_checker = ProxiedAiohttpChecker(  # type: ignore
            proxy=tor_proxy, cookie_jar=cookie_jar, logger=logger
        )

    # TODO
    i2p_checker = CheckerMock()
    if i2p_proxy:
        i2p_checker = ProxiedAiohttpChecker(  # type: ignore
            proxy=i2p_proxy, cookie_jar=cookie_jar, logger=logger
        )

    # TODO
    dns_checker = CheckerMock()
    if check_domains:
        dns_checker = AiodnsDomainResolver(logger=logger)  # type: ignore

    if logger.level == logging.DEBUG:
        await debug_ip_request(clearweb_checker, logger)

    # setup parallel executor
    executor = AsyncioQueueGeneratorExecutor(
        logger=logger,
        in_parallel=max_connections,
        timeout=timeout + 0.5,
        *args,
        **kwargs,
    )

    # make options objects for all the requests
    options: QueryOptions = {}
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

    # results from analysis of all sites
    all_results: Dict[str, QueryResultWrapper] = {}

    sites = list(site_dict.keys())

    attempts = retries + 1
    while attempts:
        tasks_dict = {}

        for sitename, site in site_dict.items():
            if sitename not in sites:
                continue
            default_result: QueryResultWrapper = {
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
                },
            )

        cur_results = []
        with alive_bar(
            len(tasks_dict), title="Searching", force_tty=True, disable=no_progressbar
        ) as progress:
            async for result in executor.run(list(tasks_dict.values())):  # type: ignore[arg-type]
                cur_results.append(result)
                progress()

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

    # closing http client session
    await clearweb_checker.close()
    await tor_checker.close()
    await i2p_checker.close()

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
                )

                # don't disable entries with other ids types
                # TODO: make normal checking
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
            skip_errors=True, auto_disable=auto_disable, diagnose=diagnose
        )
        future = asyncio.ensure_future(check_coro)
        tasks.append((site.name, future))

    if tasks:
        with alive_bar(len(tasks), title='Self-checking', force_tty=True, disable=no_progressbar) as progress:
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
            new_usernames[v] = "username"
        elif "usernames" in k:
            try:
                tree = ast.literal_eval(v)
                if isinstance(tree, list):
                    for n in tree:
                        new_usernames[n] = "username"
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
