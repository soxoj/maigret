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
    domain_search: bool
    scan_all_sites: bool
    top_sites_count: int
    scan_disabled_sites: bool
    scan_sites_list: List
    self_check_enabled: bool
    print_not_found: bool
    print_check_errors: bool
    colored_print: bool
    show_progressbar: bool
    report_sorting: str
    json_report_type: str
    txt_report: bool
    csv_report: bool
    xmind_report: bool
    pdf_report: bool
    html_report: bool
    graph_report: bool

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
            if data:
                was_inited = True

        return (
            was_inited,
            f'None of the default settings files found: {", ".join(paths)}',
        )

    @property
    def json(self):
        return self.__dict__
