# Maigret Expanded

<p align="center">
  <p align="center">
    <a href="https://pypi.org/project/maigret/">
        <img alt="PyPI version badge for Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" />
    </a>
    <a href="https://pypi.org/project/maigret/">  
        <img alt="PyPI download count for Maigret" src="https://img.shields.io/pypi/dw/maigret?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="Minimum Python version required: 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret/blob/main/LICENSE">
        <img alt="License badge for Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="View count for Maigret project" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" />
    </a>
  </p>
  <p align="center">
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300"/>
  </p>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>


# Maigret Expanded

<p align="center">
  <a href="https://pypi.org/project/maigret/"><img alt="PyPI version badge for Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" /></a>
  <a href="https://pypi.org/project/maigret/"><img alt="PyPI download count for Maigret" src="https://img.shields.io/pypi/dw/maigret?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="Minimum Python version required: 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret/blob/main/LICENSE"><img alt="License badge for Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" /></a>
  <a href="https://github.com/soxoj/maigret"><img alt="View count for Maigret project" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" /></a>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective created by Georges Simenon. His investigation method is based on understanding people’s personalities and interactions.</i>

## About

**Maigret Expanded** is a maintained fork of [Maigret](https://github.com/soxoj/maigret) that retains all of Maigret’s features for collecting dossiers on a person **by username only** and adds optional, opt‑in “extras.” These extras allow you to integrate API‑backed checks (for example, Shodan) and load custom YAML or JSON entries via `sites_extra.json`. No API keys are required for normal operation; only when you choose to use an API‑backed checker do you supply a key via environment variables (e.g. `SHODAN_API_KEY`) or your own YAML.

The upstream Maigret currently supports over 3,000 sites and defaults to checking the most popular 500. Maigret Expanded uses the same core site database and adds optional extras through a separate file. You can see the original Maigret feature overview in the [official documentation](https://maigret.readthedocs.io/en/latest/features.html).

### Additional Features in Maigret Expanded

- **Opt‑in extras via `sites_extra.json`:** You can place extra site definitions in a JSON file and point `MAIGRET_EXTRA_SITES` at it. These extras are disabled by default to avoid unexpected API calls.
- **API‑backed checkers:** Example modules (like `shodan_checker.py`) demonstrate how to integrate services requiring API keys. Keys are read from environment variables and never stored in the repository.
- **YAML/JSON customisation:** Add your own modules and site definitions without modifying the core Maigret data.
- **All base Maigret features remain:** Profile parsing, recursive username discovery, tag filtering, Tor/I2P support, etc.

## Installation

You can use this fork locally or install it globally via pip. Python 3.10+ is required (3.11 recommended).

### Quick Install from GitHub

```bash
# clone your fork and install dependencies into a virtual environment
git clone https://github.com/dmoney96/maigretexpanded.git
cd maigretexpanded
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt  # for development/testing
pip install .
