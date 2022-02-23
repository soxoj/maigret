#!/usr/bin/env python3
"""Maigret: Supported Site Listing with Alexa ranking and country tags
This module generates the listing of supported sites in file `SITES.md`
and pretty prints file with sites data.
"""
import aiohttp
import asyncio
import json
import sys
import requests
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import tqdm.asyncio

from maigret.maigret import get_response, site_self_check
from maigret.sites import MaigretSite, MaigretDatabase, MaigretEngine
from maigret.utils import CaseConverter


async def check_engine_of_site(site_name, sites_with_engines, future, engine_name, semaphore, logger):
    async with semaphore:
        response = await get_response(request_future=future,
                                      site_name=site_name,
                                      logger=logger)

        html_text, status_code, error_text, expection_text = response

        if html_text and engine_name in html_text:
            sites_with_engines.append(site_name)
            return True
    return False


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base","-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    parser.add_argument('--engine', '-e', help='check only selected engine', type=str)

    args = parser.parse_args()

    log_level = logging.INFO
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

    with open(args.base_file, "r", encoding="utf-8") as data_file:
        sites_info = json.load(data_file)
        engines = sites_info['engines']

    for engine_name, engine_data in engines.items():
        if args.engine and args.engine != engine_name:
            continue

        if not 'presenseStrs' in engine_data:
            print(f'No features to automatically detect sites on engine {engine_name}')
            continue

        engine_obj = MaigretEngine(engine_name, engine_data)

        # setup connections for checking both engine and usernames
        connector = aiohttp.TCPConnector(ssl=False)
        connector.verify_ssl=False
        session = aiohttp.ClientSession(connector=connector)

        sem = asyncio.Semaphore(100)
        loop = asyncio.get_event_loop()
        tasks = []

        # check sites without engine if they look like sites on this engine
        new_engine_sites = []
        for site_name, site_data in sites.items():
            if site_data.engine:
                continue

            future = session.get(url=site_data.url_main,
                                 allow_redirects=True,
                                 timeout=10,
                                 )

            check_engine_coro = check_engine_of_site(site_name, new_engine_sites, future, engine_name, sem, logger)
            future = asyncio.ensure_future(check_engine_coro)
            tasks.append(future)

        # progress bar
        for f in tqdm.asyncio.tqdm.as_completed(tasks):
            loop.run_until_complete(f)

        print(f'Total detected {len(new_engine_sites)} sites on engine {engine_name}')
        # dict with new found engine sites
        new_sites = {site_name: sites[site_name] for site_name in new_engine_sites}

        # update sites obj from engine
        for site_name, site in new_sites.items():
            site.request_future = None
            site.engine = engine_name
            site.update_from_engine(engine_obj)

        async def update_site_data(site_name, site_data, all_sites, logger, no_progressbar):
            updates = await site_self_check(site_name, site_data, logger, no_progressbar)
            all_sites[site_name].update(updates)

        tasks = []
        # for new_site_name, new_site_data in new_sites.items():
            # coro = update_site_data(new_site_name, new_site_data, new_sites, logger)
            # future = asyncio.ensure_future(coro)
            # tasks.append(future)

        # asyncio.gather(*tasks)
        for new_site_name, new_site_data in new_sites.items():
            coro = update_site_data(new_site_name, new_site_data, new_sites, logger, no_progressbar=True)
            loop.run_until_complete(coro)

        updated_sites_count = 0

        for s in new_sites:
            site = new_sites[s]
            site.request_future = None

            if site.disabled:
                print(f'{site.name} failed username checking of engine {engine_name}')
                continue

            site = site.strip_engine_data()

            db.update_site(site)
            updated_sites_count += 1
            db.save_to_file(args.base_file)

            print(f'Site "{s}": ' + json.dumps(site.json, indent=4))

        print(f'Updated total {updated_sites_count} sites!')
        print(f'Checking all sites on engine {engine_name}')

        loop.run_until_complete(session.close())

    print("\nFinished updating supported site listing!")
