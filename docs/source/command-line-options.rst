.. _command-line-options:

Command line options
====================

Usernames
---------

``maigret username1 username2 ...``

You can specify several usernames separated by space. Usernames are
**not** mandatory as there are other operations modes (see below).

Parsing of account pages and online documents
---------------------------------------------

``maigret --parse URL``

Maigret will try to extract information about the document/account owner
(including username and other ids) and will make a search by the
extracted username and ids. See examples in the :ref:`extracting-information-from-pages` section.

Main options
------------

Options are also configurable through settings files, see
:doc:`settings section <settings>`.

``--tags`` - Filter sites for searching by tags: sites categories and
two-letter country codes (**not a language!**). E.g. photo, dating, sport; jp, us, global.
Multiple tags can be associated with one site. **Warning**: tags markup is
not stable now. Read more :doc:`in the separate section <tags>`.

``--exclude-tags`` - Exclude sites with specific tags from the search
(blacklist). E.g. ``--exclude-tags porn,dating`` will skip all sites
tagged with ``porn`` or ``dating``. Can be combined with ``--tags`` to
include certain categories while excluding others. Read more
:doc:`in the separate section <tags>`.

``-n``, ``--max-connections`` - Allowed number of concurrent connections
**(default: 100)**.

``-a``, ``--all-sites`` - Use all sites for scan **(default: top 500)**.

``--top-sites`` - Count of sites for scan ranked by Majestic Million
**(default: top 500)**.

**Mirrors:** After the top *N* sites by Majestic Million rank are chosen (respecting
``--tags``, ``--use-disabled-sites``, etc.), Maigret may add extra sites
whose database field ``source`` names a **parent platform** that itself falls
in the Majestic Million top *N* when ranking **including disabled** sites. For example,
if ``Twitter`` ranks in the first 500 by Majestic Million, a mirror such as ``memory.lol``
(with ``source: Twitter``) is included even though it has no rank and would
otherwise be cut off. The same applies to Instagram-related mirrors (e.g.
Picuki) when ``Instagram`` is in that parent top *N* by rank—even if the
official ``Instagram`` entry is disabled and not scanned by default, its
mirrors can still be pulled in. The final list is the ranked top *N* plus
these mirrors (no fixed upper bound on mirror count).

``--timeout`` - Time (in seconds) to wait for responses from sites
**(default: 30)**. A longer timeout will be more likely to get results
from slow sites. On the other hand, this may cause a long delay to
gather all results. The choice of the right timeout should be carried
out taking into account the bandwidth of the Internet connection.

``--cookies-jar-file`` - File with custom cookies in Netscape format
(aka cookies.txt). You can install an extension to your browser to
download own cookies (`Chrome <https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid>`_, `Firefox <https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/>`_).

``--no-recursion`` - Disable parsing pages for other usernames and
recursive search by them.

``--use-disabled-sites`` - Use disabled sites to search (may cause many
false positives).

``--id-type`` - Specify identifier(s) type (default: username).
Supported types: gaia_id, vk_id, yandex_public_id, ok_id, wikimapia_uid.
Currently, you must add ``-a`` flag to run a scan on sites with custom
id types, sites will be filtered automatically.

``--ignore-ids`` - Do not make search by the specified username or other
ids. Useful for repeated scanning with found known irrelevant usernames.

``--db`` - Load Maigret database from a JSON file or an online, valid,
JSON file.

``--retries RETRIES`` - Count of attempts to restart temporarily failed
requests.

Reports
-------

``-P``, ``--pdf`` - Generate a PDF report (general report on all
usernames).

``-H``, ``--html`` - Generate an HTML report file (general report on all
usernames).

``-X``, ``--xmind`` - Generate an XMind 8 mindmap (one report per
username).

``-C``, ``--csv`` - Generate a CSV report (one report per username).

``-T``, ``--txt`` - Generate a TXT report (one report per username).

``-J``, ``--json`` - Generate a JSON report of specific type: simple,
ndjson (one report per username). E.g. ``--json ndjson``

``-M``, ``--md`` - Generate a Markdown report (general report on all
usernames). See :ref:`markdown-report` below.

``-fo``, ``--folderoutput`` - Results will be saved to this folder,
``results`` by default. Will be created if doesn’t exist.

Output options
--------------

``-v``, ``--verbose`` - Display extra information and metrics.
*(loglevel=WARNING)*

``-vv``, ``--info`` - Display service information. *(loglevel=INFO)*

``-vvv``, ``--debug``, ``-d`` - Display debugging information and site
responses. *(loglevel=DEBUG)*

``--print-not-found`` - Print sites where the username was not found.

``--print-errors`` - Print errors messages: connection, captcha, site
country ban, etc.

Other operations modes
----------------------

``--version`` - Display version information and dependencies.

``--self-check`` - Do self-checking for sites and database and disable
non-working ones **for current search session** by default. It’s useful
for testing new internet connection (it depends on provider/hosting on
which sites there will be censorship stub or captcha display). After
checking Maigret asks if you want to save updates, answering y/Y will
rewrite the local database.

``--submit URL`` - Do an automatic analysis of the given account URL or
site main page URL to determine the site engine and methods to check
account presence. After checking Maigret asks if you want to add the
site, answering y/Y will rewrite the local database.

.. _markdown-report:

Markdown report (LLM-friendly)
------------------------------

The ``--md`` / ``-M`` flag generates a Markdown report designed for both human reading and analysis by AI assistants (ChatGPT, Claude, etc.).

.. code-block:: console

   maigret username --md

The report includes:

- **Summary** with aggregated personal data (all fullnames, locations, bios found across accounts), country tags, website tags, first/last seen timestamps.
- **Per-account sections** with profile URL, site tags, and all extracted fields (username, bio, follower count, linked accounts, etc.).
- **Possible false positives** disclaimer explaining that accounts may belong to different people.
- **Ethical use** notice about applicable data protection laws.

**Using with AI tools:**

The Markdown format is optimized for LLM context windows. You can feed the report directly to an AI assistant for follow-up analysis:

.. code-block:: console

   # Generate the report
   maigret johndoe --md

   # Feed it to an AI tool
   cat reports/report_johndoe.md | llm "Analyze this OSINT report and summarize key findings"

The structured Markdown with per-site sections makes it easy for AI tools to extract relationships, cross-reference identities, and identify patterns across accounts.

