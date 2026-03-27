#!/usr/bin/env python3
"""Maigret: Supported Site Listing with Alexa ranking and country tags
This module generates the listing of supported sites in file `SITES.md`
and pretty prints file with sites data.
"""
import sys
import socket
import requests
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
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



import csv
import io
from urllib.parse import urlparse

def fetch_majestic_million():
    print("Fetching Majestic Million CSV (this may take a few seconds)...")
    ranks = {}
    url = "https://downloads.majestic.com/majestic_million.csv"
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        csv_file = io.StringIO(response.text)
        reader = csv.reader(csv_file)
        next(reader) # skip headers
        
        for row in reader:
            if not row or len(row) < 3:
                continue
            rank = int(row[0])
            domain = row[2].lower()
            ranks[domain] = rank
    except Exception as e:
        logging.error(f"Error fetching Majestic Million: {e}")
        
    print(f"Loaded {len(ranks)} domains from Majestic Million.")
    return ranks

def get_base_domain(url):
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc.lower()
    except Exception:
        return ""


def check_dns(domain, timeout=5):
    """Check if a domain resolves via DNS. Returns True if it resolves."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(domain, None)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


def check_sites_dns(sites):
    """Check DNS resolution for all sites. Returns a set of site names that failed."""
    SKIP_TLDS = ('.onion', '.i2p')
    domains = {}
    for site in sites:
        domain = get_base_domain(site.url_main)
        if domain and not any(domain.endswith(tld) for tld in SKIP_TLDS):
            domains.setdefault(domain, []).append(site)

    failed_sites = set()
    results = {}

    def resolve(domain):
        results[domain] = check_dns(domain)

    threads = []
    for domain in domains:
        t = threading.Thread(target=resolve, args=(domain,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    for domain, resolved in results.items():
        if not resolved:
            for site in domains[domain]:
                failed_sites.add(site.name)
            logging.warning(f"DNS resolution failed for {domain}")

    return failed_sites


def get_step_rank(rank):
    def get_readable_rank(r):
        return RANKS[str(r)]

    valid_step_ranks = sorted(map(int, RANKS.keys()))
    if rank == 0 or rank == sys.maxsize:
        return get_readable_rank(valid_step_ranks[-1])
    else:
        return get_readable_rank(list(filter(lambda x: x >= rank, valid_step_ranks))[0])


def main():
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter
                            )
    parser.add_argument("--base","-b", metavar="BASE_FILE",
                        dest="base_file", default="maigret/resources/data.json",
                        help="JSON file with sites data to update.")

    parser.add_argument('--with-rank', help='update with use of local data only', action='store_true')
    parser.add_argument('--empty-only', help='update only sites without rating', action='store_true')
    parser.add_argument('--exclude-engine', help='do not update score with certain engine',
                        action="append", dest="exclude_engine_list", default=[])
    parser.add_argument('--dns-check', help='disable sites whose domains do not resolve via DNS',
                        action='store_true')

    pool = list()

    args = parser.parse_args()

    db = MaigretDatabase()
    sites_subset = db.load_from_file(args.base_file).sites

    print(f"\nUpdating supported sites list (don't worry, it's needed)...")

    with open("sites.md", "w") as site_file:
        site_file.write(f"""
## List of supported sites (search methods): total {len(sites_subset)}\n
Rank data fetched from Majestic Million by domains.

""")

        if args.dns_check:
            print("Checking DNS resolution for all site domains...")
            failed = check_sites_dns(sites_subset)
            disabled_count = 0
            re_enabled_count = 0
            for site in sites_subset:
                if site.name in failed:
                    if not site.disabled:
                        site.disabled = True
                        disabled_count += 1
                        print(f"  Disabled {site.name}: DNS does not resolve ({get_base_domain(site.url_main)})")
                else:
                    if site.disabled:
                        # Re-enable previously disabled site if DNS now resolves
                        # (only if it was likely disabled due to DNS failure)
                        pass
            print(f"DNS check complete: {disabled_count} site(s) disabled, {len(failed)} domain(s) unresolvable.")

        majestic_ranks = {}
        if args.with_rank:
            majestic_ranks = fetch_majestic_million()

        for site in sites_subset:
            if not args.with_rank:
                break
            
            if site.alexa_rank < sys.maxsize and args.empty_only:
                continue
            if args.exclude_engine_list and site.engine in args.exclude_engine_list:
                continue
                
            domain = get_base_domain(site.url_main)
            
            if domain in majestic_ranks:
                site.alexa_rank = majestic_ranks[domain]
            else:
                site.alexa_rank = sys.maxsize
        
        # In memory matching complete, no threads to join
        if args.with_rank:
            print("Successfully updated ranks matching Majestic Million dataset.")

        sites_full_list = [(s, int(s.alexa_rank)) for s in sites_subset]

        sites_full_list.sort(reverse=False, key=lambda x: x[1])

        while sites_full_list[0][1] == 0:
            site = sites_full_list.pop(0)
            sites_full_list.append(site)

        for num, site_tuple in enumerate(sites_full_list):
            site, rank = site_tuple
            url_main = site.url_main
            valid_rank = get_step_rank(rank)
            all_tags = site.tags
            all_tags.sort()
            tags = ', ' + ', '.join(all_tags) if all_tags else ''
            note = ''
            if site.disabled:
                note = ', search is disabled'

            favicon = f"![](https://www.google.com/s2/favicons?domain={url_main})"
            site_file.write(f'1. {favicon} [{site}]({url_main})*: top {valid_rank}{tags}*{note}\n')
            db.update_site(site)

        site_file.write(f'\nThe list was updated at ({datetime.now(timezone.utc).date()})\n')
        db.save_to_file(args.base_file)

        statistics_text = db.get_db_stats(is_markdown=True)
        site_file.write('## Statistics\n\n')
        site_file.write(statistics_text)

    print("Finished updating supported site listing!")


if __name__ == '__main__':
    main()
