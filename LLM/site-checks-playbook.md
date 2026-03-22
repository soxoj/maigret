# Site checks — playbook (Maigret)

Short checklist for edits to [`maigret/resources/data.json`](../maigret/resources/data.json) and, when needed, [`maigret/checking.py`](../maigret/checking.py). Full guide: [`site-checks-guide.md`](site-checks-guide.md). Upstream extraction proposals: [`socid_extractor_improvements.log`](socid_extractor_improvements.log).

**Documentation maintenance:** whenever you improve Maigret, add search tooling, or change check logic, update **both** this file and [`site-checks-guide.md`](site-checks-guide.md) (see the “Documentation maintenance” section at the end of that file). When JSON API / `socid_extractor` logging rules change, update the **template header** in [`socid_extractor_improvements.log`](socid_extractor_improvements.log) in the same change.

## 0. Standard checks (do alongside reproduce / classify)

- **Public JSON API:** always look for a stable JSON (or GraphQL JSON) profile endpoint (`/api/`, `.json`, mobile-style URLs). When the API is more reliable than HTML, set **`urlProbe`** to that endpoint and keep **`url`** as the human-readable profile link (e.g. `https://picsart.com/u/{username}`). If there is no separate profile URL, use the API as `url` only. Details: **`urlProbe`** and section **2.1** in [`site-checks-guide.md`](site-checks-guide.md).
- **`socid_extractor` log (mandatory):** if you find **embedded user JSON in HTML** or a **standalone JSON profile API**, append a dated entry (with **example username**) to [`socid_extractor_improvements.log`](socid_extractor_improvements.log). Details: section **2.2** in [`site-checks-guide.md`](site-checks-guide.md).

## 1. Reproduce

- Run a targeted check:  
  `maigret USER --db /path/to/maigret/resources/data.json --site "SiteName" --print-not-found --print-errors --no-progressbar -vv`
- Compare an **existing** and a **non-existent** username (as `usernameClaimed` / `usernameUnclaimed` in JSON).
- With `-vvv`, inspect `debug.log` (raw response in the log).

## 2. Classify the cause

| Symptom | Typical cause | Action |
|--------|-----------------|--------|
| HTTP 200 for “user does not exist” | Soft 404 | Move from `status_code` to `message` or `response_url`; add `absenceStrs` / narrow `presenseStrs` |
| Generic words match (`name`, `email`) | `presenseStrs` too broad | Remove generic markers; add profile-specific ones |
| Same HTML without JS | SPA / skeleton shell | Compare **final URL and HTTP redirects** (Maigret already follows redirects by default). If the browser shows extra routes (`/posts`, `/not-found`) only **after JS**, they will **not** appear to Maigret — try a **public JSON/API** endpoint for the same site if one exists. See **Redirects and final URL** and **Picsart** in [`site-checks-guide.md`](site-checks-guide.md). |
| 403 / “Log in” / guest-only | Auth or anti-bot required | `disabled: true` |
| reCAPTCHA / “Checking your browser” | Bot protection | Try a reasonable `User-Agent` in `headers`; else `errors` + UNKNOWN or `disabled` |
| Domain does not resolve / persistent timeout | Dead service | Remove entry **only** after confirming the domain is dead |

## 3. Data edits

1. Update `url` / `urlMain` if needed (HTTPS redirects). Use optional **`urlProbe`** when the HTTP check should hit a different URL than the profile link shown in reports (API vs web UI).
2. For `message`: **always** tune string pairs so `absenceStrs` fire on “no user” pages and `presenseStrs` fire on real profiles without false absence hits.
3. Engine (`engine`, e.g. XenForo): override only differing fields in the site entry so other sites are not broken.
4. Keep `status_code` only if the response **reliably** differs by status code without soft 404.

## 4. Verify

- `maigret --self-check --site "SiteName" --db ...` for touched entries.
- `make test` before commit.

## 5. Code notes

- `process_site_result` uses strict comparison to `"status_code"` for `checkType` (not a substring trick).
- Empty `presenseStrs` with `message` means “presence always true”; a debug line is logged only at DEBUG level.

## 6. Development utilities

Quick reference for site check utilities. Full details: section **6** in [`site-checks-guide.md`](site-checks-guide.md).

| Command | Purpose |
|---------|---------|
| `python utils/site_check.py --site "X" --check-claimed` | Quick aiohttp comparison |
| `python utils/site_check.py --site "X" --maigret` | Test via Maigret checker |
| `python utils/site_check.py --site "X" --compare-methods` | Find aiohttp vs Maigret discrepancies |
| `python utils/site_check.py --site "X" --diagnose` | Full diagnosis with fix recommendations |
| `python utils/check_top_n.py --top 100` | Mass-check top 100 sites |
| `maigret --self-check --site "X"` | Self-check (reports only, no auto-disable) |
| `maigret --self-check --site "X" --auto-disable` | Self-check with auto-disable |
| `maigret --self-check --site "X" --diagnose` | Self-check with detailed diagnosis |

## 7. Quick tips (lessons learned)

Practical observations from fixing top-ranked sites. Full details: section **7** in [`site-checks-guide.md`](site-checks-guide.md).

| Tip | Why it matters |
|-----|----------------|
| **API first** | Reddit, Microsoft Learn — APIs worked when web pages were blocked. Always check `/api/`, `.json` endpoints. |
| **`urlProbe` separates check from display** | Check via API, show human URL in reports. Example: Reddit API → `www.reddit.com/user/` link. |
| **aiohttp ≠ curl** | Wikipedia returned 200 for curl, 403 for aiohttp (TLS fingerprinting). Always test with Maigret directly. |
| **Use `debug.log`** | Run with `-vvv` to see raw response. Warning messages alone can be misleading. |
| **`status_code` for clean APIs** | If API returns proper 404 for missing users, prefer `status_code` over `message`. |
| **Migrate, don't delete** | MSDN → Microsoft Learn: keep old entry disabled, create new one for current service. |

## 8. Documentation maintenance

When you change Maigret, add search tools, or change check logic, keep **this playbook**, [`site-checks-guide.md`](site-checks-guide.md), and (when applicable) the template in [`socid_extractor_improvements.log`](socid_extractor_improvements.log) aligned. New log **entries** are append-only at the bottom of that file.
