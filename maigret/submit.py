import difflib

import requests

from .checking import *


DESIRED_STRINGS = ["username", "not found", "пользователь", "profile", "lastname", "firstname", "biography",
                   "birthday", "репутация", "информация", "e-mail"]

SUPPOSED_USERNAMES = ['alex', 'god', 'admin', 'red', 'blue', 'john']

RATIO = 0.6
TOP_FEATURES = 5
URL_RE = re.compile(r'https?://(www\.)?')


def get_match_ratio(x):
    return round(max([
        difflib.SequenceMatcher(a=x.lower(), b=y).ratio()
        for y in DESIRED_STRINGS
    ]), 2)


def extract_mainpage_url(url):
    return '/'.join(url.split('/', 3)[:3])


async def site_self_check(site, logger, semaphore, db: MaigretDatabase, silent=False):
    changes = {
        'disabled': False,
    }

    check_data = [
        (site.username_claimed, QueryStatus.CLAIMED),
        (site.username_unclaimed, QueryStatus.AVAILABLE),
    ]

    logger.info(f'Checking {site.name}...')

    for username, status in check_data:
        results_dict = await maigret(
            username=username,
            site_dict={site.name: site},
            logger=logger,
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


async def detect_known_engine(db, url_exists, url_mainpage):
    try:
        r = requests.get(url_mainpage)
    except Exception as e:
        print(e)
        print('Some error while checking main page')
        return None

    for e in db.engines:
        strs_to_check = e.__dict__.get('presenseStrs')
        if strs_to_check and r and r.text:
            all_strs_in_response = True
            for s in strs_to_check:
                if not s in r.text:
                    all_strs_in_response = False
            if all_strs_in_response:
                engine_name = e.__dict__.get('name')
                print(f'Detected engine {engine_name} for site {url_mainpage}')

                sites = []
                for u in SUPPOSED_USERNAMES:
                    site_data = {
                        'urlMain': url_mainpage,
                        'name': url_mainpage.split('//')[0],
                        'engine': engine_name,
                        'usernameClaimed': u,
                        'usernameUnclaimed': 'noonewouldeverusethis7',
                    }

                    maigret_site = MaigretSite(url_mainpage.split('/')[-1], site_data)
                    maigret_site.update_from_engine(db.engines_dict[engine_name])
                    sites.append(maigret_site)

                return sites

    return None


async def check_features_manually(db, url_exists, url_mainpage, cookie_file):
    url_parts = url_exists.split('/')
    supposed_username = url_parts[-1]
    new_name = input(f'Is "{supposed_username}" a valid username? If not, write it manually: ')
    if new_name:
        supposed_username = new_name
    non_exist_username = 'noonewouldeverusethis7'

    url_user = url_exists.replace(supposed_username, '{username}')
    url_not_exists = url_exists.replace(supposed_username, non_exist_username)

    # cookies
    cookie_dict = None
    if cookie_file:
        cookie_jar = await import_aiohttp_cookies(cookie_file)
        cookie_dict = {c.key: c.value for c in cookie_jar}

    a = requests.get(url_exists, cookies=cookie_dict).text
    b = requests.get(url_not_exists, cookies=cookie_dict).text

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

    site_data = {
        'absenceStrs': absence_list,
        'presenseStrs': presence_list,
        'url': url_user,
        'urlMain': url_mainpage,
        'usernameClaimed': supposed_username,
        'usernameUnclaimed': non_exist_username,
        'checkType': 'message',
    }

    site = MaigretSite(url_mainpage.split('/')[-1], site_data)
    return site

async def submit_dialog(db, url_exists, cookie_file):
    domain_raw = URL_RE.sub('', url_exists).strip().strip('/')
    domain_raw = domain_raw.split('/')[0]

    # check for existence
    matched_sites = list(filter(lambda x: domain_raw in x.url_main + x.url, db.sites))

    if matched_sites:
        print(f'Sites with domain "{domain_raw}" already exists in the Maigret database!')
        status = lambda s: '(disabled)' if s.disabled else ''
        url_block = lambda s: f'\n\t{s.url_main}\n\t{s.url}'
        print('\n'.join([f'{site.name} {status(site)}{url_block(site)}' for site in matched_sites]))

        if input(f'Do you want to continue? [yN] ').lower() in 'n':
            return False

    url_mainpage = extract_mainpage_url(url_exists)

    sites = await detect_known_engine(db, url_exists, url_mainpage)
    if not sites:
        print('Unable to detect site engine, lets generate checking features')
        sites = [await check_features_manually(db, url_exists, url_mainpage, cookie_file)]

    print(sites[0].__dict__)

    sem = asyncio.Semaphore(1)
    log_level = logging.INFO
    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=log_level
    )
    logger = logging.getLogger('site-submit')
    logger.setLevel(log_level)

    found = False
    chosen_site = None
    for s in sites:
        chosen_site = s
        result = await site_self_check(s, logger, sem, db)
        if not result['disabled']:
            found = True
            break

    if not found:
        print(f'Sorry, we couldn\'t find params to detect account presence/absence in {chosen_site.name}.')
        print('Try to run this mode again and increase features count or choose others.')
    else:
        if input(f'Site {chosen_site.name} successfully checked. Do you want to save it in the Maigret DB? [Yn] ').lower() in 'y':
            print(chosen_site.json)
            site_data = chosen_site.strip_engine_data()
            print(site_data.json)
            db.update_site(site_data)
            return True

    return False
