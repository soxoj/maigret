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

Network and proxy options
~~~~~~~~~~~~~~~~~~~~~~~~~

``--proxy PROXY_URL`` / ``-p PROXY_URL`` - Route **every** check through
the given HTTP or SOCKS proxy. Example: ``socks5://127.0.0.1:1080``,
``http://user:pass@proxy.example:3128``. This is the flag to use for
routing the whole run through Tor (``--proxy socks5://127.0.0.1:9050``),
a residential proxy, or any corporate gateway. No default.

``--tor-proxy TOR_PROXY_URL`` - Gateway used **only** for ``.onion``
sites in the database **(default: socks5://127.0.0.1:9050)**. Clearweb
sites are unaffected — for them Maigret uses your direct connection or
``--proxy`` if you set one. Without this flag, ``.onion`` sites are
silently skipped.

``--i2p-proxy I2P_PROXY_URL`` - Gateway used **only** for ``.i2p``
sites in the database **(default: http://127.0.0.1:4444)**. Same
"only matching protocol" rule as ``--tor-proxy``.

Maigret does not start the Tor or I2P daemon for you — launch it first.
For a full walkthrough (Tor Browser vs system ``tor`` port numbers,
Tails OS recipe, timeout/retry tuning), see :doc:`tor-and-proxies`.

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
JSON file. See :ref:`custom-database` below.

``--no-autoupdate`` - Disable the automatic database update check that
runs at startup. The currently cached (or bundled) database is used
as-is.

``--force-update`` - Force a database update check at startup, ignoring
the usual check interval. Implies ``--no-autoupdate`` for the rest of
the run after the explicit update finishes.

``--retries RETRIES`` - Count of attempts to restart temporarily failed
requests.

``--cloudflare-bypass`` *(experimental)* - Route checks for sites tagged
``protection: ["cf_js_challenge"]`` / ``["cf_firewall"]`` / ``["webgate"]``
through a local Chrome-based solver (FlareSolverr by default). The bypass
is opt-in — without this flag (or
``settings.cloudflare_bypass.enabled = true``) those sites are checked
the usual way, which Cloudflare almost always blocks: you get an UNKNOWN
status with a JS-challenge / firewall error rather than a real result.
Configure the backend in ``settings.cloudflare_bypass.modules``.
See :ref:`cloudflare-bypass`. **Experimental** — the flag, schema and
routing rules may change without backwards-compatibility guarantees.

.. _custom-database:

Using a custom sites database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``--db`` flag accepts three forms:

1. **HTTP(S) URL** — fetched as-is, e.g.
   ``--db https://example.com/my_db.json``.
2. **Local file path** — absolute (``--db /tmp/private.json``) or
   relative to the current working directory
   (``--db LLM/maigret_private_db.json``).
3. **Module-relative path** — kept for backwards compatibility, resolved
   against the installed ``maigret/`` package directory (e.g. the
   default ``resources/data.json``).

Resolution order for local paths: the path is first tried as given
(absolute or cwd-relative); if that file does not exist, Maigret falls
back to the legacy module-relative resolution. If neither location
contains the file, Maigret exits with an error rather than silently
loading the bundled database.

When ``--db`` points to a custom file, automatic database updates are
skipped — the file is used exactly as provided.

On every run Maigret prints the database it actually loaded, for
example::

    [+] Using sites database: /path/to/maigret_private_db.json (6 sites)

If loading the requested database fails for any other reason (corrupt
JSON, missing required keys, …), Maigret prints a warning, falls back
to the bundled database, and reports the fallback explicitly::

    [-] Falling back to bundled database: /…/maigret/resources/data.json
    [+] Using sites database: /…/maigret/resources/data.json (3154 sites)

A typical invocation against a private database, with auto-update
disabled and all sites scanned, looks like::

    python3 -m maigret username \
        --db LLM/maigret_private_db.json \
        --no-autoupdate -a

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

``--ai`` - Run an AI-powered analysis of the search results using an
OpenAI-compatible chat completion API. The internal Markdown report is
sent to the model, which returns a short investigation summary that is
streamed to the terminal. See :ref:`ai-analysis` below.

``--ai-model`` - Model name to use with ``--ai``. Defaults to
``openai_model`` from settings (``gpt-4o`` out of the box).

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

``--self-check`` - Do self-checking for sites and database. Each site is
tested by looking up its known-claimed and known-unclaimed usernames and
verifying that the results match expectations. Individual site failures
(network errors, unexpected exceptions, etc.) are caught and logged
without stopping the overall process, so the check always runs to
completion. After checking, Maigret reports a summary of issues found.
If any sites were disabled (see ``--auto-disable``), Maigret asks if you
want to save updates; answering y/Y will rewrite the local database.

``--auto-disable`` - Used with ``--self-check``: automatically disable
sites that fail checks (incorrect detection of claimed/unclaimed
usernames, connection errors, or unexpected exceptions). Without this
flag, ``--self-check`` only **reports** issues without modifying the
database.

``--diagnose`` - Used with ``--self-check``: print detailed diagnosis
information for each failing site, including the check type, the list
of issues found, and recommendations (e.g. suggesting a different
``checkType``).

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

For a built-in alternative that calls the model for you and prints the
summary directly, see :ref:`ai-analysis` below.

.. _ai-analysis:

AI analysis (built-in)
----------------------

The ``--ai`` flag turns the search results into a short investigation
summary by sending the internal Markdown report to an OpenAI-compatible
chat completion API and streaming the model's reply to the terminal.

.. code-block:: console

   export OPENAI_API_KEY=sk-...
   maigret username --ai

   # use a smaller / cheaper model
   maigret username --ai --ai-model gpt-4o-mini

While ``--ai`` is active, per-site progress lines and the short text
report at the end are suppressed so the streamed summary is the main
output. The Markdown report itself is built in memory and is **not**
written to disk by ``--ai`` alone — combine with ``--md`` if you also
want the file on disk.

The summary follows a fixed format with sections for the most likely
real name, location, occupation, interests, languages, main website,
username variants, number of platforms, active years, a confidence
rating, and a short list of follow-up leads. The model is instructed
to rely only on what is supported by the report and to avoid mixing
clearly unrelated profiles into the main identity.

**Configuration.** The API key is resolved from
``settings.openai_api_key`` first, then from the ``OPENAI_API_KEY``
environment variable. The endpoint defaults to
``https://api.openai.com/v1`` and can be redirected to any
OpenAI-compatible service (Azure OpenAI, OpenRouter, a local server,
…) by setting ``openai_api_base_url`` in ``settings.json``. See
:ref:`settings` for the full list of options.

.. note::

   ``--ai`` makes a network request to the configured chat completion
   endpoint and sends the full Markdown report (which contains the
   gathered profile data). Use it only with providers and accounts
   you trust with that data.

