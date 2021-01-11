# -*- coding: future_annotations -*-
"""Maigret Sites Information"""
import copy
import json
import operator
import sys

import requests

from .utils import CaseConverter


class MaigretEngine:
    def __init__(self, name, data):
        self.name = name
        self.site = {}
        self.__dict__.update(data)

    @property
    def json(self):
        return self.__dict__


class MaigretSite:
    def __init__(self, name, information):
        self.name = name

        self.disabled = False
        self.similar_search = False
        self.ignore_403 = False
        self.tags = []

        self.type = 'username'
        self.headers = {}
        self.errors = {}
        self.url_subpath = ''
        self.regex_check = None
        self.url_probe = None
        self.check_type = ''
        self.request_head_only = ''

        self.presense_strs = []
        self.absence_strs = []

        self.engine = None
        self.engine_data = {}
        self.engine_obj = None
        self.request_future = None
        self.alexa_rank = None

        for k, v in information.items():
            self.__dict__[CaseConverter.camel_to_snake(k)] = v

        if (self.alexa_rank is None) or (self.alexa_rank == 0):
            # We do not know the popularity, so make site go to bottom of list.
            self.alexa_rank = sys.maxsize


    def __str__(self):
        return f"{self.name} ({self.url_main})"

    @property
    def json(self):
        result = {}
        for k, v in self.__dict__.items():
            # convert to camelCase
            field = CaseConverter.snake_to_camel(k)
            # strip empty elements
            if v in (False, '', [], {}, None, sys.maxsize, 'username'):
                continue
            if field in ['name', 'engineData', 'requestFuture', 'detectedEngine', 'engineObj']:
                continue
            result[field] = v

        return result

    def update(self, updates: dict) -> MaigretSite:
        self.__dict__.update(updates)

        return self

    def update_from_engine(self, engine: MaigretEngine) -> MaigretSite:
        engine_data = engine.site
        for k, v in engine_data.items():
            field = CaseConverter.camel_to_snake(k)
            if isinstance(v, dict):
                # TODO: assertion of intersecting keys
                # update dicts like errors
                self.__dict__.get(field, {}).update(v)
            else:
                self.__dict__[field] = v

        self.engine_obj = engine

        return self

    def strip_engine_data(self) -> MaigretSite:
        if not self.engine_obj:
            return self

        self.request_future = None
        self_copy = copy.deepcopy(self)
        engine_data = self_copy.engine_obj.site
        for field in engine_data.keys():
            if isinstance(engine_data[field], dict):
                for k in engine_data[field].keys():
                    del self_copy.__dict__[field][k]
                continue

            if field in list(self_copy.__dict__.keys()):
                del self_copy.__dict__[field]
            if CaseConverter.camel_to_snake(field) in list(self_copy.__dict__.keys()):
                del self_copy.__dict__[CaseConverter.camel_to_snake(field)]

        return self_copy


class MaigretDatabase:
    def __init__(self):
        self._sites = []
        self._engines = []

    @property
    def sites(self):
        return self._sites

    @property
    def sites_dict(self):
        return {site.name: site for site in self._sites}

    def ranked_sites_dict(self, reverse=False, top=sys.maxsize, tags=[], names=[]):
        normalized_names = list(map(str.lower, names))
        normalized_tags = list(map(str.lower, tags))

        is_tags_ok = lambda x: set(x.tags).intersection(set(normalized_tags))
        is_name_ok = lambda x: x.name.lower() in normalized_names
        is_engine_ok = lambda x: isinstance(x.engine, str) and x.engine.lower() in normalized_tags

        if not tags and not names:
            filtered_list = self.sites
        else:
            filtered_list = [s for s in self.sites if is_tags_ok(s) or is_name_ok(s) or is_engine_ok(s)]

        sorted_list = sorted(filtered_list, key=lambda x: x.alexa_rank, reverse=reverse)[:top]
        return {site.name: site for site in sorted_list}

    @property
    def engines(self):
        return self._engines

    @property
    def engines_dict(self):
        return {engine.name: engine for engine in self._engines}

    def update_site(self, site: MaigretSite) -> MaigretDatabase:
        for s in self._sites:
            if s.name == site.name:
                s = site
                return self

        self._sites.append(site)
        return self

    def save_to_file(self, filename: str) -> MaigretDatabase:
        db_data = {
            'sites': {site.name: site.strip_engine_data().json for site in self._sites},
            'engines': {engine.name: engine.json for engine in self._engines},
        }

        json_data = json.dumps(db_data, indent=4)

        with open(filename, 'w') as f:
            f.write(json_data)

        return self


    def load_from_json(self, json_data: dict) -> MaigretDatabase:
        # Add all of site information from the json file to internal site list.
        site_data = json_data.get("sites", {})
        engines_data = json_data.get("engines", {})

        for engine_name in engines_data:
            self._engines.append(MaigretEngine(engine_name, engines_data[engine_name]))

        for site_name in site_data:
            try:
                maigret_site = MaigretSite(site_name, site_data[site_name])

                engine = site_data[site_name].get('engine')
                if engine:
                    maigret_site.update_from_engine(self.engines_dict[engine])

                self._sites.append(maigret_site)
            except KeyError as error:
                raise ValueError(f"Problem parsing json content for site {site_name}: "
                                 f"Missing attribute {str(error)}."
                                 )

        return self


    def load_from_str(self, db_str: str) -> MaigretDatabase:
        try:
            data = json.loads(db_str)
        except Exception as error:
            raise ValueError(f"Problem parsing json contents from str"
                             f"'{db_str[:50]}'...:  {str(error)}."
                             )

        return self.load_from_json(data)


    def load_from_url(self, url: str) -> MaigretDatabase:
        is_url_valid = url.startswith('http://') or url.startswith('https://')

        if not is_url_valid:
            raise FileNotFoundError(f"Invalid data file URL '{url}'.")

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


    def load_from_file(self, filename: str) -> MaigretDatabase:
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
