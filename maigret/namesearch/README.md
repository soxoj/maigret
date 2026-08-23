# namesearch — OSINT lookup by full name (proof of concept)

maigret searches by **username**. This package covers the step *before* that:
turning a **full name** into search-engine dorks, running them through
[SearchAPI.io](https://www.searchapi.io/), and extracting the identifiers that
maigret can then pivot on.

```
full name → spelling variants → dork plan → SearchAPI → scored results
                                                     ↘ usernames / emails / phones → maigret
```

## Quick start

```bash
# preview the query plan, spend nothing
python3 -m maigret.namesearch "Dmitrii Danilov" --dry-run

# run it for real
export SEARCHAPI_API_KEY=...
python3 -m maigret.namesearch "Dmitrii Danilov" --max-queries 40 --json report.json

# narrow a common name down with context terms
python3 -m maigret.namesearch "Dmitrii Danilov" --context Amsterdam "social links"
```

Key options: `--max-queries` (hard credit cap), `--num` (results per query),
`--engines google bing`, `--context`, `--no-cyrillic`, `--dry-run`, `--json`.

The API key is read from `--api-key` or, in order, `$SEARCHAPI_API_KEY`,
`$SEARCHAPI_KEY`, `$SEARCH_API_KEY`. It is never written to the report.

## How it works

1. **`variants.py`** — parses the name (`Given Family`, `Given Patronymic
   Family`, `Family Given Patronymic`) and expands it into spellings worth
   querying: latin transliteration aliases (`Dmitrii` → `Dmitry`, `Dmitriy`,
   `Dmitri`), diminutives (`Dima`, `Mitya`), reversed order, initials, and an
   approximate Cyrillic back-transliteration (`Дмитрий Данилов`). It also
   generates username permutations, reusing maigret's own `Permute`.
2. **`queries.py`** — builds a weighted dork plan: plain phrase lookups,
   `site:` dorks for ~22 platforms, contact/resume/document/paste-site dorks,
   plus the `google_news` and `google_scholar` verticals. The plan is then
   deduplicated and truncated to the credit budget, with a share of the budget
   *reserved* for plain phrase lookups so that one spelling's site: dorks
   cannot crowd out every other spelling.
3. **`searchapi.py`** — async SearchAPI client: bounded concurrency, retry with
   backoff on 429/5xx, fatal stop on 401/402, per-run credit accounting. Parses
   organic results plus the knowledge-graph card and related searches.
4. **`extract.py`** — recognizes profile URLs for ~22 platforms and pulls out
   usernames, emails and phones; flags people-data aggregators (Spokeo,
   Radaris, ZoomInfo…) as noise.
5. **`pipeline.py`** — deduplicates by URL, scores each result against every
   name variant (exact phrase > all-tokens-in-any-order), groups by platform,
   merges identifiers and renders the report.

## Library usage

```python
import asyncio
from maigret.namesearch import run_name_search, render_report

report = asyncio.run(run_name_search("Dmitrii Danilov", api_key="...", max_queries=30))
print(render_report(report))
print(report.maigret_usernames)   # feed these to maigret
print(report.to_dict())           # full JSON-serializable report
```

## Known limits of the concept

- **Common names need context.** Without `--context`, a name like this returns
  several different people; the pipeline scores relevance but does not yet
  cluster results into distinct identities.
- **Latin→Cyrillic transliteration is rule-based** and approximate for family
  names outside the common `-ov/-ev/-in/-sky` endings.
- **The given-name alias dictionary is small** (~30 Slavic names) — that is the
  first place to extend, or to replace with an LLM call.
- **Credits are real money.** Every query is one request; always check
  `--dry-run` before raising `--max-queries`.
- The handoff to maigret is currently a printed command, not an automatic run.
