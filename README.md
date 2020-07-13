## WARNING

This is a [sherlock](https://github.com/sherlock-project/) fork under heavy development.

## Installation

**NOTE**: Python 3.6 or higher and pip is required.

```bash
# clone the repo and change directory
$ git clone https://github.com/soxoj/maigret && cd maigret

# install the requirements
$ python3 -m pip install -r requirements.txt
```

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md)

## Usage

```bash
$ python3 maigret --help
usage: maigret [-h] [--version] [--verbose] [--rank]
                [--folderoutput FOLDEROUTPUT] [--output OUTPUT] [--tor]
                [--unique-tor] [--csv] [--site SITE_NAME] [--proxy PROXY_URL]
                [--json JSON_FILE] [--timeout TIMEOUT] [--print-found]
                [--no-color] [--browse]
                USERNAMES [USERNAMES ...]

Maigret (Sherlock fork): Find Usernames Across Social Networks (Version 0.12.2)

positional arguments:
  USERNAMES             One or more usernames to check with social networks.

optional arguments:
  -h, --help            show this help message and exit
  --version             Display version information and dependencies.
  --verbose, -v, -d, --debug
                        Display extra debugging information and metrics.
  --rank, -r            Present websites ordered by their Alexa.com global
                        rank in popularity.
  --folderoutput FOLDEROUTPUT, -fo FOLDEROUTPUT
                        If using multiple usernames, the output of the results
                        will be saved to this folder.
  --output OUTPUT, -o OUTPUT
                        If using single username, the output of the result
                        will be saved to this file.
  --tor, -t             Make requests over Tor; increases runtime; requires
                        Tor to be installed and in system path.
  --unique-tor, -u      Make requests over Tor with new Tor circuit after each
                        request; increases runtime; requires Tor to be
                        installed and in system path.
  --csv                 Create Comma-Separated Values (CSV) File.
  --site SITE_NAME      Limit analysis to just the listed sites. Add multiple
                        options to specify more than one site.
  --proxy PROXY_URL, -p PROXY_URL
                        Make requests over a proxy. e.g.
                        socks5://127.0.0.1:1080
  --json JSON_FILE, -j JSON_FILE
                        Load data from a JSON file or an online, valid, JSON
                        file.
  --timeout TIMEOUT     Time (in seconds) to wait for response to requests.
                        Default timeout of 60.0s.A longer timeout will be more
                        likely to get results from slow sites.On the other
                        hand, this may cause a long delay to gather all
                        results.
  --print-found         Do not output sites where the username was not found.
  --no-color            Don\'t color terminal output
  --browse, -b          Browse to all results on default browser.
  --ids, -i             Search for other usernames in website pages and make
                        recursive search by them.
```

To search for only one user:
```
python3 maigret user123
```

To search for more than one user:
```
python3 maigret user1 user2 user3
```

Accounts found will be stored in an individual text file with the corresponding username (e.g ```user123.txt```).

## License

MIT © Maigret<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
