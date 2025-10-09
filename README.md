Maigret Expanded

<p align="center">
  <a href="https://github.com/dmoney96/maigretexpanded"><img alt="Repo" src="https://img.shields.io/badge/repo-maigret%20expanded-blue?style=flat-square" /></a>
  <a href="#license"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="Upstream" src="https://img.shields.io/badge/upstream-maigret-555?style=flat-square" /></a>
</p>


<p align="center">
  <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="260" alt="Maigret"/>
</p>


The Commissioner Jules Maigret is a fictional French detective created by Georges Simenon. His method is grounded in understanding people and their interactions.

⸻

What is Maigret Expanded?

Maigret Expanded is a maintained fork of the original Maigret. It keeps all core Maigret capabilities (username-based discovery across thousands of sites; profile parsing; recursive discovery; tags; Tor/I2P support; multiple report formats) and adds optional, opt-in “extras.”

Key additions:
	•	Opt-in extras via sites_extra.json (disabled by default).
	•	API-backed checkers (e.g., Shodan) that read keys from environment variables (never stored in repo).
	•	Easy customization: add your own JSON/YAML entries without touching the core Maigret data.

Normal usage needs no API keys. Keys are only needed if you choose to enable an API-backed extra.
For a complete overview of upstream features, see the Maigret docs.

⸻

Install

Option A — Recommended (virtual environment, from source)

git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded

# create & activate venv
python3 -m venv .venv
source .venv/bin/activate

# install this fork
python -m pip install --upgrade pip
pip install .

Option B — System-wide (global Python)

git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded
pip3 install .

Tip: If you previously installed a different Maigret globally, you may want to use a venv (Option A) to keep them separate.

Option C — Docker
	•	Upstream image (no extras):

docker pull soxoj/maigret
docker run -v "$PWD/reports:/app/reports" soxoj/maigret:latest username --html


	•	Local image from this fork (supports extras):

git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded
docker build -t maigret-expanded .
# mount your extras file (see below) if you use extras
docker run -e MAIGRET_EXTRA_SITES=/app/sites_extra.json \
           -v "$PWD/sites_extra.json:/app/sites_extra.json:ro" \
           -v "$PWD/reports:/app/reports" \
           maigret-expanded username --html



⸻

Quick Start (CLI)

# Basic Search
maigret username

# Make Reports
maigret username --html
maigret username --pdf
maigret username --xmind

# Filter By Tags
maigret username --tags photo,dating
maigret username --tags us

# Search Multiple Usernames On All Available Sites
maigret user1 user2 user3 -a

Use maigret --help for full options. Upstream CLI docs also apply to this fork.

⸻

Web Interface

Start the web UI and open it locally:

maigret --web 5000
# then visit http://127.0.0.1:5000


⸻

Opt-in Extras (JSON) — How to enable

Extras are off by default. You enable them by pointing the environment variable MAIGRET_EXTRA_SITES at a JSON file containing your extra entries.
	1.	Create sites_extra.json in your repo (or any path you prefer):

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

	2.	Enable extras for a run (shell session only):

export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"
maigret username

Windows (PowerShell):
setx MAIGRET_EXTRA_SITES "$PWD\sites_extra.json" (new shells only), or
$env:MAIGRET_EXTRA_SITES = "$PWD\sites_extra.json" (current shell)

⸻

Example: Shodan extra (API-backed)

This fork includes an example Shodan checker module and tests. To try it locally:

# 1) Make sure extras are enabled
export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"

# 2) Set your key (current shell only; do NOT commit keys)
export SHODAN_API_KEY="your_real_key_here"

# 3) Run a search that may leverage the checker
maigret username

To remove the key from the current shell:

unset SHODAN_API_KEY

CI tip (fork owners): store keys in GitHub Actions Secrets (e.g., SHODAN_API_KEY) and use a manual workflow_dispatch if you maintain an integration job. Never commit API keys.

⸻

Development & Testing

Set up a dev environment and run tests:

# from repo root
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q

Run a specific test:

pytest -q tests/test_shodan_checker.py
pytest -q tests/test_mastodon_api_checker.py

Common pitfalls:
	•	Env vars scope: export changes only the current shell (and child processes). Open a new shell → you’ll need to re-export.
	•	PATH conflicts: If maigret resolves to a different install, prefer running inside a venv (see Install Option A).
	•	Docker & extras: mount your sites_extra.json and set MAIGRET_EXTRA_SITES inside the container run command.

⸻

FAQs

Does this replace upstream Maigret?
No. It’s a fork that adds optional extras. Upstream Maigret remains the canonical project.

Do I need API keys?
Not for normal usage. Only if you opt into API-backed extras (e.g., Shodan).

Can I use the upstream Docker image with extras?
No. Build the image from this fork if you want extras.

Where do I put secrets?
Locally: as environment variables in your shell.
CI: as GitHub Actions Secrets in your fork.

⸻

Contributing

PRs welcome! Keep extras opt-in, documented, and key-safe (no secrets in code). Add unit tests that mock network calls. If you propose a new API-backed checker, include a short README note and a minimal example entry for sites_extra.json.

⸻

License

MIT © Maigret Expanded (this fork)
MIT © Maigret
MIT © Sherlock Project — Original concept by Siddharth Dushantha

⸻
