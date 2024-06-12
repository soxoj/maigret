# Maigret

<p align="center">
  <p align="center">
    <a href="https://pypi.org/project/maigret/">
      <img alt="PyPI" src="https://img.shields.io/pypi/v/maigret?style=flat-square">
    </a>
    <a href="https://pypi.org/project/maigret/">
      <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/maigret?style=flat-square">
    </a>
    <a href="https://pypi.org/project/maigret/">
      <img alt="Views" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square">
    </a>
  </p>
  <p align="center">
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="200"/>
  </p>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

<b>👉👉👉 [Online Telegram bot](https://t.me/osint_maigret_bot)</b>

## About

**Maigret** collects a dossier on a person **by username only**, checking for accounts on a huge number of sites and gathering all the available information from web pages. No API keys required. Maigret is an easy-to-use and powerful fork of [Sherlock](https://github.com/sherlock-project/sherlock).

Currently supported more than 3000 sites ([full list](https://github.com/soxoj/maigret/blob/main/sites.md)), search is launched against 500 popular sites in descending order of popularity by default. Also supported checking of Tor sites, I2P sites, and domains (via DNS resolving).

## Main features

* Profile pages parsing, [extraction](https://github.com/soxoj/socid_extractor) of personal info, links to other profiles, etc.
* Recursive search by new usernames and other ids found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Requests retries

See full description of Maigret features [in the documentation](https://maigret.readthedocs.io/en/latest/features.html).

## Installation

‼️ Maigret is available online via [official Telegram bot](https://t.me/osint_maigret_bot).

Maigret can be installed using pip, Docker, or simply can be launched from the cloned repo.

Standalone EXE-binaries for Windows are located in [Releases section](https://github.com/soxoj/maigret/releases) of GitHub repository.

Also, you can run Maigret using cloud shells and Jupyter notebooks (see buttons below). 

[![Open in Cloud Shell](https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md)
<a href="https://repl.it/github/soxoj/maigret"><img src="https://replit.com/badge/github/soxoj/maigret" alt="Run on Replit" height="50"></a>

<a href="https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" height="45"></a>
<a href="https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD"><img src="https://mybinder.org/badge_logo.svg" alt="Open In Binder" height="45"></a>

### Package installing

**NOTE**: Python 3.10 or higher and pip is required, **Python 3.11 is recommended.**

```bash
# install from pypi
pip3 install maigret

# usage
maigret username
```

### Cloning a repository

```bash
# or clone and install manually
git clone https://github.com/soxoj/maigret && cd maigret

# build and install
pip3 install .

# usage
maigret username
```

### Docker

```bash
# official image
docker pull soxoj/maigret

# usage
docker run -v /mydir:/app/reports soxoj/maigret:latest username --html

# manual build
docker build -t maigret .
```

## Usage examples

```bash
# make HTML, PDF, and Xmind8 reports
maigret user --html
maigret user --pdf
maigret user --xmind #Output not compatible with xmind 2022+

# search on sites marked with tags photo & dating
maigret user --tags photo,dating

# search on sites marked with tag us
maigret user --tags us

# search for three usernames on all available sites
maigret user1 user2 user3 -a
```

Use `maigret --help` to get full options description. Also options [are documented](https://maigret.readthedocs.io/en/latest/command-line-options.html).

## Contributing

Contribution guidelines can be found [here](CONTRIBUTING)

Maigret has open-source code, so you may contribute your own sites by adding them to `data.json` file, or bring changes to it's code!
If you want to contribute, don't forget to activate statistics update hook, command for it would look like this: `git config --local core.hooksPath .githooks/`
You should make your git commits from your maigret git repo folder, or else the hook wouldn't find the statistics update script.

## Demo with page parsing and recursive username search


[PDF report](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.pdf), [HTML report](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![animation of recursive search](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.svg)

![HTML report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_html_screenshot.png)

![XMind 8 report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_xmind_screenshot.png)

[Full console output](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.md)

### SOWEL classification

This tool uses the following OSINT techniques:
- [SOTL-2.2. Search For Accounts On Other Platforms](https://sowel.soxoj.com/other-platform-accounts)
- [SOTL-6.1. Check Logins Reuse To Find Another Account](https://sowel.soxoj.com/logins-reuse)
- [SOTL-6.2. Check Nicknames Reuse To Find Another Account](https://sowel.soxoj.com/nicknames-reuse) 

## License

MIT © [Maigret](https://github.com/soxoj/maigret)<br/>
MIT © [Sherlock Project](https://github.com/sherlock-project/)<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
