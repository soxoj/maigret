import difflib
import json

import requests
from mock import Mock

from .checking import *

DESIRED_STRINGS = ["username", "not found", "пользователь", "profile", "lastname", "firstname", "biography",
                   "birthday", "репутация", "информация", "e-mail"]

RATIO = 0.6
TOP_FEATURES = 5
URL_RE = re.compile(r'https?://(www\.)?')


def get_match_ratio(x):
    return round(max([
        difflib.SequenceMatcher(a=x.lower(), b=y).ratio()
        for y in DESIRED_STRINGS
    ]), 2)


def extract_domain(url):
    return '/'.join(url.split('/', 3)[:3])


async def site_self_check(site, logger, semaphore, db: MaigretDatabase, silent=False):
    query_notify = Mock()
    changes = {
        'disabled': False,
    }

    check_data = [
        (site.username_claimed, QueryStatus.CLAIMED),
        (site.username_unclaimed, QueryStatus.AVAILABLE),
    ]

    logger.info(f'Checking {site.name}...')

    for username, status in check_data:
        async with semaphore:
            results_dict = await maigret(
                username,
                {site.name: site},
                query_notify,
                logger,
                timeout=30,
                id_type=site.type,
                forced=True,
                no_progressbar=True,
            )

            # don't disable entries with other ids types
            # TODO: make normal checking
            if site.name not in results_dict:
                logger.info(results_dict)
                changes['disabled'] = True
                continue

            result = results_dict[site.name]['status']

        site_status = result.status

        if site_status != status:
            if site_status == QueryStatus.UNKNOWN:
                msgs = site.absence_strs
                etype = site.check_type
                logger.warning(
                    f'Error while searching {username} in {site.name}: {result.context}, {msgs}, type {etype}')
                # don't disable in case of available username
                if status == QueryStatus.CLAIMED:
                    changes['disabled'] = True
            elif status == QueryStatus.CLAIMED:
                logger.warning(f'Not found `{username}` in {site.name}, must be claimed')
                logger.info(results_dict[site.name])
                changes['disabled'] = True
            else:
                logger.warning(f'Found `{username}` in {site.name}, must be available')
                logger.info(results_dict[site.name])
                changes['disabled'] = True

    logger.info(f'Site {site.name} checking is finished')

    return changes


async def submit_dialog(db, url_exists):
    domain_raw = URL_RE.sub('', url_exists).strip().strip('/')
    domain_raw = domain_raw.split('/')[0]

    matched_sites = list(filter(lambda x: domain_raw in x.url_main+x.url, db.sites))
    if matched_sites:
        print(f'Sites with domain "{domain_raw}" already exists in the Maigret database!')
        status = lambda s: '(disabled)' if s.disabled else ''
        url_block = lambda s: f'\n\t{s.url_main}\n\t{s.url}'
        print('\n'.join([f'{site.name} {status(site)}{url_block(site)}' for site in matched_sites]))
        return False

    url_parts = url_exists.split('/')
    supposed_username = url_parts[-1]
    new_name = input(f'Is "{supposed_username}" a valid username? If not, write it manually: ')
    if new_name:
        supposed_username = new_name
    non_exist_username = 'noonewouldeverusethis7'

    url_user = url_exists.replace(supposed_username, '{username}')
    url_not_exists = url_exists.replace(supposed_username, non_exist_username)

    a = requests.get(url_exists).text
    b = requests.get(url_not_exists).text

    tokens_a = set(a.split('"'))
    tokens_b = set(b.split('"'))

    a_minus_b = tokens_a.difference(tokens_b)
    b_minus_a = tokens_b.difference(tokens_a)

    top_features_count = int(input(f'Specify count of features to extract [default {TOP_FEATURES}]: ') or TOP_FEATURES)

    presence_list = sorted(a_minus_b, key=get_match_ratio, reverse=True)[:top_features_count]

    print('Detected text features of existing account: ' + ', '.join(presence_list))
    features = input('If features was not detected correctly, write it manually: ')

    if features:
        presence_list = features.split(',')

    absence_list = sorted(b_minus_a, key=get_match_ratio, reverse=True)[:top_features_count]
    print('Detected text features of non-existing account: ' + ', '.join(absence_list))
    features = input('If features was not detected correctly, write it manually: ')

    if features:
        absence_list = features.split(',')

    url_main = extract_domain(url_exists)

    site_data = {
        'absenceStrs': absence_list,
        'presenseStrs': presence_list,
        'url': url_user,
        'urlMain': url_main,
        'usernameClaimed': supposed_username,
        'usernameUnclaimed': non_exist_username,
        'checkType': 'message',
    }

    site = MaigretSite(url_main.split('/')[-1], site_data)

    print(site.__dict__)

    sem = asyncio.Semaphore(1)
    log_level = logging.INFO
    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=log_level
    )
    logger = logging.getLogger('site-submit')
    logger.setLevel(log_level)

    result = await site_self_check(site, logger, sem, db)

    if result['disabled']:
        print(f'Sorry, we couldn\'t find params to detect account presence/absence in {site.name}.')
        print('Try to run this mode again and increase features count or choose others.')
    else:
        if input(f'Site {site.name} successfully checked. Do you want to save it in the Maigret DB? [yY] ') in 'yY':
            db.update_site(site)
            return True

    return False
