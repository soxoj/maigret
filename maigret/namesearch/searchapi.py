# coding: utf8
"""Minimal async SearchAPI.io client.

Only the pieces a name lookup needs: organic results, the knowledge graph card,
related searches — plus credit accounting, because every request is billable.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .queries import SearchQuery

SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
DEFAULT_ENGINE = "google"
ENV_KEYS = ("SEARCHAPI_API_KEY", "SEARCHAPI_KEY", "SEARCH_API_KEY")

logger = logging.getLogger("maigret.namesearch")


class SearchAPIError(Exception):
    """Any non-recoverable SearchAPI failure."""


class SearchAPIAuthError(SearchAPIError):
    """Missing or rejected API key."""


class SearchAPIQuotaError(SearchAPIError):
    """Credits exhausted or rate limit exceeded after retries."""


def get_api_key(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the API key from an explicit value or the environment."""
    if explicit:
        return explicit.strip()
    for env_key in ENV_KEYS:
        value = os.environ.get(env_key)
        if value:
            return value.strip()
    return None


@dataclass
class SearchResult:
    """A single organic result, annotated with the query that produced it."""

    title: str
    link: str
    snippet: str = ""
    position: int = 0
    engine: str = DEFAULT_ENGINE
    category: str = "general"
    platform: Optional[str] = None
    source_query: str = ""
    displayed_link: str = ""
    date: str = ""

    @property
    def text(self) -> str:
        return f"{self.title} {self.snippet}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "position": self.position,
            "engine": self.engine,
            "category": self.category,
            "platform": self.platform,
            "source_query": self.source_query,
            "date": self.date,
        }


@dataclass
class SearchStats:
    """Per-run accounting so the credit cost is never a surprise."""

    requests_made: int = 0
    requests_failed: int = 0
    results_total: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_made": self.requests_made,
            "requests_failed": self.requests_failed,
            "credits_spent": self.requests_made,
            "results_total": self.results_total,
            "errors": self.errors,
        }


class SearchAPIClient:
    """Async client with bounded concurrency and retry on 429/5xx."""

    def __init__(
        self,
        api_key: str,
        concurrency: int = 5,
        timeout: int = 30,
        retries: int = 3,
        results_per_query: int = 10,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        if not api_key:
            raise SearchAPIAuthError(
                "SearchAPI key is not set: pass --api-key or export SEARCHAPI_API_KEY"
            )
        self.api_key = api_key
        self.concurrency = concurrency
        self.timeout = timeout
        self.retries = retries
        self.results_per_query = results_per_query
        self.stats = SearchStats()
        self._session = session
        self._owns_session = session is None
        self._semaphore = asyncio.Semaphore(concurrency)

    async def __aenter__(self) -> "SearchAPIClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self

    async def __aexit__(self, *args) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def _request(self, query: SearchQuery) -> Dict[str, Any]:
        params = {
            "engine": query.engine,
            "q": query.query,
            "api_key": self.api_key,
            "num": str(self.results_per_query),
            **query.params,
        }

        delay = 1.0
        last_error = ""
        for attempt in range(1, self.retries + 1):
            try:
                assert self._session is not None
                async with self._session.get(SEARCHAPI_URL, params=params) as response:
                    self.stats.requests_made += 1
                    if response.status == 401:
                        raise SearchAPIAuthError("SearchAPI rejected the API key (401)")
                    if response.status == 402:
                        raise SearchAPIQuotaError("SearchAPI credits exhausted (402)")
                    if response.status in (429, 500, 502, 503, 504):
                        last_error = f"HTTP {response.status}"
                        logger.debug(
                            "retrying %s after %s (attempt %s)",
                            query.query,
                            last_error,
                            attempt,
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    if response.status != 200:
                        body = (await response.text())[:200]
                        raise SearchAPIError(f"HTTP {response.status}: {body}")
                    return await response.json()
            except (SearchAPIAuthError, SearchAPIQuotaError):
                raise
            except aiohttp.ClientError as error:
                last_error = str(error)
                logger.debug("network error for %s: %s", query.query, error)
                await asyncio.sleep(delay)
                delay *= 2
            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.debug("timeout for %s", query.query)
                await asyncio.sleep(delay)
                delay *= 2

        raise SearchAPIError(f"failed after {self.retries} attempts: {last_error}")

    async def search(
        self, query: SearchQuery
    ) -> Tuple[List[SearchResult], Dict[str, Any]]:
        """Run one query, returning organic results and extra blocks."""
        async with self._semaphore:
            try:
                payload = await self._request(query)
            except (SearchAPIAuthError, SearchAPIQuotaError):
                raise
            except SearchAPIError as error:
                self.stats.requests_failed += 1
                self.stats.errors.append(f"{query.query}: {error}")
                return [], {}

        results = parse_results(payload, query)
        self.stats.results_total += len(results)
        return results, extract_extras(payload)

    async def run(
        self, queries: List[SearchQuery]
    ) -> Tuple[List[SearchResult], List[Dict[str, Any]]]:
        """Run the whole plan concurrently, tolerating individual failures."""
        tasks = [self.search(query) for query in queries]
        all_results: List[SearchResult] = []
        all_extras: List[Dict[str, Any]] = []

        for coro in asyncio.as_completed(tasks):
            try:
                results, extras = await coro
            except (SearchAPIAuthError, SearchAPIQuotaError) as error:
                # Both are fatal for the whole run — no point burning more credits.
                self.stats.errors.append(str(error))
                raise
            all_results.extend(results)
            if extras:
                all_extras.append(extras)

        return all_results, all_extras


def parse_results(payload: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
    """Normalize the organic block of any SearchAPI engine."""
    raw_results = payload.get("organic_results") or []
    # google_news and google_scholar name their blocks differently.
    if not raw_results:
        raw_results = payload.get("news_results") or payload.get("results") or []

    results = []
    for index, item in enumerate(raw_results):
        if not isinstance(item, dict):
            continue
        link = item.get("link") or item.get("url") or ""
        if not link:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or "",
                link=link,
                snippet=item.get("snippet") or item.get("description") or "",
                position=item.get("position") or index + 1,
                engine=query.engine,
                category=query.category,
                platform=query.platform,
                source_query=query.query,
                displayed_link=item.get("displayed_link") or "",
                date=item.get("date") or "",
            )
        )

    return results


def extract_extras(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the non-organic blocks that often carry the best identity data."""
    extras: Dict[str, Any] = {}

    knowledge_graph = payload.get("knowledge_graph")
    if isinstance(knowledge_graph, dict) and knowledge_graph:
        extras["knowledge_graph"] = knowledge_graph

    answer_box = payload.get("answer_box")
    if isinstance(answer_box, dict) and answer_box:
        extras["answer_box"] = answer_box

    related = payload.get("related_searches")
    if isinstance(related, list) and related:
        extras["related_searches"] = [
            item.get("query")
            for item in related
            if isinstance(item, dict) and item.get("query")
        ]

    return extras
