import ast

from maigret.utils import is_plausible_username

def extract_usernames(info, logger):
    results = []

    for key, value in info.items():

        if 'username' in key and 'usernames' not in key:

            if is_plausible_username(value):
                results.append(value)
            else:
                logger.debug(
                    f"Rejected non-username value extracted "
                    f"under key {key!r}: {value!r}"
                )

        elif 'usernames' in key:

            try:
                parsed = ast.literal_eval(value)

                if isinstance(parsed, list):
                    for item in parsed:

                        if is_plausible_username(item):
                            results.append(item)
                        else:
                            logger.debug(
                                f"Rejected non-username item "
                                f"from list under key {key!r}: {item!r}"
                            )
            except Exception as e:
                logger.warning(e)

    return results