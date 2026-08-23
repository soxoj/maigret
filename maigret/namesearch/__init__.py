# coding: utf8
"""Proof of concept: OSINT lookup of a person by full name via SearchAPI.

maigret searches by username; this package covers the step before that —
turning a full name into search-engine dorks, running them through
SearchAPI.io, and extracting the usernames, emails and phones that maigret
can then pivot on.

Usage:
    python3 -m maigret.namesearch "Dmitrii Danilov" --dry-run
    SEARCHAPI_API_KEY=... python3 -m maigret.namesearch "Dmitrii Danilov"
"""

from .extract import Identifier, extract_identifiers, extract_profile
from .pipeline import (
    NameSearchReport,
    ScoredResult,
    plan_search,
    render_report,
    run_name_search,
    score_results,
)
from .queries import SearchQuery, build_queries
from .searchapi import (
    SearchAPIClient,
    SearchAPIError,
    SearchResult,
    get_api_key,
)
from .variants import (
    NameParts,
    NameVariant,
    name_variants,
    parse_name,
    username_candidates,
)

__all__ = [
    "Identifier",
    "NameParts",
    "NameSearchReport",
    "NameVariant",
    "ScoredResult",
    "SearchAPIClient",
    "SearchAPIError",
    "SearchQuery",
    "SearchResult",
    "build_queries",
    "extract_identifiers",
    "extract_profile",
    "get_api_key",
    "name_variants",
    "parse_name",
    "plan_search",
    "render_report",
    "run_name_search",
    "score_results",
    "username_candidates",
]
