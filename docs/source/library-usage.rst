.. _library-usage:

Library usage
=============

Maigret's CLI is a thin wrapper around an async Python API. You can embed Maigret in your own tools, pipelines, and OSINT workflows — no need to shell out.

This page covers the common patterns. For the full argument list of the underlying function, see ``maigret.checking.maigret`` in the source.

Installation
------------

.. code-block:: bash

   pip install maigret

Minimal example
---------------

A working end-to-end search against the top 500 sites:

.. code-block:: python

   import asyncio
   import logging

   from maigret import search as maigret_search
   from maigret.sites import MaigretDatabase

   # Load the bundled site database
   db = MaigretDatabase().load_from_path(
       "maigret/resources/data.json"
   )

   # Pick which sites to scan (same filtering the CLI uses)
   sites = db.ranked_sites_dict(top=500)

   results = asyncio.run(
       maigret_search(
           username="soxoj",
           site_dict=sites,
           logger=logging.getLogger("maigret"),
           timeout=30,
           is_parsing_enabled=True,
       )
   )

   for site_name, result in results.items():
       if result["status"].is_found():
           print(site_name, result["url_user"])

Key points:

- ``maigret_search`` is an ``async`` function — wrap it with ``asyncio.run(...)`` or ``await`` it from inside your own event loop.
- ``is_parsing_enabled=True`` turns on ``socid_extractor`` so ``result["ids_data"]`` is populated with profile fields (bio, linked accounts, uids, etc.).
- Each entry in the returned dict has a ``"status"`` object with ``is_found()``, plus ``url_user``, ``http_status``, ``rank``, ``ids_data``, and more.

Filtering sites
---------------

``ranked_sites_dict`` accepts the same filters as the CLI:

.. code-block:: python

   # All sites tagged as coding, top 200 by rank
   sites = db.ranked_sites_dict(top=200, tags=["coding"])

   # Exclude NSFW and dating sites
   sites = db.ranked_sites_dict(excluded_tags=["nsfw", "dating"])

   # Only specific sites by name
   sites = db.ranked_sites_dict(names=["GitHub", "Reddit", "VK"])

   # Include disabled sites (useful for maintenance / self-check)
   sites = db.ranked_sites_dict(disabled=True)

Running inside an existing event loop
-------------------------------------

If your application already runs an asyncio loop (FastAPI, aiohttp server, a Discord bot, etc.), ``await`` ``maigret_search`` directly instead of calling ``asyncio.run``:

.. code-block:: python

   async def check_username(username: str) -> dict:
       results = await maigret_search(
           username=username,
           site_dict=sites,
           logger=logger,
           timeout=30,
       )
       return {
           name: r["url_user"]
           for name, r in results.items()
           if r["status"].is_found()
       }

Routing through a proxy
-----------------------

The same proxy / Tor / I2P flags the CLI exposes are plain keyword arguments:

.. code-block:: python

   results = await maigret_search(
       username="soxoj",
       site_dict=sites,
       logger=logger,
       proxy="socks5://127.0.0.1:1080",
       tor_proxy="socks5://127.0.0.1:9050",   # used for .onion sites
       i2p_proxy="http://127.0.0.1:4444",     # used for .i2p sites
       timeout=30,
   )

Full function signature
-----------------------

.. code-block:: python

   async def maigret(
       username: str,
       site_dict: Dict[str, MaigretSite],
       logger,
       query_notify=None,
       proxy=None,
       tor_proxy=None,
       i2p_proxy=None,
       timeout=30,
       is_parsing_enabled=False,
       id_type="username",
       debug=False,
       forced=False,
       max_connections=100,
       no_progressbar=False,
       cookies=None,
       retries=0,
       check_domains=False,
   ) -> QueryResultWrapper

See :doc:`command-line-options` for a description of each option — the semantics match the CLI flags one-to-one.
