"""
Maigret main module
"""

import ast
import asyncio
import logging
import os
import sys
import platform
import re
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from typing import List, Tuple
import os.path as path

from socid_extractor import extract, parse

from .__version__ import __version__
from .checking import (
    timeout_check,
    SUPPORTED_IDS,
    self_check,
    BAD_CHARS,
    maigret,
)
from . import errors
from .notify import QueryNotifyPrint
from .report import (
    save_csv_report,
    save_xmind_report,
    save_html_report,
    save_pdf_report,
    generate_report_context,
    save_txt_report,
    SUPPORTED_JSON_REPORT_FORMATS,
    save_json_report,
    get_plaintext_report,
    sort_report_by_data_points,
    save_graph_report,
)
from .sites import MaigretDatabase
from .submit import Submitter
from .types import QueryResultWrapper
from .utils import get_dict_ascii_tree
from .settings import Settings
from .permutator import Permute


def extract_ids_from_page(url, logger, timeout=5) -> dict:
    results = {}
    # url, headers
    reqs: List[Tuple[str, set]] = [(url, set())]
    try:
        # temporary workaround for URL mutations MVP
        from socid_extractor import mutate_url

        reqs += list(mutate_url(url))
    except Exception as e:
        logger.warning(e)

    for req in reqs:
        url, headers = req
        print(f'Scanning webpage by URL {url}...')
        page, _ = parse(url, cookies_str='', headers=headers, timeout=timeout)
        logger.debug(page)
        info = extract(page)
        if not info:
            print('Nothing extracted')
        else:
            print(get_dict_ascii_tree(info.items(), new_line=False), ' ')
        for k, v in info.items():
            # TODO: merge with the same functionality in checking module
            if 'username' in k and not 'usernames' in k:
                results[v] = 'username'
            elif 'usernames' in k:
                try:
                    tree = ast.literal_eval(v)
                    if type(tree) == list:
                        for n in tree:
                            results[n] = 'username'
                except Exception as e:
                    logger.warning(e)
            if k in SUPPORTED_IDS:
                results[v] = k

    return results


def extract_ids_from_results(results: QueryResultWrapper, db: MaigretDatabase) -> dict:
    ids_results = {}
    for website_name in results:
        dictionary = results[website_name]
        # TODO: fix no site data issue
        if not dictionary:
            continue

        new_usernames = dictionary.get('ids_usernames')
        if new_usernames:
            for u, utype in new_usernames.items():
                ids_results[u] = utype

        for url in dictionary.get('ids_links', []):
            ids_results.update(db.extract_ids_from_url(url))

    return ids_results


def setup_arguments_parser(settings: Settings):
    from aiohttp import __version__ as aiohttp_version
    from requests import __version__ as requests_version
    from socid_extractor import __version__ as socid_version

    version_string = '\n'.join(
        [
            f'%(prog)s {__version__}',
            f'Socid-extractor:  {socid_version}',
            f'Aiohttp:  {aiohttp_version}',
            f'Requests:  {requests_version}',
            f'Python:  {platform.python_version()}',
        ]
    )

    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description=f"Maigret v{__version__}\n"
        "Documentation: https://maigret.readthedocs.io/\n"
        "All settings are also configurable through files, see docs.",
    )
    parser.add_argument(
        "username",
        nargs='*',
        metavar="USERNAMES",
        help="One or more usernames to search by.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version_string,
        help="Display version information and dependencies.",
    )
    parser.add_argument(
        "--timeout",
        action="store",
        metavar='TIMEOUT',
        dest="timeout",
        type=timeout_check,
        default=settings.timeout,
        help="Time in seconds to wait for response to requests "
        f"(default {settings.timeout}s). "
        "A longer timeout will be more likely to get results from slow sites. "
        "On the other hand, this may cause a long delay to gather all results. ",
    )
    parser.add_argument(
        "--retries",
        action="store",
        type=int,
        metavar='RETRIES',
        default=settings.retries_count,
        help="Attempts to restart temporarily failed requests.",
    )
    parser.add_argument(
        "-n",
        "--max-connections",
        action="store",
        type=int,
        dest="connections",
        default=settings.max_connections,
        help=f"Allowed number of concurrent connections (default {settings.max_connections}).",
    )
    parser.add_argument(
        "--no-recursion",
        action="store_true",
        dest="disable_recursive_search",
        default=(not settings.recursive_search),
        help="Disable recursive search by additional data extracted from pages.",
    )
    parser.add_argument(
        "--no-extracting",
        action="store_true",
        dest="disable_extracting",
        default=(not settings.info_extracting),
        help="Disable parsing pages for additional data and other usernames.",
    )
    parser.add_argument(
        "--id-type",
        dest="id_type",
        default='username',
        choices=SUPPORTED_IDS,
        help="Specify identifier(s) type (default: username).",
    )
    parser.add_argument(
        "--permute",
        action="store_true",
        default=False,
        help="Permute at least 2 usernames to generate more possible usernames.",
    )
    parser.add_argument(
        "--db",
        metavar="DB_FILE",
        dest="db_file",
        default=settings.sites_db_path,
        help="Load Maigret database from a JSON file or HTTP web resource.",
    )
    parser.add_argument(
        "--cookies-jar-file",
        metavar="COOKIE_FILE",
        dest="cookie_file",
        default=settings.cookie_jar_file,
        help="File with cookies.",
    )
    parser.add_argument(
        "--ignore-ids",
        action="append",
        metavar='IGNORED_IDS',
        dest="ignore_ids_list",
        default=settings.ignore_ids_list,
        help="Do not make search by the specified username or other ids.",
    )
    # reports options
    parser.add_argument(
        "--folderoutput",
        "-fo",
        dest="folderoutput",
        default=settings.reports_path,
        metavar="PATH",
        help="If using multiple usernames, the output of the results will be saved to this folder.",
    )
    parser.add_argument(
        "--proxy",
        "-p",
        metavar='PROXY_URL',
        action="store",
        dest="proxy",
        default=settings.proxy_url,
        help="Make requests over a proxy. e.g. socks5://127.0.0.1:1080",
    )
    parser.add_argument(
        "--tor-proxy",
        metavar='TOR_PROXY_URL',
        action="store",
        default=settings.tor_proxy_url,
        help="Specify URL of your Tor gateway. Default is socks5://127.0.0.1:9050",
    )
    parser.add_argument(
        "--i2p-proxy",
        metavar='I2P_PROXY_URL',
        action="store",
        default=settings.i2p_proxy_url,
        help="Specify URL of your I2P gateway. Default is http://127.0.0.1:4444",
    )
    parser.add_argument(
        "--with-domains",
        action="store_true",
        default=settings.domain_search,
        help="Enable (experimental) feature of checking domains on usernames.",
    )

    filter_group = parser.add_argument_group(
        'Site filtering', 'Options to set site search scope'
    )
    filter_group.add_argument(
        "-a",
        "--all-sites",
        action="store_true",
        dest="all_sites",
        default=settings.scan_all_sites,
        help="Use all sites for scan.",
    )
    filter_group.add_argument(
        "--top-sites",
        action="store",
        default=settings.top_sites_count,
        metavar="N",
        type=int,
        help="Count of sites for scan ranked by Alexa Top (default: 500).",
    )
    filter_group.add_argument(
        "--tags", dest="tags", default='', help="Specify tags of sites (see `--stats`)."
    )
    filter_group.add_argument(
        "--site",
        action="append",
        metavar='SITE_NAME',
        dest="site_list",
        default=settings.scan_sites_list,
        help="Limit analysis to just the specified sites (multiple option).",
    )
    filter_group.add_argument(
        "--use-disabled-sites",
        action="store_true",
        default=settings.scan_disabled_sites,
        help="Use disabled sites to search (may cause many false positives).",
    )

    modes_group = parser.add_argument_group(
        'Operating modes',
        'Various functions except the default search by a username. '
        'Modes are executed sequentially in the order of declaration.',
    )
    modes_group.add_argument(
        "--parse",
        dest="parse_url",
        default='',
        metavar='URL',
        help="Parse page by URL and extract username and IDs to use for search.",
    )
    modes_group.add_argument(
        "--submit",
        metavar='URL',
        type=str,
        dest="new_site_to_submit",
        default=False,
        help="URL of existing profile in new site to submit.",
    )
    modes_group.add_argument(
        "--self-check",
        action="store_true",
        default=settings.self_check_enabled,
        help="Do self check for sites and database and disable non-working ones.",
    )
    modes_group.add_argument(
        "--stats",
        action="store_true",
        default=False,
        help="Show database statistics (most frequent sites engines and tags).",
    )
    modes_group.add_argument(
        "--web",
        metavar='PORT',
        type=int,
        nargs='?',  # Optional PORT value
        const=5000,  # Default PORT if `--web` is provided without a value
        default=None,  # Explicitly set default to None
        help="Launch the web interface on the specified port (default: 5000 if no PORT is provided).",
    )
    output_group = parser.add_argument_group(
        'Output options', 'Options to change verbosity and view of the console output'
    )
    output_group.add_argument(
        "--print-not-found",
        action="store_true",
        dest="print_not_found",
        default=settings.print_not_found,
        help="Print sites where the username was not found.",
    )
    output_group.add_argument(
        "--print-errors",
        action="store_true",
        dest="print_check_errors",
        default=settings.print_check_errors,
        help="Print errors messages: connection, captcha, site country ban, etc.",
    )
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        dest="verbose",
        default=False,
        help="Display extra information and metrics.",
    )
    output_group.add_argument(
        "--info",
        "-vv",
        action="store_true",
        dest="info",
        default=False,
        help="Display extra/service information and metrics.",
    )
    output_group.add_argument(
        "--debug",
        "-vvv",
        "-d",
        action="store_true",
        dest="debug",
        default=False,
        help="Display extra/service/debug information and metrics, save responses in debug.log.",
    )
    output_group.add_argument(
        "--no-color",
        action="store_true",
        dest="no_color",
        default=(not settings.colored_print),
        help="Don't color terminal output",
    )
    output_group.add_argument(
        "--no-progressbar",
        action="store_true",
        dest="no_progressbar",
        default=(not settings.show_progressbar),
        help="Don't show progressbar.",
    )

    report_group = parser.add_argument_group(
        'Report formats', 'Supported formats of report files'
    )
    report_group.add_argument(
        "-T",
        "--txt",
        action="store_true",
        dest="txt",
        default=settings.txt_report,
        help="Create a TXT report (one report per username).",
    )
    report_group.add_argument(
        "-C",
        "--csv",
        action="store_true",
        dest="csv",
        default=settings.csv_report,
        help="Create a CSV report (one report per username).",
    )
    report_group.add_argument(
        "-H",
        "--html",
        action="store_true",
        dest="html",
        default=settings.html_report,
        help="Create an HTML report file (general report on all usernames).",
    )
    report_group.add_argument(
        "-X",
        "--xmind",
        action="store_true",
        dest="xmind",
        default=settings.xmind_report,
        help="Generate an XMind 8 mindmap report (one report per username).",
    )
    report_group.add_argument(
        "-P",
        "--pdf",
        action="store_true",
        dest="pdf",
        default=settings.pdf_report,
        help="Generate a PDF report (general report on all usernames).",
    )
    report_group.add_argument(
        "-G",
        "--graph",
        action="store_true",
        dest="graph",
        default=settings.graph_report,
        help="Generate a graph report (general report on all usernames).",
    )
    report_group.add_argument(
        "-J",
        "--json",
        action="store",
        metavar='TYPE',
        dest="json",
        default=settings.json_report_type,
        choices=SUPPORTED_JSON_REPORT_FORMATS,
        help=f"Generate a JSON report of specific type: {', '.join(SUPPORTED_JSON_REPORT_FORMATS)}"
        " (one report per username).",
    )

    parser.add_argument(
        "--reports-sorting",
        default=settings.report_sorting,
        choices=('default', 'data'),
        help="Method of results sorting in reports (default: in order of getting the result)",
    )
    return parser


async def main():
    # Logging
    log_level = logging.ERROR
    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=log_level,
    )
    logger = logging.getLogger('maigret')
    logger.setLevel(log_level)

    # Load settings
    settings = Settings()
    settings_loaded, err = settings.load()

    if not settings_loaded:
        logger.error(err)
        sys.exit(3)

    arg_parser = setup_arguments_parser(settings)
    args = arg_parser.parse_args()

    # Re-set logging level based on args
    if args.debug:
        log_level = logging.DEBUG
    elif args.info:
        log_level = logging.INFO
    elif args.verbose:
        log_level = logging.WARNING
    logger.setLevel(log_level)

    if args.web is not None:
        from maigret.web.app import app

        port = (
            args.web if args.web else 5000
        )  # args.web is either the specified port or 5000 by default
        app.run(port=port)
        return

    # Usernames initial list
    usernames = {
        u: args.id_type
        for u in args.username
        if u and u not in ['-'] and u not in args.ignore_ids_list
    }
    original_usernames = ""
    if args.permute and len(usernames) > 1 and args.id_type == 'username':
        original_usernames = " ".join(usernames.keys())
        usernames = Permute(usernames).gather(method='strict')

    parsing_enabled = not args.disable_extracting
    recursive_search_enabled = not args.disable_recursive_search

    # Make prompts
    if args.proxy is not None:
        print("Using the proxy: " + args.proxy)

    if args.parse_url:
        extracted_ids = extract_ids_from_page(
            args.parse_url, logger, timeout=args.timeout
        )
        usernames.update(extracted_ids)

    if args.tags:
        args.tags = list(set(str(args.tags).split(',')))

    db_file = path.join(path.dirname(path.realpath(__file__)), args.db_file)

    if args.top_sites == 0 or args.all_sites:
        args.top_sites = sys.maxsize

    # Create notify object for query results.
    query_notify = QueryNotifyPrint(
        result=None,
        verbose=args.verbose,
        print_found_only=not args.print_not_found,
        skip_check_errors=not args.print_check_errors,
        color=not args.no_color,
    )

    # Create object with all information about sites we are aware of.
    db = MaigretDatabase().load_from_path(db_file)
    get_top_sites_for_id = lambda x: db.ranked_sites_dict(
        top=args.top_sites,
        tags=args.tags,
        names=args.site_list,
        disabled=args.use_disabled_sites,
        id_type=x,
    )

    site_data = get_top_sites_for_id(args.id_type)

    if args.new_site_to_submit:
        submitter = Submitter(db=db, logger=logger, settings=settings, args=args)
        is_submitted = await submitter.dialog(args.new_site_to_submit, args.cookie_file)
        if is_submitted:
            db.save_to_file(db_file)
        await submitter.close()

    # Database self-checking
    if args.self_check:
        if len(site_data) == 0:
            query_notify.warning(
                'No sites to self-check with the current filters! Exiting...'
            )
            return

        query_notify.success(
            f'Maigret sites database self-check started for {len(site_data)} sites...'
        )
        is_need_update = await self_check(
            db,
            site_data,
            logger,
            proxy=args.proxy,
            max_connections=args.connections,
            tor_proxy=args.tor_proxy,
            i2p_proxy=args.i2p_proxy,
        )
        if is_need_update:
            if input('Do you want to save changes permanently? [Yn]\n').lower() in (
                'y',
                '',
            ):
                db.save_to_file(db_file)
                print('Database was successfully updated.')
            else:
                print('Updates will be applied only for current search session.')

        if args.verbose or args.debug:
            query_notify.info(
                'Scan sessions flags stats: ' + str(db.get_scan_stats(site_data))
            )

    # Database statistics
    if args.stats:
        print(db.get_db_stats())

    report_dir = path.join(os.getcwd(), args.folderoutput)

    # Make reports folder is not exists
    os.makedirs(report_dir, exist_ok=True)

    # Define one report filename template
    report_filepath_tpl = path.join(report_dir, 'report_{username}{postfix}')

    if usernames == {}:
        # magic params to exit after init
        query_notify.warning('No usernames to check, exiting.')
        sys.exit(0)

    if len(usernames) > 1 and args.permute and args.id_type == 'username':
        query_notify.warning(
            f"{len(usernames)} permutations from {original_usernames} to check..."
            + get_dict_ascii_tree(usernames, prepend="\t")
        )

    if not site_data:
        query_notify.warning('No sites to check, exiting!')
        sys.exit(2)

    query_notify.warning(
        f'Starting a search on top {len(site_data)} sites from the Maigret database...'
    )
    if not args.all_sites:
        query_notify.warning(
            'You can run search by full list of sites with flag `-a`', '!'
        )

    already_checked = set()
    general_results = []

    while usernames:
        username, id_type = list(usernames.items())[0]
        del usernames[username]

        if username.lower() in already_checked:
            continue

        already_checked.add(username.lower())

        if username in args.ignore_ids_list:
            query_notify.warning(
                f'Skip a search by username {username} cause it\'s marked as ignored.'
            )
            continue

        # check for characters do not supported by sites generally
        found_unsupported_chars = set(BAD_CHARS).intersection(set(username))
        if found_unsupported_chars:
            pretty_chars_str = ','.join(
                map(lambda s: f'"{s}"', found_unsupported_chars)
            )
            query_notify.warning(
                f'Found unsupported URL characters: {pretty_chars_str}, skip search by username "{username}"'
            )
            continue

        sites_to_check = get_top_sites_for_id(id_type)

        results = await maigret(
            username=username,
            site_dict=dict(sites_to_check),
            query_notify=query_notify,
            proxy=args.proxy,
            tor_proxy=args.tor_proxy,
            i2p_proxy=args.i2p_proxy,
            timeout=args.timeout,
            is_parsing_enabled=parsing_enabled,
            id_type=id_type,
            debug=args.verbose,
            logger=logger,
            cookies=args.cookie_file,
            forced=args.use_disabled_sites,
            max_connections=args.connections,
            no_progressbar=args.no_progressbar,
            retries=args.retries,
            check_domains=args.with_domains,
        )

        errs = errors.notify_about_errors(
            results, query_notify, show_statistics=args.verbose
        )
        for e in errs:
            query_notify.warning(*e)

        if args.reports_sorting == "data":
            results = sort_report_by_data_points(results)

        general_results.append((username, id_type, results))

        # TODO: tests
        if recursive_search_enabled:
            extracted_ids = extract_ids_from_results(results, db)
            query_notify.warning(f'Extracted IDs: {extracted_ids}')
            usernames.update(extracted_ids)

        # reporting for a one username
        if args.xmind:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(username=username, postfix='.xmind')
            save_xmind_report(filename, username, results)
            query_notify.warning(f'XMind report for {username} saved in {filename}')

        if args.csv:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(username=username, postfix='.csv')
            save_csv_report(filename, username, results)
            query_notify.warning(f'CSV report for {username} saved in {filename}')

        if args.txt:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(username=username, postfix='.txt')
            save_txt_report(filename, username, results)
            query_notify.warning(f'TXT report for {username} saved in {filename}')

        if args.json:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(
                username=username, postfix=f'_{args.json}.json'
            )
            save_json_report(filename, username, results, report_type=args.json)
            query_notify.warning(
                f'JSON {args.json} report for {username} saved in {filename}'
            )

    # reporting for all the result
    if general_results:
        if args.html or args.pdf:
            query_notify.warning('Generating report info...')
        report_context = generate_report_context(general_results)
        # determine main username
        username = report_context['username']

        if args.html:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(
                username=username, postfix='_plain.html'
            )
            save_html_report(filename, report_context)
            query_notify.warning(f'HTML report on all usernames saved in {filename}')

        if args.pdf:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(username=username, postfix='.pdf')
            save_pdf_report(filename, report_context)
            query_notify.warning(f'PDF report on all usernames saved in {filename}')

        if args.graph:
            username = username.replace('/', '_')
            filename = report_filepath_tpl.format(
                username=username, postfix='_graph.html'
            )
            save_graph_report(filename, general_results, db)
            query_notify.warning(f'Graph report on all usernames saved in {filename}')

        text_report = get_plaintext_report(report_context)
        if text_report:
            query_notify.info('Short text report:')
            print(text_report)

    # update database
    db.save_to_file(db_file)


def run():
    try:
        if sys.version_info.minor >= 10:
            asyncio.run(main())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
    except KeyboardInterrupt:
        print('Maigret is interrupted.')
        sys.exit(1)


if __name__ == "__main__":
    run()
