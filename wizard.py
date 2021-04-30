#!/usr/bin/env python3
import asyncio
import logging
import maigret


# top popular sites from the Maigret database
TOP_SITES_COUNT = 300
# Maigret HTTP requests timeout
TIMEOUT = 10
# max parallel requests
MAX_CONNECTIONS = 50


if __name__ == '__main__':
    # setup logging and asyncio
    logger = logging.getLogger('maigret')
    logger.setLevel(logging.WARNING)
    loop = asyncio.get_event_loop()

    # setup Maigret
    db = maigret.MaigretDatabase().load_from_file('./maigret/resources/data.json')
    # also can be downloaded from web
    # db = MaigretDatabase().load_from_url(MAIGRET_DB_URL)

    # user input
    username = input('Enter username to search: ')

    sites_count_raw = input(
        f'Select the number of sites to search ({TOP_SITES_COUNT} for default, {len(db.sites_dict)} max): '
    )
    sites_count = int(sites_count_raw) or TOP_SITES_COUNT

    sites = db.ranked_sites_dict(top=sites_count)

    show_progressbar_raw = input('Do you want to show a progressbar? [Yn] ')
    show_progressbar = show_progressbar_raw.lower() != 'n'

    extract_info_raw = input(
        'Do you want to extract additional info from accounts\' pages? [Yn] '
    )
    extract_info = extract_info_raw.lower() != 'n'

    use_notifier_raw = input(
        'Do you want to use notifier for displaying results while searching? [Yn] '
    )
    use_notifier = use_notifier_raw.lower() != 'n'

    notifier = None
    if use_notifier:
        notifier = maigret.Notifier(print_found_only=True, skip_check_errors=True)

    # search!
    search_func = maigret.search(
        username=username,
        site_dict=sites,
        timeout=TIMEOUT,
        logger=logger,
        max_connections=MAX_CONNECTIONS,
        query_notify=notifier,
        no_progressbar=(not show_progressbar),
        is_parsing_enabled=extract_info,
    )

    results = loop.run_until_complete(search_func)

    input('Search completed. Press any key to show results.')

    for sitename, data in results.items():
        is_found = data['status'].is_found()
        print(f'{sitename} - {"Found!" if is_found else "Not found"}')
