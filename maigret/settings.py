import os
import os.path as path
import json
from typing import List

SETTINGS_FILES_PATHS = [
    path.join(path.dirname(path.realpath(__file__)), "resources/settings.json"),
    '~/.maigret/settings.json',
    path.join(os.getcwd(), 'settings.json'),
]


class Settings:
    # main maigret setting
    retries_count: int
    sites_db_path: str
    timeout: int
    max_connections: int
    recursive_search: bool
    info_extracting: bool
    cookie_jar_file: str
    ignore_ids_list: List
    reports_path: str
    proxy_url: str
    tor_proxy_url: str
    i2p_proxy_url: str

    # submit mode settings
    presence_strings: list
    supposed_usernames: list

    def __init__(self):
        pass

    def load(self, paths=None):
        was_inited = False

        if not paths:
            paths = SETTINGS_FILES_PATHS

        for filename in paths:
            data = {}

            try:
                with open(filename, "r", encoding="utf-8") as file:
                    data = json.load(file)
            except FileNotFoundError:
                # treast as a normal situation
                pass
            except Exception as error:
                return False, ValueError(
                    f"Problem with parsing json contents of "
                    f"settings file '{filename}':  {str(error)}."
                )

            self.__dict__.update(data)
            import logging

            logging.error(data)
            if data:
                was_inited = True

        return (
            was_inited,
            f'None of the default settings files found: {", ".join(paths)}',
        )

    @property
    def json(self):
        return self.__dict__
