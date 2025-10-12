# Maigret Expanded

[![Repo](https://img.shields.io/badge/repo-maigret%20expanded-blue?style=flat-square)](https://github.com/dmoney96/maigretexpanded)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#license)
[![Upstream](https://img.shields.io/badge/upstream-maigret-555?style=flat-square)](https://github.com/soxoj/maigret)

![Maigret](https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png)

## What is Maigret Expanded?

Maigret Expanded is a maintained fork of Maigret. It keeps all core Maigret capabilities
(username-based discovery across thousands of sites; profile parsing; recursive discovery; tag filters;
Tor/I2P; multiple report formats) and adds optional, opt-in extras.

Extras include:
- Opt-in site entries via "sites_extra.json" (disabled by default).
- API-backed checkers (e.g., Shodan) that read keys from environment variables (never stored in the repo).
- Easy customization: add your own JSON/YAML entries without touching the core Maigret data.

Normal usage requires no API keys. Keys are only needed if you enable an API-backed extra.
Upstream feature overview: https://maigret.readthedocs.io/

---

## Install

**CLI name used in this fork:** `maigretexpanded`.
If you also have upstream installed, you may still have a separate `maigret` on your PATH.
All examples below use `maigretexpanded` to avoid confusion.


Note: the CLI command name remains "maigret".

### Option A — Recommended (virtual environment, from source)

    git clone https://github.com/dmoney96/maigretexpanded.git
    cd maigretexpanded

    python3 -m venv .venv
    source .venv/bin/activate

    python -m pip install --upgrade pip
    pip install .

### Option B — System-wide (global Python)

    git clone https://github.com/dmoney96/maigretexpanded.git
    cd maigretexpanded
    pip3 install .

Tip: if you already have another Maigret installed globally, prefer Option A to avoid PATH conflicts.

### Option C — Docker

Upstream image (no extras):

    docker pull soxoj/maigret
    docker run -v "$PWD/reports:/app/reports" soxoj/maigret:latest username --html

Local image from this fork (supports extras):

    git clone https://github.com/dmoney96/maigretexpanded.git
    cd maigretexpanded
    docker build -t maigret-expanded .

If you use extras, mount your extras file and set the env var:

    docker run -e MAIGRET_EXTRA_SITES=/app/sites_extra.json \
               -v "$PWD/sites_extra.json:/app/sites_extra.json:ro" \
               -v "$PWD/reports:/app/reports" \
               maigretexpanded-expanded username --html

---

## Quick Start (CLI)

Basic search:

    maigretexpanded username

Reports:

    maigretexpanded username --html
    maigretexpanded username --pdf
    maigretexpanded username --xmind   # XMind 8 format

Filter by tags:

    maigretexpanded username --tags photo,dating
    maigretexpanded username --tags us

Multiple usernames across all sites:

    maigretexpanded user1 user2 user3 -a

Full CLI help:

    maigretexpanded --help

---

## Web Interface

Start the web UI and open it locally:

    maigretexpanded --web 5000
    # then visit http://127.0.0.1:5000

---

## Opt-in Extras

Extras are off by default. Point MAIGRET_EXTRA_SITES to a JSON file containing your extra entries.

1) Create "sites_extra.json":

    {
      "shodan": {
        "name": "Shodan",
        "url": "https://api.shodan.io/shodan/host/search?query={username}",
        "type": "username",
        "priority": 120,
        "enabled_by_default": false,
        "notes": "Opt-in: requires SHODAN_API_KEY; limited info."
      }
    }

2) Enable for your shell session:

    export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"
    maigretexpanded username

Windows PowerShell:

    $env:MAIGRET_EXTRA_SITES = "$PWD\sites_extra.json"
    maigretexpanded username

---

## Example: Shodan Extra (API-backed)

    # 1) Enable extras
    export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"

    # 2) Provide your key for this shell (do NOT commit keys)
    export SHODAN_API_KEY="your_real_key_here"

    # 3) Run
    maigretexpanded username

    # Remove key from current shell
    unset SHODAN_API_KEY

---

## Troubleshooting

Wrong Maigret is running (PATH conflict)? Run inside the venv from this repo:

    source .venv/bin/activate
    which -a maigret

Docker + extras: remember to mount "sites_extra.json" and set:
-e MAIGRET_EXTRA_SITES=/app/sites_extra.json

macOS system-wide/pipx build error about "pycairo" (seen when not using a venv)?
Install build deps, then retry:

    brew install pkg-config cairo

Getting errors?

maigretexpanded username \
  --tags dev,forum,media,us \
  -n 8 --timeout 25 --retries 1 --no-recursion --print-errors

Want to get granular with site allows?

# Curated set that tends to give “hard” confirmations
SITES=(
  GitHub GitHubGist Keybase
  YouTube TikTok Twitch Imgur
  AppleDeveloper AppleDiscussions
  Duolingo TradingView Roblox
  Chess Letterboxd MixCloud
  Venmo Docker\ Hub
)

maigretexpanded username \
  -n 8 --timeout 25 --retries 1 --no-recursion --print-errors \
  $(printf ' --site %q' "${SITES[@]}")

# Curated set that tends to give “hard” confirmations
SITES=(
  GitHub GitHubGist Keybase
  YouTube TikTok Twitch Imgur
  AppleDeveloper AppleDiscussions
  Duolingo TradingView Roblox
  Chess Letterboxd MixCloud
  Venmo Docker\ Hub
)

---
## Other Considerations

Reading results (what to trust)
	•	Strong: entries that show structured fields (e.g., uid, created_at, follower_count, bio, etc.) or point to a canonical profile URL (like github.com/<user>).
	•	Weak: “search/filter” URLs (e.g., …/search?query=dmoney96) or generic list pages—treat these as possible leads, not confirmations.

If Cloudflare/403 noise stays high
	•	Keep -n low (6–8).
	•	Bump --timeout to 30.
	•	If you have a clean residential/VPN exit, try it (some sites block specific ASNs harshly).
	•	Re-run only the sites that failed with captchas (Cloudflare) or 403s.
---

## Contributing

PRs welcome! Keep extras opt-in, document them, and never commit secrets.
If you add an API-backed checker, include a short note and a minimal example entry for "sites_extra.json".

---

## License

MIT © Maigret Expanded (this fork)
MIT © Maigret
MIT © Sherlock Project — Original concept by Siddharth Dushantha
