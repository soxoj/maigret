"""Maigret Sites Information"""
from __future__ import annotations
import json
import operator
import sys

import requests


class MaigretEngine:
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.__dict__.update(kwargs)


class MaigretSite:
    def __init__(self, name, url_main, url_username_format, popularity_rank,
                 username_claimed, username_unclaimed,
                 information):
        """Create Site Information Object.

        Contains information about a specific web site.

        Keyword Arguments:
        self                   -- This object.
        name                   -- String which identifies site.
        url_main               -- String containing URL for home of site.
        url_username_format    -- String containing URL for Username format
                                  on site.
                                  NOTE:  The string should contain the
                                         token "{}" where the username should
                                         be substituted.  For example, a string
                                         of "https://somesite.com/users/{}"
                                         indicates that the individual
                                         usernames would show up under the
                                         "https://somesite.com/users/" area of
                                         the web site.
        popularity_rank        -- Integer indicating popularity of site.
                                  In general, smaller numbers mean more
                                  popular ("0" or None means ranking
                                  information not available).
        username_claimed       -- String containing username which is known
                                  to be claimed on web site.
        username_unclaimed     -- String containing username which is known
                                  to be unclaimed on web site.
        information            -- Dictionary containing all known information
                                  about web site.
                                  NOTE:  Custom information about how to
                                         actually detect the existence of the
                                         username will be included in this
                                         dictionary.  This information will
                                         be needed by the detection method,
                                         but it is only recorded in this
                                         object for future use.

        Return Value:
        Nothing.
        """

        self.name = name
        self.url_main = url_main
        self.url_username_format = url_username_format

        if (popularity_rank is None) or (popularity_rank == 0):
            # We do not know the popularity, so make site go to bottom of list.
            popularity_rank = sys.maxsize
        self.popularity_rank = popularity_rank

        self.username_claimed = username_claimed
        self.username_unclaimed = username_unclaimed
        self.information = information
        self.disabled = information.get('disabled', False)
        self.similar_search = information.get('similarSearch', False)
        self.ignore_403 = information.get('ignore_403', False)
        self.tags = information.get('tags', [])

        self.type = information.get('type', 'username')
        self.headers = information.get('headers', {})
        self.errors = information.get('errors', {})
        self.url_subpath = information.get('urlSubpath', '')
        self.regex_check = information.get('regexCheck', None)
        self.url_probe = information.get('urlProbe', None)
        self.check_type = information.get('errorType', '')
        self.request_head_only = information.get('request_head_only', '')

        self.presense_strs = information.get('presenseStrs', [])
        self.absence_strs = information.get('errorMsg', [])
        self.request_future = None


    def __str__(self):
        return f"{self.name} ({self.url_main})"


class MaigretDatabase:
    def __init__(self):
        self._sites = []
        self._engines = []

    @property
    def sites(self: MaigretDatabase):
        return self._sites

    @property
    def sites_dict(self):
        return {site.name: site for site in self._sites}
    

    @property
    def engines(self: MaigretDatabase):
        return self._engines


    def load_from_json(self: MaigretDatabase, json_data: dict) -> MaigretDatabase:
        # Add all of site information from the json file to internal site list.
        site_data = json_data.get("sites")
        engines_data = json_data.get("engines")

        for engine_name in engines_data:
            self._engines.append(MaigretEngine(engine_name, engines_data[engine_name]))

        for site_name in site_data:
            try:
                site = {}
                site_user_info = site_data[site_name]
                # If popularity unknown, make site be at bottom of list.
                popularity_rank = site_user_info.get("rank", sys.maxsize)

                if 'engine' in site_user_info:
                    engine_info = engines_data[site_user_info['engine']]['site']
                    site.update(engine_info)

                site.update(site_user_info)

                maigret_site = MaigretSite(site_name,
                                    site["urlMain"],
                                    site["url"],
                                    popularity_rank,
                                    site["username_claimed"],
                                    site["username_unclaimed"],
                                    site
                                    )

                self._sites.append(maigret_site)
            except KeyError as error:
                raise ValueError(f"Problem parsing json content for site {site_name}: "
                                 f"Missing attribute {str(error)}."
                                 )

        return self


    def load_from_str(self: MaigretDatabase, db_str: str) -> MaigretDatabase:
        try:
            data = json.loads(db_str)
        except Exception as error:
            raise ValueError(f"Problem parsing json contents from str"
                             f"'{db_str[:50]}'...:  {str(error)}."
                             )

        return self.load_from_json(data)


    def load_from_url(self: MaigretDatabase, url: str) -> MaigretDatabase:
        is_url_valid = url.startswith('http://') or url.startswith('https://')

        if not is_url_valid:
            return False

        try:
            response = requests.get(url=url)
        except Exception as error:
            raise FileNotFoundError(f"Problem while attempting to access "
                                    f"data file URL '{url}':  "
                                    f"{str(error)}"
                                    )

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as error:
                raise ValueError(f"Problem parsing json contents at "
                                 f"'{url}':  {str(error)}."
                                 )
        else:
            raise FileNotFoundError(f"Bad response while accessing "
                                    f"data file URL '{url}'."
                                    )

        return self.load_from_json(data)


    def load_from_file(self: MaigretDatabase, filename: str) -> MaigretDatabase:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                except Exception as error:
                    raise ValueError(f"Problem parsing json contents from "
                                     f"file '{filename}':  {str(error)}."
                                     )
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Problem while attempting to access "
                                    f"data file '{filename}'."
                                    )

        return self.load_from_json(data)


    def site_name_list(self: MaigretDatabase, popularity_rank=False):
        """Get Site Name List.

        Keyword Arguments:
        self                   -- This object.
        popularity_rank        -- Boolean indicating if list should be sorted
                                  by popularity rank.
                                  Default value is False.
                                  NOTE:  List is sorted in ascending
                                         alphabetical order is popularity rank
                                         is not requested.

        Return Value:
        List of strings containing names of sites.
        """

        if popularity_rank:
            # Sort in ascending popularity rank order.
            site_rank_name = \
                sorted([(site.popularity_rank, site.name) for site in self],
                       key=operator.itemgetter(0)
                       )
            site_names = [name for _, name in site_rank_name]
        else:
            # Sort in ascending alphabetical order.
            site_names = sorted([site.name for site in self], key=str.lower)

        return site_names
