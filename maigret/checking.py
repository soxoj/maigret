import asyncio
import logging
from mock import Mock
import re
import ssl
import sys
import tqdm
import time
from typing import Callable, Any, Iterable, Tuple

import aiohttp
import tqdm.asyncio
from aiohttp_socks import ProxyConnector
from mock import Mock
from python_socks import _errors as proxy_errors
from socid_extractor import extract

from .activation import ParsingActivator, import_aiohttp_cookies
from .result import QueryResult, QueryStatus
from .sites import MaigretDatabase, MaigretSite

supported_recursive_search_ids = (
    'yandex_public_id',
    'gaia_id',
    'vk_id',
    'ok_id',
    'wikimapia_uid',
    'steam_id',
    'uidme_uguid',
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

QueryDraft = Tuple[Callable, Any, Any]
QueriesDraft = Iterable[QueryDraft]


def create_task_func():
    if sys.version_info.minor > 6:
        create_asyncio_task = asyncio.create_task
    else:
        loop = asyncio.get_event_loop()
        create_asyncio_task = loop.create_task
    return create_asyncio_task

class AsyncExecutor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs['logger']

    async def run(self, tasks: QueriesDraft):
        start_time = time.time()
        results = await self._run(tasks)
        self.execution_time = time.time() - start_time
        self.logger.debug(f'Spent time: {self.execution_time}')
        return results

    async def _run(self, tasks: QueriesDraft):
        await asyncio.sleep(0)


class AsyncioSimpleExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run(self, tasks: QueriesDraft):
        futures = [f(*args, **kwargs) for f, args, kwargs in tasks]
        return await asyncio.gather(*futures)


class AsyncioProgressbarExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run(self, tasks: QueriesDraft):
        futures = [f(*args, **kwargs) for f, args, kwargs in tasks]
        results = []
        for f in tqdm.asyncio.tqdm.as_completed(futures):
            results.append(await f)
        return results


class AsyncioProgressbarSemaphoreExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.semaphore = asyncio.Semaphore(kwargs.get('in_parallel', 1))

    async def _run(self, tasks: QueriesDraft):
        async def _wrap_query(q: QueryDraft):
            async with self.semaphore:
                f, args, kwargs = q
                return await f(*args, **kwargs)

        async def semaphore_gather(tasks: QueriesDraft):
            coros = [_wrap_query(q) for q in tasks]
            results = []
            for f in tqdm.asyncio.tqdm.as_completed(coros):
                results.append(await f)
            return results

        return await semaphore_gather(tasks)


class AsyncioProgressbarQueueExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workers_count = kwargs.get('in_parallel', 10)
        self.progress_func = kwargs.get('progress_func', tqdm.tqdm)
        self.queue = asyncio.Queue(self.workers_count)
        self.timeout = kwargs.get('timeout')

    async def worker(self):
        while True:
            try:
                f, args, kwargs = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            query_future = f(*args, **kwargs)
            query_task = create_task_func()(query_future)
            try:
                result = await asyncio.wait_for(query_task, timeout=self.timeout)
            except asyncio.TimeoutError:
                result = None

            self.results.append(result)
            self.progress.update(1)
            self.queue.task_done()

    async def _run(self, queries: QueriesDraft):
        self.results = []

        queries_list = list(queries)

        min_workers = min(len(queries_list), self.workers_count)

        workers = [create_task_func()(self.worker())
                   for _ in range(min_workers)]

        self.progress = self.progress_func(total=len(queries_list))
        for t in queries_list:
            await self.queue.put(t)
        await self.queue.join()
        for w in workers:
            w.cancel()
        self.progress.close()
        return self.results


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
        # python-specific exceptions
        if sys.version_info.minor > 6:
            if isinstance(err, ssl.SSLCertVerificationError) or isinstance(err, ssl.SSLError):
                error_text = "SSL Error"
                expection_text = str(err)
        else:
            logger.warning(f'Unhandled error while requesting {site_name}: {err}')
            logger.debug(err, exc_info=True)
            error_text = "Some Error"
            expection_text = str(err)

    # TODO: return only needed information
    return html_text, status_code, error_text, expection_text


async def update_site_dict_from_response(sitename, site_dict, results_info, logger, query_notify):
    site_obj = site_dict[sitename]
    future = site_obj.request_future
    if not future:
        # ignore: search by incompatible id type
        return

    response = await get_response(request_future=future,
                                  site_name=sitename,
                                  logger=logger)

    return sitename, process_site_result(response, query_notify, logger, results_info, site_obj)


# TODO: move to separate class
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
                                                        site.ignore403)

    if site.activation and html_text:
        is_need_activation = any([s for s in site.activation['marks'] if s in html_text])
        if is_need_activation:
            method = site.activation['method']
            try:
                activate_fun = getattr(ParsingActivator(), method)
                # TODO: async call
                activate_fun(site, logger)
            except AttributeError:
                logger.warning(f'Activation method {method} for site {site.name} not found!')
            except Exception as e:
                logger.warning(f'Failed activation {method} for site {site.name}: {e}')

    # presense flags
    # True by default
    presense_flags = site.presense_strs
    is_presense_detected = False
    if html_text:
        if not presense_flags:
            is_presense_detected = True
            site.stats['presense_flag'] = None
        else:
            for presense_flag in presense_flags:
                if presense_flag in html_text:
                    is_presense_detected = True
                    site.stats['presense_flag'] = presense_flag
                    logger.info(presense_flag)
                    break

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
            results_info['ids_links'] = eval(extracted_ids_data.get('links', '[]'))
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


async def maigret(username, site_dict, logger, query_notify=None,
                  proxy=None, timeout=None, is_parsing_enabled=False,
                  id_type='username', debug=False, forced=False,
                  max_connections=100, no_progressbar=False,
                  cookies=None):
    """Main search func

    Checks for existence of username on certain sites.

    Keyword Arguments:
    username               -- Username string will be used for search.
    site_dict              -- Dictionary containing sites data.
    query_notify           -- Object with base type of QueryNotify().
                              This will be used to notify the caller about
                              query results.
    logger                 -- Standard Python logger object.
    timeout                -- Time in seconds to wait before timing out request.
                              Default is no timeout.
    is_parsing_enabled     -- Extract additional info from account pages.
    id_type                -- Type of username to search.
                              Default is 'username', see all supported here:
                              https://github.com/soxoj/maigret/wiki/Supported-identifier-types
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

    # Notify caller that we are starting the query.
    if not query_notify:
        query_notify = Mock()

    query_notify.start(username, id_type)

    # TODO: connector
    connector = ProxyConnector.from_url(proxy) if proxy else aiohttp.TCPConnector(ssl=False)
    # connector = aiohttp.TCPConnector(ssl=False)
    connector.verify_ssl = False

    cookie_jar = None
    if cookies:
        logger.debug(f'Using cookies jar file {cookies}')
        cookie_jar = await import_aiohttp_cookies(cookies)

    session = aiohttp.ClientSession(connector=connector, trust_env=True, cookie_jar=cookie_jar)

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

        if site.type != id_type:
            continue

        if site.disabled and not forced:
            logger.debug(f'Site {site.name} is disabled, skipping...')
            continue

        # Results from analysis of this specific site
        results_site = {}

        # Record URL of main site and username
        results_site['username'] = username
        results_site['parsing_enabled'] = is_parsing_enabled
        results_site['url_main'] = site.url_main
        results_site['cookies'] = cookie_jar and cookie_jar.filter_cookies(site.url_main) or None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:55.0) Gecko/20100101 Firefox/55.0',
        }

        headers.update(site.headers)

        if 'url' not in site.__dict__:
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

            for k, v in site.get_params.items():
                url_probe += f'&{k}={v}'

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

            future = request_method(url=url_probe, headers=headers,
                                    allow_redirects=allow_redirects,
                                    timeout=timeout,
                                    )

            # Store future in data for access later
            # TODO: move to separate obj
            site.request_future = future

        # Add this site's results into final dictionary with all of the other results.
        results_total[site_name] = results_site

    coroutines = []
    for sitename, result_obj in results_total.items():
        coroutines.append((update_site_dict_from_response, [sitename, site_dict, result_obj, logger, query_notify], {}))

    if no_progressbar:
        executor = AsyncioSimpleExecutor(logger=logger)
    else:
        executor = AsyncioProgressbarQueueExecutor(logger=logger, in_parallel=max_connections, timeout=timeout+0.5)

    results = await executor.run(coroutines)

    await session.close()

    # Notify caller that all queries are finished.
    query_notify.finish()

    data = {}
    for result in results:
        # TODO: still can be empty
        if result:
            try:
                data[result[0]] = result[1]
            except Exception as e:
                logger.error(e, exc_info=True)
                logger.info(result)

    return data


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


async def site_self_check(site, logger, semaphore, db: MaigretDatabase, silent=False):
    changes = {
        'disabled': False,
    }

    try:
        check_data = [
            (site.username_claimed, QueryStatus.CLAIMED),
            (site.username_unclaimed, QueryStatus.AVAILABLE),
        ]
    except Exception as e:
        logger.error(e)
        logger.error(site.__dict__)
        check_data = []

    logger.info(f'Checking {site.name}...')

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
            )

            # don't disable entries with other ids types
            # TODO: make normal checking
            if site.name not in results_dict:
                logger.info(results_dict)
                changes['disabled'] = True
                continue

            result = results_dict[site.name]['status']

        site_status = result.status

        if site_status != status:
            if site_status == QueryStatus.UNKNOWN:
                msgs = site.absence_strs
                etype = site.check_type
                logger.warning(
                    f'Error while searching {username} in {site.name}: {result.context}, {msgs}, type {etype}')
                # don't disable in case of available username
                if status == QueryStatus.CLAIMED:
                    changes['disabled'] = True
            elif status == QueryStatus.CLAIMED:
                logger.warning(f'Not found `{username}` in {site.name}, must be claimed')
                logger.info(results_dict[site.name])
                changes['disabled'] = True
            else:
                logger.warning(f'Found `{username}` in {site.name}, must be available')
                logger.info(results_dict[site.name])
                changes['disabled'] = True

    logger.info(f'Site {site.name} checking is finished')

    if changes['disabled'] != site.disabled:
        site.disabled = changes['disabled']
        db.update_site(site)
        if not silent:
            action = 'Disabled' if site.disabled else 'Enabled'
            print(f'{action} site {site.name}...')

    return changes


async def self_check(db: MaigretDatabase, site_data: dict, logger, silent=False,
                     max_connections=10) -> bool:
    sem = asyncio.Semaphore(max_connections)
    tasks = []
    all_sites = site_data

    def disabled_count(lst):
        return len(list(filter(lambda x: x.disabled, lst)))

    disabled_old_count = disabled_count(all_sites.values())

    for _, site in all_sites.items():
        check_coro = site_self_check(site, logger, sem, db, silent)
        future = asyncio.ensure_future(check_coro)
        tasks.append(future)

    for f in tqdm.asyncio.tqdm.as_completed(tasks):
        await f

    disabled_new_count = disabled_count(all_sites.values())
    total_disabled = disabled_new_count - disabled_old_count

    if total_disabled >= 0:
        message = 'Disabled'
    else:
        message = 'Enabled'
        total_disabled *= -1

    if not silent:
        print(
            f'{message} {total_disabled} ({disabled_old_count} => {disabled_new_count}) checked sites. Run with `--info` flag to get more information')

    return total_disabled != 0
