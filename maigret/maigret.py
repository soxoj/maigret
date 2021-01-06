"""
Maigret main module
"""

import asyncio
import csv
import http.cookiejar as cookielib
import json
import logging
import os
import platform
import re
import ssl
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from http.cookies import SimpleCookie

import aiohttp
from aiohttp_socks import ProxyConnector
from python_socks import _errors as proxy_errors
import requests
import tqdm.asyncio
from mock import Mock
from socid_extractor import parse, extract

from .notify import QueryNotifyPrint
from .result import QueryResult, QueryStatus
from .sites import MaigretDatabase, MaigretSite
from .report import save_csv_report, genxmindfile

import xmind

__version__ = '0.1.8'

supported_recursive_search_ids = (
    'yandex_public_id',
    'gaia_id',
    'vk_id',
    'ok_id',
    'wikimapia_uid',
)

common_errors = {
    '<title>Attention Required! | Cloudflare</title>': 'Cloudflare captcha',
    'Please stand by, while we are checking your browser': 'Cloudflare captcha',
    '<title>Доступ ограничен</title>': 'Rostelecom censorship',
    'document.getElementById(\'validate_form_submit\').disabled=true': 'Mail.ru captcha',
    'Verifying your browser, please wait...<br>DDoS Protection by</font> Blazingfast.io': 'Blazingfast protection',
    '404</h1><p class="error-card__description">Мы&nbsp;не&nbsp;нашли страницу': 'MegaFon 404 page',
    'Доступ к информационному ресурсу ограничен на основании Федерального закона': 'MGTS censorship',
    'Incapsula incident ID': 'Incapsula antibot protection',
}

unsupported_characters = '#'

cookies_file = 'cookies.txt'


async def get_response(request_future, site_name, logger):
    html_text = None
    status_code = 0

    error_text = "General Unknown Error"
    expection_text = None

    try:
        response = await request_future

        status_code = response.status
        response_content = await response.content.read()
        charset = response.charset or 'utf-8'
        decoded_content = response_content.decode(charset, 'ignore')
        html_text = decoded_content

        if status_code > 0:
            error_text = None

        logger.debug(html_text)

    except asyncio.TimeoutError as errt:
        error_text = "Timeout Error"
        expection_text = str(errt)
    except (ssl.SSLCertVerificationError, ssl.SSLError) as err:
        error_text = "SSL Error"
        expection_text = str(err)
    except aiohttp.client_exceptions.ClientConnectorError as err:
        error_text = "Error Connecting"
        expection_text = str(err)
    except aiohttp.http_exceptions.BadHttpMessage as err:
        error_text = "HTTP Error"
        expection_text = str(err)
    except proxy_errors.ProxyError as err:
        error_text = "Proxy Error"
        expection_text = str(err)
    except Exception as err:
        logger.warning(f'Unhandled error while requesting {site_name}: {err}')
        logger.debug(err, exc_info=True)
        error_text = "Some Error"
        expection_text = str(err)

    # TODO: return only needed information
    return html_text, status_code, error_text, expection_text


async def update_site_dict_from_response(sitename, site_dict, results_info, semaphore, logger, query_notify):
    async with semaphore:
        site_obj = site_dict[sitename]
        future = site_obj.request_future
        if not future:
            # ignore: search by incompatible id type
            return

        response = await get_response(request_future=future,
                                      site_name=sitename,
                                      logger=logger)

        site_dict[sitename] = process_site_result(response, query_notify, logger, results_info, site_obj)


# TODO: move info separate module
def detect_error_page(html_text, status_code, fail_flags, ignore_403):
    # Detect service restrictions such as a country restriction
    for flag, msg in fail_flags.items():
        if flag in html_text:
            return 'Some site error', msg

    # Detect common restrictions such as provider censorship and bot protection
    for flag, msg in common_errors.items():
        if flag in html_text:
            return 'Error', msg

    # Detect common site errors
    if status_code == 403 and not ignore_403:
        return 'Access denied', 'Access denied, use proxy/vpn'
    elif status_code >= 500:
        return f'Error {status_code}', f'Site error {status_code}'

    return None, None


def process_site_result(response, query_notify, logger, results_info, site: MaigretSite):
    if not response:
        return results_info

    fulltags = site.tags

    # Retrieve other site information again
    username = results_info['username']
    is_parsing_enabled = results_info['parsing_enabled']
    url = results_info.get("url_user")
    logger.debug(url)

    status = results_info.get("status")
    if status is not None:
        # We have already determined the user doesn't exist here
        return results_info

    # Get the expected check type
    check_type = site.check_type

    # Get the failure messages and comments
    failure_errors = site.errors

    # TODO: refactor
    if not response:
        logger.error(f'No response for {site.name}')
        return results_info

    html_text, status_code, error_text, expection_text = response
    site_error_text = '?'

    # TODO: add elapsed request time counting
    response_time = None

    if logger.level == logging.DEBUG:
        with open('debug.txt', 'a') as f:
            status = status_code or 'No response'
            f.write(f'url: {url}\nerror: {str(error_text)}\nr: {status}\n')
            if html_text:
                f.write(f'code: {status}\nresponse: {str(html_text)}\n')

    if status_code and not error_text:
        error_text, site_error_text = detect_error_page(html_text, status_code, failure_errors,
                                                        site.ignore_403)

    # presense flags
    # True by default
    presense_flags = site.presense_strs
    is_presense_detected = html_text and all(
        [(presense_flag in html_text) for presense_flag in presense_flags]) or not presense_flags

    if error_text is not None:
        logger.debug(error_text)
        result = QueryResult(username,
                             site.name,
                             url,
                             QueryStatus.UNKNOWN,
                             query_time=response_time,
                             context=f'{error_text}: {site_error_text}', tags=fulltags)
    elif check_type == "message":
        absence_flags = site.absence_strs
        is_absence_flags_list = isinstance(absence_flags, list)
        absence_flags_set = set(absence_flags) if is_absence_flags_list else {absence_flags}
        # Checks if the error message is in the HTML
        is_absence_detected = any([(absence_flag in html_text) for absence_flag in absence_flags_set])
        if not is_absence_detected and is_presense_detected:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.CLAIMED,
                                 query_time=response_time, tags=fulltags)
        else:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.AVAILABLE,
                                 query_time=response_time, tags=fulltags)
    elif check_type == "status_code":
        # Checks if the status code of the response is 2XX
        if (not status_code >= 300 or status_code < 200) and is_presense_detected:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.CLAIMED,
                                 query_time=response_time, tags=fulltags)
        else:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.AVAILABLE,
                                 query_time=response_time, tags=fulltags)
    elif check_type == "response_url":
        # For this detection method, we have turned off the redirect.
        # So, there is no need to check the response URL: it will always
        # match the request.  Instead, we will ensure that the response
        # code indicates that the request was successful (i.e. no 404, or
        # forward to some odd redirect).
        if 200 <= status_code < 300 and is_presense_detected:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.CLAIMED,
                                 query_time=response_time, tags=fulltags)
        else:
            result = QueryResult(username,
                                 site.name,
                                 url,
                                 QueryStatus.AVAILABLE,
                                 query_time=response_time, tags=fulltags)
    else:
        # It should be impossible to ever get here...
        raise ValueError(f"Unknown check type '{check_type}' for "
                         f"site '{site.name}'")

    extracted_ids_data = {}

    if is_parsing_enabled and result.status == QueryStatus.CLAIMED:
        try:
            extracted_ids_data = extract(html_text)
        except Exception as e:
            logger.warning(f'Error while parsing {site.name}: {e}', exc_info=True)

        if extracted_ids_data:
            new_usernames = {}
            for k, v in extracted_ids_data.items():
                if 'username' in k:
                    new_usernames[v] = 'username'
                if k in supported_recursive_search_ids:
                    new_usernames[v] = k

            results_info['ids_usernames'] = new_usernames
            result.ids_data = extracted_ids_data

    # Notify caller about results of query.
    query_notify.update(result, site.similar_search)

    # Save status of request
    results_info['status'] = result

    # Save results from request
    results_info['http_status'] = status_code
    results_info['is_similar'] = site.similar_search
    # results_site['response_text'] = html_text
    results_info['rank'] = site.alexa_rank
    return results_info


async def maigret(username, site_dict, query_notify, logger,
                  proxy=None, timeout=None, recursive_search=False,
                  id_type='username', tags=None, debug=False, forced=False,
                  max_connections=100, no_progressbar=False):
    """Main search func

    Checks for existence of username on various social media sites.

    Keyword Arguments:
    username               -- String indicating username that report
                              should be created against.
    site_dict              -- Dictionary containing all of the site data.
    query_notify           -- Object with base type of QueryNotify().
                              This will be used to notify the caller about
                              query results.
    proxy                  -- String indicating the proxy URL
    timeout                -- Time in seconds to wait before timing out request.
                              Default is no timeout.
    recursive_search       -- Search for other usernames in website pages & recursive search by them.

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

    # Notify caller that we are starting the query.
    if tags is None:
        tags = set()
    query_notify.start(username, id_type)

    # TODO: connector
    connector = ProxyConnector.from_url(proxy) if proxy else aiohttp.TCPConnector(ssl=False)
    # connector = aiohttp.TCPConnector(ssl=False)
    connector.verify_ssl=False
    session = aiohttp.ClientSession(connector=connector)

    if logger.level == logging.DEBUG:
        future = session.get(url='https://icanhazip.com')
        ip, status, error, expection = await get_response(future, None, logger)
        if ip:
            logger.debug(f'My IP is: {ip.strip()}')
        else:
            logger.debug(f'IP requesting {error}: {expection}')


    # Results from analysis of all sites
    results_total = {}

    # First create futures for all requests. This allows for the requests to run in parallel
    for site_name, site in site_dict.items():

        fulltags = site.tags

        if site.type != id_type:
            continue

        site_tags = set(fulltags)
        if tags:
            if not set(tags).intersection(site_tags):
                continue

        if site.disabled and not forced:
            continue

        # Results from analysis of this specific site
        results_site = {}

        # Record URL of main site and username
        results_site['username'] = username
        results_site['parsing_enabled'] = recursive_search
        results_site['url_main'] = site.url_main


        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:55.0) Gecko/20100101 Firefox/55.0',
        }

        headers.update(site.headers)

        if not 'url' in site.__dict__:
            logger.error('No URL for site %s', site.name)
        # URL of user on site (if it exists)
        url = site.url.format(
            urlMain=site.url_main,
            urlSubpath=site.url_subpath,
            username=username
        )
        # workaround to prevent slash errors
        url = re.sub('(?<!:)/+', '/', url)

        # Don't make request if username is invalid for the site
        if site.regex_check and re.search(site.regex_check, username) is None:
            # No need to do the check at the site: this user name is not allowed.
            results_site['status'] = QueryResult(username,
                                                 site_name,
                                                 url,
                                                 QueryStatus.ILLEGAL)
            results_site["url_user"] = ""
            results_site['http_status'] = ""
            results_site['response_text'] = ""
            query_notify.update(results_site['status'])
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


            if site.check_type == 'status_code' and site.request_head_only:
                # In most cases when we are detecting by status code,
                # it is not necessary to get the entire body:  we can
                # detect fine with just the HEAD response.
                request_method = session.head
            else:
                # Either this detect method needs the content associated
                # with the GET response, or this specific website will
                # not respond properly unless we request the whole page.
                request_method = session.get

            if site.check_type == "response_url":
                # Site forwards request to a different URL if username not
                # found.  Disallow the redirect so we can capture the
                # http status from the original URL request.
                allow_redirects = False
            else:
                # Allow whatever redirect that the site wants to do.
                # The final result of the request will be what is available.
                allow_redirects = True

            # TODO: cookies using
            # def parse_cookies(cookies_str):
            #     cookies = SimpleCookie()
            #     cookies.load(cookies_str)
            #     return {key: morsel.value for key, morsel in cookies.items()}
            #
            # if os.path.exists(cookies_file):
            #     cookies_obj = cookielib.MozillaCookieJar(cookies_file)
            #     cookies_obj.load(ignore_discard=True, ignore_expires=True)

            future = request_method(url=url_probe, headers=headers,
                                    allow_redirects=allow_redirects,
                                    timeout=timeout,
                                    )

            # Store future in data for access later
            # TODO: move to separate obj
            site.request_future = future

        # Add this site's results into final dictionary with all of the other results.
        results_total[site_name] = results_site

    # TODO: move into top-level function

    sem = asyncio.Semaphore(max_connections)

    tasks = []
    for sitename, result_obj in results_total.items():
        update_site_coro = update_site_dict_from_response(sitename, site_dict, result_obj, sem, logger, query_notify)
        future = asyncio.ensure_future(update_site_coro)
        tasks.append(future)

    if no_progressbar:
        await asyncio.gather(*tasks)
    else:
        for f in tqdm.asyncio.tqdm.as_completed(tasks):
            await f

    await session.close()

    # Notify caller that all queries are finished.
    query_notify.finish()

    return results_total


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


async def site_self_check(site_name, site_data, logger, no_progressbar=False):
    query_notify = Mock()
    changes = {
        'disabled': False,
    }

    check_data = [
        (site_data.username_claimed, QueryStatus.CLAIMED),
        (site_data.username_unclaimed, QueryStatus.AVAILABLE),
    ]

    logger.info(f'Checking {site_name}...')

    for username, status in check_data:
        results = await maigret(
            username,
            {site_name: site_data},
            query_notify,
            logger,
            timeout=30,
            forced=True,
            no_progressbar=no_progressbar,
        )

        # don't disable entries with other ids types
        if site_name not in results:
            logger.info(results)
            changes['disabled'] = True
            continue

        site_status = results[site_name]['status'].status
        if site_status != status:
            if site_status == QueryStatus.UNKNOWN:
                msgs = site_data.absence_strs
                etype = site_data.check_type
                logger.info(f'Error while searching {username} in {site_name}: {msgs}, type {etype}')
                # don't disable in case of available username
                if status == QueryStatus.CLAIMED:
                    changes['disabled'] = True
            elif status == QueryStatus.CLAIMED:
                logger.info(f'Not found `{username}` in {site_name}, must be claimed')
                logger.info(results[site_name])
                changes['disabled'] = True
            else:
                logger.info(f'Found `{username}` in {site_name}, must be available')
                logger.info(results[site_name])
                changes['disabled'] = True

    logger.info(f'Site {site_name} checking is finished')
    return changes


async def self_check(json_file, logger):
    db = MaigretDatabase()
    db.load_from_file(json_file)
    sites = db.sites
    all_sites = {}

    def disabled_count(data):
        return len(list(filter(lambda x: x.get('disabled', False), data)))

    async def update_site_data(site_name, site_data, all_sites, logger):
        updates = await site_self_check(site_name, dict(site_data), logger)
        all_sites[site_name].update(updates)

    for site in sites:
        all_sites[site.name] = site.information

    disabled_old_count = disabled_count(all_sites.values())

    tasks = []
    for site_name, site_data in all_sites.items():
        future = asyncio.ensure_future(update_site_data(site_name, site_data, all_sites, logger))
        tasks.append(future)

    await asyncio.gather(*tasks)

    disabled_new_count = disabled_count(all_sites.values())
    total_disabled = disabled_new_count - disabled_old_count
    if total_disabled > 0:
        message = 'Disabled'
    else:
        message = 'Enabled'
        total_disabled *= -1
    print(f'{message} {total_disabled} checked sites. Run with `--info` flag to get more information')

    with open(json_file, 'w') as f:
        data['sites'] = all_sites
        json.dump(data, f, indent=4)


async def main():
    version_string = f"%(prog)s {__version__}\n" + \
                     f"{requests.__description__}:  {requests.__version__}\n" + \
                     f"Python:  {platform.python_version()}"

    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=f"Maigret v{__version__}"
                            )
    parser.add_argument("--version",
                        action="version", version=version_string,
                        help="Display version information and dependencies."
                        )
    parser.add_argument("--info",
                        action="store_true", dest="info", default=False,
                        help="Display service information."
                        )
    parser.add_argument("--verbose", "-v",
                        action="store_true", dest="verbose", default=False,
                        help="Display extra information and metrics."
                        )
    parser.add_argument("-d", "--debug",
                        action="store_true", dest="debug", default=False,
                        help="Saving debugging information and sites responses in debug.txt."
                        )
    parser.add_argument("--rank", "-r",
                        action="store_true", dest="rank", default=False,
                        help="Present websites ordered by their Alexa.com global rank in popularity.")
    parser.add_argument("--folderoutput", "-fo", dest="folderoutput", default="reports",
                        help="If using multiple usernames, the output of the results will be saved to this folder."
                        )
    parser.add_argument("--csv",
                        action="store_true", dest="csv", default=False,
                        help="Create Comma-Separated Values (CSV) File."
                        )
    parser.add_argument("--site",
                        action="append", metavar='SITE_NAME',
                        dest="site_list", default=None,
                        help="Limit analysis to just the listed sites (use several times to specify more than one)"
                        )
    parser.add_argument("--proxy", "-p", metavar='PROXY_URL',
                        action="store", dest="proxy", default=None,
                        help="Make requests over a proxy. e.g. socks5://127.0.0.1:1080"
                        )
    parser.add_argument("--json", "-j", metavar="JSON_FILE",
                        dest="json_file", default=None,
                        help="Load data from a JSON file or an online, valid, JSON file.")
    parser.add_argument("--timeout",
                        action="store", metavar='TIMEOUT',
                        dest="timeout", type=timeout_check, default=10,
                        help="Time (in seconds) to wait for response to requests."
                             "Default timeout of 10.0s."
                             "A longer timeout will be more likely to get results from slow sites."
                             "On the other hand, this may cause a long delay to gather all results."
                        )
    parser.add_argument("--print-not-found",
                        action="store_true", dest="print_not_found", default=False,
                        help="Print sites where the username was not found."
                        )
    parser.add_argument("--print-errors",
                        action="store_true", dest="print_check_errors", default=False,
                        help="Print errors messages: connection, captcha, site country ban, etc."
                        )
    parser.add_argument("--no-color",
                        action="store_true", dest="no_color", default=False,
                        help="Don't color terminal output"
                        )
    parser.add_argument("--browse", "-b",
                        action="store_true", dest="browse", default=False,
                        help="Browse to all results on default bowser."
                        )
    parser.add_argument("--no-recursion",
                        action="store_true", dest="disable_recursive_search", default=False,
                        help="Disable parsing pages for other usernames and recursive search by them."
                        )
    parser.add_argument("--self-check",
                        action="store_true", default=False,
                        help="Do self check for sites and database and disable non-working ones."
                        )
    parser.add_argument("--use-disabled-sites",
                        action="store_true", default=False,
                        help="Use disabled sites to search (may cause many false positives)."
                        )
    parser.add_argument("--parse",
                        dest="parse_url", default='',
                        help="Parse page by URL and extract username and IDs to use for search."
                        )
    parser.add_argument("username",
                        nargs='+', metavar='USERNAMES',
                        action="store",
                        help="One or more usernames to check with social networks."
                        )
    parser.add_argument("--tags",
                        dest="tags", default='',
                        help="Specify tags of sites."
                        )

    parser.add_argument("-x","--xmind",
                        action="store_true",
                        dest="xmind", default=False,
                        help="Generate an xmind 8 mindmap"
                        )

    args = parser.parse_args()

    # Logging
    log_level = logging.ERROR
    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=log_level
    )

    if args.debug:
        log_level = logging.DEBUG
    elif args.info:
        log_level = logging.INFO
    elif args.verbose:
        log_level = logging.WARNING

    logger = logging.getLogger('maigret')
    logger.setLevel(log_level)

    # Usernames initial list
    usernames = {
        u: 'username'
        for u in args.username
        if u not in ['-']
    }

    recursive_search_enabled = not args.disable_recursive_search

    # Make prompts
    if args.proxy is not None:
        print("Using the proxy: " + args.proxy)

    if args.parse_url:
        page, _ = parse(args.parse_url, cookies_str='')
        info = extract(page)
        text = 'Extracted ID data from webpage: ' + ', '.join([f'{a}: {b}' for a, b in info.items()])
        print(text)
        for k, v in info.items():
            if 'username' in k:
                usernames[v] = 'username'
            if k in supported_recursive_search_ids:
                usernames[v] = k

    if args.tags:
        args.tags = set(str(args.tags).split(','))

    if args.json_file is None:
        args.json_file = \
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         "resources/data.json"
                         )

    # Database self-checking
    if args.self_check:
        print('Maigret sites database self-checking...')
        await self_check(args.json_file, logger)

    # Create object with all information about sites we are aware of.
    try:
        site_data_all = MaigretDatabase().load_from_file(args.json_file).sites_dict
    except Exception as error:
        print(f"ERROR:  {error}")
        sys.exit(1)

    if args.site_list is None:
        # Not desired to look at a sub-set of sites
        site_data = site_data_all
    else:
        # User desires to selectively run queries on a sub-set of the site list.

        # Make sure that the sites are supported & build up pruned site database.
        site_data = {}
        site_missing = []
        for site in args.site_list:
            for existing_site in site_data_all:
                if site.lower() == existing_site.lower():
                    site_data[existing_site] = site_data_all[existing_site]
            if not site_data:
                # Build up list of sites not supported for future error message.
                site_missing.append(f"'{site}'")

        if site_missing:
            print(
                f"Error: Desired sites not found: {', '.join(site_missing)}.")
            sys.exit(1)

    if args.rank:
        # Sort data by rank
        site_dataCpy = dict(site_data)
        ranked_sites = sorted(site_data, key=lambda k: ("rank" not in k, site_data[k].get("rank", sys.maxsize)))
        site_data = {}
        for site in ranked_sites:
            site_data[site] = site_dataCpy.get(site)

    # Database consistency
    enabled_count = len(list(filter(lambda x: not x.disabled, site_data.values())))
    print(f'Sites in database, enabled/total: {enabled_count}/{len(site_data)}')

    # Create notify object for query results.
    query_notify = QueryNotifyPrint(result=None,
                                    verbose=args.verbose,
                                    print_found_only=not args.print_not_found,
                                    skip_check_errors=not args.print_check_errors,
                                    color=not args.no_color)

    already_checked = set()

    while usernames:
        username, id_type = list(usernames.items())[0]
        del usernames[username]

        if username.lower() in already_checked:
            continue
        else:
            already_checked.add(username.lower())

        # check for characters do not supported by sites generally
        found_unsupported_chars = set(unsupported_characters).intersection(set(username))

        if found_unsupported_chars:
            pretty_chars_str = ','.join(map(lambda s: f'"{s}"', found_unsupported_chars))
            print(f'Found unsupported URL characters: {pretty_chars_str}, skip search by username "{username}"')
            continue

        results = await maigret(username,
                                dict(site_data),
                                query_notify,
                                proxy=args.proxy,
                                timeout=args.timeout,
                                recursive_search=recursive_search_enabled,
                                id_type=id_type,
                                tags=args.tags,
                                debug=args.verbose,
                                logger=logger,
                                forced=args.use_disabled_sites,
                                )

        if args.folderoutput:
            # The usernames results should be stored in a targeted folder.
            # If the folder doesn't exist, create it first
            os.makedirs(args.folderoutput, exist_ok=True)
            result_file = os.path.join(args.folderoutput, f"{username}.txt")
            if args.xmind:
                xmind_path = os.path.join(args.folderoutput, f"{username}.xmind")
        else:
            result_file = f"{username}.txt"
            if args.xmind:
                xmind_path = f"{username}.xmind"

        if args.xmind:
            genxmindfile(xmind_path, username, results)

        with open(result_file, "w", encoding="utf-8") as file:
            exists_counter = 0
            for website_name in results:
                dictionary = results[website_name]
                # TODO: fix no site data issue
                if not dictionary:
                    continue
                new_usernames = dictionary.get('ids_usernames')
                if new_usernames:
                    for u, utype in new_usernames.items():
                        usernames[u] = utype

                if dictionary.get("status").status == QueryStatus.CLAIMED:
                    exists_counter += 1
                    file.write(dictionary["url_user"] + "\n")
            file.write(f"Total Websites Username Detected On : {exists_counter}")

        if args.csv:
            save_csv_report(username, results)


def run():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print('Maigret is interrupted.')
        sys.exit(1)


if __name__ == "__main__":
    run()