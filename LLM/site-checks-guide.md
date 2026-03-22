# Site checks — guide (Maigret)

Working document for future changes: workflow, findings from reviews, and practical steps. See also [`site-checks-playbook.md`](site-checks-playbook.md) (short checklist), [`socid_extractor_improvements.log`](socid_extractor_improvements.log) (proposals for upstream identity extraction), and the code in [`maigret/checking.py`](../maigret/checking.py).

**Documentation maintenance:** whenever you improve Maigret, add search tooling, or change check logic, update **this file** and [`site-checks-playbook.md`](site-checks-playbook.md) in sync (see the section at the end). If you change rules about the JSON API check or the `socid_extractor` log format, update **[`socid_extractor_improvements.log`](socid_extractor_improvements.log)** (template / header) together with this guide.

---

## 1. How checks work

Logic lives in `process_site_result` ([`maigret/checking.py`](../maigret/checking.py)):

| `checkType` | Meaning |
|-------------|---------|
| `message` | Profile is “found” if the HTML contains **none** of the `absenceStrs` substrings **and** at least one `presenseStrs` marker matches. If `presenseStrs` is **empty**, presence is treated as true for **any** page (risky configuration). |
| `status_code` | HTTP **2xx** is enough — only safe if the server does **not** return 200 for “user not found”. |
| `response_url` | Custom flow with **redirects disabled** so the status/URL of the *first* response can be used. |

For other `checkType` values, [`make_site_result`](../maigret/checking.py) sets **`allow_redirects=True`**: the client follows redirects and `process_site_result` sees the **final** response body and status (not the pre-redirect hop). You do **not** need to “turn on” follow-redirect separately for most sites.

Sites with an `engine` field (e.g. XenForo) are merged with a template from the `engines` section in [`maigret/resources/data.json`](../maigret/resources/data.json) ([`MaigretSite.update_from_engine`](../maigret/sites.py)).

### `urlProbe`: probe URL vs reported profile URL

- **`url`** — pattern for the **public profile page** users should open (what appears in reports as `url_user`). Supports `{username}`, `{urlMain}`, `{urlSubpath}`; the username segment is URL-encoded when the string is built ([`make_site_result`](../maigret/checking.py)).
- **`urlProbe`** (optional) — if set, Maigret sends the HTTP **GET** (or HEAD where applicable) to **this** URL for the check, instead of to `url`. Same placeholders. Use it when the reliable signal is a **JSON/API** endpoint but the human-facing link must stay on the main site (e.g. `https://picsart.com/u/{username}` + probe `https://api.picsart.com/users/show/{username}.json`, or GitHub’s `https://github.com/{username}` + `https://api.github.com/users/{username}`).

If `urlProbe` is omitted, the probe URL defaults to `url`.

### Redirects and final URL as a signal

If the **HTML shell** looks the same for “user exists” and “user does not exist” (typical SPA), it is still worth checking whether the **server** behaves differently:

- **Final URL** after redirects (e.g. profile canonical URL vs `/404` path).
- **Redirect chain** length or target host (e.g. lander vs profile).

If that differs reliably, you may be able to use **`checkType`: `response_url`** in [`data.json`](../maigret/resources/data.json) (no auto-follow) or extend logic — but only when the difference is stable.

**Server-side HTTP vs client-side navigation.** Maigret follows **HTTP** redirects only; it does **not** run JavaScript. If the browser shows a navigation to `/u/name/posts` or `/not-found` **after** the SPA bundle loads, that may never appear as an extra hop in `curl`/aiohttp — only a **trailing-slash** `301` might show up. Always confirm with `curl -sIL` / a small script whether the **Location** chain differs for real vs fake users before relying on URL-based rules.

**Empirical check (claimed vs non-existent usernames, `GET` with follow redirects, no JS):**

| Site | Result |
|------|--------|
| **Kaskus** | No HTTP redirects beyond the request path; same generic `<title>` and near-identical body length — **no** discriminating signal from redirects alone. |
| **Bibsonomy** | Both requests redirect to **`/pow-challenge/?return=/user/...`** (proof-of-work). Only the `return` path changes with the username; **both** existing and fake hit the same challenge flow — not a profile-vs-missing distinction. |
| **Picsart (web UI `https://picsart.com/u/{username}`)** | Only a **trailing-slash** `301`; the first HTML is the same empty app shell (~3 KiB) for real and fake users. Browser-only routes such as `…/posts` vs `…/not-found` are **not** visible as additional HTTP redirects in this pipeline. |

**Picsart — workable check via public API.** The site exposes **`https://api.picsart.com/users/show/{username}.json`**: JSON with `"status":"success"` and a user object when the account exists, and `"reason":"user_not_found"` when it does not. Put that URL in **`urlProbe`**, set **`url`** to the web profile pattern **`https://picsart.com/u/{username}`**, and use **`checkType`: `message`** with narrow `presenseStrs` / `absenceStrs` so reports show the human link while the request hits the API (see **`urlProbe`** above).

For **Kaskus** and **Bibsonomy**, HTTP-level comparison still does **not** unlock a safe check without PoW / richer signals; keep **`disabled: true`** until something stable appears (API, SSR markers, etc.).

---

## 2. Standard checks: public JSON API and `socid_extractor` log

### 2.1 Public JSON API (always)

When diagnosing a site—especially **SPAs**, **soft 404s**, or **near-identical HTML** for real vs fake users—**routinely look for a public JSON (or JSON-like) API** used for profile or user lookup. Typical leads: paths containing `/api/`, `/v1/`, `graphql`, `users/show`, `.json` suffixes, or the same endpoints mobile apps use. Verify with `curl` (or the Maigret request path) that **claimed** and **unclaimed** usernames produce **reliably different** bodies or status codes. If such an endpoint is more stable than HTML, put it in **`urlProbe`** and keep **`url`** as the canonical profile page on the main site (see **`urlProbe`** in section 1). If there is no separate public URL for humans, you may still point **`url`** at the API only (reports will show that URL).

This is a **standard** part of site-check work, not an optional extra.

### 2.2 Mandatory: [`LLM/socid_extractor_improvements.log`](socid_extractor_improvements.log)

If you discover **either**:

1. **JSON embedded in HTML** with user/profile fields (inline scripts, `__NEXT_DATA__`, `application/ld+json`, hydration blobs, etc.), or  
2. A **standalone JSON HTTP response** (public API) with user/profile data for that service,

you **must append** a proposal block to **[`LLM/socid_extractor_improvements.log`](socid_extractor_improvements.log)**.

**Why:** Maigret calls [`socid_extractor.extract`](https://pypi.org/project/socid-extractor/) on the response body ([`extract_ids_data` in `checking.py`](../maigret/checking.py)) to fill `ids_data`. New payloads usually need a **new scheme** upstream (`flags`, `regex`, optional `extract_json`, `fields`, optional `url_mutations` / `transforms`), matching patterns such as **`GitHub API`** or **`Gitlab API`** in `socid_extractor`’s `schemes.py`.

**Each log entry must include:**

- **Date** — ISO `YYYY-MM-DD` (day you add the entry).  
- **Example username** — Prefer the site’s `usernameClaimed` from `data.json`, or any account that reproduces the payload.  
- **Proposal** — Use the **block template** in the log file: detection idea, optional URL mutation, and field mappings in the same style as existing schemes.

If the service is **already covered** by an existing `socid_extractor` scheme, add a **short** entry anyway (date, example username, scheme name, “already implemented”) so there is an audit trail.

Do **not** paste secrets, cookies, or full private JSON; short key names and structure hints are enough.

---

## 3. Improvement workflow

### Phase A — Reproduce

1. Targeted run:
   ```bash
   maigret --db /path/to/maigret/resources/data.json \
     TEST_USERNAME \
     --site "SiteName" \
     --print-not-found --print-errors \
     --no-progressbar -vv
   ```
2. Run separately with a **real** existing username and a **definitely non-existent** one (as `usernameClaimed` / `usernameUnclaimed` in JSON).
3. If needed: `-vvv` and `debug.log` (raw response).
4. Automated pair check:
   ```bash
   maigret --db ... --self-check --site "SiteName" --no-progressbar
   ```

### Phase B — Classify the cause

| Symptom | Likely cause |
|---------|----------------|
| False “found” with `status_code` | Soft 404 (200 on a “not found” page). |
| False “found” with `message` | Overly broad `presenseStrs` (`name`, `email`, JSON keys) or stale `absenceStrs`. |
| Same HTML for different users | SPA / skeleton shell before hydration — also compare **final URL / redirect chain** (see above); if still identical, often `disabled`. |
| Login page instead of profile | XenForo etc.: guest, `ignore403`, “must be logged in” strings. |
| reCAPTCHA / “Checking your browser” / “not a bot” | Bot protection; Maigret’s default User-Agent may worsen the response. |
| Redirect to another domain / lander | Stale URL template. |

### Phase C — Edits in [`data.json`](../maigret/resources/data.json)

1. Update `url` / `urlMain` if needed (HTTPS, new profile path).
2. Replace inappropriate `status_code` with `message` (or `response_url`), choosing:
   - **`absenceStrs`** — only what reliably appears on the “user does not exist” page;
   - **`presenseStrs`** — narrow markers of a real profile (avoid generic words).
3. For XenForo: override only fields that differ in the site entry; do not break the global `engines` template.
4. Refresh `usernameClaimed` / `usernameUnclaimed` if reference accounts disappeared.
5. Set **`headers`** (e.g. another `User-Agent`) if the site serves a captcha only to “suspicious” clients.
6. Use **`errors`**: HTML substring → meaningful check error (UNKNOWN), so it is not confused with “available”.

### Phase D — Decision criteria

| Outcome | When to use |
|---------|-------------|
| **Check fixed** | The `claimed` / `unclaimed` pair behaves predictably, `--self-check` passes, no regression on a similar site with the same engine. |
| **Check disabled** (`disabled: true`) | Cloudflare / anti-bot / login required / indistinguishable SPA without stable markers. |
| **Entry removed** | **Only** if the domain/service is gone (NXDOMAIN, clearly dead project), not “because it is hard to fix”. |

### Phase E — Before commit

- `maigret --self-check` for affected sites.
- `make test`.

---

## 4. Findings from reviews (concrete site batch)

Summary from an earlier false-positive review for: OpenSea, Mercado Livre, Redtube, Tom’s Guide, Kaggle, Kaskus, Livemaster, TechPowerUp, authorSTREAM, Bibsonomy, Bulbagarden, iXBT, Serebii, Picsart, Hashnode, hi5.

### What most often broke checks

1. **`status_code` where content checks are needed** — soft 404 with status 200.
2. **Broad `presenseStrs`** — matches on error pages or generic SPA shells.
3. **XenForo + guest** — HTML includes strings like “You must be logged in” that overlap the engine template.
4. **User-Agent** — on some sites (e.g. Kaggle) the default UA triggered a reCAPTCHA page instead of profile HTML; a deliberate `User-Agent` in site `headers` helped.
5. **SPAs and redirects** — identical first HTML, redirect to lander / another product (hi5 → Tagged), URL format changes by region (Mercado Livre).

### What worked as a fix

- Switching to **`message`** with narrow strings from **`<title>`** or unique markup where stable (**Kaggle**, **Mercado Livre**, **Hashnode**).
- For **Kaggle**, additionally: **`headers`**, **`errors`** for browser-check text.
- **Redtube** stayed valid on **`status_code`** with a stable **404** for non-existent users.
- **Picsart**: the web profile URL is a thin SPA shell; use the **JSON API** (`api.picsart.com/users/show/{username}.json`) in **`url`** with **`message`**-style markers (`"status":"success"` vs `user_not_found`), not the browser-only `/posts` vs `/not-found` navigation.

### What required disabling checks

Where you **cannot** reliably tell “profile exists” from “no profile” without bypassing protection, login, or full JS:

- Anti-bot / captcha / “not a bot” page;
- Guest-only access to the needed page;
- SPA with indistinguishable first response;
- Forums returning **403** and a login page instead of a member profile for the member-search URL;
- Stale URLs that redirect to a stub.

In those cases **`disabled: true`** is better than false “found”; remove the DB entry only on **actual** domain death.

### Code notes

- For the `status_code` branch in `process_site_result`, use **strict** comparison `check_type == "status_code"`, not a substring match inside `"status_code"`.
- Treat empty `presenseStrs` with `message` as risky: when debugging, watch DEBUG-level logs if that diagnostics exists in code.

---

## 5. Future ideas (Maigret improvements)

- A mode or script: one site, two usernames, print statuses and first N bytes of the response (wrapper around `maigret()`).
- Document in CLI help that **`--use-disabled-sites`** is needed to analyze disabled entries.

---

## 6. Development utilities

### 6.1 `utils/site_check.py` — Single site diagnostics

A comprehensive utility for testing individual sites with multiple modes:

```bash
# Basic comparison of claimed vs unclaimed (aiohttp)
python utils/site_check.py --site "VK" --check-claimed

# Test via Maigret's checker directly
python utils/site_check.py --site "VK" --maigret

# Compare aiohttp vs Maigret results (find discrepancies)
python utils/site_check.py --site "VK" --compare-methods

# Full diagnosis with recommendations
python utils/site_check.py --site "VK" --diagnose

# Test with custom URL
python utils/site_check.py --url "https://example.com/{username}" --compare user1 user2

# Find a valid username for a site
python utils/site_check.py --site "VK" --find-user
```

**Key features:**
- `--maigret` — Uses Maigret's actual checking code, not raw aiohttp
- `--compare-methods` — Shows if aiohttp and Maigret see different results (useful for debugging)
- `--diagnose` — Validates checkType against actual responses, suggests fixes
- Color output with markers detection (captcha, cloudflare, login, etc.)
- `--json` flag for machine-readable output

**When to use each mode:**

| Mode | Use case |
|------|----------|
| `--check-claimed` | Quick sanity check: do claimed/unclaimed still differ? |
| `--maigret` | Verify Maigret's actual behavior matches expectations |
| `--compare-methods` | Debug "works in curl but fails in Maigret" issues |
| `--diagnose` | Full analysis when a site is broken, get fix recommendations |

### 6.2 `utils/check_top_n.py` — Mass site checking

Batch-check top N sites by Alexa rank with categorized reporting:

```bash
# Check top 100 sites
python utils/check_top_n.py --top 100

# Faster with more parallelism
python utils/check_top_n.py --top 100 --parallel 10

# Output JSON report
python utils/check_top_n.py --top 100 --output report.json

# Only show broken sites
python utils/check_top_n.py --top 100 --only-broken
```

**Output categories:**
- `working` — Site check passes
- `broken` — Check fails (wrong status, missing markers)
- `timeout` — Request timed out
- `anti_bot` — 403/429 or captcha detected
- `error` — Connection or other errors
- `disabled` — Already disabled in data.json

**Report includes:**
- Summary counts by category
- List of broken sites with issues
- Recommendations for fixes (e.g., "Switch to checkType: status_code")

### 6.3 Self-check behavior (`--self-check`)

The self-check command has been improved to be less aggressive:

```bash
# Check sites WITHOUT auto-disabling (default)
maigret --self-check --site "VK"

# Auto-disable failing sites (old behavior)
maigret --self-check --site "VK" --auto-disable

# Show detailed diagnosis for each failure
maigret --self-check --site "VK" --diagnose
```

**Behavior changes:**

| Flag | Effect |
|------|--------|
| `--self-check` alone | Reports issues but does NOT disable sites |
| `--auto-disable` | Automatically disables sites that fail (opt-in) |
| `--diagnose` | Prints detailed diagnosis with recommendations |

**Why this matters:**
- Old behavior was too aggressive — sites got disabled without explanation
- New behavior reports issues and suggests fixes
- Explicit `--auto-disable` required to modify database

---

## 7. Lessons learned (practical observations)

Collected from hands-on work fixing top-ranked sites (Reddit, Wikipedia, Microsoft Learn, Baidu, etc.).

### 7.1 JSON API is the first thing to look for

Both Reddit and Microsoft Learn had working public APIs that solved the problem entirely. The web pages were SPAs or blocked by anti-bot measures, but the APIs worked reliably:

- **Reddit**: `https://api.reddit.com/user/{username}/about` — returns JSON with user data or `{"message": "Not Found", "error": 404}`.
- **Microsoft Learn**: `https://learn.microsoft.com/api/profiles/{username}` — returns JSON with `userName` field or HTTP 404.

This confirms the playbook recommendation: always check for `/api/`, `.json`, GraphQL endpoints before giving up on a site.

### 7.2 `urlProbe` is a powerful tool

It separates "what we check" (API) from "what we show the user" (human-readable profile URL). Reddit is a perfect example:

```json
{
  "url": "https://www.reddit.com/user/{username}",
  "urlProbe": "https://api.reddit.com/user/{username}/about",
  "checkType": "message",
  "presenseStrs": ["\"name\":"],
  "absenceStrs": ["Not Found"]
}
```

The check hits the API, but reports display `www.reddit.com/user/blue`.

### 7.3 aiohttp ≠ curl ≠ requests

Wikipedia returned HTTP 200 for `curl` and Python `requests`, but HTTP 403 for `aiohttp`. This is **TLS fingerprinting** — the server identifies the HTTP library by cryptographic characteristics of the TLS handshake, not by headers.

**Key insight:** Changing `User-Agent` does **not** help against TLS fingerprinting. Always test with aiohttp directly (or via Maigret with `-vvv` and `debug.log`), not just `curl`.

```python
# This returns 403 for Wikipedia even with browser UA:
async with aiohttp.ClientSession() as session:
    async with session.get(url, headers={"User-Agent": "Mozilla/5.0 ..."}) as resp:
        print(resp.status)  # 403
```

### 7.4 HTTP 403 in Maigret can mean different things

Initially it seemed Wikipedia was returning 403, but `curl` showed 200. Only `debug.log` revealed the real picture — aiohttp was getting blocked at TLS level.

**Lesson:** Use `-vvv` flag and inspect `debug.log` for raw response status and body. The warning message alone may be misleading.

### 7.5 Dead services migrate, not disappear

MSDN Social and TechNet profiles redirected to Microsoft Learn. Instead of deleting old entries:

1. Keep old entries with `disabled: true` as historical record.
2. Create a new entry for the current service with working API.

This preserves audit trail and avoids breaking existing workflows.

### 7.6 `status_code` is more reliable than `message` for APIs

Microsoft Learn API returns HTTP 404 for non-existent users — a clean signal without HTML parsing. For JSON APIs that return proper HTTP status codes, `status_code` is often the best choice:

```json
{
  "checkType": "status_code",
  "urlProbe": "https://learn.microsoft.com/api/profiles/{username}"
}
```

No need for fragile string matching when the API speaks HTTP correctly.

### 7.7 The playbook classification works

The decision tree from the documentation accurately describes real-world cases:

| Situation | Playbook says | Actual result |
|-----------|---------------|---------------|
| Captcha (Baidu) | `disabled: true` | Correct |
| TLS fingerprinting (Wikipedia) | `disabled: true` (anti-bot) | Correct |
| Working API available (Reddit, MS Learn) | Use `urlProbe` | Correct |
| Service migrated (MSDN → MS Learn) | Update URL or create new entry | Correct |

---

## Documentation maintenance

For any of the changes below, **always** keep these artifacts in sync — this file ([`site-checks-guide.md`](site-checks-guide.md)), [`site-checks-playbook.md`](site-checks-playbook.md), and (when rules or templates change) the header/template in [`socid_extractor_improvements.log`](socid_extractor_improvements.log):

- Maigret code changes (including [`maigret/checking.py`](../maigret/checking.py), request executors, CLI);
- New or changed search tools / helper utilities for site checks;
- Changes to rules or semantics of `checkType`, `data.json` fields, self-check, etc.;
- Changes to the **public JSON API** diagnostic step or **mandatory** `socid_extractor` logging rules.

Prefer updating the guide, playbook, and log template in one commit or in the same task so instructions do not diverge. **Append-only:** new proposals go at the bottom of `socid_extractor_improvements.log`; do not delete historical entries when editing the template.
