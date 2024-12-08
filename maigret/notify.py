"""Sherlock Notify Module

This module defines the objects for notifying the caller about the
results of queries.
"""

import sys

from colorama import Fore, Style, init

from .result import MaigretCheckStatus
from .utils import get_dict_ascii_tree


class QueryNotify:
    """Query Notify Object.

    Base class that describes methods available to notify the results of
    a query.
    It is intended that other classes inherit from this base class and
    override the methods to implement specific functionality.
    """

    def __init__(self, result=None):
        """Create Query Notify Object.

        Contains information about a specific method of notifying the results
        of a query.

        Keyword Arguments:
        self                   -- This object.
        result                 -- Object of type QueryResult() containing
                                  results for this query.

        Return Value:
        Nothing.
        """

        self.result = result

        return

    def start(self, message=None, id_type="username"):
        """Notify Start.

        Notify method for start of query.  This method will be called before
        any queries are performed.  This method will typically be
        overridden by higher level classes that will inherit from it.

        Keyword Arguments:
        self                   -- This object.
        message                -- Object that is used to give context to start
                                  of query.
                                  Default is None.

        Return Value:
        Nothing.
        """

        return

    def update(self, result):
        """Notify Update.

        Notify method for query result.  This method will typically be
        overridden by higher level classes that will inherit from it.

        Keyword Arguments:
        self                   -- This object.
        result                 -- Object of type QueryResult() containing
                                  results for this query.

        Return Value:
        Nothing.
        """

        self.result = result

        return

    def finish(self, message=None):
        """Notify Finish.

        Notify method for finish of query.  This method will be called after
        all queries have been performed.  This method will typically be
        overridden by higher level classes that will inherit from it.

        Keyword Arguments:
        self                   -- This object.
        message                -- Object that is used to give context to start
                                  of query.
                                  Default is None.

        Return Value:
        Nothing.
        """

        return

    def __str__(self):
        """Convert Object To String.

        Keyword Arguments:
        self                   -- This object.

        Return Value:
        Nicely formatted string to get information about this object.
        """
        result = str(self.result)

        return result


class QueryNotifyPrint(QueryNotify):
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

        super().__init__(result)
        self.verbose = verbose
        self.print_found_only = print_found_only
        self.skip_check_errors = skip_check_errors
        self.color = color

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

    def start(self, message, id_type):
        """Notify Start.

        Will print the title to the standard output.

        Keyword Arguments:
        self                   -- This object.
        message                -- String containing username that the series
                                  of queries are about.

        Return Value:
        Nothing.
        """

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

    def _colored_print(self, fore_color, msg):
        if self.color:
            print(Style.BRIGHT + fore_color + msg)
        else:
            print(msg)

    def success(self, message, symbol="+"):
        msg = f"[{symbol}] {message}"
        self._colored_print(Fore.GREEN, msg)

    def warning(self, message, symbol="-"):
        msg = f"[{symbol}] {message}"
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
        notify = None
        self.result = result

        ids_data_text = ""
        if self.result.ids_data:
            ids_data_text = get_dict_ascii_tree(self.result.ids_data.items(), " ")

        # Output to the terminal is desired.
        if result.status == MaigretCheckStatus.CLAIMED:
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
