# coding: utf8
"""Tests for the name-search proof of concept (maigret.namesearch)."""

import json

import pytest

from maigret.namesearch import (
    build_queries,
    extract_profile,
    name_variants,
    parse_name,
    plan_search,
    score_results,
    username_candidates,
)
from maigret.namesearch.extract import (
    extract_emails,
    extract_identifiers,
    extract_phones,
    is_noise,
    merge_identifiers,
    usernames_from,
)
from maigret.namesearch.pipeline import render_report
from maigret.namesearch.queries import SearchQuery, dedup_and_budget
from maigret.namesearch.searchapi import (
    SearchAPIAuthError,
    SearchAPIClient,
    SearchResult,
    extract_extras,
    get_api_key,
    parse_results,
)
from maigret.namesearch import searchapi as searchapi_module
from maigret.namesearch.variants import match_score, to_cyrillic


async def _no_sleep(_seconds):
    """Drop-in for asyncio.sleep so retry tests stay instant."""
    return None


def test_parse_name_given_family():
    parts = parse_name("Dmitrii Danilov")
    assert (parts.given, parts.family, parts.middle) == ("Dmitrii", "Danilov", "")
    assert parts.is_usable


def test_parse_name_with_patronymic_in_both_orders():
    given_first = parse_name("Dmitrii Sergeevich Danilov")
    assert (given_first.given, given_first.middle, given_first.family) == (
        "Dmitrii",
        "Sergeevich",
        "Danilov",
    )

    family_first = parse_name("Danilov Dmitrii Sergeevich")
    assert (family_first.given, family_first.middle, family_first.family) == (
        "Dmitrii",
        "Sergeevich",
        "Danilov",
    )


def test_parse_name_single_token():
    parts = parse_name("Danilov")
    assert parts.given == "Danilov"
    assert not parts.is_usable


def test_to_cyrillic_common_endings():
    assert to_cyrillic("Danilov") == "Данилов"
    assert to_cyrillic("Petrovsky") == "Петровский"
    assert to_cyrillic("Данилов") == "Данилов"


def test_name_variants_cover_translit_and_cyrillic():
    variants = name_variants(parse_name("Dmitrii Danilov"))
    texts = {v.text for v in variants}

    assert "Dmitrii Danilov" in texts
    assert "Dmitry Danilov" in texts  # latin alias
    assert "Дмитрий Данилов" in texts  # cyrillic form
    assert "Danilov Dmitrii" in texts  # reordered
    assert "D. Danilov" in texts  # initials
    # no duplicates
    assert len(texts) == len(variants)


def test_name_variants_without_cyrillic():
    variants = name_variants(parse_name("Dmitrii Danilov"), with_cyrillic=False)
    assert all(v.script == "latin" for v in variants)


def test_name_variants_unknown_given_name():
    variants = name_variants(parse_name("Cornelius Vanderbilt"))
    assert "Cornelius Vanderbilt" in {v.text for v in variants}


def test_username_candidates():
    candidates = username_candidates(parse_name("Dmitrii Danilov"))
    assert "dmitrii_danilov" in candidates
    assert "ddanilov" in candidates
    assert "dmitrydanilov" in candidates  # alias-based
    assert all(len(c) >= 3 for c in candidates)


def test_build_queries_respects_budget_and_keeps_general_queries():
    variants = name_variants(parse_name("Dmitrii Danilov"))
    plan = build_queries(variants, max_queries=20)

    assert len(plan) == 20
    assert len({q.key for q in plan}) == 20

    generals = [q for q in plan if q.category == "general"]
    # The reservation must survive the flood of site: dorks.
    assert len(generals) >= 6
    assert any(q.variant.startswith("Дмитрий") for q in plan)


def test_build_queries_with_context_terms():
    variants = name_variants(parse_name("Dmitrii Danilov"), with_cyrillic=False)
    plan = build_queries(variants, context=["Amsterdam", "social links"], max_queries=5)
    general = [q for q in plan if q.category == "general"][0]
    assert "Amsterdam" in general.query
    assert '"social links"' in general.query


def test_build_queries_empty_variants():
    assert build_queries([]) == []


def test_dedup_and_budget_drops_duplicates():
    queries = [
        SearchQuery(query="a", weight=0.5),
        SearchQuery(query="a", weight=0.9),
        SearchQuery(query="b", weight=0.7),
    ]
    result = dedup_and_budget(queries, max_queries=10)
    assert [q.query for q in result] == ["a", "b"]


@pytest.mark.parametrize(
    "url,platform,username",
    [
        (
            "https://www.linkedin.com/in/dmitrii-danilov-123",
            "LinkedIn",
            "dmitrii-danilov-123",
        ),
        ("https://github.com/ddanilov", "GitHub", "ddanilov"),
        ("https://twitter.com/d_danilov", "X (Twitter)", "d_danilov"),
        ("https://t.me/danilovd", "Telegram", "danilovd"),
        ("https://vk.com/dmitrii.danilov", "VK", "dmitrii.danilov"),
        ("https://medium.com/@dmitrii", "Medium", "dmitrii"),
        ("https://www.reddit.com/user/danilov_d/", "Reddit", "danilov_d"),
    ],
)
def test_extract_profile_known_platforms(url, platform, username):
    assert extract_profile(url) == (platform, username)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/soxoj/maigret",  # repo, not a profile
        "https://facebook.com/groups",  # reserved slug
        "https://example.com/dmitrii",  # unknown platform
        "https://t.me/1234",  # numeric
    ],
)
def test_extract_profile_rejects_non_profiles(url):
    assert extract_profile(url) is None


def test_extract_emails_and_phones():
    text = "Contact: dmitrii.danilov@example.com or +31 6 1234 5678, ref 2024"
    assert extract_emails(text) == ["dmitrii.danilov@example.com"]
    assert extract_phones(text) == ["+31612345678"]


def test_extract_phones_ignores_short_and_degenerate_numbers():
    assert extract_phones("call 12345 or 0000000000000") == []


def test_extract_emails_ignores_asset_names():
    assert extract_emails("avatar@2x.png and a@b.co") == ["a@b.co"]


def test_is_noise_detects_people_aggregators():
    assert is_noise("https://www.spokeo.com/Dmitrii-Danilov")
    assert not is_noise("https://github.com/ddanilov")


def test_extract_identifiers_and_merge():
    identifiers = extract_identifiers(
        "https://github.com/ddanilov",
        "Dmitrii Danilov — ddanilov@example.com",
        confidence=1.0,
    )
    kinds = {i.kind for i in identifiers}
    assert kinds == {"username", "email"}

    duplicated = identifiers + extract_identifiers(
        "https://github.com/ddanilov", "Dmitrii Danilov", confidence=0.4
    )
    merged = merge_identifiers(duplicated)
    usernames = [i for i in merged if i.kind == "username"]
    assert len(usernames) == 1
    assert usernames[0].confidence == 1.0

    assert usernames_from(merged) == ["ddanilov"]


def test_match_score_ranks_phrase_above_tokens():
    variants = name_variants(parse_name("Dmitrii Danilov"))
    exact = match_score("Dmitrii Danilov — profile", variants)
    reordered = match_score("Danilov, Dmitrii S., PhD", variants)
    unrelated = match_score("Cooking recipes", variants)

    assert exact == 1.0
    assert 0 < reordered <= exact
    assert unrelated == 0.0


SEARCHAPI_PAYLOAD = {
    "search_metadata": {"status": "Success"},
    "knowledge_graph": {"title": "Dmitrii Danilov", "type": "Researcher"},
    "organic_results": [
        {
            "position": 1,
            "title": "Dmitrii Danilov - GitHub",
            "link": "https://github.com/ddanilov",
            "snippet": "Dmitrii Danilov, contact ddanilov@example.com",
        },
        {
            "position": 2,
            "title": "Spokeo listing",
            "link": "https://www.spokeo.com/Dmitrii-Danilov",
            "snippet": "Dmitrii Danilov public records",
        },
        {"position": 3, "title": "no link here"},
    ],
    "related_searches": [{"query": "dmitrii danilov linkedin"}],
}


def test_parse_results_skips_entries_without_links():
    query = SearchQuery(query='"Dmitrii Danilov"', category="general")
    results = parse_results(SEARCHAPI_PAYLOAD, query)
    assert len(results) == 2
    assert results[0].link == "https://github.com/ddanilov"
    assert results[0].source_query == '"Dmitrii Danilov"'


def test_parse_results_supports_news_block():
    query = SearchQuery(query='"x"', engine="google_news", category="news")
    payload = {"news_results": [{"title": "T", "link": "https://news.example/1"}]}
    assert parse_results(payload, query)[0].engine == "google_news"


def test_extract_extras():
    extras = extract_extras(SEARCHAPI_PAYLOAD)
    assert extras["knowledge_graph"]["type"] == "Researcher"
    assert extras["related_searches"] == ["dmitrii danilov linkedin"]


def test_score_results_marks_noise_and_extracts():
    variants = name_variants(parse_name("Dmitrii Danilov"))
    query = SearchQuery(query='"Dmitrii Danilov"', category="general")
    scored = score_results(parse_results(SEARCHAPI_PAYLOAD, query), variants)

    by_url = {s.result.link: s for s in scored}
    github = by_url["https://github.com/ddanilov"]
    spokeo = by_url["https://www.spokeo.com/Dmitrii-Danilov"]

    assert github.relevance == 1.0
    assert not github.noise
    assert spokeo.noise
    assert any(
        i.kind == "username" and i.value == "ddanilov" for i in github.identifiers
    )


def test_score_results_deduplicates_urls():
    variants = name_variants(parse_name("Dmitrii Danilov"))
    results = [
        SearchResult(title="A", link="https://github.com/ddanilov"),
        SearchResult(title="A", link="https://github.com/ddanilov", platform="GitHub"),
    ]
    scored = score_results(results, variants)
    assert len(scored) == 1
    assert scored[0].result.platform == "GitHub"


def test_get_api_key_prefers_explicit_value(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_API_KEY", "from-env")
    assert get_api_key("explicit") == "explicit"
    assert get_api_key(None) == "from-env"

    monkeypatch.delenv("SEARCHAPI_API_KEY")
    assert get_api_key(None) is None


def test_client_requires_api_key():
    with pytest.raises(SearchAPIAuthError):
        SearchAPIClient(api_key="")


class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    """Minimal stand-in for aiohttp.ClientSession."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        status, payload = self.responses.pop(0)
        return _FakeResponse(status, payload)


async def test_client_search_parses_payload():
    session = _FakeSession([(200, SEARCHAPI_PAYLOAD)])
    client = SearchAPIClient(api_key="k", session=session)
    results, extras = await client.search(SearchQuery(query='"Dmitrii Danilov"'))

    assert len(results) == 2
    assert extras["knowledge_graph"]
    assert client.stats.requests_made == 1

    params = session.calls[0][1]
    assert params["api_key"] == "k"
    assert params["engine"] == "google"


async def test_client_raises_on_auth_error():
    session = _FakeSession([(401, {})])
    client = SearchAPIClient(api_key="bad", session=session)
    with pytest.raises(SearchAPIAuthError):
        await client.search(SearchQuery(query="q"))


async def test_client_retries_then_reports_failure(monkeypatch):
    monkeypatch.setattr(searchapi_module.asyncio, "sleep", _no_sleep)
    session = _FakeSession([(429, {}), (429, {}), (429, {})])
    client = SearchAPIClient(api_key="k", session=session, retries=3)
    results, extras = await client.search(SearchQuery(query="q"))

    assert results == []
    assert client.stats.requests_made == 3  # every attempt is billable
    assert client.stats.requests_failed == 1
    assert client.stats.errors


async def test_client_run_aggregates_queries():
    session = _FakeSession([(200, SEARCHAPI_PAYLOAD), (200, SEARCHAPI_PAYLOAD)])
    client = SearchAPIClient(api_key="k", session=session)
    results, extras = await client.run([SearchQuery(query="a"), SearchQuery(query="b")])

    assert len(results) == 4
    assert len(extras) == 2
    assert client.stats.requests_made == 2


def test_plan_search_spends_no_credits():
    report = plan_search("Dmitrii Danilov", max_queries=12)
    assert len(report.plan) == 12
    assert report.stats is None
    assert report.results == []
    # Without any search results the fallback usernames come from permutations.
    assert report.maigret_usernames


def test_report_to_dict_and_render():
    report = plan_search("Dmitrii Danilov", max_queries=5)
    variants = report.variants
    query = SearchQuery(query='"Dmitrii Danilov"', category="general")
    report.results = score_results(parse_results(SEARCHAPI_PAYLOAD, query), variants)
    report.identifiers = merge_identifiers(
        [i for s in report.results if not s.noise for i in s.identifiers]
    )

    payload = report.to_dict()
    assert payload["parsed"]["family"] == "Danilov"
    assert payload["maigret_usernames"] == ["ddanilov"]
    assert len(payload["results"]) == 2

    text = render_report(report)
    assert "Dmitrii Danilov" in text
    assert "maigret ddanilov" in text
    # Aggregator noise must not reach the human-facing summary.
    assert "spokeo" not in text.lower()
