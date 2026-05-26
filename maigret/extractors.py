import ast

from maigret.utils import is_plausible_username

def extract_usernames(info, logger):
    """
    Extract plausible usernames from socid_extractor results.

    Supports:
    - single username fields (e.g. "profile_username")
    - serialized username lists (e.g. "other_usernames")

    Invalid values such as URLs or emails are ignored.
    """
    results = []

    for key, value in info.items():

        # Single username field
        if 'username' in key and 'usernames' not in key:

            if is_plausible_username(value):
                results.append(value)
            else:
                logger.debug(
                    f"Rejected non-username value extracted "
                    f"under key {key!r}: {value!r}"
                )
        # Serialized username list field
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