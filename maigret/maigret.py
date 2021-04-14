"""
Maigret main module
"""
import aiohttp
import asyncio
import logging
import os
import sys
import platform
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import requests
from socid_extractor import extract, parse, __version__ as socid_version

from .checking import timeout_check, supported_recursive_search_ids, self_check, unsupported_characters, maigret
from .notify import QueryNotifyPrint
from .report import save_csv_report, save_xmind_report, save_html_report, save_pdf_report, \
    generate_report_context, save_txt_report, SUPPORTED_JSON_REPORT_FORMATS, check_supported_json_format, \
    save_json_report
from .sites import MaigretDatabase
from .submit import submit_dialog
from .utils import get_dict_ascii_tree

__version__ = '0.1.19'


async def main():
    version_string = '\n'.join([
        f'%(prog)s {__version__}',
        f'Socid-extractor:  {socid_version}',
        f'Aiohttp:  {aiohttp.__version__}',
        f'Requests:  {requests.__version__}',
        f'Python:  {platform.python_version()}',
    ])

    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=f"Maigret v{__version__}"
                            )
    parser.add_argument("--version",
                        action="version", version=version_string,
                        help="Display version information and dependencies."
                        )
    parser.add_argument("--info", "-vv",
                        action="store_true", dest="info", default=False,
                        help="Display service information."
                        )
    parser.add_argument("--verbose", "-v",
                        action="store_true", dest="verbose", default=False,
                        help="Display extra information and metrics."
                        )
    parser.add_argument("-d", "--debug", "-vvv",
                        action="store_true", dest="debug", default=False,
                        help="Saving debugging information and sites responses in debug.txt."
                        )
    parser.add_argument("--site",
                        action="append", metavar='SITE_NAME',
                        dest="site_list", default=[],
                        help="Limit analysis to just the listed sites (use several times to specify more than one)"
                        )
    parser.add_argument("--proxy", "-p", metavar='PROXY_URL',
                        action="store", dest="proxy", default=None,
                        help="Make requests over a proxy. e.g. socks5://127.0.0.1:1080"
                        )
    parser.add_argument("--db", metavar="DB_FILE",
                        dest="db_file", default=None,
                        help="Load Maigret database from a JSON file or an online, valid, JSON file.")
    parser.add_argument("--cookies-jar-file", metavar="COOKIE_FILE",
                        dest="cookie_file", default=None,
                        help="File with cookies.")
    parser.add_argument("--timeout",
                        action="store", metavar='TIMEOUT',
                        dest="timeout", type=timeout_check, default=10,
                        help="Time (in seconds) to wait for response to requests."
                             "Default timeout of 10.0s. "
                             "A longer timeout will be more likely to get results from slow sites."
                             "On the other hand, this may cause a long delay to gather all results."
                        )
    parser.add_argument("-n", "--max-connections",
                        action="store", type=int,
                        dest="connections", default=100,
                        help="Allowed number of concurrent connections."
                        )
    parser.add_argument("-a", "--all-sites",
                        action="store_true", dest="all_sites", default=False,
                        help="Use all sites for scan."
                        )
    parser.add_argument("--top-sites",
                        action="store", default=500, type=int,
                        help="Count of sites for scan ranked by Alexa Top (default: 500)."
                        )
    parser.add_argument("--print-not-found",
                        action="store_true", dest="print_not_found", default=False,
                        help="Print sites where the username was not found."
                        )
    parser.add_argument("--print-errors",
                        action="store_true", dest="print_check_errors", default=False,
                        help="Print errors messages: connection, captcha, site country ban, etc."
                        )
    parser.add_argument("--submit", metavar='EXISTING_USER_URL',
                        type=str, dest="new_site_to_submit", default=False,
                        help="URL of existing profile in new site to submit."
                        )
    parser.add_argument("--no-color",
                        action="store_true", dest="no_color", default=False,
                        help="Don't color terminal output"
                        )
    parser.add_argument("--no-progressbar",
                        action="store_true", dest="no_progressbar", default=False,
                        help="Don't show progressbar."
                        )
    parser.add_argument("--browse", "-b",
                        action="store_true", dest="browse", default=False,
                        help="Browse to all results on default bowser."
                        )
    parser.add_argument("--no-recursion",
                        action="store_true", dest="disable_recursive_search", default=False,
                        help="Disable recursive search by additional data extracted from pages."
                        )
    parser.add_argument("--no-extracting",
                        action="store_true", dest="disable_extracting", default=False,
                        help="Disable parsing pages for additional data and other usernames."
                        )
    parser.add_argument("--self-check",
                        action="store_true", default=False,
                        help="Do self check for sites and database and disable non-working ones."
                        )
    parser.add_argument("--stats",
                        action="store_true", default=False,
                        help="Show database statistics."
                        )
    parser.add_argument("--use-disabled-sites",
                        action="store_true", default=False,
                        help="Use disabled sites to search (may cause many false positives)."
                        )
    parser.add_argument("--parse",
                        dest="parse_url", default='',
                        help="Parse page by URL and extract username and IDs to use for search."
                        )
    parser.add_argument("--id-type",
                        dest="id_type", default='username',
                        help="Specify identifier(s) type (default: username)."
                        )
    parser.add_argument("--ignore-ids",
                        action="append", metavar='IGNORED_IDS',
                        dest="ignore_ids_list", default=[],
                        help="Do not make search by the specified username or other ids."
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
    # reports options
    parser.add_argument("--folderoutput", "-fo", dest="folderoutput", default="reports",
                        help="If using multiple usernames, the output of the results will be saved to this folder."
                        )
    parser.add_argument("-T", "--txt",
                        action="store_true", dest="txt", default=False,
                        help="Create a TXT report (one report per username)."
                        )
    parser.add_argument("-C", "--csv",
                        action="store_true", dest="csv", default=False,
                        help="Create a CSV report (one report per username)."
                        )
    parser.add_argument("-H", "--html",
                        action="store_true", dest="html", default=False,
                        help="Create an HTML report file (general report on all usernames)."
                        )
    parser.add_argument("-X", "--xmind",
                        action="store_true",
                        dest="xmind", default=False,
                        help="Generate an XMind 8 mindmap report (one report per username)."
                        )
    parser.add_argument("-P", "--pdf",
                        action="store_true",
                        dest="pdf", default=False,
                        help="Generate a PDF report (general report on all usernames)."
                        )
    parser.add_argument("-J", "--json",
                        action="store", metavar='REPORT_TYPE',
                        dest="json", default='', type=check_supported_json_format,
                        help=f"Generate a JSON report of specific type: {', '.join(SUPPORTED_JSON_REPORT_FORMATS)}"
                             " (one report per username)."
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
        u: args.id_type
        for u in args.username
        if u not in ['-']
           and u not in args.ignore_ids_list
    }

    parsing_enabled = not args.disable_extracting
    recursive_search_enabled = not args.disable_recursive_search

    # Make prompts
    if args.proxy is not None:
        print("Using the proxy: " + args.proxy)

    if args.parse_url:
        # url, headers
        reqs = [(args.parse_url, set())]
        try:
            # temporary workaround for URL mutations MVP
            from socid_extractor import mutate_url
            reqs += list(mutate_url(args.parse_url))
        except:
            pass

        for req in reqs:
            url, headers = req
            print(f'Scanning webpage by URL {url}...')
            page, _ = parse(url, cookies_str='', headers=headers)
            info = extract(page)
            if not info:
                print('Nothing extracted')
            else:
                print(get_dict_ascii_tree(info.items(), new_line=False), ' ')
            for k, v in info.items():
                if 'username' in k:
                    usernames[v] = 'username'
                if k in supported_recursive_search_ids:
                    usernames[v] = k

    if args.tags:
        args.tags = list(set(str(args.tags).split(',')))

    if args.db_file is None:
        args.db_file = \
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         "resources/data.json"
                         )

    if args.top_sites == 0 or args.all_sites:
        args.top_sites = sys.maxsize

    # Create notify object for query results.
    query_notify = QueryNotifyPrint(result=None,
                                    verbose=args.verbose,
                                    print_found_only=not args.print_not_found,
                                    skip_check_errors=not args.print_check_errors,
                                    color=not args.no_color)

    # Create object with all information about sites we are aware of.
    db = MaigretDatabase().load_from_file(args.db_file)
    get_top_sites_for_id = lambda x: db.ranked_sites_dict(top=args.top_sites, tags=args.tags,
                                                          names=args.site_list,
                                                          disabled=False, id_type=x)

    site_data = get_top_sites_for_id(args.id_type)

    if args.new_site_to_submit:
        is_submitted = await submit_dialog(db, args.new_site_to_submit, args.cookie_file)
        if is_submitted:
            db.save_to_file(args.db_file)

    # Database self-checking
    if args.self_check:
        print('Maigret sites database self-checking...')
        is_need_update = await self_check(db, site_data, logger, max_connections=args.connections)
        if is_need_update:
            if input('Do you want to save changes permanently? [Yn]\n').lower() == 'y':
                db.save_to_file(args.db_file)
                print('Database was successfully updated.')
            else:
                print('Updates will be applied only for current search session.')
        print(db.get_scan_stats(site_data))

    if args.stats:
        print(db.get_db_stats(db.sites_dict))

    # Make reports folder is not exists
    os.makedirs(args.folderoutput, exist_ok=True)

    # Define one report filename template
    report_filepath_tpl = os.path.join(args.folderoutput, 'report_{username}{postfix}')

    # Database stats
    # TODO: verbose info about filtered sites
    # enabled_count = len(list(filter(lambda x: not x.disabled, site_data.values())))
    # print(f'Sites in database, enabled/total: {enabled_count}/{len(site_data)}')

    if usernames == {}:
        # magic params to exit after init
        query_notify.warning('No usernames to check, exiting.')
        sys.exit(0)

    if not site_data:
        query_notify.warning('No sites to check, exiting!')
        sys.exit(2)
    else:
        query_notify.warning(f'Starting a search on top {len(site_data)} sites from the Maigret database...')
        if not args.all_sites:
            query_notify.warning(f'You can run search by full list of sites with flag `-a`', '!')

    already_checked = set()
    general_results = []

    while usernames:
        username, id_type = list(usernames.items())[0]
        del usernames[username]

        if username.lower() in already_checked:
            continue
        else:
            already_checked.add(username.lower())

        if username in args.ignore_ids_list:
            query_notify.warning(f'Skip a search by username {username} cause it\'s marked as ignored.')
            continue

        # check for characters do not supported by sites generally
        found_unsupported_chars = set(unsupported_characters).intersection(set(username))

        if found_unsupported_chars:
            pretty_chars_str = ','.join(map(lambda s: f'"{s}"', found_unsupported_chars))
            query_notify.warning(
                f'Found unsupported URL characters: {pretty_chars_str}, skip search by username "{username}"')
            continue

        sites_to_check = get_top_sites_for_id(id_type)

        results = await maigret(username=username,
                                site_dict=dict(sites_to_check),
                                query_notify=query_notify,
                                proxy=args.proxy,
                                timeout=args.timeout,
                                is_parsing_enabled=parsing_enabled,
                                id_type=id_type,
                                debug=args.verbose,
                                logger=logger,
                                cookies=args.cookie_file,
                                forced=args.use_disabled_sites,
                                max_connections=args.connections,
                                no_progressbar=args.no_progressbar,
                                )

        general_results.append((username, id_type, results))

        # TODO: tests
        for website_name in results:
            dictionary = results[website_name]
            # TODO: fix no site data issue
            if not dictionary or not recursive_search_enabled:
                continue

            new_usernames = dictionary.get('ids_usernames')
            if new_usernames:
                for u, utype in new_usernames.items():
                    usernames[u] = utype

            for url in dictionary.get('ids_links', []):
                for s in db.sites:
                    u = s.detect_username(url)
                    if u:
                        usernames[u] = 'username'

        # reporting for a one username
        if args.xmind:
            filename = report_filepath_tpl.format(username=username, postfix='.xmind')
            save_xmind_report(filename, username, results)
            query_notify.warning(f'XMind report for {username} saved in {filename}')

        if args.csv:
            filename = report_filepath_tpl.format(username=username, postfix='.csv')
            save_csv_report(filename, username, results)
            query_notify.warning(f'CSV report for {username} saved in {filename}')

        if args.txt:
            filename = report_filepath_tpl.format(username=username, postfix='.txt')
            save_txt_report(filename, username, results)
            query_notify.warning(f'TXT report for {username} saved in {filename}')

        if args.json:
            filename = report_filepath_tpl.format(username=username, postfix=f'_{args.json}.json')
            save_json_report(filename, username, results, report_type=args.json)
            query_notify.warning(f'JSON {args.json} report for {username} saved in {filename}')

    # reporting for all the result
    if general_results:
        if args.html or args.pdf:
            query_notify.warning('Generating report info...')
        report_context = generate_report_context(general_results)
        # determine main username
        username = report_context['username']

        if args.html:
            filename = report_filepath_tpl.format(username=username, postfix='.html')
            save_html_report(filename, report_context)
            query_notify.warning(f'HTML report on all usernames saved in {filename}')

        if args.pdf:
            filename = report_filepath_tpl.format(username=username, postfix='.pdf')
            save_pdf_report(filename, report_context)
            query_notify.warning(f'PDF report on all usernames saved in {filename}')
    # update database
    db.save_to_file(args.db_file)


def run():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print('Maigret is interrupted.')
        sys.exit(1)


if __name__ == "__main__":
    run()
