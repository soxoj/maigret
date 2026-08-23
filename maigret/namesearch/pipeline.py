# coding: utf8
"""Name search pipeline: plan -> query -> extract -> score -> report."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .extract import (
    Identifier,
    domain_of,
    extract_identifiers,
    is_noise,
    merge_identifiers,
    usernames_from,
)
from .queries import SearchQuery, build_queries
from .searchapi import SearchAPIClient, SearchResult, SearchStats
from .variants import (
    NameParts,
    NameVariant,
    match_score,
    name_variants,
    parse_name,
    username_candidates,
)

logger = logging.getLogger("maigret.namesearch")

# Below this a result is kept in the JSON but hidden from the console summary.
RELEVANCE_THRESHOLD = 0.3


@dataclass
class ScoredResult:
    """A search result with a name-relevance score attached."""

    result: SearchResult
    relevance: float
    noise: bool = False
    identifiers: List[Identifier] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = self.result.to_dict()
        payload["relevance"] = self.relevance
        payload["noise"] = self.noise
        payload["identifiers"] = [i.to_dict() for i in self.identifiers]
        return payload


@dataclass
class NameSearchReport:
    """Everything one name lookup produced."""

    name: str
    parts: NameParts
    variants: List[NameVariant]
    plan: List[SearchQuery]
    results: List[ScoredResult] = field(default_factory=list)
    identifiers: List[Identifier] = field(default_factory=list)
    extras: List[Dict[str, Any]] = field(default_factory=list)
    stats: Optional[SearchStats] = None
    context: List[str] = field(default_factory=list)

    @property
    def relevant(self) -> List[ScoredResult]:
        return [
            r
            for r in self.results
            if r.relevance >= RELEVANCE_THRESHOLD and not r.noise
        ]

    @property
    def by_platform(self) -> Dict[str, List[ScoredResult]]:
        grouped: Dict[str, List[ScoredResult]] = defaultdict(list)
        for scored in self.relevant:
            platform = (
                scored.result.platform or domain_of(scored.result.link) or "other"
            )
            grouped[platform].append(scored)
        return dict(sorted(grouped.items(), key=lambda kv: -len(kv[1])))

    @property
    def maigret_usernames(self) -> List[str]:
        """Found usernames first, generated permutations as a fallback."""
        found = usernames_from(self.identifiers)
        if found:
            return found
        return username_candidates(self.parts, limit=10)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parsed": {
                "given": self.parts.given,
                "middle": self.parts.middle,
                "family": self.parts.family,
            },
            "context": self.context,
            "variants": [
                {"text": v.text, "kind": v.kind, "script": v.script}
                for v in self.variants
            ],
            "plan": [
                {
                    "query": q.query,
                    "engine": q.engine,
                    "category": q.category,
                    "platform": q.platform,
                }
                for q in self.plan
            ],
            "results": [r.to_dict() for r in self.results],
            "identifiers": [i.to_dict() for i in self.identifiers],
            "extras": self.extras,
            "maigret_usernames": self.maigret_usernames,
            "stats": self.stats.to_dict() if self.stats else {},
        }


def plan_search(
    name: str,
    context: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    max_queries: int = 40,
    with_cyrillic: bool = True,
) -> NameSearchReport:
    """Build the query plan without spending a single credit (dry run)."""
    parts = parse_name(name)
    variants = name_variants(parts, with_cyrillic=with_cyrillic)
    plan = build_queries(
        variants, context=context, engines=engines, max_queries=max_queries
    )
    return NameSearchReport(
        name=name,
        parts=parts,
        variants=variants,
        plan=plan,
        context=list(context or []),
    )


def score_results(
    results: List[SearchResult], variants: List[NameVariant]
) -> List[ScoredResult]:
    """Deduplicate by URL, score by name match, extract identifiers."""
    by_url: Dict[str, SearchResult] = {}
    for result in results:
        existing = by_url.get(result.link)
        # Keep the occurrence that came from the most specific query.
        if existing is None or (
            existing.platform is None and result.platform is not None
        ):
            by_url[result.link] = result

    scored: List[ScoredResult] = []
    for result in by_url.values():
        relevance = match_score(result.text, variants)
        url_relevance = match_score(
            result.link.replace("-", " ").replace("/", " "), variants
        )
        relevance = round(min(1.0, max(relevance, url_relevance * 0.9)), 2)

        identifiers = extract_identifiers(
            result.link, result.text, confidence=relevance
        )
        scored.append(
            ScoredResult(
                result=result,
                relevance=relevance,
                noise=is_noise(result.link),
                identifiers=identifiers,
            )
        )

    return sorted(scored, key=lambda s: (-s.relevance, s.result.link))


async def run_name_search(
    name: str,
    api_key: str,
    context: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    max_queries: int = 40,
    concurrency: int = 5,
    results_per_query: int = 10,
    with_cyrillic: bool = True,
) -> NameSearchReport:
    """Full pipeline: plan the dorks, run them, score and extract."""
    report = plan_search(
        name,
        context=context,
        engines=engines,
        max_queries=max_queries,
        with_cyrillic=with_cyrillic,
    )
    if not report.plan:
        logger.warning("empty query plan for %r", name)
        return report

    async with SearchAPIClient(
        api_key=api_key,
        concurrency=concurrency,
        results_per_query=results_per_query,
    ) as client:
        raw_results, extras = await client.run(report.plan)
        report.stats = client.stats

    report.results = score_results(raw_results, report.variants)
    report.extras = extras
    report.identifiers = merge_identifiers(
        [i for scored in report.results if not scored.noise for i in scored.identifiers]
    )

    return report


def render_report(report: NameSearchReport, top: int = 25) -> str:
    """Human-readable console summary."""
    lines: List[str] = []
    lines.append(f"Name search: {report.name}")
    parsed = (
        f"{report.parts.given} / {report.parts.middle or '-'} / {report.parts.family}"
    )
    lines.append(f"Parsed (given/middle/family): {parsed}")
    if report.context:
        lines.append(f"Context terms: {', '.join(report.context)}")

    lines.append("")
    lines.append(f"Name variants ({len(report.variants)}):")
    for variant in report.variants:
        lines.append(f"  - {variant.text}  [{variant.kind}]")

    lines.append("")
    lines.append(f"Query plan ({len(report.plan)} requests):")
    for query in report.plan:
        lines.append(f"  - {query}")

    if report.stats:
        stats = report.stats
        lines.append("")
        lines.append(
            f"Requests: {stats.requests_made} (failed {stats.requests_failed}), "
            f"credits spent: {stats.requests_made}, raw results: {stats.results_total}"
        )
        for error in stats.errors[:5]:
            lines.append(f"  ! {error}")

    if report.results:
        relevant = report.relevant
        lines.append("")
        lines.append(
            f"Relevant results: {len(relevant)} of {len(report.results)} unique URLs"
        )
        for platform, items in report.by_platform.items():
            lines.append("")
            lines.append(f"  [{platform}] {len(items)}")
            for scored in items[:top]:
                lines.append(f"    {scored.relevance:.2f}  {scored.result.title[:80]}")
                lines.append(f"          {scored.result.link}")

    if report.identifiers:
        lines.append("")
        lines.append("Extracted identifiers:")
        for identifier in report.identifiers:
            platform = f" @{identifier.platform}" if identifier.platform else ""
            lines.append(
                f"  {identifier.kind:8} {identifier.value}{platform} "
                f"(confidence {identifier.confidence})"
            )

    for extra in report.extras:
        if "knowledge_graph" in extra:
            lines.append("")
            lines.append("Knowledge graph card:")
            for key, value in list(extra["knowledge_graph"].items())[:12]:
                lines.append(f"  {key}: {str(value)[:120]}")

    usernames = report.maigret_usernames
    if usernames:
        lines.append("")
        lines.append("Next step — username search with maigret:")
        lines.append(f"  maigret {' '.join(usernames[:10])}")

    return "\n".join(lines)
