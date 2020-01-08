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

RANKS = {str(i):str(i) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 100, 500]}
RANKS.update({
    '1000': '1K',
    '5000': '5K',
    '10000': '10K',
    '100000': '100K',
    '10000000': '1M',
    '50000000': '10M',
})

def get_rank(domain_to_query, dest, print_errors=True):
    #Retrieve ranking data via alexa API
    url = f"http://data.alexa.com/data?cli=10&url={domain_to_query}"
    xml_data = requests.get(url).text
    root = ET.fromstring(xml_data)

    try:
        #Get ranking for this site.
        dest['rank'] = int(root.find('.//REACH').attrib['RANK'])
        country = root.find('.//COUNTRY')
        if not country is None and country.attrib:
            country_code = country.attrib['CODE']
            tags = set(dest.get('tags', []))
            if country_code:
                tags.add(country_code.lower())
            dest['tags'] = sorted(list(tags))
            if 'type' in dest and dest['type'] != 'username':
                dest['disabled'] = False
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
    if rank == 0:
        return get_readable_rank(valid_step_ranks[-1])
    else:
        return get_readable_rank(list(filter(lambda x: x >= rank, valid_step_ranks))[0])


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base","-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    pool = list()

    args = parser.parse_args()

    with open(args.base_file, "r", encoding="utf-8") as data_file:
        sites_info = json.load(data_file)
        data = sites_info['sites']
        engines = sites_info['engines']

    with open("sites.md", "w") as site_file:
        data_length = len(data)
        site_file.write(f"""
## List of supported sites: total {data_length}\n
Rank data fetched from Alexa by domains.

""")

        for social_network in data:
            url_main = data.get(social_network).get("urlMain")
            data.get(social_network)["rank"] = 0
            th = threading.Thread(target=get_rank, args=(url_main, data.get(social_network)))
            pool.append((social_network, url_main, th))
            th.start()

        index = 1
        for social_network, url_main, th in pool:
            th.join()
            sys.stdout.write("\r{0}".format(f"Updated {index} out of {data_length} entries"))
            sys.stdout.flush()
            index = index + 1

        sites_full_list = [(site, site_data['rank']) for site, site_data in data.items()]
        sites_full_list.sort(reverse=False, key=lambda x: x[1])

        while sites_full_list[0][1] == 0:
            site = sites_full_list.pop(0)
            sites_full_list.append(site)

        for num, site_tuple in enumerate(sites_full_list):
            site, rank = site_tuple
            url_main = data[site]['urlMain']
            valid_rank = get_step_rank(rank)
            all_tags = data[site].get('tags', [])
            tags = ', ' + ', '.join(all_tags) if all_tags else ''
            note = ''
            if data[site].get('disabled'):
                note = ', search is disabled'
            site_file.write(f'1. [{site}]({url_main})*: top {valid_rank}{tags}*{note}\n')

        site_file.write(f'\nAlexa.com rank data fetched at ({datetime.utcnow()} UTC)\n')

    sorted_json_data = json.dumps({'sites': data, 'engines': engines}, indent=2, sort_keys=True)

    with open(args.base_file, "w") as data_file:
        data_file.write(sorted_json_data)

    print("\nFinished updating supported site listing!")
