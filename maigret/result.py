"""Maigret Result Module

This module defines various objects for recording the results of queries.
"""

from enum import Enum


class MaigretCheckStatus(Enum):
    """Query Status Enumeration.

    Describes status of query about a given username.
    """

    CLAIMED = "Claimed"  # Username Detected
    AVAILABLE = "Available"  # Username Not Detected
    UNKNOWN = "Unknown"  # Error Occurred While Trying To Detect Username
    ILLEGAL = "Illegal"  # Username Not Allowable For This Site

    def __str__(self):
        """Convert Object To String.

        Keyword Arguments:
        self                   -- This object.

        Return Value:
        Nicely formatted string to get information about this object.
        """
        return self.value


class MaigretCheckResult:
    """
    Describes result of checking a given username on a given site
    """

    def __init__(
        self,
        username,
        site_name,
        site_url_user,
        status,
        ids_data=None,
        query_time=None,
        context=None,
        error=None,
        tags=[],
    ):
        """
        Keyword Arguments:
        self                   -- This object.
        username               -- String indicating username that query result
                                  was about.
        site_name              -- String which identifies site.
        site_url_user          -- String containing URL for username on site.
                                  NOTE:  The site may or may not exist:  this
                                         just indicates what the name would
                                         be, if it existed.
        status                 -- Enumeration of type QueryStatus() indicating
                                  the status of the query.
        query_time             -- Time (in seconds) required to perform query.
                                  Default of None.
        context                -- String indicating any additional context
                                  about the query.  For example, if there was
                                  an error, this might indicate the type of
                                  error that occurred.
                                  Default of None.
        ids_data               -- Extracted from website page info about other
                                  usernames and inner ids.

        Return Value:
        Nothing.
        """

        self.username = username
        self.site_name = site_name
        self.site_url_user = site_url_user
        self.status = status
        self.query_time = query_time
        self.context = context
        self.ids_data = ids_data
        self.tags = tags
        self.error = error

    def json(self):
        return {
            "username": self.username,
            "site_name": self.site_name,
            "url": self.site_url_user,
            "status": str(self.status),
            "ids": self.ids_data or {},
            "tags": self.tags,
        }

    def is_found(self):
        return self.status == MaigretCheckStatus.CLAIMED

    def __str__(self):
        """Convert Object To String.

        Keyword Arguments:
        self                   -- This object.

        Return Value:
        Nicely formatted string to get information about this object.
        """
        status = str(self.status)
        if self.context is not None:
            # There is extra context information available about the results.
            # Append it to the normal response text.
            status += f" ({self.context})"

        return status
