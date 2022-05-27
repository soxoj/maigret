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

Recursive search
----------------

Maigret can extract some :ref:`common ids <supported-identifier-types>` and usernames from links on the account page (often people placed links to their other accounts) and immediately start new searches. All the gathered information will be displayed in CLI output and reports.

Enabled by default, can be disabled with ``--no-recursion``.

Reports
-------

Maigret currently supports HTML, PDF, TXT, XMind 8 mindmap, and JSON reports.

HTML/PDF reports contain:

- profile photo
- all the gathered personal info
- additional information about supposed personal data (full name, gender, location), resulting from statistics of all found accounts

Also, there is a short text report in the CLI output after the end of a searching phase.

**Warning**: XMind 8 mindmaps are incompatible with XMind 2022!

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
