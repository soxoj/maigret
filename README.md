# Maigret

<div align="center">
  <div>
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
  </div>
  <div>
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300" alt="Maigret logo"/>
  </div>
</div>

**Maigret** collects a dossier on a person **by username only**, checking for accounts on a huge number of sites and gathering all the available information from web pages. No API keys required.

<a id="one-minute"></a>
## In one minute

Ensure you have Python 3.10 or higher.

```bash
pip install maigret
maigret YOUR_USERNAME
```

No install? Try the [Telegram bot](https://t.me/maigret_search_bot) or a [Cloud Shell](#cloud-shells). See also: [Quick start](https://maigret.readthedocs.io/en/latest/quick-start.html). Want a web UI? See [how to launch it](#web-interface).

[Telegram bot](https://t.me/maigret_search_bot) · [Commercial use & API](#commercial-use)

## About

3 000+ sites supported ([full list](https://github.com/soxoj/maigret/blob/main/sites.md)), top 500 checked by default. Tor, I2P, and plain domains (DNS) are also supported.

## Powered By Maigret

Professional OSINT and social-media analysis tools built on Maigret:

<a href="https://github.com/SocialLinks-IO/sociallinks-api"><img height="60" alt="Social Links API" src="https://github.com/user-attachments/assets/789747b2-d7a0-4d4e-8868-ffc4427df660"></a>
<a href="https://sociallinks.io/products/sl-crimewall"><img height="60" alt="Social Links Crimewall" src="https://github.com/user-attachments/assets/0b18f06c-2f38-477b-b946-1be1a632a9d1"></a>
<a href="https://usersearch.ai/"><img height="60" alt="UserSearch" src="https://github.com/user-attachments/assets/66daa213-cf7d-40cf-9267-42f97cf77580"></a>

## Main features

* Profile page parsing, [extraction](https://github.com/soxoj/socid_extractor) of personal info, links to other profiles, etc.
* Recursive search by new usernames and other IDs found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Requests retries
* [Auto-updated site database](https://maigret.readthedocs.io/en/latest/settings.html#database-auto-update) from GitHub on every run (once per 24 h); fallback to the bundled DB if offline

Full list: [features](https://maigret.readthedocs.io/en/latest/features.html).

## Installation

Already ran the [In one minute](#one-minute) steps? You're set. Below are alternative methods.

Don't want to install anything? Use the [Telegram bot](https://t.me/maigret_search_bot).

### Windows

Download a standalone EXE from [Releases](https://github.com/soxoj/maigret/releases). Video guide: https://youtu.be/qIgwTZOmMmM.

<a id="cloud-shells"></a>
### Cloud Shells

Run Maigret in the browser via cloud shells or Jupyter notebooks:

[![Open in Cloud Shell](https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md)
<a href="https://repl.it/github/soxoj/maigret"><img src="https://replit.com/badge/github/soxoj/maigret" alt="Run on Replit" height="50"></a>

<a href="https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" height="45"></a>
<a href="https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD"><img src="https://mybinder.org/badge_logo.svg" alt="Open In Binder" height="45"></a>

### Local installation (pip)

```bash
# install from pypi
pip3 install maigret

# usage
maigret username
```

### From source

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

### Troubleshooting

Build errors? See the [troubleshooting guide](https://maigret.readthedocs.io/en/latest/installation.html#troubleshooting).

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

Run `maigret --help` for all options. Docs: [CLI options](https://maigret.readthedocs.io/en/latest/command-line-options.html), [more examples](https://maigret.readthedocs.io/en/latest/usage-examples.html).

<a id="web-interface"></a>
### Web interface

Maigret has a built-in web UI with a results graph and downloadable reports.

<details>
<summary>Web Interface Screenshots</summary>

![Web interface: how to start](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot_start.png)

![Web interface: results](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot.png)

</details>

```console
maigret --web 5000
```

Open http://127.0.0.1:5000, enter a username, and view results.

## Contributing

Add sites to `data.json` or submit code changes. See [development docs](https://maigret.readthedocs.io/en/latest/development.html).

## Demo

### Video (asciinema)

<a href="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ">
  <img src="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ.svg" alt="asciicast" width="600">
</a>

### Reports

[PDF report](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.pdf), [HTML report](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![HTML report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_html_screenshot.png)

![XMind 8 report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_xmind_screenshot.png)

[Full console output](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.md)

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

## Disclaimer

**For educational and lawful purposes only.** You are responsible for complying with all applicable laws (GDPR, CCPA, etc.) in your jurisdiction. The authors bear no responsibility for misuse.

## Feedback

[Open an issue](https://github.com/soxoj/maigret/issues) · [GitHub Discussions](https://github.com/soxoj/maigret/discussions) · [Telegram](https://t.me/soxoj)

## Commercial Use

Need a **daily-updated site database** or a **username-check API**? Reach out:

📧 [maigret@soxoj.com](mailto:maigret@soxoj.com)

- Site database — 5 000+ sites, updated daily
- Username check API — integrate Maigret into your product

## SOWEL classification

OSINT techniques used:
- [SOTL-2.2. Search For Accounts On Other Platforms](https://sowel.soxoj.com/other-platform-accounts)
- [SOTL-6.1. Check Logins Reuse To Find Another Account](https://sowel.soxoj.com/logins-reuse)
- [SOTL-6.2. Check Nicknames Reuse To Find Another Account](https://sowel.soxoj.com/nicknames-reuse) 

## License

MIT © [Maigret](https://github.com/soxoj/maigret)
