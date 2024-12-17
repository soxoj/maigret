import asyncio
import json
import re
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from aiohttp import ClientSession, TCPConnector
from aiohttp_socks import ProxyConnector
import cloudscraper
from colorama import Fore, Style

from .activation import import_aiohttp_cookies
from .result import MaigretCheckResult
from .settings import Settings
from .sites import MaigretDatabase, MaigretEngine, MaigretSite
from .utils import get_random_user_agent
from .checking import site_self_check
from .utils import get_match_ratio, generate_random_username


class CloudflareSession:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    async def get(self, *args, **kwargs):
        await asyncio.sleep(0)
        res = self.scraper.get(*args, **kwargs)
        self.last_text = res.text
        self.status = res.status_code
        return self

    def status_code(self):
        return self.status

    async def text(self):
        await asyncio.sleep(0)
        return self.last_text

    async def close(self):
        pass


class Submitter:
    HEADERS = {
        "User-Agent": get_random_user_agent(),
    }

    SEPARATORS = "\"'\n"

    RATIO = 0.6
    TOP_FEATURES = 5
    URL_RE = re.compile(r"https?://(www\.)?")

    def __init__(self, db: MaigretDatabase, settings: Settings, logger, args):
        self.settings = settings
        self.args = args
        self.db = db
        self.logger = logger

        from aiohttp_socks import ProxyConnector

        proxy = self.args.proxy
        cookie_jar = None
        if args.cookie_file:
            if not os.path.exists(args.cookie_file):
                logger.error(f"Cookie file {args.cookie_file} does not exist!")
            else:
                cookie_jar = import_aiohttp_cookies(args.cookie_file)

        connector = ProxyConnector.from_url(proxy) if proxy else TCPConnector(ssl=False)
        connector.verify_ssl = False
        self.session = ClientSession(
            connector=connector, trust_env=True, cookie_jar=cookie_jar
        )

    async def close(self):
        await self.session.close()

    @staticmethod
    def get_alexa_rank(site_url_main):
        import requests
        import xml.etree.ElementTree as ElementTree

        url = f"http://data.alexa.com/data?cli=10&url={site_url_main}"
        xml_data = requests.get(url).text
        root = ElementTree.fromstring(xml_data)
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
        # Call the general function from the checking.py
        changes = await site_self_check(
            site=site,
            logger=self.logger,
            semaphore=semaphore,
            db=self.db,
            silent=silent,
            proxy=self.args.proxy,
            cookies=self.args.cookie_file,
            # Don't skip errors in submit mode - we need check both false positives/true negatives
            skip_errors=False,
        )
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

    async def detect_known_engine(
        self, url_exists, url_mainpage, session, follow_redirects, headers
    ) -> [List[MaigretSite], str]:

        session = session or self.session
        resp_text, _ = await self.get_html_response_to_compare(
            url_exists, session, follow_redirects, headers
        )

        for engine in self.db.engines:
            strs_to_check = engine.__dict__.get("presenseStrs")
            if strs_to_check and resp_text:
                all_strs_in_response = True
                for s in strs_to_check:
                    if s not in resp_text:
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
                            "name": url_mainpage.split("//")[1].split("/")[0],
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

                    return sites, resp_text

        return [], resp_text

    @staticmethod
    def extract_username_dialog(url):
        url_parts = url.rstrip("/").split("/")
        supposed_username = url_parts[-1].strip('@')
        entered_username = input(
            f"{Fore.GREEN}[?] Is \"{supposed_username}\" a valid username? If not, write it manually: {Style.RESET_ALL}"
        )
        return entered_username if entered_username else supposed_username

    # TODO: replace with checking.py/SimpleAiohttpChecker call
    @staticmethod
    async def get_html_response_to_compare(
        url: str, session: ClientSession = None, redirects=False, headers: Dict = None
    ):
        async with session.get(
            url, allow_redirects=redirects, headers=headers
        ) as response:
            # Try different encodings or fallback to 'ignore' errors
            try:
                html_response = await response.text(encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    html_response = await response.text(encoding='latin1')
                except UnicodeDecodeError:
                    html_response = await response.text(errors='ignore')
            return html_response, response.status

    async def check_features_manually(
        self,
        username: str,
        url_exists: str,
        cookie_filename="",  # TODO: use cookies
        session: ClientSession = None,
        follow_redirects=False,
        headers: dict = None,
    ) -> Tuple[List[str], List[str], str, str]:

        random_username = generate_random_username()
        url_of_non_existing_account = url_exists.lower().replace(
            username.lower(), random_username
        )

        try:
            session = session or self.session
            first_html_response, first_status = await self.get_html_response_to_compare(
                url_exists, session, follow_redirects, headers
            )
            second_html_response, second_status = (
                await self.get_html_response_to_compare(
                    url_of_non_existing_account, session, follow_redirects, headers
                )
            )
            await session.close()
        except Exception as e:
            self.logger.error(
                f"Error while getting HTTP response for username {username}: {e}",
                exc_info=True,
            )
            return None, None, str(e), random_username

        self.logger.info(f"URL with existing account: {url_exists}")
        self.logger.info(
            f"HTTP response status for URL with existing account: {first_status}"
        )
        self.logger.info(
            f"HTTP response length URL with existing account: {len(first_html_response)}"
        )
        self.logger.debug(first_html_response)

        self.logger.info(f"URL with existing account: {url_of_non_existing_account}")
        self.logger.info(
            f"HTTP response status for URL with non-existing account: {second_status}"
        )
        self.logger.info(
            f"HTTP response length URL with non-existing account: {len(second_html_response)}"
        )
        self.logger.debug(second_html_response)

        # TODO: filter by errors, move to dialog function
        if (
            "/cdn-cgi/challenge-platform" in first_html_response
            or "\t\t\t\tnow: " in first_html_response
            or "Sorry, you have been blocked" in first_html_response
        ):
            self.logger.info("Cloudflare detected, skipping")
            return None, None, "Cloudflare detected, skipping", random_username

        tokens_a = set(re.split(f'[{self.SEPARATORS}]', first_html_response))
        tokens_b = set(re.split(f'[{self.SEPARATORS}]', second_html_response))

        a_minus_b = tokens_a.difference(tokens_b)
        b_minus_a = tokens_b.difference(tokens_a)

        a_minus_b = list(map(lambda x: x.strip('\\'), a_minus_b))
        b_minus_a = list(map(lambda x: x.strip('\\'), b_minus_a))

        # Filter out strings containing usernames
        a_minus_b = [s for s in a_minus_b if username.lower() not in s.lower()]
        b_minus_a = [s for s in b_minus_a if random_username.lower() not in s.lower()]

        def filter_tokens(token: str, html_response: str) -> bool:
            is_in_html = token in html_response
            is_long_str = len(token) >= 50
            is_number = re.match(r'^\d\.?\d+$', token) or re.match(r':^\d+$', token)
            is_whitelisted_number = token in ['200', '404', '403']

            return not (
                is_in_html or is_long_str or (is_number and not is_whitelisted_number)
            )

        a_minus_b = list(
            filter(lambda t: filter_tokens(t, second_html_response), a_minus_b)
        )
        b_minus_a = list(
            filter(lambda t: filter_tokens(t, first_html_response), b_minus_a)
        )

        if len(a_minus_b) == len(b_minus_a) == 0:
            return (
                None,
                None,
                "HTTP responses for pages with existing and non-existing accounts are the same",
                random_username,
            )

        match_fun = get_match_ratio(self.settings.presence_strings)

        presence_list = sorted(a_minus_b, key=match_fun, reverse=True)[
            : self.TOP_FEATURES
        ]
        absence_list = sorted(b_minus_a, key=match_fun, reverse=True)[
            : self.TOP_FEATURES
        ]

        self.logger.info(f"Detected presence features: {presence_list}")
        self.logger.info(f"Detected absence features: {absence_list}")

        return presence_list, absence_list, "Found", random_username

    async def add_site(self, site):
        sem = asyncio.Semaphore(1)
        print(
            f"{Fore.BLUE}{Style.BRIGHT}[*] Adding site {site.name}, let's check it...{Style.RESET_ALL}"
        )

        result = await self.site_self_check(site, sem)
        if result["disabled"]:
            print(f"Checks failed for {site.name}, please, verify them manually.")
            return {
                "valid": False,
                "reason": "checks_failed",
            }

        while True:
            print("\nAvailable fields to edit:")
            editable_fields = {
                '1': 'name',
                '2': 'tags',
                '3': 'url',
                '4': 'url_main',
                '5': 'username_claimed',
                '6': 'username_unclaimed',
                '7': 'presense_strs',
                '8': 'absence_strs',
            }

            for num, field in editable_fields.items():
                current_value = getattr(site, field)
                print(f"{num}. {field} (current: {current_value})")

            print("0. finish editing")
            print("10. reject and block domain")
            print("11. invalid params, remove")

            choice = input("\nSelect field number to edit (0-8): ").strip()

            if choice == '0':
                break

            if choice == '10':
                return {
                    "valid": False,
                    "reason": "manual block",
                }

            if choice == '11':
                return {
                    "valid": False,
                    "reason": "remove",
                }

            if choice in editable_fields:
                field = editable_fields[choice]
                current_value = getattr(site, field)
                new_value = input(
                    f"Enter new value for {field} (current: {current_value}): "
                ).strip()

                if field in ['tags', 'presense_strs', 'absence_strs']:
                    new_value = list(map(str.strip, new_value.split(',')))

                if new_value:
                    setattr(site, field, new_value)
                    print(f"Updated {field} to: {new_value}")

        self.logger.info(site.json)
        self.db.update_site(site)
        return {
            "valid": True,
        }

    async def dialog(self, url_exists, cookie_file):
        """
        An implementation of the submit mode:
        - User provides a URL of a existing social media account
        - Maigret tries to detect the site engine and understand how to check
          for account presence with HTTP responses analysis
        - If detection succeeds, Maigret generates a new site entry/replace old one in the database
        """
        old_site = None
        additional_options_enabled = self.logger.level in (
            logging.DEBUG,
            logging.WARNING,
        )

        domain_raw = self.URL_RE.sub("", url_exists).strip().strip("/")
        domain_raw = domain_raw.split("/")[0]
        self.logger.info('Domain is %s', domain_raw)

        # check for existence
        matched_sites = list(
            filter(lambda x: domain_raw in x.url_main + x.url, self.db.sites)
        )

        if matched_sites:
            # TODO: update the existing site
            print(
                f"{Fore.YELLOW}[!] Sites with domain \"{domain_raw}\" already exists in the Maigret database!{Style.RESET_ALL}"
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

            if (
                input(
                    f"{Fore.GREEN}[?] Do you want to continue? [yN] {Style.RESET_ALL}"
                ).lower()
                in "n"
            ):
                return False

            site_names = [site.name for site in matched_sites]
            site_name = (
                input(
                    f"{Fore.GREEN}[?] Which site do you want to update in case of success? 1st by default. [{', '.join(site_names)}] {Style.RESET_ALL}"
                )
                or matched_sites[0].name
            )
            old_site = next(
                (site for site in matched_sites if site.name == site_name), None
            )
            print(
                f'{Fore.GREEN}[+] We will update site "{old_site.name}" in case of success.{Style.RESET_ALL}'
            )

        # Check if the site check is ordinary or not
        if old_site and (old_site.url_probe or old_site.activation):
            skip = input(
                f"{Fore.RED}[!] The site check depends on activation / probing mechanism! Consider to update it manually. Continue? [yN]{Style.RESET_ALL}"
            )
            if skip.lower() in ['n', '']:
                return False

            # TODO: urlProbe support
            # TODO: activation support

        url_mainpage = self.extract_mainpage_url(url_exists)

        # headers update
        custom_headers = dict(self.HEADERS)
        while additional_options_enabled:
            header_key = input(
                f'{Fore.GREEN}[?] Specify custom header if you need or just press Enter to skip. Header name: {Style.RESET_ALL}'
            )
            if not header_key:
                break
            header_value = input(f'{Fore.GREEN}[?] Header value: {Style.RESET_ALL}')
            custom_headers[header_key.strip()] = header_value.strip()

        # redirects settings update
        redirects = False
        if additional_options_enabled:
            redirects = (
                'y'
                in input(
                    f'{Fore.GREEN}[?] Should we do redirects automatically? [yN] {Style.RESET_ALL}'
                ).lower()
            )

        print('Detecting site engine, please wait...')
        sites = []
        text = None
        try:
            sites, text = await self.detect_known_engine(
                url_exists,
                url_exists,
                session=None,
                follow_redirects=redirects,
                headers=custom_headers,
            )
        except KeyboardInterrupt:
            print('Engine detect process is interrupted.')

        if 'cloudflare' in text.lower():
            print(
                'Cloudflare protection detected. I will use cloudscraper for further work'
            )
            # self.session = CloudflareSession()

        if not sites:
            print("Unable to detect site engine, lets generate checking features")

            supposed_username = self.extract_username_dialog(url_exists)
            self.logger.info(f"Supposed username: {supposed_username}")

            # TODO: pass status_codes
            # check it here and suggest to enable / auto-enable redirects
            presence_list, absence_list, status, non_exist_username = (
                await self.check_features_manually(
                    username=supposed_username,
                    url_exists=url_exists,
                    cookie_filename=cookie_file,
                    follow_redirects=redirects,
                    headers=custom_headers,
                )
            )

            if status == "Found":
                site_data = {
                    "absenceStrs": absence_list,
                    "presenseStrs": presence_list,
                    "url": url_exists.replace(supposed_username, '{username}'),
                    "urlMain": url_mainpage,
                    "usernameClaimed": supposed_username,
                    "usernameUnclaimed": non_exist_username,
                    "headers": custom_headers,
                    "checkType": "message",
                }
                self.logger.info(json.dumps(site_data, indent=4))

                if custom_headers != self.HEADERS:
                    site_data['headers'] = custom_headers

                site = MaigretSite(url_mainpage.split("/")[-1], site_data)
                sites.append(site)

            else:
                print(
                    f"{Fore.RED}[!] The check for site failed! Reason: {status}{Style.RESET_ALL}"
                )
                return False

        self.logger.debug(sites[0].__dict__)

        sem = asyncio.Semaphore(1)

        print(f"{Fore.GREEN}[*] Checking, please wait...{Style.RESET_ALL}")
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
                f"{Fore.RED}[!] The check for site '{chosen_site.name}' failed!{Style.RESET_ALL}"
            )
            print(
                "Try to run this mode again and increase features count or choose others."
            )
            self.logger.debug(json.dumps(chosen_site.json))
            return False
        else:
            if (
                input(
                    f"{Fore.GREEN}[?] Site {chosen_site.name} successfully checked. Do you want to save it in the Maigret DB? [Yn] {Style.RESET_ALL}"
                )
                .lower()
                .strip("y")
            ):
                return False

        if self.args.verbose:
            self.logger.info(
                "Verbose mode is enabled, additional settings are available"
            )
            source = input(
                f"{Fore.GREEN}[?] Name the source site if it is mirror: {Style.RESET_ALL}"
            )
            if source:
                chosen_site.source = source

        default_site_name = old_site.name if old_site else chosen_site.name
        new_name = (
            input(
                f"{Fore.GREEN}[?] Change site name if you want [{default_site_name}]: {Style.RESET_ALL}"
            )
            or default_site_name
        )
        if new_name != default_site_name:
            self.logger.info(f"New site name is {new_name}")
            chosen_site.name = new_name

        default_tags_str = ""
        if old_site:
            default_tags_str = f' [{", ".join(old_site.tags)}]'

        new_tags = input(
            f"{Fore.GREEN}[?] Site tags{default_tags_str}: {Style.RESET_ALL}"
        )
        if new_tags:
            chosen_site.tags = list(map(str.strip, new_tags.split(',')))
        else:
            chosen_site.tags = []
        self.logger.info(f"Site tags are: {', '.join(chosen_site.tags)}")
        # rank = Submitter.get_alexa_rank(chosen_site.url_main)
        # if rank:
        #     print(f'New alexa rank: {rank}')
        #     chosen_site.alexa_rank = rank

        self.logger.info(chosen_site.json)
        site_data = chosen_site.strip_engine_data()
        self.logger.info(site_data.json)

        if old_site:
            # Update old site with new values and log changes
            fields_to_check = {
                'url': 'URL',
                'url_main': 'Main URL',
                'username_claimed': 'Username claimed',
                'username_unclaimed': 'Username unclaimed',
                'check_type': 'Check type',
                'presense_strs': 'Presence strings',
                'absence_strs': 'Absence strings',
                'tags': 'Tags',
                'source': 'Source',
                'headers': 'Headers',
            }

            for field, display_name in fields_to_check.items():
                old_value = getattr(old_site, field)
                new_value = getattr(site_data, field)
                if field == 'tags' and not new_tags:
                    continue
                if str(old_value) != str(new_value):
                    print(
                        f"{Fore.YELLOW}[*] '{display_name}' updated: {Fore.RED}{old_value} {Fore.YELLOW}to {Fore.GREEN}{new_value}{Style.RESET_ALL}"
                    )
                old_site.__dict__[field] = new_value

        # update the site
        final_site = old_site if old_site else site_data
        self.db.update_site(final_site)

        # save the db in file
        if self.args.db_file != self.settings.sites_db_path:
            print(
                f"{Fore.GREEN}[+] Maigret DB is saved to {self.args.db}.{Style.RESET_ALL}"
            )
            self.db.save_to_file(self.args.db)

        return True
