import json


class Settings:
    presence_strings: list
    supposed_usernames: list

    def __init__(self, filename):
        data = {}

        try:
            with open(filename, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except Exception as error:
                    raise ValueError(
                        f"Problem with parsing json contents of "
                        f"settings file '{filename}':  {str(error)}."
                    )
        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"Problem while attempting to access settings file '{filename}'."
            ) from error

        self.__dict__.update(data)

    @property
    def json(self):
        return self.__dict__
