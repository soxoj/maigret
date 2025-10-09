# Maigret Expanded

<p align="center">
  <a href="https://pypi.org/project/maigret/"><img alt="PyPI version badge for Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" /></a>
  <a href="https://pypi.org/project/maigret/"><img alt="PyPI download count for Maigret" src="https://img.shields.io/pypi/dw/maigret?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="Minimum Python version required: 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret/blob/main/LICENSE"><img alt="License badge for Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="View count for Maigret project" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" /></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300"/>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective created by Georges Simenon. His method is based on understanding people’s personalities and interactions.</i>

---

## What is Maigret Expanded?

**Maigret Expanded** is a maintained fork of [Maigret](https://github.com/soxoj/maigret). It keeps all core Maigret features (username-based account discovery across thousands of sites, profile parsing, recursive discovery, tag filters, Tor/I2P support, reports) and adds **optional, opt-in “extras”**:

- **Opt-in extras via `sites_extra.json`** (disabled by default).
- **API-backed checkers** (e.g., Shodan) that read keys from environment variables.
- **Easy customization** with your own JSON/YAML entries without touching core data.

> Normal usage requires **no API keys**. Keys are only needed if you opt into API-backed extras.  
> For the original Maigret feature overview, see the [official docs](https://maigret.readthedocs.io/en/latest/features.html).

---

## Quick Start (recommended: virtualenv)

```bash
# 1) clone this fork
git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded

# 2) create & activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 3) install
pip install --upgrade pip
pip install .

# 4) basic usage
maigret username
