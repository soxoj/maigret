#!/usr/bin/env python3
"""Maigret: Supported Site Listing with Alexa ranking and country tags
This module generates the listing of supported sites in file `SITES.md`
and pretty prints file with sites data.
"""
import json
import sys
import requests
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from maigret.maigret import MaigretDatabase

RANKS = {str(i):str(i) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 100, 500]}
RANKS.update({
    '1000': '1K',
    '5000': '5K',
    '10000': '10K',
    '100000': '100K',
    '10000000': '10M',
    '50000000': '50M',
    '100000000': '100M',
})

SEMAPHORE = threading.Semaphore(10)

def get_rank(domain_to_query, site, print_errors=True):
    with SEMAPHORE:
        #Retrieve ranking data via alexa API
        url = f"http://data.alexa.com/data?cli=10&url={domain_to_query}"
        xml_data = requests.get(url).text
        root = ET.fromstring(xml_data)

        try:
            #Get ranking for this site.
            site.alexa_rank = int(root.find('.//REACH').attrib['RANK'])
            country = root.find('.//COUNTRY')
            if not country is None and country.attrib:
                country_code = country.attrib['CODE']
                tags = set(site.tags)
                if country_code:
                    tags.add(country_code.lower())
                site.tags = sorted(list(tags))
                if site.type != 'username':
                    site.disabled = False
        except Exception as e:
            if print_errors:
                logging.error(e)
                # We did not find the rank for some reason.
                print(f"Error retrieving rank information for '{domain_to_query}'")
                print(f"     Returned XML is |{xml_data}|")

        return


def get_step_rank(rank):
    def get_readable_rank(r):
        return RANKS[str(r)]

    valid_step_ranks = sorted(map(int, RANKS.keys()))
    if rank == 0 or rank == sys.maxsize:
        return get_readable_rank(valid_step_ranks[-1])
    else:
        return get_readable_rank(list(filter(lambda x: x >= rank, valid_step_ranks))[0])


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base","-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    parser.add_argument('--empty-only', help='update only sites without rating', action='store_true')
    parser.add_argument('--exclude-engine', help='do not update score with certain engine',
                        action="append", dest="exclude_engine_list", default=[])

    pool = list()

    args = parser.parse_args()

    db = MaigretDatabase()
    sites_subset = db.load_from_file(args.base_file).sites

    with open("sites.md", "w") as site_file:
        site_file.write(f"""
## List of supported sites: total {len(sites_subset)}\n
Rank data fetched from Alexa by domains.

""")

        for site in sites_subset:
            url_main = site.url_main
            if site.alexa_rank < sys.maxsize and args.empty_only:
                continue
            if args.exclude_engine_list and site.engine in args.exclude_engine_list:
                continue
            site.alexa_rank = 0
            th = threading.Thread(target=get_rank, args=(url_main, site))
            pool.append((site.name, url_main, th))
            th.start()

        index = 1
        for site_name, url_main, th in pool:
            th.join()
            sys.stdout.write("\r{0}".format(f"Updated {index} out of {len(sites_subset)} entries"))
            sys.stdout.flush()
            index = index + 1

        sites_full_list = [(s, s.alexa_rank) for s in sites_subset]

        sites_full_list.sort(reverse=False, key=lambda x: x[1])

        while sites_full_list[0][1] == 0:
            site = sites_full_list.pop(0)
            sites_full_list.append(site)

        for num, site_tuple in enumerate(sites_full_list):
            site, rank = site_tuple
            url_main = site.url_main
            valid_rank = get_step_rank(rank)
            all_tags = site.tags
            tags = ', ' + ', '.join(all_tags) if all_tags else ''
            note = ''
            if site.disabled:
                note = ', search is disabled'

            favicon = f"![](https://www.google.com/s2/favicons?domain={url_main})"
            site_file.write(f'1. {favicon} [{site}]({url_main})*: top {valid_rank}{tags}*{note}\n')
            db.update_site(site)

        site_file.write(f'\nAlexa.com rank data fetched at ({datetime.utcnow()} UTC)\n')
        db.save_to_file(args.base_file)

    print("\nFinished updating supported site listing!")
