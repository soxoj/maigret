import os
import os.path as path
import json

SETTINGS_FILES_PATHS = [
    path.join(path.dirname(path.realpath(__file__)), "resources/settings.json"),
    '~/.maigret/settings.json',
    path.join(os.getcwd(), 'settings.json'),
]


class Settings:
    # main maigret setting
    retries_count: int

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
