import asyncio
import logging
import maigret


TOP_SITES_COUNT = 300
TIMEOUT = 10
MAX_CONNECTIONS = 50


def main():
    logger = logging.getLogger('maigret')
    logger.setLevel(logging.WARNING)
    loop = asyncio.get_event_loop()

    db = maigret.MaigretDatabase().load_from_file('./maigret/resources/data.json')

    username = input('Enter username to search: ')
    sites_count = int(input(
        f'Select the number of sites to search ({TOP_SITES_COUNT} for default, {len(db.sites_dict)} max): '
    )) or TOP_SITES_COUNT
    sites = db.ranked_sites_dict(top=sites_count)

    show_progressbar = input('Do you want to show a progressbar? [Yn] ').lower() != 'n'
    extract_info = input(
        'Do you want to extract additional info from accounts\' pages? [Yn] '
    ).lower() != 'n'
    use_notifier = input(
        'Do you want to use notifier for displaying results while searching? [Yn] '
    ).lower() != 'n'

    notifier = None
    if use_notifier:
        notifier = maigret.Notifier(print_found_only=True, skip_check_errors=True)

    search_func = maigret.search(
        username=username,
        site_dict=sites,
        timeout=TIMEOUT,
        logger=logger,
        max_connections=MAX_CONNECTIONS,
        query_notify=notifier,
        no_progressbar=not show_progressbar,
        is_parsing_enabled=extract_info,
    )

    results = loop.run_until_complete(search_func)

    input('Search completed. Press any key to show results.')

    for sitename, data in results.items():
        is_found = data['status'].is_found()
        print(f'{sitename} - {"Found!" if is_found else "Not found"}')


if __name__ == '__main__':
    main()
