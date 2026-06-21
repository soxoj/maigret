"""Console and query notification helpers.

This module defines objects for notifying the caller about the results of queries.
"""

import sys

from colorama import Fore, Style, init

from .result import MaigretCheckStatus, KeywordMatchStatus
from .utils import get_dict_ascii_tree


class QueryNotifyPrint:
    """Query Notify Print Object.

    Query notify class that prints results.
    """

    def __init__(
        self,
        result=None,
        verbose=False,
        print_found_only=False,
        skip_check_errors=False,
        color=True,
        silent=False,
    ):
        """Create Query Notify Print Object.

        Contains information about a specific method of notifying the results
        of a query.

        Keyword Arguments:
        self                   -- This object.
        result                 -- Object of type QueryResult() containing
                                  results for this query.
        verbose                -- Boolean indicating whether to give verbose output.
        print_found_only       -- Boolean indicating whether to only print found sites.
        color                  -- Boolean indicating whether to color terminal output

        Return Value:
        Nothing.
        """

        # Colorama module's initialization.
        init(autoreset=True)

        self.result = result
        self.verbose = verbose
        self.print_found_only = print_found_only
        self.skip_check_errors = skip_check_errors
        self.color = color
        self.silent = silent

        return

    def make_colored_terminal_notify(
        self, status, text, status_color, text_color, appendix
    ):
        text = [
            f"{Style.BRIGHT}{Fore.WHITE}[{status_color}{status}{Fore.WHITE}]"
            + f"{text_color} {text}: {Style.RESET_ALL}"
            + f"{appendix}"
        ]
        return "".join(text)

    def make_simple_terminal_notify(
        self, status, text, status_color, text_color, appendix
    ):
        return f"[{status}] {text}: {appendix}"

    def make_terminal_notify(self, *args):
        if self.color:
            return self.make_colored_terminal_notify(*args)
        else:
            return self.make_simple_terminal_notify(*args)

    def start(self, message=None, id_type="username"):
        """Notify Start.

        Will print the title to the standard output.

        Keyword Arguments:
        self                   -- This object.
        message                -- String containing username that the series
                                  of queries are about.

        Return Value:
        Nothing.
        """

        if self.silent:
            return

        title = f"Checking {id_type}"
        if self.color:
            print(
                Style.BRIGHT
                + Fore.GREEN
                + "["
                + Fore.YELLOW
                + "*"
                + Fore.GREEN
                + f"] {title}"
                + Fore.WHITE
                + f" {message}"
                + Fore.GREEN
                + " on:"
            )
        else:
            print(f"[*] {title} {message} on:")

    def finish(self, message=None):
        # Hook called at the end of a run. Currently a no-op; kept on the
        # surface because the search loop calls it (checking.py:finish()).
        return

    def _colored_print(self, fore_color, msg):
        if self.color:
            print(Style.BRIGHT + fore_color + msg)
        else:
            print(msg)

    def success(self, message, symbol="+"):
        msg = f"[{symbol}] {message}"
        self._colored_print(Fore.GREEN, msg)

    def warning(self, message, symbol="-", advice=None):
        """Print a warning. When ``advice`` is supplied it is appended after
        the headline in *normal* weight (same colour), so the actionable
        text reads as guidance rather than as part of the alarm itself."""
        msg = f"[{symbol}] {message}"
        if advice and self.color:
            # Bold + yellow for the count line; turn off bold for the advice
            # but keep the yellow until the line is reset at the end.
            print(
                Style.BRIGHT + Fore.YELLOW + msg
                + Style.NORMAL + ". " + advice
                + Style.RESET_ALL
            )
        elif advice:
            # No-colour mode: dot separator is enough to distinguish the
            # parts, no ANSI codes leak into the output.
            print(f"{msg}. {advice}")
        else:
            self._colored_print(Fore.YELLOW, msg)

    def info(self, message, symbol="*"):
        msg = f"[{symbol}] {message}"
        self._colored_print(Fore.BLUE, msg)

    def update(self, result, is_similar=False):
        """Notify Update.

        Will print the query result to the standard output.

        Keyword Arguments:
        self                   -- This object.
        result                 -- Object of type QueryResult() containing
                                  results for this query.

        Return Value:
        Nothing.
        """
        if self.silent:
            return

        notify = None
        self.result = result

        ids_data_text = ""
        if self.result.ids_data:
            ids_data_text = get_dict_ascii_tree(self.result.ids_data.items(), " ")

        # Output to the terminal is desired.
        if result.status == MaigretCheckStatus.CLAIMED:
            # Check if this is a keyword match
            if (result.keyword_match_status == KeywordMatchStatus.KEYWORD_FOUND and 
                result.keywords):
                # Keyword-context match: site contains username + at least one keyword
                color = Fore.LIGHTGREEN_EX
                status = "++"
                notify = self.make_terminal_notify(
                    status,
                    result.site_name,
                    color,
                    color,
                    result.site_url_user + ids_data_text,
                )
            else:
                # Normal claimed site
                color = Fore.BLUE if is_similar else Fore.GREEN
                status = "?" if is_similar else "+"
                notify = self.make_terminal_notify(
                    status,
                    result.site_name,
                    color,
                    color,
                    result.site_url_user + ids_data_text,
                )
        elif result.status == MaigretCheckStatus.AVAILABLE:
            if not self.print_found_only:
                notify = self.make_terminal_notify(
                    "-",
                    result.site_name,
                    Fore.RED,
                    Fore.YELLOW,
                    "Not found!" + ids_data_text,
                )
        elif result.status == MaigretCheckStatus.UNKNOWN:
            if not self.skip_check_errors:
                notify = self.make_terminal_notify(
                    "?",
                    result.site_name,
                    Fore.RED,
                    Fore.RED,
                    str(self.result.error) + ids_data_text,
                )
        elif result.status == MaigretCheckStatus.ILLEGAL:
            if not self.print_found_only:
                text = "Illegal Username Format For This Site!"
                notify = self.make_terminal_notify(
                    "-",
                    result.site_name,
                    Fore.RED,
                    Fore.YELLOW,
                    text + ids_data_text,
                )
        else:
            # It should be impossible to ever get here...
            raise ValueError(
                f"Unknown Query Status '{str(result.status)}' for "
                f"site '{self.result.site_name}'"
            )

        if notify:
            sys.stdout.write("\x1b[1K\r")
            print(notify)

        return notify

    def __str__(self):
        """Convert Object To String.

        Keyword Arguments:
        self                   -- This object.

        Return Value:
        Nicely formatted string to get information about this object.
        """
        result = str(self.result)

        return result


PATREON_URL = "https://www.patreon.com/soxoj"
INTRO_TEXT = "MAIGRET - collect a dossier by username from 3000+ sites"


def _format_intro(use_color: bool) -> str:
    if not use_color:
        return f"[+] {INTRO_TEXT}"
    tag = f"{Style.BRIGHT}{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}]{Style.RESET_ALL}"
    text = f"{Style.BRIGHT}{Fore.GREEN}{INTRO_TEXT}{Style.RESET_ALL}"
    return f"{tag} {text}"


def print_intro_banner(no_color: bool = False, silent: bool = False) -> None:
    """Print the Maigret intro tagline. Skipped only in silent (--ai) mode."""
    if silent:
        return
    print(_format_intro(use_color=not no_color))


def _format_donate_banner(use_color: bool) -> str:
    title = "Support Maigret — sites database & development"
    link_label = "Donate on Patreon:"

    if not use_color:
        return f"[♥] {title}\n[♥] {link_label} {PATREON_URL}"

    tag = f"{Style.BRIGHT}{Fore.WHITE}[{Fore.RED}♥{Fore.WHITE}]{Style.RESET_ALL}"
    title_c = f"{Style.BRIGHT}{Fore.WHITE}{title}{Style.RESET_ALL}"
    label_c = f"{Style.BRIGHT}{Fore.WHITE}{link_label}{Style.RESET_ALL}"
    url_c = f"{Style.BRIGHT}{Fore.RED}{PATREON_URL}{Style.RESET_ALL}"
    return f"{tag} {title_c}\n{tag} {label_c} {url_c}"


def print_donate_banner(no_color: bool = False, silent: bool = False) -> None:
    """Print a colored donation banner. Skipped only in silent (--ai) mode."""
    if silent:
        return
    print(_format_donate_banner(use_color=not no_color))
