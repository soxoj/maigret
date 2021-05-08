# Maigret

<p align="center">
  <p align="center">
    <a href="https://pypi.org/project/maigret/">
      <img alt="PyPI" src="https://img.shields.io/pypi/v/maigret?style=flat-square">
    </a>
    <a href="https://pypi.org/project/maigret/">
      <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/maigret?style=flat-square">
    </a>
    <a href="https://gitter.im/maigret-osint/community">
      <img alt="Chat - Gitter" src="./static/chat_gitter.svg" />
    </a>
    <a href="https://twitter.com/intent/follow?screen_name=sox0j">
      <img src="https://img.shields.io/twitter/follow/sox0j?label=Follow%20sox0j&style=social&color=blue" alt="Follow @sox0j" />
    </a>
  </p>
  <p align="center">
    <img src="./static/maigret.png" height="200"/>
  </p>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

## About

**Maigret** collect a dossier on a person **by username only**, checking for accounts on a huge number of sites and gathering all the available information from web pages. Maigret is an easy-to-use and powerful fork of [Sherlock](https://github.com/sherlock-project/sherlock).

Currently supported more than 2000 sites ([full list](./sites.md)), search is launched against 500 popular sites in descending order of popularity by default.

## Main features

* Profile pages parsing, [extraction](https://github.com/soxoj/socid_extractor) of personal info, links to other profiles, etc.
* Recursive search by new usernames and other ids found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Requests retries

See full description of Maigret features [in the Wiki](https://github.com/soxoj/maigret/wiki/Features).

## Installation

Maigret can be installed using pip, Docker, or simply can be launched from the cloned repo.
Also you can run Maigret using cloud shells (see buttons below). 

[![Open in Cloud Shell](https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md) [![Run on Repl.it](https://user-images.githubusercontent.com/27065646/92304596-bf719b00-ef7f-11ea-987f-2c1f3c323088.png)](https://repl.it/github/soxoj/maigret)
<a href="https://colab.research.google.com/gist//soxoj/879b51bc3b2f8b695abb054090645000/maigret.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" height="40"></a>

### Package installing

**NOTE**: Python 3.6 or higher and pip is required, **Python 3.8 is recommended.**

```bash
# install from pypi
pip3 install maigret

# or clone and install manually
git clone https://github.com/soxoj/maigret && cd maigret
pip3 install .

# usage
maigret username
```

### Cloning a repository

```bash
git clone https://github.com/soxoj/maigret && cd maigret
pip3 install -r requirements.txt

# usage
./maigret.py username
```

### Docker

```bash
# official image
docker pull soxoj/maigret

# usage
docker run soxoj/maigret:latest username

# manual build
docker build -t maigret .
```

## Usage examples

```bash
# make HTML and PDF reports
maigret user --html --pdf

# search on sites marked with tags photo & dating
maigret user --tags photo,dating

# search for three usernames on all available sites
maigret user1 user2 user3 -a
```

Use `maigret --help` to get full options description. Also options are documented in [the Maigret Wiki](https://github.com/soxoj/maigret/wiki/Command-line-options).


## Demo with page parsing and recursive username search

[PDF report](./static/report_alexaimephotographycars.pdf), [HTML report](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![animation of recursive search](./static/recursive_search.svg)

![HTML report screenshot](./static/report_alexaimephotography_html_screenshot.png)

![XMind report screenshot](./static/report_alexaimephotography_xmind_screenshot.png)


[Full console output](./static/recursive_search.md)

## License

MIT © [Maigret](https://github.com/soxoj/maigret)<br/>
MIT © [Sherlock Project](https://github.com/sherlock-project/)<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
