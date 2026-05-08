.. _settings:

Settings
==============

.. warning::
   The settings system is under development and may be subject to change.

Options are also configurable through settings files. See
`settings JSON file <https://github.com/soxoj/maigret/blob/main/maigret/resources/settings.json>`_
for the list of currently supported options.

After start Maigret tries to load configuration from the following sources in exactly the same order:

.. code-block:: console

  # relative path, based on installed package path
  resources/settings.json

  # absolute path, configuration file in home directory
  ~/.maigret/settings.json

  # relative path, based on current working directory
  settings.json

Missing any of these files is not an error.
If the next settings file contains already known option,
this option will be rewrited. So it is possible to make
custom configuration for different users and directories.

.. _database-auto-update:

Database auto-update
--------------------

Maigret ships with a bundled site database, but it gets outdated between releases. To keep the database current, Maigret automatically checks for updates on startup.

**How it works:**

1. On startup, Maigret checks if more than 24 hours have passed since the last update check.
2. If so, it fetches a lightweight metadata file (~200 bytes) from GitHub to see if a newer database is available.
3. If a newer, compatible database exists, Maigret downloads it to ``~/.maigret/data.json`` and uses it instead of the bundled copy.
4. If the download fails or the new database is incompatible with your Maigret version, the bundled database is used as a fallback.

The downloaded database has **higher priority** than the bundled one — it replaces, not overlays.

**Status messages** are printed only when an action occurs:

.. code-block:: text

   [*] DB auto-update: checking for updates...
   [+] DB auto-update: database updated successfully (3180 sites)
   [*] DB auto-update: database is up to date (3157 sites)
   [!] DB auto-update: latest database requires maigret >= 0.6.0, you have 0.5.0

**Forcing an update:**

Use the ``--force-update`` flag to check for updates immediately, ignoring the check interval:

.. code-block:: console

   maigret username --force-update

The update happens at startup, then the search continues normally with the freshly downloaded database.

**Disabling auto-update:**

Use the ``--no-autoupdate`` flag to skip the update check entirely:

.. code-block:: console

   maigret username --no-autoupdate

Or set it permanently in ``~/.maigret/settings.json``:

.. code-block:: json

   {
       "no_autoupdate": true
   }

This is recommended for **Docker containers**, **CI pipelines**, and **air-gapped environments**.

**Configuration options** (in ``settings.json``):

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Setting
     - Default
     - Description
   * - ``no_autoupdate``
     - ``false``
     - Disable auto-update entirely
   * - ``autoupdate_check_interval_hours``
     - ``24``
     - How often to check for updates (in hours)
   * - ``db_update_meta_url``
     - GitHub raw URL
     - URL of the metadata file (for custom mirrors)

**Using a custom database** with ``--db`` always skips auto-update — you are explicitly choosing your data source.

Cloudflare webgate
------------------

.. warning::

   **Experimental.** The ``cloudflare_bypass`` block is under active
   development; field names, defaults, and the trigger-protection routing
   rules may change without backwards-compatibility guarantees.

The ``cloudflare_bypass`` block in ``settings.json`` configures the optional
bypass described in :ref:`cloudflare-bypass`. Default value:

.. code-block:: json

   {
       "cloudflare_bypass": {
           "enabled": false,
           "session_prefix": "maigret",
           "trigger_protection": ["cf_js_challenge", "cf_firewall", "webgate"],
           "modules": [
               {
                   "name": "flaresolverr",
                   "method": "json_api",
                   "url": "http://localhost:8191/v1",
                   "max_timeout_ms": 60000
               },
               {
                   "name": "chrome_webgate",
                   "method": "url_rewrite",
                   "url": "http://localhost:8000/html?url={url}&retries=1"
               }
           ]
       }
   }

**Fields.**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Description
   * - ``enabled``
     - When ``true``, the bypass is active for every run; when ``false``
       (the default), it activates only on ``--cloudflare-bypass``.
   * - ``trigger_protection``
     - List of ``site.protection`` values that route a check through the
       webgate. Sites whose protection is empty or doesn't intersect this
       list use the default (aiohttp / curl_cffi) checker.
   * - ``session_prefix``
     - Prefix for the FlareSolverr ``session`` field. Maigret appends the
       process PID so concurrent runs don't collide. Reusing a session
       caches cf_clearance between checks of the same domain.
   * - ``modules``
     - Ordered list of backend modules. The first reachable module
       handles the check; later ones serve as a fallback chain.

**Module methods.**

* ``json_api`` — FlareSolverr-compatible POST endpoint at ``url``.
  Preserves real upstream HTTP status, headers and final URL.
  Optional ``max_timeout_ms`` (default ``60000``) is the per-request
  budget the solver is allowed to spend on the JS challenge.
* ``url_rewrite`` — legacy CloudflareBypassForScraping endpoint. The
  ``url`` must contain a ``{url}`` placeholder; the original probe URL
  is URL-encoded and substituted in. Returns rendered HTML only —
  ``checkType: status_code`` and ``response_url`` checks misfire under
  this method (treated as a synthetic HTTP 200 on success).

**Optional ``proxy`` field (``json_api`` only).**

A module may carry a ``proxy`` entry that the solver routes the upstream
request through. Useful when a site enforces ``ip_reputation`` rules
that block the solver host. Two forms are accepted:

.. code-block:: json

   { "proxy": "socks5://localhost:1080" }

.. code-block:: json

   { "proxy": { "url": "http://gw.example:3128",
                "username": "u",
                "password": "p" } }

Only ``url``/``username``/``password`` are forwarded; other keys are
dropped. Cloudflare ``Error 1015 / 1020`` responses indicate the IP is
rate-limited or banned — switch the proxy rather than retrying.
.. _ai-analysis-settings:

AI analysis
-----------

The ``--ai`` flag (see :ref:`ai-analysis`) talks to an OpenAI-compatible
chat completion API. Three settings control how that request is made:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Setting
     - Default
     - Description
   * - ``openai_api_key``
     - ``""`` (empty)
     - API key. If empty, Maigret falls back to the ``OPENAI_API_KEY``
       environment variable.
   * - ``openai_model``
     - ``gpt-4o``
     - Default model name. Overridable per-run with ``--ai-model``.
   * - ``openai_api_base_url``
     - ``https://api.openai.com/v1``
     - Base URL of the chat completion API. Point this at any
       OpenAI-compatible service (Azure OpenAI, OpenRouter, a local
       server, …) to use it instead of OpenAI directly.

Example ``~/.maigret/settings.json`` snippet using a non-OpenAI
endpoint:

.. code-block:: json

   {
       "openai_api_key": "sk-...",
       "openai_model": "gpt-4o-mini",
       "openai_api_base_url": "https://openrouter.ai/api/v1"
   }

The key resolution order is ``settings.openai_api_key`` → ``OPENAI_API_KEY``
environment variable; the first non-empty value wins.

.. note::

   ``--ai`` sends the full internal Markdown report (which contains the
   gathered profile data) to the configured endpoint. Only use providers
   and accounts you trust with that data.
