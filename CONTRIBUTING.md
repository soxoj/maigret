# How to contribute

Hey! I'm really glad you're reading this. Maigret contains a lot of sites, and it is very hard to keep all the sites operational. That's why any fix is important.

## Code of Conduct

Please read and follow the [Code of Conduct](CODE_OF_CONDUCT.md) to foster a welcoming and inclusive community.

## Local setup

Install Maigret with development dependencies via [Poetry](https://python-poetry.org/):

```bash
git clone https://github.com/soxoj/maigret && cd maigret
poetry install --with dev
```

Activate the repo's git hooks **once after cloning**:

```bash
git config --local core.hooksPath .githooks/
```

The pre-commit hook does two things every time you commit changes that touch the site database:

- regenerates the database signature `maigret/resources/db_meta.json` (used to detect compatible auto-updates), and
- regenerates `sites.md` (the human-readable list of supported sites with per-engine statistics).

It also auto-stages the regenerated files so they land in the same commit as your edits. **Always run `git commit` from inside the repo so the hook can fire** — without it, your PR will land with a stale signature and a stale `sites.md`, and database auto-update will misbehave for users on your branch.

## How to contribute

There are two main ways to help.

### 1. Add a new site

**Beginner.** Use the `--submit` mode — Maigret takes a single existing-account URL, auto-detects the site engine, picks `presenseStrs` / `absenceStrs`, and offers to add the entry:

```bash
maigret --submit https://example.com/users/alice
```

`--submit` works well when the site has clean status codes and no anti-bot protection. It will *not* discover a public JSON API (`urlProbe`), classify protection (`tls_fingerprint`, `cf_js_challenge`, `ip_reputation`, ...), or recognise SPA / soft-404 pages. For those, fall back to manual editing.

**Advanced.** Edit `maigret/resources/data.json` by hand — see *Editing `data.json` safely* below. There is also an `add-a-site` issue template if you want a maintainer to do it for you.

### 2. Fix existing sites

The most useful work in this project is keeping checks accurate over time. Sites change layout, switch engines, add Cloudflare, redirect to login walls — every fix is welcome.

**Where to start.** Good candidates:

- Issues with the `false-positive` label.
- Sites currently `disabled: true` in `data.json` — many were disabled on a transient symptom and have since healed.
- Sites for which `--self-check --diagnose` reports a problem.
- A focused audit of one engine (vBulletin, XenForo, phpBB, Discourse, Flarum, ...). Engine-wide breakage usually has a single root cause and several sites can be fixed in one PR.

**Diagnose with built-in tools.**

> By default, Maigret skips entries with `disabled: true` in every mode (`--self-check`, `--site`, plain search). Whenever your target is a disabled site — diagnosing it, validating a fix, running the two-filter check below — pass **`--use-disabled-sites`** explicitly. Without the flag, the site is silently dropped from the run and you get an empty result that looks like "everything's fine".

- Per-site diagnosis with recommendations:

  ```bash
  maigret --self-check --site "SiteName" --diagnose
  # add --use-disabled-sites if the entry is currently disabled
  ```

  Without `--auto-disable`, this only reports — it never edits the database. Add `--auto-disable` only when you really want to write the result back.

- Single-site comparison of claimed vs unclaimed responses (status, markers, headers):

  ```bash
  python utils/site_check.py --site "SiteName" --diagnose
  python utils/site_check.py --site "SiteName" --compare-methods   # raw aiohttp vs Maigret's checker
  ```

- Mass check of top-N sites:

  ```bash
  python utils/check_top_n.py --top 100 --only-broken
  ```

### Understanding `checkType`

Each site entry uses one of three `checkType` modes to decide whether a profile exists. Picking the right one for your site is the most important data-modeling decision in `data.json`:

- **`message`** (most common, most flexible) — Maigret fetches the page and inspects the HTML body. The profile is reported as found when the body contains at least one substring from `presenseStrs` **and** none of the substrings from `absenceStrs`. Pick narrow, profile-specific markers: a `<title>` fragment unique to profile pages, a CSS class only rendered on profiles (e.g. `"profile-card"`), or a JSON field name from an embedded data blob (`"displayName":`). Avoid generic words (`name`, `email`) and HTML/ARIA boilerplate (`polite`, `alert`, `navigation`, `status`) — they match on every page including error and anti-bot challenge pages, and produce false positives. If the marker contains non-ASCII text, double-check the page is UTF-8 (some legacy sites serve KOI8-R or Windows-1251, in which case byte-level matching silently fails — prefer ASCII markers or a JSON API).

- **`status_code`** — Maigret only looks at the HTTP status code; 2xx means "found", anything else means "not found". Use this only when the site reliably returns proper status codes — typically clean JSON APIs that return HTTP 200 for real users and HTTP 404 for missing ones. Don't use it for sites that return HTTP 200 with a soft "user not found" page (this is the single most common cause of false-positive checks).

- **`response_url`** — Maigret follows the redirect chain and inspects the final URL. Useful when the server reliably redirects missing-user URLs to a different path (e.g. `/login`, `/404`, the homepage) while existing-user URLs stay put. For most sites `message` is a better fit; reach for `response_url` only when a redirect-based signal is genuinely the most stable one.

**`urlProbe` (optional, works with any `checkType`).** If the most reliable signal lives at a different URL than the public profile page — a JSON API, a GraphQL endpoint, a mobile-app route — set `urlProbe` to that URL. Maigret fetches `urlProbe` for the check, but reports continue to show the human-readable `url` so users see a profile link they can click. Examples: GitHub uses `https://github.com/{username}` as `url` and `https://api.github.com/users/{username}` as `urlProbe`; Picsart uses the web profile as `url` and `https://api.picsart.com/users/show/{username}.json` as `urlProbe`. A clean public API is almost always more stable than parsing HTML — it's worth probing for one before settling on `message` against the SPA shell.

**Errors vs absence.** Anything that means "the server can't answer right now" — rate limits, captchas, "Checking your browser", "unusual traffic", maintenance pages — belongs in `errors` (mapping the substring to a human-readable error string), not in `absenceStrs`. The `errors` mechanism produces an UNKNOWN result instead of a false CLAIMED or false AVAILABLE.

Full reference for `checkType`, `urlProbe`, `engine`, and the rest of the `data.json` schema is in the [development guide](docs/source/development.rst), section *How to fix false-positives*.

### Editing `data.json` safely

`data.json` is a single ~36 000-line JSON file. **Make surgical, line-level edits only.** Never rewrite it by reading it into a Python dict and dumping it back — `json.load` + `json.dump` reformats every entry and produces an unreviewable 70 000-line diff. The same rule applies to any helper script that touches the file: it must preserve the original formatting of untouched entries.

If your editor reformats JSON on save, disable that for `data.json` before editing.

### Two-filter validation when re-enabling a site

Removing `disabled: true` requires **two** independent checks. `--self-check` alone is not sufficient — it only verifies the two specific usernames recorded in the entry, so a site that returns CLAIMED for *any* arbitrary username will still pass the self-check.

```bash
# Filter 1: self-check on the recorded claimed/unclaimed pair
maigret --self-check --site "SiteName" --use-disabled-sites

# Filter 2: live probe with a clearly fake username — nothing should match
maigret noonewouldeverusethis7 --site "SiteName" --use-disabled-sites --print-not-found
```

Both filters need `--use-disabled-sites`, since a candidate for re-enable still has `disabled: true` in the working tree until your edit lands. If you forget the flag, both commands silently no-op.

If the second command reports `[+]` for the fake username, the check is a false positive — do not enable. This step takes seconds and is non-negotiable for any re-enable PR.

## Site naming, tags, and protection

- **Site naming conventions** (Title Case by default, brand-specific exceptions, no `www.` prefix, etc.) are documented in the [development guide](docs/source/development.rst), section *Site naming conventions*.

- **Country tags** (`us`, `ru`, `kr`, ...) attribute an account to a country of origin or residence — they're not a traffic-share label. Global services (GitHub, YouTube, Reddit) get **no** country tag; regional services (VK → `ru`, Naver → `kr`) **must** have one. Don't assign a country tag from Alexa/SimilarWeb audience stats.

- **Category tags** must come from the canonical `"tags"` array at the bottom of `data.json`. The `test_tags_validity` test fails if you introduce an unregistered tag. If no existing tag fits well, either pick the closest reasonable match or add the new tag to the canonical list as an explicit, separate change. Don't use platform names (`writefreely`, `pixelfed`) — use category names (`blog`, `photo`).

- **Protection tags** (`tls_fingerprint`, `ip_reputation`, `cf_js_challenge`, `cf_firewall`, `aws_waf_js_challenge`, `ddos_guard_challenge`, `js_challenge`, `custom_bot_protection`) describe the kind of anti-bot protection a site uses. One of them — **`tls_fingerprint`** — is load-bearing: when a site fingerprints the TLS handshake (JA3/JA4) and blocks non-browser clients, tagging it with `tls_fingerprint` makes Maigret automatically swap its HTTP client to [`curl_cffi`](https://github.com/lexiforest/curl_cffi) with Chrome browser emulation, which is usually enough to pass. The site stays `enabled` — no `disabled: true` is needed. Examples: Instagram, NPM, Codepen, Kickstarter, Letterboxd. The remaining tags are documentation-only and pair with `disabled: true` until a per-provider solver is integrated. The full taxonomy and the rules for picking the right tag are in the [development guide](docs/source/development.rst), section *protection (site protection tracking)*. Don't add a protection tag without empirical evidence it applies in the current environment.

## Testing

CI runs the same checks on every PR, but please run them locally first:

```bash
make format     # auto-format with black
make lint       # flake / mypy
make test       # pytest with coverage
```

## Submitting changes

Open a [GitHub PR](https://github.com/soxoj/maigret/pulls) against `main`. Always write a clear log message:

```
$ git commit -m "A brief summary of the commit
>
> A paragraph describing what changed and its impact."
```

One-line messages are fine for small changes; bigger changes should explain the *why* in the body.

## Coding conventions

### General

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python.
- Make sure all tests pass before opening the PR.

### Code style

- **Indentation**: 4 spaces per level.
- **Imports**: standard library first, third-party next, project-local last; group them logically.

### Naming

- **Variables and functions**: `snake_case`.
- **Classes**: `CamelCase`.
- **Constants**: `UPPER_CASE`.

Start reading the code and you'll get the hang of it.

## Getting help

If you're stuck on something — a check that won't behave, a setup error, an unclear field in `data.json`, or just want to discuss an approach before opening a PR — there are two places to ask:

- [GitHub Discussions](https://github.com/soxoj/maigret/discussions) — searchable, public, good for technical questions and design ideas. Prefer this for anything other contributors might run into too.
- Telegram: [@soxoj](https://t.me/soxoj) — direct channel to the maintainer, good for quick questions and informal chat.

Bug reports and feature requests still belong in [GitHub Issues](https://github.com/soxoj/maigret/issues).

## License

Maigret is MIT-licensed; by submitting a contribution you agree to publish it under the same license. There is no CLA.
