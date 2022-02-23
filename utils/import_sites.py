#!/usr/bin/env python3
import json
import random
import re

import tqdm.asyncio
from mock import Mock
import requests

from maigret.maigret import *
from maigret.result import QueryStatus
from maigret.sites import MaigretSite

URL_RE = re.compile(r"https?://(www\.)?")
TIMEOUT = 200


async def maigret_check(site, site_data, username, status, logger):
    query_notify = Mock()
    logger.debug(f'Checking {site}...')

    for username, status in [(username, status)]:
        results = await maigret(
            username,
            {site: site_data},
            logger,
            query_notify,
            timeout=TIMEOUT,
            forced=True,
            no_progressbar=True,
        )

        if results[site]['status'].status != status:
            if results[site]['status'].status == QueryStatus.UNKNOWN:
                msg = site_data.absence_strs
                etype = site_data.check_type
                context = results[site]['status'].context

                logger.debug(f'Error while searching {username} in {site}, must be claimed. Context: {context}')
                # if site_data.get('errors'):
                #     continue
                return False

            if status == QueryStatus.CLAIMED:
                logger.debug(f'Not found {username} in {site}, must be claimed')
                logger.debug(results[site])
                pass
            else:
                logger.debug(f'Found {username} in {site}, must be available')
                logger.debug(results[site])
                pass
            return False

    return site_data


async def check_and_add_maigret_site(site_data, semaphore, logger, ok_usernames, bad_usernames):
    async with semaphore:
        sitename = site_data.name
        positive = False
        negative = False

        for ok_username in ok_usernames:
            site_data.username_claimed = ok_username
            status = QueryStatus.CLAIMED
            if await maigret_check(sitename, site_data, ok_username, status, logger):
                # print(f'{sitename} positive case is okay')
                positive = True
                break

        for bad_username in bad_usernames:
            site_data.username_unclaimed = bad_username
            status = QueryStatus.AVAILABLE
            if await maigret_check(sitename, site_data, bad_username, status, logger):
                # print(f'{sitename} negative case is okay')
                negative = True
                break

        if positive and negative:
            site_data = site_data.strip_engine_data()

            db.update_site(site_data)
            print(site_data.json)
            try:
                db.save_to_file(args.base_file)
            except Exception as e:
                logging.error(e, exc_info=True)
            print(f'Saved new site {sitename}...')
            ok_sites.append(site_data)


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base", "-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    parser.add_argument("--add-engine", dest="add_engine", help="Additional engine to check")

    parser.add_argument("--only-engine", dest="only_engine", help="Use only this engine from detected to check")

    parser.add_argument('--check', help='only check sites in database', action='store_true')

    parser.add_argument('--random', help='shuffle list of urls', action='store_true', default=False)

    parser.add_argument('--top', help='top count of records in file', type=int, default=10000)

    parser.add_argument('--filter', help='substring to filter input urls', type=str, default='')

    parser.add_argument('--username', help='preferable username to check with', type=str)

    parser.add_argument(
        "--info",
        "-vv",
        action="store_true",
        dest="info",
        default=False,
        help="Display service information.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        dest="verbose",
        default=False,
        help="Display extra information and metrics.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        "-vvv",
        action="store_true",
        dest="debug",
        default=False,
        help="Saving debugging information and sites responses in debug.txt.",
    )

    parser.add_argument("urls_file",
                        metavar='URLS_FILE',
                        action="store",
                        help="File with base site URLs"
                        )

    args = parser.parse_args()

    log_level = logging.ERROR
    if args.debug:
        log_level = logging.DEBUG
    elif args.info:
        log_level = logging.INFO
    elif args.verbose:
        log_level = logging.WARNING

    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=log_level
    )
    logger = logging.getLogger('engines-check')
    logger.setLevel(log_level)

    db = MaigretDatabase()
    sites_subset = db.load_from_file(args.base_file).sites
    sites = {site.name: site for site in sites_subset}
    engines = db.engines

    # TODO: usernames extractors
    ok_usernames = ['alex', 'god', 'admin', 'red', 'blue', 'john']
    if args.username:
        ok_usernames = [args.username] + ok_usernames

    bad_usernames = ['noonewouldeverusethis7']

    with open(args.urls_file, 'r') as urls_file:
        urls = urls_file.read().splitlines()
        if args.random:
            random.shuffle(urls)
        urls = urls[:args.top]

    raw_maigret_data = json.dumps({site.name: site.json for site in sites_subset})

    new_sites = []
    for site in tqdm.asyncio.tqdm(urls):
        site_lowercase = site.lower()

        domain_raw = URL_RE.sub('', site_lowercase).strip().strip('/')
        domain_raw = domain_raw.split('/')[0]

        if args.filter and args.filter not in domain_raw:
            logger.debug('Site %s skipped due to filtering by "%s"', domain_raw, args.filter)
            continue

        if domain_raw in raw_maigret_data:
            logger.debug(f'Site {domain_raw} already exists in the Maigret database!')
            continue

        if '"' in domain_raw:
            logger.debug(f'Invalid site {domain_raw}')
            continue

        main_page_url = '/'.join(site.split('/', 3)[:3])

        site_data = {
            'url': site,
            'urlMain': main_page_url,
            'name': domain_raw,
        }

        try:
            r = requests.get(main_page_url, timeout=5)
        except:
            r = None
            pass

        detected_engines = []

        for e in engines:
            strs_to_check = e.__dict__.get('presenseStrs')
            if strs_to_check and r and r.text:
                all_strs_in_response = True
                for s in strs_to_check:
                    if not s in r.text:
                        all_strs_in_response = False
                if all_strs_in_response:
                    engine_name = e.__dict__.get('name')
                    detected_engines.append(engine_name)
                    logger.info(f'Detected engine {engine_name} for site {main_page_url}')

        if args.only_engine and args.only_engine in detected_engines:
            detected_engines = [args.only_engine]
        elif not detected_engines and args.add_engine:
            logging.debug('Could not detect any engine, applying default engine %s...', args.add_engine)
            detected_engines = [args.add_engine]

        def create_site_from_engine(sitename, data, e):
            site = MaigretSite(sitename, data)
            site.update_from_engine(db.engines_dict[e])
            site.engine = e
            return site

        for engine_name in detected_engines:
            site = create_site_from_engine(domain_raw, site_data, engine_name)
            new_sites.append(site)
            logger.debug(site.json)

            # if engine_name == "phpBB":
            #     site_data_with_subpath = dict(site_data)
            #     site_data_with_subpath["urlSubpath"] = "/forum"
            #     site = create_site_from_engine(domain_raw, site_data_with_subpath, engine_name)
            #     new_sites.append(site)

        # except Exception as e:
        #     print(f'Error: {str(e)}')
        #     pass

    print(f'Found {len(new_sites)}/{len(urls)} new sites')

    if args.check:
        for s in new_sites:
            print(s.url_main)
        sys.exit(0)

    sem = asyncio.Semaphore(20)
    loop = asyncio.get_event_loop()

    ok_sites = []
    tasks = []
    for site in new_sites:
        check_coro = check_and_add_maigret_site(site, sem, logger, ok_usernames, bad_usernames)
        future = asyncio.ensure_future(check_coro)
        tasks.append(future)

    for f in tqdm.asyncio.tqdm.as_completed(tasks, timeout=TIMEOUT):
        try:
            loop.run_until_complete(f)
        except asyncio.exceptions.TimeoutError:
            pass

    print(f'Found and saved {len(ok_sites)} sites!')
