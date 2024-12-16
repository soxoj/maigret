.. _features:

Features
========

This is the list of Maigret features.

.. _web-interface:

Web Interface
-------------

You can run Maigret with a web interface, where you can view the graph with results and download reports of all formats on a single page.


.. image:: https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot_start.png
   :alt: Web interface: how to start


.. image:: https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot.png
   :alt: Web interface: results


Instructions:

1. Run Maigret with the ``--web`` flag and specify the port number.

.. code-block:: console

  maigret --web 5000

2. Open http://127.0.0.1:5000 in your browser and enter one or more usernames to make a search.

3. Wait a bit for the search to complete and view the graph with results, the table with all accounts found, and download reports of all formats.

Personal info gathering
-----------------------

Maigret does the `parsing of accounts webpages and extraction <https://github.com/soxoj/socid-extractor>`_ of personal info, links to other profiles, etc.
Extracted info displayed as an additional result in CLI output and as tables in HTML and PDF reports.
Also, Maigret use found ids and usernames from links to start a recursive search.

Enabled by default, can be disabled with ``--no extracting``.

.. code-block:: text

    $ python3 -m maigret soxoj --timeout 5
        [-] Starting a search on top 500 sites from the Maigret database...
        [!] You can run search by full list of sites with flag `-a`
        [*] Checking username soxoj on:
        ...
        [+] GitHub: https://github.com/soxoj
                ├─uid: 31013580
                ├─image: https://avatars.githubusercontent.com/u/31013580?v=4
                ├─created_at: 2017-08-14T17:03:07Z
                ├─location: Amsterdam, Netherlands
                ├─follower_count: 1304
                ├─following_count: 54
                ├─fullname: Soxoj
                ├─public_gists_count: 3
                ├─public_repos_count: 88
                ├─twitter_username: sox0j
                ├─bio: Head of OSINT Center of Excellence in @SocialLinks-IO
                ├─is_company: Social Links
                └─blog_url: soxoj.com
        ...

Recursive search
----------------

Maigret has the ability to scan account pages for :ref:`common identifiers <supported-identifier-types>` and usernames found in links.
When people include links to their other social media accounts, Maigret can automatically detect and initiate new searches for those profiles.
Any information discovered through this process will be shown in both the command-line interface output and generated reports.

Enabled by default, can be disabled with ``--no-recursion``.


.. code-block:: text

    $ python3 -m maigret soxoj --timeout 5
        [-] Starting a search on top 500 sites from the Maigret database...
        [!] You can run search by full list of sites with flag `-a`
        [*] Checking username soxoj on:
        ...
        [+] GitHub: https://github.com/soxoj
                ├─uid: 31013580
                ├─image: https://avatars.githubusercontent.com/u/31013580?v=4
                ├─created_at: 2017-08-14T17:03:07Z
                ├─location: Amsterdam, Netherlands
                ├─follower_count: 1304
                ├─following_count: 54
                ├─fullname: Soxoj
                ├─public_gists_count: 3
                ├─public_repos_count: 88
                ├─twitter_username: sox0j     <===== another username found here
                ├─bio: Head of OSINT Center of Excellence in @SocialLinks-IO
                ├─is_company: Social Links
                └─blog_url: soxoj.com
        ...
        Searching |████████████████████████████████████████| 500/500 [100%] in 9.1s (54.85/s)
        [-] You can see detailed site check errors with a flag `--print-errors`
        [*] Checking username sox0j on:
        [+] Telegram: https://t.me/sox0j
            ├─fullname: @Sox0j
            ...

Username permutations
---------------------

Maigret can generate permutations of usernames. Just pass a few usernames in the CLI and use ``--permute`` flag.
Thanks to `@balestek <https://github.com/balestek>`_ for the idea and implementation.

.. code-block:: text

    $ python3 -m maigret --permute hope dream --timeout 5
    [-] 12 permutations from hope dream to check...
        ├─ hopedream
        ├─ _hopedream 
        ├─ hopedream_
        ├─ hope_dream
        ├─ hope-dream
        ├─ hope.dream
        ├─ dreamhope
        ├─ _dreamhope
        ├─ dreamhope_
        ├─ dream_hope
        ├─ dream-hope
        └─ dream.hope
    [-] Starting a search on top 500 sites from the Maigret database...
    [!] You can run search by full list of sites with flag `-a`
    [*] Checking username hopedream on:
    ...

Reports 
-------

Maigret currently supports HTML, PDF, TXT, XMind 8 mindmap, and JSON reports.

HTML/PDF reports contain:

- profile photo
- all the gathered personal info
- additional information about supposed personal data (full name, gender, location), resulting from statistics of all found accounts

Also, there is a short text report in the CLI output after the end of a searching phase.

.. warning::
   XMind 8 mindmaps are incompatible with XMind 2022!

Tags
----

The Maigret sites database very big (and will be bigger), and it is maybe an overhead to run a search for all the sites.
Also, it is often hard to understand, what sites more interesting for us in the case of a certain person.

Tags markup allows selecting a subset of sites by interests (photo, messaging, finance, etc.) or by country. Tags of found accounts grouped and displayed in the reports.

See full description :doc:`in the Tags Wiki page <tags>`.

Censorship and captcha detection
--------------------------------

Maigret can detect common errors such as censorship stub pages, CloudFlare captcha pages, and others. 
If you get more them 3% errors of a certain type in a session, you've got a warning message in the CLI output with recommendations to improve performance and avoid problems.

Retries
-------

Maigret will do retries of the requests with temporary errors got (connection failures, proxy errors, etc.).

One attempt by default, can be changed with option ``--retries N``.

Archives and mirrors checking
-----------------------------

The Maigret database contains not only the original websites, but also mirrors, archives, and aggregators. For example:

- `Picuki <https://www.picuki.com/>`_, Instagram mirror
- (no longer available) `Reddit BigData search <https://camas.github.io/reddit-search/>`_
- (no longer available) `Twitter shadowban <https://shadowban.eu/>`_ checker

It allows getting additional info about the person and checking the existence of the account even if the main site is unavailable (bot protection, captcha, etc.)

Activation
----------
The activation mechanism helps make requests to sites requiring additional authentication like cookies, JWT tokens, or custom headers.

It works by implementing a custom function that:

1. Makes a specialized HTTP request to a specific website endpoint
2. Processes the response
3. Updates the headers/cookies for that site in the local Maigret database

Since activation only triggers after encountering specific errors, a retry (or another Maigret run) is needed to obtain a valid response with the updated authentication.

The activation mechanism is enabled by default, and cannot be disabled at the moment.

See for more details in Development section :ref:`activation-mechanism`.

.. _extracting-information-from-pages:

Extraction of information from account pages
--------------------------------------------

Maigret can parse URLs and content of web pages by URLs to extract info about account owner and other meta information.

You must specify the URL with the option ``--parse``, it's can be a link to an account or an online document. List of supported sites `see here <https://github.com/soxoj/socid-extractor#sites>`_.

After the end of the parsing phase, Maigret will start the search phase by :doc:`supported identifiers <supported-identifier-types>` found (usernames, ids, etc.).

.. code-block:: console

  $ maigret --parse https://docs.google.com/spreadsheets/d/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw/edit\#gid\=0

  Scanning webpage by URL https://docs.google.com/spreadsheets/d/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw/edit#gid=0...
  ┣╸org_name: Gooten
  ┗╸mime_type: application/vnd.google-apps.ritz
  Scanning webpage by URL https://clients6.google.com/drive/v2beta/files/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw?fields=alternateLink%2CcopyRequiresWriterPermission%2CcreatedDate%2Cdescription%2CdriveId%2CfileSize%2CiconLink%2Cid%2Clabels(starred%2C%20trashed)%2ClastViewedByMeDate%2CmodifiedDate%2Cshared%2CteamDriveId%2CuserPermission(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)%2Cpermissions(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)%2Cparents(id)%2Ccapabilities(canMoveItemWithinDrive%2CcanMoveItemOutOfDrive%2CcanMoveItemOutOfTeamDrive%2CcanAddChildren%2CcanEdit%2CcanDownload%2CcanComment%2CcanMoveChildrenWithinDrive%2CcanRename%2CcanRemoveChildren%2CcanMoveItemIntoTeamDrive)%2Ckind&supportsTeamDrives=true&enforceSingleParent=true&key=AIzaSyC1eQ1xj69IdTMeii5r7brs3R90eck-m7k...
  ┣╸created_at: 2016-02-16T18:51:52.021Z
  ┣╸updated_at: 2019-10-23T17:15:47.157Z
  ┣╸gaia_id: 15696155517366416778
  ┣╸fullname: Nadia Burgess
  ┣╸email: nadia@gooten.com
  ┣╸image: https://lh3.googleusercontent.com/a-/AOh14GheZe1CyNa3NeJInWAl70qkip4oJ7qLsD8vDy6X=s64
  ┗╸email_username: nadia

.. code-block:: console

  $ maigret.py --parse https://steamcommunity.com/profiles/76561199113454789
  Scanning webpage by URL https://steamcommunity.com/profiles/76561199113454789...
  ┣╸steam_id: 76561199113454789
  ┣╸nickname: Pok
  ┗╸username: Machine42


Simple API
----------

Maigret can be easily integrated with the use of Python package `maigret <https://pypi.org/project/maigret/>`_.

Example: the official `Telegram bot <https://github.com/soxoj/maigret-tg-bot>`_
