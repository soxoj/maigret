.. _faq:

FAQ
===

Short answers to the questions users most often type into the docs
search. For deeper coverage each section links to the relevant page.

Can I search by email address?
------------------------------

**No.** Maigret only takes a username (or one of the
:doc:`supported identifier types <supported-identifier-types>`) as
input — searching by an email or mail address is out of scope.
Looking up a mail address requires different techniques (probing
password-reset flows, registration endpoints) and is the job of a
separate class of tool.

Recommended open-source tools for email lookup:

- `mailcat <https://github.com/sharsil/mailcat>`_
- `holehe <https://github.com/megadose/holehe>`_
- `user-scanner <https://github.com/kaifcodec/user-scanner>`_

Online services:

- `Noimosiny <https://noimosiny.com>`_
- `OSINT Industries <https://osint.industries>`_
- `Epieos <https://epieos.com>`_

Note: if Maigret has already found an account for a username, it often
extracts the linked email from the profile page automatically — see
:ref:`extracting-information-from-pages`.

Can I configure a proxy / SOCKS / Tor / I2P?
--------------------------------------------

**Yes.** Three flags cover three distinct goals:

- ``--proxy URL`` — route **every** check through the given HTTP or
  SOCKS proxy (also the right flag for routing the whole run through Tor
  with ``socks5://127.0.0.1:9050``, a residential proxy, or a corporate
  gateway).
- ``--tor-proxy URL`` — used **only** for ``.onion`` sites in the
  database. Clearweb sites still go via your direct connection (or
  ``--proxy`` if set).
- ``--i2p-proxy URL`` — same idea, only for ``.i2p`` hosts.

The most common confusion is ``--proxy`` vs ``--tor-proxy``: ``--proxy``
is "everything through this gateway", ``--tor-proxy`` is "only onion
sites through Tor".

Full walkthrough (Tor Browser vs system ``tor`` port numbers, Tails OS,
timeout / retry tuning): :doc:`tor-and-proxies`.

If your goal is actually "bypass WAF blocks / fix 403 errors", see the
*Sites fail / timeout / 403* section below — a residential proxy almost
always outperforms Tor or a VPN for that.

Can I use a VPN with Maigret?
-----------------------------

**Yes**, but ``--proxy`` is usually a better choice. A VPN works
transparently at the OS level — Maigret needs no special configuration
to use one. However:

- ``--proxy`` is per-process: it does not affect other apps and does not
  leak when toggled.
- ``--proxy`` makes the egress IP visible in logs, which is useful when
  diagnosing why a batch of sites returned ``UNKNOWN``.
- ``--proxy`` accepts a different value per run, so you can rotate
  between residential and datacenter exits without touching system
  network settings.

If a lot of sites are returning 403, the cause is almost certainly that
the VPN exit IP is on a WAF blocklist (Cloudflare, DDoS-Guard, Akamai
all blanket-block common VPN ranges). A residential proxy via
``--proxy`` is the usual fix — see the
`"Lots of sites fail / timeout / return 403" section
<https://github.com/soxoj/maigret/blob/main/TROUBLESHOOTING.md#lots-of-sites-fail--timeout--return-403>`_
in TROUBLESHOOTING.md.

Does Maigret check domains via DNS?
-----------------------------------

**Yes, experimentally.** With ``--with-domains`` Maigret resolves a
small set of ``{username}.<tld>`` patterns through DNS (A-records) in
parallel with the normal HTTP checks. The current set is
``.ddns.net``, ``.com``, ``.pro``, ``.me``, ``.biz``, ``.email``,
``.guru`` — 7 entries in the database with ``protocol: dns``.

.. code-block:: console

   maigret <username> --with-domains

The flag is marked **experimental**: DNS-only checks can flag parking
domains and catch-all wildcards as if the username were registered, so
treat hits as a lead rather than confirmation.

If your task is wider DNS reconnaissance — subdomain enumeration, WHOIS
history, typo-squatting — Maigret is the wrong tool. Established
alternatives:

- `dnstwist <https://github.com/elceef/dnstwist>`_ — typo-squatting and
  look-alike domains.
- `amass <https://github.com/owasp-amass/amass>`_ /
  `subfinder <https://github.com/projectdiscovery/subfinder>`_ —
  subdomain enumeration.
- `theHarvester <https://github.com/laramies/theHarvester>`_ —
  email / host / subdomain harvesting by domain.

Is there a Maigret Telegram bot?
--------------------------------

**Yes.** A community-maintained bot lets you run Maigret without
installing anything locally:

- Working instance: `sites.google.com/view/maigret-bot-link
  <https://sites.google.com/view/maigret-bot-link>`_ (redirect — the
  hosted bot may move between providers).
- Source code: `github.com/soxoj/maigret-tg-bot
  <https://github.com/soxoj/maigret-tg-bot>`_.

On the question of *searching Telegram itself*: Maigret checks whether a
``t.me/<user>`` page exists as part of the normal run, but it does not
parse channels, posts, members, or message contents. For Telegram
content OSINT you need a dedicated tool.

Where is the web interface?
---------------------------

.. code-block:: console

   maigret --web 5000

Then open http://127.0.0.1:5000. Screenshots and a full walkthrough are
in :ref:`web-interface`.

Sites fail / timeout / return 403 — connection failures
-------------------------------------------------------

This is the most common report and is almost always caused by anti-bot
protection (Cloudflare, DDoS-Guard, Akamai) or a slow link, not by a
bug in Maigret. Quick tweaks, in order:

1. ``--timeout 60`` — the default 30 s is tight for slow networks and
   for Tor.
2. ``--retries 2`` — covers transient failures.
3. ``-n 20`` — lower concurrency reduces WAF rate-limiting.
4. ``--proxy http://user:pass@residential-proxy:port`` — datacenter IPs
   (AWS, GCP, DigitalOcean) and most VPN ranges are blanket-blocked;
   residential / mobile exits usually fix the bulk of 403s.

The full troubleshooting matrix (per-error recipes for 403, timeout,
SSL, captcha, ``UNKNOWN`` floods) lives in
`TROUBLESHOOTING.md
<https://github.com/soxoj/maigret/blob/main/TROUBLESHOOTING.md>`_.

How do I generate a PDF report?
-------------------------------

PDF support is an optional extra because it pulls heavy graphics
dependencies:

.. code-block:: console

   pip install 'maigret[pdf]'
   maigret <username> --pdf

On Linux / macOS you also need system libraries (Pango, Cairo,
GDK-PixBuf). Per-OS install steps are in the
*Optional: PDF reports* section of :doc:`installation`.

For other report formats (``--html``, ``--md``, ``--json``, ``--csv``,
``--txt``, ``--xmind``), see :doc:`command-line-options`.
