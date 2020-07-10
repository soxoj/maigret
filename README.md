## WARNING

This is a sherlock fork under heavy development.

## Installation

**NOTE**: Python 3.6 or higher is required.

```bash
# clone the repo
$ git clone https://github.com/sherlock-project/sherlock.git

# change the working directory to sherlock
$ cd sherlock

# install python3 and python3-pip if they are not installed

# install the requirements
$ python3 -m pip install -r requirements.txt
```

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/sherlock-project/sherlock&tutorial=README.md)

## Usage

```bash
$ python3 sherlock --help
usage: sherlock [-h] [--version] [--verbose] [--rank]
                [--folderoutput FOLDEROUTPUT] [--output OUTPUT] [--tor]
                [--unique-tor] [--csv] [--site SITE_NAME] [--proxy PROXY_URL]
                [--json JSON_FILE] [--timeout TIMEOUT] [--print-found]
                [--no-color] [--browse]
                USERNAMES [USERNAMES ...]

Sherlock: Find Usernames Across Social Networks (Version 0.12.2)

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
python3 sherlock user123
```

To search for more than one user:
```
python3 sherlock user1 user2 user3
```

Accounts found will be stored in an individual text file with the corresponding username (e.g ```user123.txt```).

## Anaconda (Windows) Notes

If you are using Anaconda in Windows, using 'python3' might not work. Use 'python' instead.

## Docker Notes

If docker is installed you can build an image and run this as a container.

```
docker build -t mysherlock-image .
```

Once the image is built, sherlock can be invoked by running the following:

```
docker run --rm -t mysherlock-image user123
```

The optional ```--rm``` flag removes the container filesystem on completion to prevent cruft build-up. See: https://docs.docker.com/engine/reference/run/#clean-up---rm

The optional ```-t``` flag allocates a pseudo-TTY which allows colored output. See: https://docs.docker.com/engine/reference/run/#foreground

Use the following command to access the saved results:

```
docker run --rm -t -v "$PWD/results:/opt/sherlock/results" mysherlock-image -o /opt/sherlock/results/text.txt user123
```

The ```-v "$PWD/results:/opt/sherlock/results"``` option tells docker to create (or use) the folder `results` in the
present working directory and to mount it at `/opt/sherlock/results` on the docker container.
The `-o /opt/sherlock/results/text.txt` option tells `sherlock` to output the result.

Or you can use "Docker Hub" to run `sherlock`:
```
docker run theyahya/sherlock user123
```

### Using `docker-compose`

You can use the `docker-compose.yml` file from the repository and use this command:

```
docker-compose run sherlock -o /opt/sherlock/results/text.txt user123
```

## Adding New Sites

Please look at the Wiki entry on
[adding new sites](https://github.com/TheYahya/sherlock/wiki/Adding-Sites-To-Sherlock)
to understand the issues.

**NOTE**: Sherlock is not accepting adult sites in the standard list.

## Tests

Thank you for contributing to Sherlock!

Before creating a pull request with new development, please run the tests
to ensure that everything is working great.  It would also be a good idea to run the tests
before starting development to distinguish problems between your
environment and the Sherlock software.

The following is an example of the command line to run all the tests for
Sherlock.  This invocation hides the progress text that Sherlock normally
outputs, and instead shows the verbose output of the tests.

```
$ cd sherlock
$ python3 -m unittest tests.all --verbose
```

Note that we do currently have 100% test coverage.  Unfortunately, some of
the sites that Sherlock checks are not always reliable, so it is common
to get response problems.  Any problems in connection will show up as
warnings in the tests instead of true errors.

If some sites are failing due to connection problems (site is down, in maintenance, etc)
you can exclude them from tests by creating a `tests/.excluded_sites` file with a
list of sites to ignore (one site name per line).

## License

MIT © Maigret<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
