"""Sherlock: Supported Site Listing
This module generates the listing of supported sites.
"""
import json
import sys
import requests
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from argparse import ArgumentParser, RawDescriptionHelpFormatter


def get_rank(domain_to_query, dest):
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
    except Exception as e:
        logging.error(e)
        # We did not find the rank for some reason.
        print(f"Error retrieving rank information for '{domain_to_query}'")
        print(f"     Returned XML is |{xml_data}|")

    return


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base","-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    pool = list()

    args = parser.parse_args()

    with open(args.base_file, "r", encoding="utf-8") as data_file:
        data = json.load(data_file)

    with open("sites.md", "w") as site_file:
        data_length = len(data)
        site_file.write(f'## List of supported sites: total {data_length}\n')

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
            site_file.write(f'{num+1}. [{site}]({url_main}), top {rank}\n')

        site_file.write(f'\nAlexa.com rank data fetched at ({datetime.utcnow()} UTC)\n')

    sorted_json_data = json.dumps(data, indent=2, sort_keys=True)

    with open(args.base_file, "w") as data_file:
        data_file.write(sorted_json_data)

    print("\nFinished updating supported site listing!")
