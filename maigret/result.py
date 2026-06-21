"""Maigret Result Module

This module defines various objects for recording the results of queries.
"""

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict

if TYPE_CHECKING:
    from aiohttp import CookieJar
    from .sites import MaigretSite

class KeywordMatchStatus(Enum):
    """Keyword Match Status Enumeration.
    
    Describes the status of keyword matching for a given site.
    """
    
    NO_KEYWORDS = "No Keywords"
    KEYWORD_FOUND = "Keyword Found"
    KEYWORDS_NOT_FOUND = "Keywords Not Found"
    
    def __str__(self):
        """Convert Object To String.
        
        Keyword Arguments:
        self                   -- This object.
        
        Return Value:
        Nicely formatted string to get information about this object.
        """
        return self.value

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
        keywords=None,
        keyword_match_status=None
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
        keywords               -- List of keywords to search for in page content.
                                  Default of None.
        keyword_match_status   -- Enumeration of type KeywordMatchStatus()
                                  indicating keyword matching status.
                                  Default of None.

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
        self.keywords = keywords or []
        self.keyword_match_status = keyword_match_status or KeywordMatchStatus.NO_KEYWORDS

    def json(self):
        return {
            "username": self.username,
            "site_name": self.site_name,
            "url": self.site_url_user,
            "status": str(self.status),
            "ids": self.ids_data or {},
            "tags": self.tags,
            "keywords": self.keywords,
            "keyword_match_status": str(self.keyword_match_status)
        }

    def is_found(self):
        return self.status == MaigretCheckStatus.CLAIMED

    def __repr__(self):
        return f"<{self.__str__()}>"

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


class SiteResult(TypedDict, total=False):
    """Per-site result dict, keyed by site name in the top-level results dict.

    Populated across three phases — make_site_result, process_site_result,
    then report generation — so every field is optional from the type
    system's point of view.
    """

    # make_site_result
    site: "MaigretSite"
    username: str
    keywords: List[str]
    parsing_enabled: bool
    url_main: str
    cookies: Optional["CookieJar"]
    url_user: str
    url_probe: str
    future: asyncio.Future
    checker: Any  # CheckerBase lives in checking.py; importing back here is circular

    # process_site_result
    status: MaigretCheckResult
    http_status: Any  # int on success, "" on error branches — mixed by design
    is_similar: bool
    rank: Optional[int]
    response_text: str

    # extract_ids_data
    ids_usernames: Dict[str, str]
    ids_links: List[str]

    # added during report generation
    found: bool
    ids_data: Dict[str, Any]
    sitename: str  # only set for per-line JSON export
