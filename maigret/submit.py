import asyncio
import re
from typing import List
import xml.etree.ElementTree as ET
import requests

from .activation import import_aiohttp_cookies
from .checking import maigret
from .result import QueryStatus
from .settings import Settings
from .sites import MaigretDatabase, MaigretSite, MaigretEngine
from .utils import get_random_user_agent, get_match_ratio


class Submitter:
    HEADERS = {
        "User-Agent": get_random_user_agent(),
    }

    SEPARATORS = "\"'"

    RATIO = 0.6
    TOP_FEATURES = 5
    URL_RE = re.compile(r"https?://(www\.)?")

    def __init__(self, db: MaigretDatabase, settings: Settings, logger):
        self.settings = settings
        self.db = db
        self.logger = logger

    @staticmethod
    def get_alexa_rank(site_url_main):
        url = f"http://data.alexa.com/data?cli=10&url={site_url_main}"
        xml_data = requests.get(url).text
        root = ET.fromstring(xml_data)
        alexa_rank = 0

        try:
            alexa_rank = int(root.find('.//REACH').attrib['RANK'])
        except Exception:
            pass

        return alexa_rank

    @staticmethod
    def extract_mainpage_url(url):
        return "/".join(url.split("/", 3)[:3])

    async def site_self_check(self, site, semaphore, silent=False):
        changes = {
            "disabled": False,
        }

        check_data = [
            (site.username_claimed, QueryStatus.CLAIMED),
            (site.username_unclaimed, QueryStatus.AVAILABLE),
        ]

        self.logger.info(f"Checking {site.name}...")

        for username, status in check_data:
            results_dict = await maigret(
                username=username,
                site_dict={site.name: site},
                logger=self.logger,
                timeout=30,
                id_type=site.type,
                forced=True,
                no_progressbar=True,
            )

            # don't disable entries with other ids types
            # TODO: make normal checking
            if site.name not in results_dict:
                self.logger.info(results_dict)
                changes["disabled"] = True
                continue

            result = results_dict[site.name]["status"]

            site_status = result.status

            if site_status != status:
                if site_status == QueryStatus.UNKNOWN:
                    msgs = site.absence_strs
                    etype = site.check_type
                    self.logger.warning(
                        "Error while searching '%s' in %s: %s, %s, check type %s",
                        username,
                        site.name,
                        result.context,
                        msgs,
                        etype,
                    )
                    # don't disable in case of available username
                    if status == QueryStatus.CLAIMED:
                        changes["disabled"] = True
                elif status == QueryStatus.CLAIMED:
                    self.logger.warning(
                        f"Not found `{username}` in {site.name}, must be claimed"
                    )
                    self.logger.info(results_dict[site.name])
                    changes["disabled"] = True
                else:
                    self.logger.warning(
                        f"Found `{username}` in {site.name}, must be available"
                    )
                    self.logger.info(results_dict[site.name])
                    changes["disabled"] = True

        self.logger.info(f"Site {site.name} checking is finished")

        return changes

    def generate_additional_fields_dialog(self, engine: MaigretEngine, dialog):
        fields = {}
        if 'urlSubpath' in engine.site.get('url', ''):
            msg = (
                'Detected engine suppose additional URL subpath using (/forum/, /blog/, etc). '
                'Enter in manually if it exists: '
            )
            subpath = input(msg).strip('/')
            if subpath:
                fields['urlSubpath'] = f'/{subpath}'
        return fields

    async def detect_known_engine(self, url_exists, url_mainpage) -> List[MaigretSite]:
        try:
            r = requests.get(url_mainpage)
            self.logger.debug(r.text)
        except Exception as e:
            self.logger.warning(e)
            print("Some error while checking main page")
            return []

        for engine in self.db.engines:
            strs_to_check = engine.__dict__.get("presenseStrs")
            if strs_to_check and r and r.text:
                all_strs_in_response = True
                for s in strs_to_check:
                    if s not in r.text:
                        all_strs_in_response = False
                sites = []
                if all_strs_in_response:
                    engine_name = engine.__dict__.get("name")

                    print(f"Detected engine {engine_name} for site {url_mainpage}")

                    usernames_to_check = self.settings.supposed_usernames
                    supposed_username = self.extract_username_dialog(url_exists)
                    if supposed_username:
                        usernames_to_check = [supposed_username] + usernames_to_check

                    add_fields = self.generate_additional_fields_dialog(
                        engine, url_exists
                    )

                    for u in usernames_to_check:
                        site_data = {
                            "urlMain": url_mainpage,
                            "name": url_mainpage.split("//")[1],
                            "engine": engine_name,
                            "usernameClaimed": u,
                            "usernameUnclaimed": "noonewouldeverusethis7",
                            **add_fields,
                        }
                        self.logger.info(site_data)

                        maigret_site = MaigretSite(
                            url_mainpage.split("/")[-1], site_data
                        )
                        maigret_site.update_from_engine(
                            self.db.engines_dict[engine_name]
                        )
                        sites.append(maigret_site)

                    return sites

        return []

    def extract_username_dialog(self, url):
        url_parts = url.rstrip("/").split("/")
        supposed_username = url_parts[-1].strip('@')
        entered_username = input(
            f'Is "{supposed_username}" a valid username? If not, write it manually: '
        )
        return entered_username if entered_username else supposed_username

    async def check_features_manually(
        self, url_exists, url_mainpage, cookie_file, redirects=False
    ):
        custom_headers = {}
        while True:
            header_key = input(
                'Specify custom header if you need or just press Enter to skip. Header name: '
            )
            if not header_key:
                break
            header_value = input('Header value: ')
            custom_headers[header_key.strip()] = header_value.strip()

        supposed_username = self.extract_username_dialog(url_exists)
        non_exist_username = "noonewouldeverusethis7"

        url_user = url_exists.replace(supposed_username, "{username}")
        url_not_exists = url_exists.replace(supposed_username, non_exist_username)

        headers = dict(self.HEADERS)
        headers.update(custom_headers)

        # cookies
        cookie_dict = None
        if cookie_file:
            self.logger.info(f'Use {cookie_file} for cookies')
            cookie_jar = import_aiohttp_cookies(cookie_file)
            cookie_dict = {c.key: c.value for c in cookie_jar}

        exists_resp = requests.get(
            url_exists, cookies=cookie_dict, headers=headers, allow_redirects=redirects
        )
        self.logger.debug(url_exists)
        self.logger.debug(exists_resp.status_code)
        self.logger.debug(exists_resp.text)

        non_exists_resp = requests.get(
            url_not_exists,
            cookies=cookie_dict,
            headers=headers,
            allow_redirects=redirects,
        )
        self.logger.debug(url_not_exists)
        self.logger.debug(non_exists_resp.status_code)
        self.logger.debug(non_exists_resp.text)

        a = exists_resp.text
        b = non_exists_resp.text

        tokens_a = set(re.split(f'[{self.SEPARATORS}]', a))
        tokens_b = set(re.split(f'[{self.SEPARATORS}]', b))

        a_minus_b = tokens_a.difference(tokens_b)
        b_minus_a = tokens_b.difference(tokens_a)

        if len(a_minus_b) == len(b_minus_a) == 0:
            print("The pages for existing and non-existing account are the same!")

        top_features_count = int(
            input(
                f"Specify count of features to extract [default {self.TOP_FEATURES}]: "
            )
            or self.TOP_FEATURES
        )

        match_fun = get_match_ratio(self.settings.presence_strings)

        presence_list = sorted(a_minus_b, key=match_fun, reverse=True)[
            :top_features_count
        ]

        print("Detected text features of existing account: " + ", ".join(presence_list))
        features = input("If features was not detected correctly, write it manually: ")

        if features:
            presence_list = list(map(str.strip, features.split(",")))

        absence_list = sorted(b_minus_a, key=match_fun, reverse=True)[
            :top_features_count
        ]
        print(
            "Detected text features of non-existing account: " + ", ".join(absence_list)
        )
        features = input("If features was not detected correctly, write it manually: ")

        if features:
            absence_list = list(map(str.strip, features.split(",")))

        site_data = {
            "absenceStrs": absence_list,
            "presenseStrs": presence_list,
            "url": url_user,
            "urlMain": url_mainpage,
            "usernameClaimed": supposed_username,
            "usernameUnclaimed": non_exist_username,
            "checkType": "message",
        }

        if headers != self.HEADERS:
            site_data['headers'] = headers

        site = MaigretSite(url_mainpage.split("/")[-1], site_data)
        return site

    async def dialog(self, url_exists, cookie_file):
        domain_raw = self.URL_RE.sub("", url_exists).strip().strip("/")
        domain_raw = domain_raw.split("/")[0]
        self.logger.info('Domain is %s', domain_raw)

        # check for existence
        matched_sites = list(
            filter(lambda x: domain_raw in x.url_main + x.url, self.db.sites)
        )

        if matched_sites:
            print(
                f'Sites with domain "{domain_raw}" already exists in the Maigret database!'
            )
            status = lambda s: "(disabled)" if s.disabled else ""
            url_block = lambda s: f"\n\t{s.url_main}\n\t{s.url}"
            print(
                "\n".join(
                    [
                        f"{site.name} {status(site)}{url_block(site)}"
                        for site in matched_sites
                    ]
                )
            )

            if input("Do you want to continue? [yN] ").lower() in "n":
                return False

        url_mainpage = self.extract_mainpage_url(url_exists)

        print('Detecting site engine, please wait...')
        sites = []
        try:
            sites = await self.detect_known_engine(url_exists, url_mainpage)
        except KeyboardInterrupt:
            print('Engine detect process is interrupted.')

        if not sites:
            print("Unable to detect site engine, lets generate checking features")
            sites = [
                await self.check_features_manually(
                    url_exists, url_mainpage, cookie_file
                )
            ]

        self.logger.debug(sites[0].__dict__)

        sem = asyncio.Semaphore(1)

        print("Checking, please wait...")
        found = False
        chosen_site = None
        for s in sites:
            chosen_site = s
            result = await self.site_self_check(s, sem)
            if not result["disabled"]:
                found = True
                break

        if not found:
            print(
                f"Sorry, we couldn't find params to detect account presence/absence in {chosen_site.name}."
            )
            print(
                "Try to run this mode again and increase features count or choose others."
            )
            return False
        else:
            if (
                input(
                    f"Site {chosen_site.name} successfully checked. Do you want to save it in the Maigret DB? [Yn] "
                )
                .lower()
                .strip("y")
            ):
                return False

        chosen_site.name = input("Change site name if you want: ") or chosen_site.name
        chosen_site.tags = list(map(str.strip, input("Site tags: ").split(',')))
        rank = Submitter.get_alexa_rank(chosen_site.url_main)
        if rank:
            print(f'New alexa rank: {rank}')
            chosen_site.alexa_rank = rank

        self.logger.debug(chosen_site.json)
        site_data = chosen_site.strip_engine_data()
        self.logger.debug(site_data.json)
        self.db.update_site(site_data)
        return True
