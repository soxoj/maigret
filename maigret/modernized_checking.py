"""
Modernized checking module for Maigret.
This is an optimized version of the original checking.py that uses the improved
HTTP client and executor implementations.
"""

# Standard library imports
import ast
import asyncio
import logging
import random
import re
import ssl
import sys
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import quote

# Third party imports
import aiodns
from alive_progress import alive_bar
from aiohttp import ClientSession, TCPConnector, http_exceptions
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError
from python_socks import _errors as proxy_errors
from socid_extractor import extract

try:
    from mock import Mock
except ImportError:
    from unittest.mock import Mock

# Local imports
from . import errors
from .activation import ParsingActivator, import_aiohttp_cookies
from .errors import CheckError
from .http_checker_wrapper import get_http_checker, close_http_checkers
from .optimized_executor import OptimizedExecutor, DynamicPriorityExecutor
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


# TODO: move to separate class
def detect_error_page(
    html_text, status_code, fail_flags, ignore_403
) -> Optional[CheckError]:
    """
    Detect error pages and site-specific restrictions.
    
    Args:
        html_text: HTML content from response
        status_code: HTTP status code
        fail_flags: Site-specific failure flags
        ignore_403: Whether to ignore 403 status code
        
    Returns:
        CheckError or None if no error detected
    """
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

    elif status_code >= 500:
        return CheckError("Server", f"{status_code} status code")

    return None


def debug_response_logging(url, html_text, status_code, check_error):
    """
    Log debug information about a response.
    
    Args:
        url: Request URL
        html_text: Response content
        status_code: HTTP status code
        check_error: Error if any
    """
    with open("debug.log", "a") as f:
        status = status_code or "No response"
        f.write(f"url: {url}\nerror: {check_error}\nr: {status}\n")
        if html_text:
            f.write(f"code: {status}\nresponse: {str(html_text)}\n")


def process_site_result(
    response, query_notify, logger, results_info: QueryResultWrapper, site: MaigretSite
):
    """
    Process the response from a site check.
    
    Args:
        response: Site check response (text, status, error)
        query_notify: Notification object
        logger: Logger instance
        results_info: Results information
        site: Site being checked
        
    Returns:
        Updated results information
    """
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

    # TODO: add elapsed request time counting
    response_time = None

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
    elif check_type in "status_code":
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
    """
    Prepare the result object for a site check.
    
    Args:
        site: Site to check
        username: Username to check
        options: Check options
        logger: Logger instance
        
    Returns:
        Result wrapper object
    """
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

    # Get appropriate checker from options
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

        if site.check_type == "status_code" and site.request_head_only:
            # In most cases when we are detecting by status code,
            # it is not necessary to get the entire body:  we can
            # detect fine with just the HEAD response.
            request_method = 'head'
        else:
            # Either this detect method needs the content associated
            # with the GET response, or this specific website will
            # not respond properly unless we request the whole page.
            request_method = 'get'

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
        )

        # Store future request object in the results object
        results_site["future"] = future

    results_site["checker"] = checker

    return results_site


async def check_site_for_username(
    site, username, options: QueryOptions, logger, query_notify, *args, **kwargs
) -> Tuple[str, QueryResultWrapper]:
    """
    Check a site for a username.
    
    Args:
        site: Site to check
        username: Username to check
        options: Check options
        logger: Logger instance
        query_notify: Notification object
        
    Returns:
        Tuple of (site name, result)
    """
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

    response = await checker.check()

    response_result = process_site_result(
        response, query_notify, logger, default_result, site
    )

    query_notify.update(response_result['status'], site.similar_search)

    return site.name, response_result


async def debug_ip_request(checker, logger):
    """
    Make a request to check the current IP.
    
    Args:
        checker: HTTP checker
        logger: Logger instance
    """
    checker.prepare(url="https://icanhazip.com")
    ip, status, check_error = await checker.check()
    if ip:
        logger.debug(f"My IP is: {ip.strip()}")
    else:
        logger.debug(f"IP requesting {check_error.type}: {check_error.desc}")


def get_failed_sites(results: Dict[str, QueryResultWrapper]) -> List[str]:
    """
    Get a list of sites that failed to check.
    
    Args:
        results: Check results
        
    Returns:
        List of failed site names
    """
    sites = []
    for sitename, r in results.items():
        status = r.get('status', {})
        if status and status.error:
            if errors.is_permanent(status.error.type):
                continue
            sites.append(sitename)
    return sites


async def modernized_maigret(
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
    use_dynamic_executor=True,
    *args,
    **kwargs,
) -> QueryResultWrapper:
    """
    Modernized main search function.
    Checks for existence of username on certain sites using optimized components.
    
    Args:
        username: Username to check
        site_dict: Dictionary of sites to check
        logger: Logger instance
        query_notify: Notification object
        proxy: HTTP proxy
        tor_proxy: Tor proxy
        i2p_proxy: I2P proxy
        timeout: Request timeout
        is_parsing_enabled: Whether to parse profile pages
        id_type: Type of identifier to check
        debug: Enable debug mode
        forced: Force checking disabled sites
        max_connections: Maximum concurrent connections
        no_progressbar: Disable progress bar
        cookies: Cookie jar file
        retries: Number of retries for failed checks
        check_domains: Check domain availability
        use_dynamic_executor: Use the dynamic priority executor
        
    Returns:
        Dictionary of results
    """
    # notify caller that we are starting the query.
    if not query_notify:
        query_notify = Mock()

    query_notify.start(username, id_type)

    cookie_jar = None
    if cookies:
        logger.debug(f"Using cookies jar file {cookies}")
        cookie_jar = import_aiohttp_cookies(cookies)

    # Create optimized checkers
    clearweb_checker = get_http_checker(
        "simple", proxy=proxy, cookie_jar=cookie_jar, logger=logger
    )
    
    tor_checker = get_http_checker("mock", logger=logger)
    if tor_proxy:
        tor_checker = get_http_checker(
            "proxied", proxy=tor_proxy, cookie_jar=cookie_jar, logger=logger
        )
    
    i2p_checker = get_http_checker("mock", logger=logger)
    if i2p_proxy:
        i2p_checker = get_http_checker(
            "proxied", proxy=i2p_proxy, cookie_jar=cookie_jar, logger=logger
        )
    
    dns_checker = get_http_checker("mock", logger=logger)
    if check_domains:
        dns_checker = get_http_checker("dns", logger=logger)

    if logger.level == logging.DEBUG:
        await debug_ip_request(clearweb_checker, logger)

    # setup optimized executor
    executor_class = DynamicPriorityExecutor if use_dynamic_executor else OptimizedExecutor
    
    # Create a simple progress function to avoid nested progress bars
    def simple_progress_func(total, **kwargs):
        class SimpleProgress:
            def __init__(self, total):
                self.total = total
                self.current = 0
                
            def __enter__(self):
                return self
                
            def __exit__(self, *args):
                pass
                
            def __call__(self, n=1):
                self.current += n
                logger.debug(f"Progress: {self.current}/{self.total}")
        
        return SimpleProgress(total)
    
    executor = executor_class(
        logger=logger,
        in_parallel=max_connections,
        timeout=timeout + 0.5,
        progress_func=simple_progress_func,
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
            # Run all tasks and get results
            results = await executor.run(list(tasks_dict.values()))
            for result in results:
                if result is not None:
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
    await close_http_checkers()

    # notify caller that all queries are finished
    query_notify.finish()

    return all_results


def extract_ids_data(html_text, logger, site) -> Dict:
    """
    Extract IDs from HTML content.
    
    Args:
        html_text: HTML content
        logger: Logger instance
        site: Site being checked
        
    Returns:
        Dictionary of extracted IDs
    """
    try:
        return extract(html_text)
    except Exception as e:
        logger.warning(f"Error while parsing {site.name}: {e}", exc_info=True)
        return {}


def parse_usernames(extracted_ids_data, logger) -> Dict:
    """
    Parse usernames from extracted IDs.
    
    Args:
        extracted_ids_data: Dictionary of extracted IDs
        logger: Logger instance
        
    Returns:
        Dictionary of usernames
    """
    new_usernames = {}
    for k, v in extracted_ids_data.items():
        if "username" in k and not "usernames" in k:
            new_usernames[v] = "username"
        elif "usernames" in k:
            try:
                tree = ast.literal_eval(v)
                if type(tree) == list:
                    for n in tree:
                        new_usernames[n] = "username"
            except Exception as e:
                logger.warning(e)
        if k in SUPPORTED_IDS:
            new_usernames[v] = k
    return new_usernames


def update_results_info(results_info, extracted_ids_data, new_usernames):
    """
    Update results with extracted IDs information.
    
    Args:
        results_info: Results information
        extracted_ids_data: Dictionary of extracted IDs
        new_usernames: Dictionary of usernames
        
    Returns:
        Updated results information
    """
    results_info["ids_usernames"] = new_usernames
    links = ascii_data_display(extracted_ids_data.get("links", "[]"))
    if "website" in extracted_ids_data:
        links.append(extracted_ids_data["website"])
    results_info["ids_links"] = links
    return results_info