# ****************************** -*-
"""Maigret Sites Information"""
import copy
import json
import sys
from typing import Optional, List, Dict, Any, Tuple

import requests

from .utils import CaseConverter, URLMatcher, is_country_tag


class MaigretEngine:
    site: Dict[str, Any] = {}

    def __init__(self, name, data):
        self.name = name
        self.__dict__.update(data)

    @property
    def json(self):
        return self.__dict__


class MaigretSite:
    NOT_SERIALIZABLE_FIELDS = [
        "name",
        "engineData",
        "requestFuture",
        "detectedEngine",
        "engineObj",
        "stats",
        "urlRegexp",
    ]

    username_claimed = ""
    username_unclaimed = ""
    url_subpath = ""
    url_main = ""
    url = ""
    disabled = False
    similar_search = False
    ignore403 = False
    tags: List[str] = []

    type = "username"
    headers: Dict[str, str] = {}
    errors: Dict[str, str] = {}
    activation: Dict[str, Any] = {}
    regex_check = None
    url_probe = None
    check_type = ""
    request_head_only = ""
    get_params: Dict[str, Any] = {}

    presense_strs: List[str] = []
    absence_strs: List[str] = []
    stats: Dict[str, Any] = {}

    engine = None
    engine_data: Dict[str, Any] = {}
    engine_obj: Optional["MaigretEngine"] = None
    request_future = None
    alexa_rank = None
    source = None

    protocol = ''

    def __init__(self, name, information):
        self.name = name
        self.url_subpath = ""

        for k, v in information.items():
            self.__dict__[CaseConverter.camel_to_snake(k)] = v

        if (self.alexa_rank is None) or (self.alexa_rank == 0):
            # We do not know the popularity, so make site go to bottom of list.
            self.alexa_rank = sys.maxsize

        self.update_detectors()

    def __str__(self):
        return f"{self.name} ({self.url_main})"

    def update_detectors(self):
        if "url" in self.__dict__:
            url = self.url
            for group in ["urlMain", "urlSubpath"]:
                if group in url:
                    url = url.replace(
                        "{" + group + "}",
                        self.__dict__[CaseConverter.camel_to_snake(group)],
                    )

            self.url_regexp = URLMatcher.make_profile_url_regexp(url, self.regex_check)

    def detect_username(self, url: str) -> Optional[str]:
        if self.url_regexp:
            match_groups = self.url_regexp.match(url)
            if match_groups:
                return match_groups.groups()[-1].rstrip("/")

        return None

    def extract_id_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        if not self.url_regexp:
            return None

        match_groups = self.url_regexp.match(url)
        if not match_groups:
            return None

        _id = match_groups.groups()[-1].rstrip("/")
        _type = self.type

        return _id, _type

    @property
    def pretty_name(self):
        if self.source:
            return f"{self.name} [{self.source}]"
        return self.name

    @property
    def json(self):
        result = {}
        for k, v in self.__dict__.items():
            # convert to camelCase
            field = CaseConverter.snake_to_camel(k)
            # strip empty elements
            if v in (False, "", [], {}, None, sys.maxsize, "username"):
                continue
            if field in self.NOT_SERIALIZABLE_FIELDS:
                continue
            result[field] = v

        return result

    @property
    def errors_dict(self) -> dict:
        errors: Dict[str, str] = {}
        if self.engine_obj:
            errors.update(self.engine_obj.site.get('errors', {}))
        errors.update(self.errors)
        return errors

    def get_url_template(self) -> str:
        url = URLMatcher.extract_main_part(self.url)
        if url.startswith("{username}"):
            url = "SUBDOMAIN"
        elif url == "":
            url = f"{self.url} ({self.engine or 'no engine'})"
        else:
            parts = url.split("/")
            url = "/" + "/".join(parts[1:])
        return url

    def update(self, updates: "dict") -> "MaigretSite":
        self.__dict__.update(updates)
        self.update_detectors()

        return self

    def update_from_engine(self, engine: MaigretEngine) -> "MaigretSite":
        engine_data = engine.site
        for k, v in engine_data.items():
            field = CaseConverter.camel_to_snake(k)
            if isinstance(v, dict):
                # TODO: assertion of intersecting keys
                # update dicts like errors
                self.__dict__.get(field, {}).update(v)
            elif isinstance(v, list):
                self.__dict__[field] = self.__dict__.get(field, []) + v
            else:
                self.__dict__[field] = v

        self.engine_obj = engine
        self.update_detectors()

        return self

    def strip_engine_data(self) -> "MaigretSite":
        if not self.engine_obj:
            return self

        self.request_future = None
        self.url_regexp = None

        self_copy = copy.deepcopy(self)
        engine_data = self_copy.engine_obj and self_copy.engine_obj.site or {}
        site_data_keys = list(self_copy.__dict__.keys())

        for k in engine_data.keys():
            field = CaseConverter.camel_to_snake(k)
            is_exists = field in site_data_keys
            # remove dict keys
            if isinstance(engine_data[k], dict) and is_exists:
                for f in engine_data[k].keys():
                    if f in self_copy.__dict__[field]:
                        del self_copy.__dict__[field][f]
                continue
            # remove list items
            if isinstance(engine_data[k], list) and is_exists:
                for f in engine_data[k]:
                    if f in self_copy.__dict__[field]:
                        self_copy.__dict__[field].remove(f)
                continue
            if is_exists:
                del self_copy.__dict__[field]

        return self_copy


class MaigretDatabase:
    def __init__(self):
        self._tags: list = []
        self._sites: list = []
        self._engines: list = []

    @property
    def sites(self):
        return self._sites

    @property
    def sites_dict(self):
        return {site.name: site for site in self._sites}

    def ranked_sites_dict(
        self,
        reverse=False,
        top=sys.maxsize,
        tags=[],
        names=[],
        disabled=True,
        id_type="username",
    ):
        """
        Ranking and filtering of the sites list
        """
        normalized_names = list(map(str.lower, names))
        normalized_tags = list(map(str.lower, tags))

        is_name_ok = lambda x: x.name.lower() in normalized_names
        is_source_ok = lambda x: x.source and x.source.lower() in normalized_names
        is_engine_ok = (
            lambda x: isinstance(x.engine, str) and x.engine.lower() in normalized_tags
        )
        is_tags_ok = lambda x: set(x.tags).intersection(set(normalized_tags))
        is_protocol_in_tags = lambda x: x.protocol and x.protocol in normalized_tags
        is_disabled_needed = lambda x: not x.disabled or (
            "disabled" in tags or disabled
        )
        is_id_type_ok = lambda x: x.type == id_type

        filter_tags_engines_fun = (
            lambda x: not tags
            or is_engine_ok(x)
            or is_tags_ok(x)
            or is_protocol_in_tags(x)
        )
        filter_names_fun = lambda x: not names or is_name_ok(x) or is_source_ok(x)

        filter_fun = (
            lambda x: filter_tags_engines_fun(x)
            and filter_names_fun(x)
            and is_disabled_needed(x)
            and is_id_type_ok(x)
        )

        filtered_list = [s for s in self.sites if filter_fun(s)]

        sorted_list = sorted(
            filtered_list, key=lambda x: x.alexa_rank, reverse=reverse
        )[:top]
        return {site.name: site for site in sorted_list}

    @property
    def engines(self):
        return self._engines

    @property
    def engines_dict(self):
        return {engine.name: engine for engine in self._engines}

    def update_site(self, site: MaigretSite) -> "MaigretDatabase":
        for s in self._sites:
            if s.name == site.name:
                s = site
                return self

        self._sites.append(site)
        return self

    def save_to_file(self, filename: str) -> "MaigretDatabase":
        db_data = {
            "sites": {site.name: site.strip_engine_data().json for site in self._sites},
            "engines": {engine.name: engine.json for engine in self._engines},
            "tags": self._tags,
        }

        json_data = json.dumps(db_data, indent=4)

        with open(filename, "w") as f:
            f.write(json_data)

        return self

    def load_from_json(self, json_data: dict) -> "MaigretDatabase":
        # Add all of site information from the json file to internal site list.
        site_data = json_data.get("sites", {})
        engines_data = json_data.get("engines", {})
        tags = json_data.get("tags", [])

        self._tags += tags

        for engine_name in engines_data:
            self._engines.append(MaigretEngine(engine_name, engines_data[engine_name]))

        for site_name in site_data:
            try:
                maigret_site = MaigretSite(site_name, site_data[site_name])

                engine = site_data[site_name].get("engine")
                if engine:
                    maigret_site.update_from_engine(self.engines_dict[engine])

                self._sites.append(maigret_site)
            except KeyError as error:
                raise ValueError(
                    f"Problem parsing json content for site {site_name}: "
                    f"Missing attribute {str(error)}."
                )

        return self

    def load_from_str(self, db_str: "str") -> "MaigretDatabase":
        try:
            data = json.loads(db_str)
        except Exception as error:
            raise ValueError(
                f"Problem parsing json contents from str"
                f"'{db_str[:50]}'...:  {str(error)}."
            )

        return self.load_from_json(data)

    def load_from_url(self, url: str) -> "MaigretDatabase":
        is_url_valid = url.startswith("http://") or url.startswith("https://")

        if not is_url_valid:
            raise FileNotFoundError(f"Invalid data file URL '{url}'.")

        try:
            response = requests.get(url=url)
        except Exception as error:
            raise FileNotFoundError(
                f"Problem while attempting to access "
                f"data file URL '{url}':  "
                f"{str(error)}"
            )

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as error:
                raise ValueError(
                    f"Problem parsing json contents at " f"'{url}':  {str(error)}."
                )
        else:
            raise FileNotFoundError(
                f"Bad response while accessing " f"data file URL '{url}'."
            )

        return self.load_from_json(data)

    def load_from_file(self, filename: "str") -> "MaigretDatabase":
        try:
            with open(filename, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except Exception as error:
                    raise ValueError(
                        f"Problem parsing json contents from "
                        f"file '{filename}':  {str(error)}."
                    )
        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"Problem while attempting to access " f"data file '{filename}'."
            ) from error

        return self.load_from_json(data)

    def get_scan_stats(self, sites_dict):
        sites = sites_dict or self.sites_dict
        found_flags = {}
        for _, s in sites.items():
            if "presense_flag" in s.stats:
                flag = s.stats["presense_flag"]
                found_flags[flag] = found_flags.get(flag, 0) + 1

        return found_flags


    def extract_ids_from_url(self, url: str) -> dict:
        results = {}
        for s in self._sites:
            result = s.extract_id_from_url(url)
            if not result:
                continue
            _id, _type = result
            results[_id] = _type
        return results


    def get_db_stats(self, sites_dict):
        if not sites_dict:
            sites_dict = self.sites_dict()

        urls = {}
        tags = {}
        output = ""
        disabled_count = 0
        total_count = len(sites_dict)

        for _, site in sites_dict.items():
            if site.disabled:
                disabled_count += 1

            url_type = site.get_url_template()
            urls[url_type] = urls.get(url_type, 0) + 1

            if not site.tags:
                tags["NO_TAGS"] = tags.get("NO_TAGS", 0) + 1

            for tag in filter(lambda x: not is_country_tag(x), site.tags):
                tags[tag] = tags.get(tag, 0) + 1

        output += f"Enabled/total sites: {total_count - disabled_count}/{total_count}\n"
        output += "Top profile URLs:\n"
        for url, count in sorted(urls.items(), key=lambda x: x[1], reverse=True)[:20]:
            if count == 1:
                break
            output += f"{count}\t{url}\n"

        output += "Top tags:\n"
        for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:200]:
            mark = ""
            if tag not in self._tags:
                mark = " (non-standard)"
            output += f"{count}\t{tag}{mark}\n"

        return output
