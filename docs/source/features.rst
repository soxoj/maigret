.. _features:

Features
========

This is the list of Maigret features.

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
--------------------

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

- `Reddit BigData search <https://camas.github.io/reddit-search/>`_
- `Picuki <https://www.picuki.com/>`_, Instagram mirror
- `Twitter shadowban <https://shadowban.eu/>`_ checker

It allows getting additional info about the person and checking the existence of the account even if the main site is unavailable (bot protection, captcha, etc.)

Simple API
----------

Maigret can be easily integrated with the use of Python package `maigret <https://pypi.org/project/maigret/>`_.

Example: the official `Telegram bot <https://github.com/soxoj/maigret-tg-bot>`_
