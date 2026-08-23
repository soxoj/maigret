# coding: utf8
"""Search query (dork) planning.

Every SearchAPI request costs a credit, so the plan is explicit and budgeted:
queries are generated with a weight, sorted, and truncated to `max_queries`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .variants import NameVariant

# Categories, used both for weighting and for grouping the report.
CATEGORY_WEIGHTS = {
    "general": 1.0,
    "social": 0.9,
    "professional": 0.85,
    "code": 0.8,
    "contacts": 0.7,
    "docs": 0.6,
    "news": 0.5,
    "academic": 0.5,
    "leaks": 0.45,
}

# (platform, site: expression, category)
PLATFORM_DORKS = [
    ("LinkedIn", "linkedin.com/in", "professional"),
    ("Facebook", "facebook.com", "social"),
    ("X (Twitter)", "x.com", "social"),
    ("Twitter", "twitter.com", "social"),
    ("Instagram", "instagram.com", "social"),
    ("VK", "vk.com", "social"),
    ("Odnoklassniki", "ok.ru", "social"),
    ("Telegram", "t.me", "social"),
    ("GitHub", "github.com", "code"),
    ("GitLab", "gitlab.com", "code"),
    ("Habr", "habr.com", "code"),
    ("Stack Overflow", "stackoverflow.com", "code"),
    ("Medium", "medium.com", "professional"),
    ("YouTube", "youtube.com", "social"),
    ("Reddit", "reddit.com", "social"),
    ("Behance", "behance.net", "professional"),
    ("Dribbble", "dribbble.com", "professional"),
    ("SoundCloud", "soundcloud.com", "social"),
    ("Keybase", "keybase.io", "code"),
    ("About.me", "about.me", "professional"),
    ("Gravatar", "gravatar.com", "social"),
    ("Speakerdeck", "speakerdeck.com", "professional"),
]

EMAIL_HINTS = (
    '"@gmail.com" OR "@yandex.ru" OR "@mail.ru" OR "@protonmail.com" OR "@outlook.com"'
)
RESUME_HINTS = 'CV OR resume OR "curriculum vitae" OR резюме'
CONTACT_HINTS = 'contact OR email OR "phone" OR телефон'
PASTE_SITES = [
    "pastebin.com",
    "ghostbin.com",
    "justpaste.it",
    "telegra.ph",
    "docs.google.com",
]


@dataclass
class SearchQuery:
    """One planned request to SearchAPI."""

    query: str
    engine: str = "google"
    category: str = "general"
    platform: Optional[str] = None
    variant: str = ""
    weight: float = 1.0
    params: Dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.engine}::{self.query}"

    def __str__(self) -> str:
        return f"[{self.engine}/{self.category}] {self.query}"


def _quoted(text: str) -> str:
    return f'"{text}"'


def build_queries(
    variants: List[NameVariant],
    context: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    include_platforms: bool = True,
    include_docs: bool = True,
    include_leaks: bool = True,
    max_queries: int = 40,
) -> List[SearchQuery]:
    """Build a budgeted query plan out of name variants.

    `context` holds optional disambiguation terms (city, employer, job title).
    They are ANDed into the general queries, which is what turns a hopeless
    common-name search into a usable one.
    """
    engines = engines or ["google"]
    context = [c for c in (context or []) if c.strip()]
    context_expr = " ".join(_quoted(c) if " " in c else c for c in context)

    if not variants:
        return []

    queries: List[SearchQuery] = []
    primary = [v for v in variants if v.kind in ("canonical", "translit", "cyrillic")]
    top_variants = primary[:3] or variants[:1]

    # 1. Plain name lookups, one per spelling, across the requested engines.
    for variant in variants:
        for engine in engines:
            query = _quoted(variant.text)
            if context_expr:
                query = f"{query} {context_expr}"
            queries.append(
                SearchQuery(
                    query=query,
                    engine=engine,
                    category="general",
                    variant=variant.text,
                    weight=variant.weight * CATEGORY_WEIGHTS["general"],
                )
            )

    # 2. Per-platform site: dorks for the strongest spellings only. Secondary
    # spellings are penalized so that one variant's dorks cannot eat the whole
    # budget before the next variant is tried at all.
    if include_platforms:
        for rank, variant in enumerate(top_variants):
            rank_penalty = 1.0 / (1 + rank)
            for platform, domain, category in PLATFORM_DORKS:
                queries.append(
                    SearchQuery(
                        query=f"site:{domain} {_quoted(variant.text)}",
                        engine=engines[0],
                        category=category,
                        platform=platform,
                        variant=variant.text,
                        weight=variant.weight
                        * CATEGORY_WEIGHTS[category]
                        * rank_penalty,
                    )
                )

    # 3. Contact and resume hunting.
    for variant in top_variants[:2]:
        queries.append(
            SearchQuery(
                query=f"{_quoted(variant.text)} ({EMAIL_HINTS})",
                engine=engines[0],
                category="contacts",
                variant=variant.text,
                weight=variant.weight * CATEGORY_WEIGHTS["contacts"],
            )
        )
        queries.append(
            SearchQuery(
                query=f"{_quoted(variant.text)} ({RESUME_HINTS})",
                engine=engines[0],
                category="professional",
                variant=variant.text,
                weight=variant.weight * CATEGORY_WEIGHTS["professional"],
            )
        )
        queries.append(
            SearchQuery(
                query=f"{_quoted(variant.text)} ({CONTACT_HINTS})",
                engine=engines[0],
                category="contacts",
                variant=variant.text,
                weight=variant.weight * CATEGORY_WEIGHTS["contacts"] * 0.9,
            )
        )

    # 4. Documents that tend to carry full names verbatim.
    if include_docs:
        for variant in top_variants[:2]:
            queries.append(
                SearchQuery(
                    query=f"{_quoted(variant.text)} (filetype:pdf OR filetype:doc OR filetype:xlsx)",
                    engine=engines[0],
                    category="docs",
                    variant=variant.text,
                    weight=variant.weight * CATEGORY_WEIGHTS["docs"],
                )
            )

    # 5. Paste sites and dumps.
    if include_leaks:
        sites_expr = " OR ".join(f"site:{s}" for s in PASTE_SITES)
        for variant in top_variants[:1]:
            queries.append(
                SearchQuery(
                    query=f"({sites_expr}) {_quoted(variant.text)}",
                    engine=engines[0],
                    category="leaks",
                    variant=variant.text,
                    weight=variant.weight * CATEGORY_WEIGHTS["leaks"],
                )
            )

    # 6. News and academic verticals — separate SearchAPI engines.
    for variant in top_variants[:1]:
        queries.append(
            SearchQuery(
                query=_quoted(variant.text),
                engine="google_news",
                category="news",
                variant=variant.text,
                weight=variant.weight * CATEGORY_WEIGHTS["news"],
            )
        )
        queries.append(
            SearchQuery(
                query=_quoted(variant.text),
                engine="google_scholar",
                category="academic",
                variant=variant.text,
                weight=variant.weight * CATEGORY_WEIGHTS["academic"],
            )
        )

    return dedup_and_budget(queries, max_queries)


def dedup_and_budget(queries: List[SearchQuery], max_queries: int) -> List[SearchQuery]:
    """Drop duplicates, then keep the best queries within the credit budget.

    Plain `"<spelling>"` lookups are reserved a share of the budget first: they
    are few, they are the only queries that can surface an unexpected platform,
    and without a reservation a long list of site: dorks for one spelling would
    push every other spelling out of the plan entirely.
    """
    seen = set()
    unique: List[SearchQuery] = []
    for query in sorted(queries, key=lambda q: -q.weight):
        if query.key in seen:
            continue
        seen.add(query.key)
        unique.append(query)

    if max_queries <= 0 or len(unique) <= max_queries:
        return unique

    reserve_limit = max(1, max_queries // 3)
    reserved = [q for q in unique if q.category == "general"][:reserve_limit]
    reserved_keys = {q.key for q in reserved}
    rest = [q for q in unique if q.key not in reserved_keys]

    selected = reserved + rest[: max_queries - len(reserved)]
    return sorted(selected, key=lambda q: -q.weight)
