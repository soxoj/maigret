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
| Generic words match (`name`, `email`) | `presenseStrs` too broad | Remove generic markers; add profile-specific ones. **Avoid** ARIA/boilerplate words (`polite`, `alert`, `navigation`, etc.) — see 7.17 in guide |
| Same HTML without JS | SPA / skeleton shell | Compare **final URL and HTTP redirects** (Maigret already follows redirects by default). If the browser shows extra routes (`/posts`, `/not-found`) only **after JS**, they will **not** appear to Maigret — try a **public JSON/API** endpoint for the same site if one exists. See **Redirects and final URL** and **Picsart** in [`site-checks-guide.md`](site-checks-guide.md). |
| Unclaimed redirects to homepage | Site returns 301/302 to main page | Use `presenseStrs` with a profile-specific marker (e.g. title fragment unique to profile pages). See 7.19 in guide |
| 403 / “Log in” / guest-only | Auth or anti-bot required | `disabled: true` |
| reCAPTCHA / “Checking your browser” / “Client Challenge” | Bot protection | Add challenge text to `errors` (→ UNKNOWN). Try a reasonable `User-Agent` in `headers`. If intermittent, `errors` is better than `disabled`. See 7.18 in guide |
| Non-standard HTTP code (468, 520–530) | CDN/WAF anti-bot | `disabled: true`. Check with `curl -sIL` to confirm the code comes from an intermediary. See 7.20 in guide |
| Non-ASCII `absenceStrs` not matching despite visible text | Page encoding ≠ UTF-8 | Check `Content-Type` for charset (KOI8-R, Windows-1251, etc.). Use ASCII-only markers, a JSON API, or `disabled: true`. See 7.16 in guide |
| Domain does not resolve / persistent timeout | Dead service | Remove entry **only** after confirming the domain is dead |

## 3. Data edits

**CRITICAL — surgical edits only.** Never rewrite `data.json` via `json.load()` + `json.dump()` — this reformats the entire ~36 000-line file and produces an unreviewable diff. Make targeted, line-level edits to only the fields you are changing. See Phase C in [`site-checks-guide.md`](site-checks-guide.md).

1. Update `url` / `urlMain` if needed (HTTPS redirects). Use optional **`urlProbe`** when the HTTP check should hit a different URL than the profile link shown in reports (API vs web UI).
2. For `message`: **always** tune string pairs so `absenceStrs` fire on “no user” pages and `presenseStrs` fire on real profiles without false absence hits.
   - **Never** use ARIA/boilerplate words as `presenseStrs` (`polite`, `alert`, `navigation`, `status`, `main`, etc.).
   - If markers contain **non-ASCII text**, verify the page charset is UTF-8. Non-UTF-8 pages (KOI8-R, Windows-1251) will silently fail byte comparison — prefer ASCII-only markers or a JSON API.
3. Engine (`engine`, e.g. XenForo): override only differing fields in the site entry so other sites are not broken.
4. Keep `status_code` only if the response **reliably** differs by status code without soft 404.
5. Add **anti-bot challenge text** to `errors` (not `absenceStrs`) when the site intermittently serves challenge pages. Common patterns: `”Client Challenge”`, `”Just a moment”`, `”Checking your browser”`, `”Attention Required”`. This produces UNKNOWN instead of false CLAIMED.

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
| **Engine templates break silently** | vBulletin `absenceStrs` failed on ~12 forums at once — many require login, showing a generic page with no error text. Check the engine template first. |
| **Search-by-author is unreliable** | phpBB `search.php?author=` checks for posts, not accounts. A user with zero posts looks identical to a non-existent user. Avoid these URLs. |
| **Some sites always generate a page** | Pbase stubs "pbase Artist {name}" for any path; ffm.bio fuzzy-matches to the nearest real entry. No markers can help — `disabled: true`. |
| **TLS fingerprinting degrades over time** | Kaggle's custom `User-Agent` fix stopped working — aiohttp now gets 404 for both usernames. Accept `disabled: true` when no API exists. |
| **API endpoints bypass Cloudflare** | Fandom `api.php` and Substack `/api/v1/` returned clean JSON while main pages were blocked by Cloudflare. Always try API paths on the same domain. |
| **Inspect Network tab for POST APIs** | Many modern platforms (e.g., Discord) heavily protect HTML profiles but expose unauthenticated `POST` endpoints for username checks. Maigret supports this natively: define `"request_method": "POST"` and `"request_payload": {"username": "{username}"}` in `data.json` to query them! |
| **Strict JSON markers are bulletproof** | When probing APIs, use `checkType: "message"` with exact JSON substrings (like `"{\"taken\": false}"`). Unlike HTML layout checks, this approach is immune to UI redesigns, A/B testing, and language translations. |
| **GraphQL supports GET too** | hashnode GraphQL works via `GET ?query=...` (URL-encoded). You can use either native POST payloads or GET `urlProbe` for GraphQL. |
| **URL-encode braces for template safety** | GraphQL `{...}` conflicts with Maigret's `{username}`. Use `%7B`/`%7D` for literal braces in `urlProbe` — `.format()` ignores percent-encoded chars. |
| **Anti-bot bypass via simple UA** | "Anubis" anti-bot PoW screens (like on Weblate) intercept modern browser UAs via HTTP 307. Hardcoding `"headers": {"User-Agent": "python-requests/2.25.1"}` circumvents the scraper filter and restores default detection logic. |
| **Rate-limit → `errors`, not `absenceStrs`** | Rate-limit wording varies across API versions. If the phrasing doesn't match `absenceStrs` and `presenseStrs` is empty, the result is a false CLAIMED. Put all "can't answer right now" strings (rate limit, CAPTCHA, maintenance) in `errors` so the result is UNKNOWN. |
| **Non-UTF-8 encoding breaks markers** | opennet.ru serves KOI8-R; UTF-8 `absenceStrs` never match raw bytes. Use ASCII-only markers, a JSON API, or `disabled: true`. |
| **ARIA attrs are presenseStrs traps** | `"polite"`, `"alert"`, `"navigation"` match `aria-live`/ARIA landmarks on any page including anti-bot challenges. Use profile-specific markers instead. |
| **Anti-bot challenge + broad markers = false CLAIMED** | Challenge pages bypass `absenceStrs` but match broad `presenseStrs`. Add challenge text (e.g. `"Client Challenge"`) to `errors` → UNKNOWN. Better than disabling for intermittent issues. |
| **Redirect-to-homepage as signal** | Salon24.pl 301-redirects unclaimed users to homepage. Use `presenseStrs` with a profile-only marker (e.g. `"- salon24.pl</title>"`). |
| **Non-standard anti-bot HTTP codes** | HTTP 468 (Tengine), 520–530 (Cloudflare) — not standard 403/429. Check with `curl -sIL`; if code is from intermediary → `disabled: true`. |
| **`--diagnose` doesn't test POST** | `site_check.py --diagnose` uses GET only. For POST APIs (Discord, Holopin), verify with `curl -X POST` or `maigret --self-check`. |

## 8. Site naming rules

Site names in `data.json` are the **keys** of the `"sites"` object and appear in user-facing reports. Follow these rules:

| Rule | Example | Counter-example |
|------|---------|-----------------|
| **Title Case** by default | `Hacker News`, `Product Hunt` | ~~`hackernews`~~, ~~`product hunt`~~ |
| **Lowercase** if the brand is written that way | `kofi`, `note`, `hi5` | ~~`Kofi`~~, ~~`Note`~~ |
| **No domain suffix** unless it is part of the recognized brand | `Flickr`, `Calendly`, `Upwork` | ~~`www.flickr.com`~~, ~~`calendly.com`~~ |
| **Domain OK** when the brand is commonly written with it | `last.fm`, `VC.ru`, `Archive.org` | |
| **No full UPPERCASE** unless the brand is an acronym/initialism | `VK`, `CNET`, `ICQ`, `IFTTT` | ~~`BOOTH`~~, ~~`VSCO`~~ → `Booth`, `VSCO` (brand) |
| **`{username}` templates** in names are OK | `{username}.tilda.ws` | |
| **Spaces** are allowed when the brand uses them | `Star Citizen`, `Google Maps` | |
| **No `www.` or `https://`** prefix | `Flickr`, `Change.org` | ~~`www.flickr.com`~~, ~~`https:`~~ |

When in doubt, check how the service refers to itself on its homepage or in its page title.

## 9. Tagging rules

### Country tags (ISO 3166-1 alpha-2)

The goal of a country tag is to **attribute a person to their country of origin or residence**, not to be a perfect truth source.

| Scenario | Action | Example |
|----------|--------|---------|
| Site is global, account says nothing about country | **No country tag** | GitHub, YouTube, Reddit, Medium, Udemy |
| Account implies connection to a specific country | **Add country tag** | VK → `ru`, Naver → `kr`, Zhihu → `cn` |
| Service used mostly in a few specific countries | **Multiple country tags OK** | Xing → `de`, `eu` |
| Very local/regional site | **Must have country tag** | Nairaland → `ng`, 4pda → `ru` |

**Do NOT** assign country tags based on traffic statistics (e.g. Alexa/SimilarWeb audience data). A site popular in India by traffic is not "Indian" if it is used globally. The `in` tag was previously over-applied this way.

### Category tags

- Every tag used in `data.json` must be registered in the `"tags"` array at the bottom of the file. The `test_tags_validity` test enforces this.
- Do not use platform/software names as tags (`writefreely`, `pixelfed`). Use category names instead (`blog`, `photo`).
- Avoid 2-letter category tags that collide with ISO country codes (e.g. `ai` = Anguilla). The `is_country_tag()` function treats any 2-letter tag as a country code.
- Keep existing category tags when modifying country tags.
- Top-50 sites by alexaRank must have at least one category tag (enforced by `test_top_sites_have_category_tag`).

## 10. Documentation maintenance

When you change Maigret, add search tools, or change check logic, keep **this playbook**, [`site-checks-guide.md`](site-checks-guide.md), and (when applicable) the template in [`socid_extractor_improvements.log`](socid_extractor_improvements.log) aligned. New log **entries** are append-only at the bottom of that file.
