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
               maigret-expanded username --html

---

## Quick Start (CLI)

Basic search:

    maigret username

Reports:

    maigret username --html
    maigret username --pdf
    maigret username --xmind   # XMind 8 format

Filter by tags:

    maigret username --tags photo,dating
    maigret username --tags us

Multiple usernames across all sites:

    maigret user1 user2 user3 -a

Full CLI help:

    maigret --help

---

## Web Interface

Start the web UI and open it locally:

    maigret --web 5000
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
    maigret username

Windows PowerShell:

    $env:MAIGRET_EXTRA_SITES = "$PWD\sites_extra.json"
    maigret username

---

## Example: Shodan Extra (API-backed)

    # 1) Enable extras
    export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"

    # 2) Provide your key for this shell (do NOT commit keys)
    export SHODAN_API_KEY="your_real_key_here"

    # 3) Run
    maigret username

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

---

## Contributing

PRs welcome! Keep extras opt-in, document them, and never commit secrets.
If you add an API-backed checker, include a short note and a minimal example entry for "sites_extra.json".

---

## License

MIT © Maigret Expanded (this fork)
MIT © Maigret
MIT © Sherlock Project — Original concept by Siddharth Dushantha
