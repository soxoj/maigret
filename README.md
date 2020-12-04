# Maigret

<p align="center">
  <img src="static/maigret.png" />
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

## About

Purpose of Maigret - **collect a dossier on a person by username only**, checking for accounts on a huge number of sites.

This is a [sherlock](https://github.com/sherlock-project/) fork with cool features under heavy development.
*Don't forget to regularly update source code from repo*.

Currently supported >1300 sites ([full list](/sites.md)).

## Main features

* Profile pages parsing, [extracting](https://github.com/soxoj/socid_extractor) personal info, links to other profiles, etc.
* Recursive search by new usernames found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Very few false positives

## Installation

**NOTE**: Python 3.7 or higher and pip is required.

**Python 3.8 is recommended.**

```bash
# clone the repo and change directory
$ git clone https://git.rip/soxoj/maigret && cd maigret

# install the requirements
$ python3 -m pip install -r requirements.txt
```

## Using examples

```bash
python3 maigret user

python3 maigret user1 user2 user3
```

With Docker:
```
docker build -t maigret .

docker run maigret user
```

## Demo with page parsing and recursive username search

```bash
python3 maigret alexaimephotographycars
```

![animation of recursive search](./static/recursive_search.svg)

[Full output](./static/recursive_search.md)

## License

MIT © [Maigret](https://github.com/soxoj/maigret)<br/>
MIT © [Sherlock Project](https://github.com/sherlock-project/)<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
