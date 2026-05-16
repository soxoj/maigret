.. _tor-and-proxies:

Tor, I2P, and proxies
=====================

Maigret can route checks through an HTTP/SOCKS proxy, the Tor network, or I2P. Three CLI flags cover three distinct goals — knowing which one you need is the most common stumbling block.

``--proxy`` vs ``--tor-proxy`` (and ``--i2p-proxy``)
----------------------------------------------------

The most-asked question (see `issue #544 <https://github.com/soxoj/maigret/issues/544>`_):

- **You want every check to go through Tor** (e.g. you're on Tails OS, or behind a country-level block, or your IP is rate-limited). → Use ``--proxy``, pointing at your Tor SOCKS port:

  .. code-block:: console

     maigret <username> --proxy socks5://127.0.0.1:9050

- **You want to reach ``.onion`` sites in the Maigret database**, while the rest of the run still uses your normal connection. → Use ``--tor-proxy``:

  .. code-block:: console

     maigret <username> --tor-proxy socks5://127.0.0.1:9050

  ``--tor-proxy`` is **only** consulted for sites whose ``url`` is a ``.onion`` host. For every other site Maigret uses your direct connection (or ``--proxy`` if set). Without ``--tor-proxy``, ``.onion`` sites are silently skipped.

The same split applies to ``--i2p-proxy``: it is consulted only for ``.i2p`` hosts, never for clearweb sites.

Defaults: ``--tor-proxy`` defaults to ``socks5://127.0.0.1:9050`` and ``--i2p-proxy`` to ``http://127.0.0.1:4444``. ``--proxy`` has no default. Maigret does **not** launch ``tor`` or an I2P router for you — start the daemon first.

Tor Browser vs system ``tor``: port numbers
-------------------------------------------

The SOCKS port differs by Tor installation:

- **System ``tor`` daemon** (``apt install tor``, ``brew install tor``, Tails) listens on ``9050``.
- **Tor Browser bundle** ships its own ``tor`` listening on ``9150``.

If a connection refuses, try the other port:

.. code-block:: console

   # system tor
   maigret <username> --proxy socks5://127.0.0.1:9050

   # Tor Browser running in the background
   maigret <username> --proxy socks5://127.0.0.1:9150

A note on results over Tor
--------------------------

Most public WAFs (Cloudflare, DDoS-Guard, AWS WAF, Akamai) block Tor exit nodes by default — usually more aggressively than they block datacenter IPs. A Tor run typically produces **more UNKNOWNs and fewer CLAIMEDs** than the same run from a residential connection. This is not a bug in Maigret; it is the cost of anonymity.

Recommended flags for a Tor run:

.. code-block:: console

   maigret <username> --proxy socks5://127.0.0.1:9050 --timeout 60 --retries 2

- ``--timeout 60`` — Tor circuits add 1–3 seconds per request; the default 30 s causes spurious timeouts.
- ``--retries 2`` — retries cover transient circuit failures, which are common on Tor.
- Optional ``-n 20`` — lowering concurrency (default 100) reduces the chance of exits rate-limiting you.

If you mainly need to bypass WAFs (rather than to remain anonymous), a residential proxy will usually outperform Tor by a wide margin. See the **"Lots of sites fail / timeout / return 403"** section in `TROUBLESHOOTING.md <https://github.com/soxoj/maigret/blob/main/TROUBLESHOOTING.md>`_.

Running on Tails OS
-------------------

Tails forces every outbound connection through Tor at the network layer. Maigret needs no special configuration to comply — pointing ``--proxy`` at the Tails Tor daemon is enough:

.. code-block:: console

   maigret <username> --proxy socks5://127.0.0.1:9050 --timeout 60

Things that are **not** needed:

- ``torsocks maigret …`` and ``torify maigret …`` — these wrap libc socket calls, but Maigret's HTTP client (``aiohttp`` / ``curl_cffi``) bypasses libc for network I/O, so the wrapper has no effect. Use ``--proxy`` instead.
- ``--tor-proxy`` — on Tails, *everything* must go via Tor (the OS enforces this), so the niche "only .onion via Tor" mode that ``--tor-proxy`` provides does not apply.

Installation over Tor on Tails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``pip`` itself does not know about Tor; on Tails you need ``torsocks`` to wrap it:

.. code-block:: console

   torsocks pip install --user maigret

After install, the binary lands in ``~/.local/bin/maigret``. If ``maigret: command not found``, either add ``~/.local/bin`` to ``PATH`` or invoke it as ``python3 -m maigret <username>``.

Persisting Maigret across Tails sessions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tails wipes ``~/.local/`` on reboot unless you configure the Persistent Storage to keep it. This is Tails configuration, not Maigret configuration — see the official Tails docs:

- `Persistent Storage on Tails <https://tails.boum.org/doc/persistent_storage/>`_
- `Configuring Persistent Storage features <https://tails.boum.org/doc/persistent_storage/configure/>`_

A step-by-step recipe contributed by a user (persisting ``~/.local/lib/python3.9`` and ``~/.local/bin`` and patching ``.bashrc``) is in `issue #544 <https://github.com/soxoj/maigret/issues/544#issuecomment-1356469171>`_. Treat it as a starting point: the Python version and Tails internals change between Tails releases.

Reports on Tails — where to save them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default ``reports/`` directory lives next to the working directory and is wiped with the amnesiac session. To save reports somewhere persistent, either pass ``-fo``:

.. code-block:: console

   maigret <username> --html -fo "/home/amnesia/Persistent/maigret-reports"

or set ``"reports_path"`` in your ``settings.json`` to a persistent path. See :doc:`settings`.

Programmatic equivalents (Python library)
-----------------------------------------

The same options are available through the Python API. See :doc:`library-usage` — the relevant keyword arguments are ``proxy=``, ``tor_proxy=`` and ``i2p_proxy=``, accepting the same URL formats as the CLI flags.

See also
--------

- :doc:`command-line-options` — full reference for the three flags.
- `TROUBLESHOOTING.md <https://github.com/soxoj/maigret/blob/main/TROUBLESHOOTING.md>`_ — quick recipes for ``.onion`` / I2P sites and for WAF-induced 403s.
- :doc:`library-usage` — proxy options for embedded use.
