# Maigret Expanded

<p align="center">
  <a href="https://github.com/dmoney96/maigretexpanded"><img alt="Repo" src="https://img.shields.io/badge/repo-maigret%20expanded-blue?style=flat-square" /></a>
  <a href="#license"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="Upstream" src="https://img.shields.io/badge/upstream-maigret-555?style=flat-square" /></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="260" alt="Maigret"/>
</p>

*Maigret Expanded* is a maintained fork of [Maigret](https://github.com/soxoj/maigret). It keeps all core Maigret capabilities—username-based discovery across thousands of sites, profile parsing, recursive discovery, tag filters, Tor/I2P support, multiple report formats—and adds **optional, opt-in extras** that you can enable per run.

---

## What’s different here?

- **Opt-in extras via `sites_extra.json`** (disabled by default).
- **API-backed checkers** (e.g. Shodan) read keys from environment variables (never stored in repo).
- **Easy customization**: add your own JSON/YAML entries without touching the core Maigret data.

> **No API keys are required** for normal use. Keys are only needed if you enable an API-backed extra.  
> For an overview of upstream features, see the official Maigret docs.

---

## Install

### Option A — Recommended (virtual environment, from source)

```bash
git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded

# create & activate venv
python3 -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1

# install this fork
python -m pip install --upgrade pip
pip install .