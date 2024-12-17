# Maigret

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

<b>👉👉👉 [Online Telegram bot](https://t.me/osint_maigret_bot)</b>

## About

**Maigret** collects a dossier on a person **by username only**, checking for accounts on a huge number of sites and gathering all the available information from web pages. No API keys are required. Maigret is an easy-to-use and powerful fork of [Sherlock](https://github.com/sherlock-project/sherlock).

Currently supports more than 3000 sites ([full list](https://github.com/soxoj/maigret/blob/main/sites.md)), search is launched against 500 popular sites in descending order of popularity by default. Also supported checking Tor sites, I2P sites, and domains (via DNS resolving).

## Powered By Maigret

These are professional tools for social media content analysis and OSINT investigations that use Maigret (banners are clickable).

<a href="https://github.com/SocialLinks-IO/sociallinks-api"><img height="60" alt="Social Links API" src="https://github.com/user-attachments/assets/789747b2-d7a0-4d4e-8868-ffc4427df660"></a>
<a href="https://sociallinks.io/products/sl-crimewall"><img height="60" alt="Social Links Crimewall" src="https://github.com/user-attachments/assets/0b18f06c-2f38-477b-b946-1be1a632a9d1"></a>
<a href="https://usersearch.ai/"><img height="60" alt="UserSearch" src="https://github.com/user-attachments/assets/66daa213-cf7d-40cf-9267-42f97cf77580"></a>

## Main features

* Profile page parsing, [extraction](https://github.com/soxoj/socid_extractor) of personal info, links to other profiles, etc.
* Recursive search by new usernames and other IDs found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Requests retries

See the full description of Maigret features [in the documentation](https://maigret.readthedocs.io/en/latest/features.html).

## Installation

‼️ Maigret is available online via [official Telegram bot](https://t.me/osint_maigret_bot). Consider using it if you don't want to install anything.

### Windows

Standalone EXE-binaries for Windows are located in [Releases section](https://github.com/soxoj/maigret/releases) of GitHub repository.

Video guide on how to run it: https://youtu.be/qIgwTZOmMmM.

### Installation in Cloud Shells

You can launch Maigret using cloud shells and Jupyter notebooks. Press one of the buttons below and follow the instructions to launch it in your browser.

[![Open in Cloud Shell](https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md)
<a href="https://repl.it/github/soxoj/maigret"><img src="https://replit.com/badge/github/soxoj/maigret" alt="Run on Replit" height="50"></a>

<a href="https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" height="45"></a>
<a href="https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD"><img src="https://mybinder.org/badge_logo.svg" alt="Open In Binder" height="45"></a>

### Local installation

Maigret can be installed using pip, Docker, or simply can be launched from the cloned repo.


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

### Web interface

You can run Maigret with a web interface, where you can view the graph with results and download reports of all formats on a single page.

<details>
<summary>Web Interface Screenshots</summary>

![Web interface: how to start](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot_start.png)

![Web interface: results](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot.png)

</details>

Instructions:

1. Run Maigret with the ``--web`` flag and specify the port number.

```console
maigret --web 5000
```
2. Open http://127.0.0.1:5000 in your browser and enter one or more usernames to make a search.

3. Wait a bit for the search to complete and view the graph with results, the table with all accounts found, and download reports of all formats.

## Contributing

Maigret has open-source code, so you may contribute your own sites by adding them to `data.json` file, or bring changes to it's code!

For more information about development and contribution, please read the [development documentation](https://maigret.readthedocs.io/en/latest/development.html).

## Demo with page parsing and recursive username search

### Video (asciinema)

<a href="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ">
  <img src="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ.svg" alt="asciicast" width="600">
</a>

### Reports

[PDF report](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.pdf), [HTML report](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![HTML report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_html_screenshot.png)

![XMind 8 report screenshot](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_xmind_screenshot.png)

[Full console output](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.md)

## Disclaimer

**This tool is intended for educational and lawful purposes only.** The developers do not endorse or encourage any illegal activities or misuse of this tool. Regulations regarding the collection and use of personal data vary by country and region, including but not limited to GDPR in the EU, CCPA in the USA, and similar laws worldwide.

It is your sole responsibility to ensure that your use of this tool complies with all applicable laws and regulations in your jurisdiction. Any illegal use of this tool is strictly prohibited, and you are fully accountable for your actions.

The authors and developers of this tool bear no responsibility for any misuse or unlawful activities conducted by its users.

## Feedback

If you have any questions, suggestions, or feedback, please feel free to [open an issue](https://github.com/soxoj/maigret/issues), create a [GitHub discussion](https://github.com/soxoj/maigret/discussions), or contact the author directly via [Telegram](https://t.me/soxoj).

## SOWEL classification

This tool uses the following OSINT techniques:
- [SOTL-2.2. Search For Accounts On Other Platforms](https://sowel.soxoj.com/other-platform-accounts)
- [SOTL-6.1. Check Logins Reuse To Find Another Account](https://sowel.soxoj.com/logins-reuse)
- [SOTL-6.2. Check Nicknames Reuse To Find Another Account](https://sowel.soxoj.com/nicknames-reuse) 

## License

MIT © [Maigret](https://github.com/soxoj/maigret)<br/>
MIT © [Sherlock Project](https://github.com/sherlock-project/)<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
