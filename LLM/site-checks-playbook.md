# Site checks — playbook (Maigret)

Short checklist for edits to [`maigret/resources/data.json`](../maigret/resources/data.json) and, when needed, [`maigret/checking.py`](../maigret/checking.py). Full guide: [`site-checks-guide.md`](site-checks-guide.md). Upstream extraction proposals: [`socid_extractor_improvements.log`](socid_extractor_improvements.log).

**Documentation maintenance:** whenever you improve Maigret, add search tooling, or change check logic, update **both** this file and [`site-checks-guide.md`](site-checks-guide.md) (see the “Documentation maintenance” section at the end of that file). When JSON API / `socid_extractor` logging rules change, update the **template header** in [`socid_extractor_improvements.log`](socid_extractor_improvements.log) in the same change.

## 0. Standard checks (do alongside reproduce / classify)

- **Public JSON API:** always look for a stable JSON (or GraphQL JSON) profile endpoint (`/api/`, `.json`, mobile-style URLs). Prefer it in `url` when it differentiates claimed vs unclaimed users better than HTML. Details: section **2.1** in [`site-checks-guide.md`](site-checks-guide.md).
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

1. Update `url` / `urlMain` if needed (HTTPS redirects).
2. For `message`: **always** tune string pairs so `absenceStrs` fire on “no user” pages and `presenseStrs` fire on real profiles without false absence hits.
3. Engine (`engine`, e.g. XenForo): override only differing fields in the site entry so other sites are not broken.
4. Keep `status_code` only if the response **reliably** differs by status code without soft 404.

## 4. Verify

- `maigret --self-check --site "SiteName" --db ...` for touched entries.
- `make test` before commit.

## 5. Code notes

- `process_site_result` uses strict comparison to `"status_code"` for `checkType` (not a substring trick).
- Empty `presenseStrs` with `message` means “presence always true”; a debug line is logged only at DEBUG level.

## 6. Documentation maintenance

When you change Maigret, add search tools, or change check logic, keep **this playbook**, [`site-checks-guide.md`](site-checks-guide.md), and (when applicable) the template in [`socid_extractor_improvements.log`](socid_extractor_improvements.log) aligned. New log **entries** are append-only at the bottom of that file.
