.. _development:

Development
==============

Frequently Asked Questions
--------------------------

1. Where to find the list of supported sites?

The human-readable list of supported sites is available in the `sites.md <https://github.com/soxoj/maigret/blob/main/sites.md>`_ file in the repository.
It's been generated automatically from the main JSON file with the list of supported sites.

The machine-readable JSON file with the list of supported sites is available in the
`data.json <https://github.com/soxoj/maigret/blob/main/maigret/resources/data.json>`_ file in the directory `resources`.

2. Which methods to check the account presence are supported?

The supported methods (``checkType`` values in ``data.json``) are:

- ``message`` - the most reliable method, checks if any string from ``presenceStrs`` is present and none of the strings from ``absenceStrs`` are present in the HTML response
- ``status_code`` - checks that status code of the response is 2XX
- ``response_url`` - check if there is not redirect and the response is 2XX

.. note::
   Maigret natively treats specific anti-bot HTTP status codes (like LinkedIn's ``HTTP 999``) as a standard "Not Found/Available" signal instead of throwing an infrastructure Server Error, gracefully preventing false positives.

See the details of check mechanisms in the `checking.py <https://github.com/soxoj/maigret/blob/main/maigret/checking.py#L339>`_ file.

.. note::
   Maigret now uses the **Majestic Million** dataset for site popularity sorting instead of the discontinued Alexa Rank API. For backward compatibility with existing configurations and parsers, the ranking field in `data.json` and internal site models remains named ``alexaRank`` and ``alexa_rank``.

**Mirrors and ``--top-sites``:** When you limit scans with ``--top-sites N``, Maigret also includes *mirror* sites (entries whose ``source`` field points at a parent platform such as Twitter or Instagram) if that parent would appear in the Majestic Million top *N* when disabled sites are considered for ranking. See the **Mirrors** paragraph under ``--top-sites`` in :doc:`command-line-options`.

Testing
-------

It is recommended use Python 3.10 for testing.

Install test requirements:

.. code-block:: console

  poetry install --with dev


Use the following commands to check Maigret:

.. code-block:: console

  # run linter and typing checks
  # order of checks:
  # - critical syntax errors or undefined names
  # - flake checks
  # - mypy checks
  make lint

  # run black formatter
  make format

  # run testing with coverage html report
  # current test coverage is 58%
  make test

  # open html report
  open htmlcov/index.html

  # get flamechart of imports to estimate startup time
  make speed


Site naming conventions
-----------------------------------------------

Site names are the keys in ``data.json`` and appear in user-facing reports. Follow these rules:

- **Title Case** by default: ``Product Hunt``, ``Hacker News``.
- **Lowercase** only if the brand itself is written that way: ``kofi``, ``note``, ``hi5``.
- **No domain suffix** (``calendly.com`` → ``Calendly``), unless the domain is part of the recognized brand name: ``last.fm``, ``VC.ru``, ``Archive.org``.
- **No full UPPERCASE** unless the brand is an acronym: ``VK``, ``CNET``, ``ICQ``, ``IFTTT``.
- **No** ``www.`` **or** ``https://`` **prefix** in the name.
- **Spaces** are allowed when the brand uses them: ``Star Citizen``, ``Google Maps``.
- **{username} templates** in names are acceptable: ``{username}.tilda.ws``.

When in doubt, check how the service refers to itself on its homepage.

How to fix false-positives
-----------------------------------------------

If you want to work with sites database, don't forget to activate statistics update git hook, command for it would look like this: ``git config --local core.hooksPath .githooks/``.

You should make your git commits from your maigret git repo folder, or else the hook wouldn't find the statistics update script.

1. Determine the problematic site.

If you already know which site has a false-positive and want to fix it specifically, go to the next step.

Otherwise, simply run a search with a random username (e.g. `laiuhi3h4gi3u4hgt`) and check the results.
Alternatively, you can use the `community Telegram bot <https://sites.google.com/view/maigret-bot-link>`_.

2. Open the account link in your browser and check:

- If the site is completely gone, remove it from the list
- If the site still works but looks different, update in data.json how we check it
- If the site requires login to view profiles, disable checking it

3. Find the site in the `data.json <https://github.com/soxoj/maigret/blob/main/maigret/resources/data.json>`_ file.

If the ``checkType`` method is not ``message`` and you are going to fix check, update it:
- put ``message`` in ``checkType``
- put in ``absenceStrs`` a keyword that is present in the HTML response for an non-existing account
- put in ``presenceStrs`` a keyword that is present in the HTML response for an existing account

If you have trouble determining the right keywords, you can use automatic detection by passing the account URL with the ``--submit`` option:

.. code-block:: console

  maigret --submit https://my.mail.ru/bk/alex

To disable checking, set ``disabled`` to ``true`` or simply run:

.. code-block:: console

  maigret --self-check --site My.Mail.ru@bk.ru

To debug the check method using the response HTML, you can run:

.. code-block:: console

  maigret soxoj --site My.Mail.ru@bk.ru -d 2> response.txt

There are few options for sites data.json helpful in various cases:

- ``engine`` - a predefined check for the sites of certain type (e.g. forums), see the ``engines`` section in the JSON file
- ``headers`` - a dictionary of additional headers to be sent to the site
- ``requestHeadOnly`` - set to ``true`` if it's enough to make a HEAD request to the site
- ``regexCheck`` - a regex to check if the username is valid, in case of frequent false-positives
- ``requestMethod`` - set the HTTP method to use (e.g., ``POST``). By default, Maigret natively defaults to GET or HEAD.
- ``requestPayload`` - a dictionary with the JSON payload to send for POST requests (e.g., ``{"username": "{username}"}``), extremely useful for parsing GraphQL or modern JSON APIs.
- ``protection`` - a list of protection types detected on the site (see below).

``protection`` (site protection tracking)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``protection`` field records what kind of anti-bot protection a site uses. Maigret reads this field and automatically applies the appropriate bypass mechanism where one exists.

Two categories of tag:

- **Load-bearing.** Maigret changes its HTTP client or headers based on the tag. Currently only ``tls_fingerprint`` (switches to ``curl_cffi`` with Chrome-class TLS).
- **Documentation-only.** Maigret does **not** change behavior based on the tag; it records *why* the site is hard so a future solver can target the right set of sites without re-auditing.

Within the documentation-only tags, there is a further split that dictates whether the site is ``disabled: true``:

- ``ip_reputation`` is the **only** doc-tag that **keeps the site enabled**. It means "works for most users, fails from datacenter/cloud IPs." Disabling would silently hide a working site from anyone with a clean IP. The fix is **external** to Maigret (residential IP or ``--proxy``).
- ``cf_js_challenge``, ``cf_firewall``, ``aws_waf_js_challenge``, ``ddos_guard_challenge``, ``custom_bot_protection``, ``js_challenge`` all pair with ``disabled: true``. They mean "does not work for anyone right now"; the tag identifies the provider so that when a bypass ships, every site with that tag can be re-enabled in one pass.

Supported values:

- ``tls_fingerprint`` *(load-bearing; site stays enabled)* — the site fingerprints the TLS handshake (JA3/JA4) and blocks non-browser clients. Maigret automatically uses ``curl_cffi`` with Chrome browser emulation to bypass this. Requires the ``curl_cffi`` package (included as a dependency). Examples: Instagram, NPM, Codepen, Kickstarter, Letterboxd.
- ``ip_reputation`` *(documentation-only; site stays enabled)* — the site blocks requests from datacenter/cloud IPs regardless of headers or TLS. Cannot be bypassed automatically; run Maigret from a regular internet connection (not a datacenter) or use a proxy (``--proxy``). The site is **not** marked ``disabled`` because it continues to work for users on residential IPs. Examples: Reddit, Patreon, Figma, OnlyFans.
- ``cf_js_challenge`` *(documentation-only; pair with ``disabled: true``)* — Cloudflare Managed Challenge / Turnstile JS challenge. Symptom: HTTP 403 with ``cf-mitigated: challenge`` header; body contains ``challenges.cloudflare.com``, ``_cf_chl_opt``, ``window._cf_chl``, or "Just a moment". Not bypassable via ``curl_cffi`` TLS impersonation (verified across Chrome 123/124/131, Safari 17/18, Firefox 133/135, Edge 101 — all return the same 403 challenge page); a real browser executing the challenge JS is required to obtain the clearance cookie. Sites stay ``disabled: true`` until a CF-challenge solver is integrated. Examples: DMOJ, Elakiri, Fanlore, Bdoutdoors, TheStudentRoom, forum.hr.
- ``cf_firewall`` *(documentation-only; pair with ``disabled: true``)* — Cloudflare firewall rule / bot score block (WAF action=block, **not** action=challenge). Symptom: HTTP 403 served by Cloudflare (``server: cloudflare``, ``cf-ray`` header) **without** JS-challenge markers — body typically shows "Access denied", "Attention Required", or just a bare 1015/1016/1020 error page. Unlike ``ip_reputation``, residential IPs are **not** sufficient to bypass — Cloudflare decides based on a composite of bot score, TLS fingerprint, UA, ASN, and custom site-owner rules, so ``curl_cffi`` Chrome impersonation from a residential line still returns 403. Sites stay ``disabled: true`` until a per-site bypass (cookies, real browser, or residential+clean session) is found. Examples: Fark, Fodors, Huntingnet, Hunttalk.
- ``aws_waf_js_challenge`` *(documentation-only; pair with ``disabled: true``)* — the site is protected by AWS WAF with a JavaScript challenge. Symptom: HTTP 202 with empty body and ``x-amzn-waf-action: challenge`` header (a token-granting challenge that requires executing the CAPTCHA/challenge JS bundle). Neither ``curl_cffi`` TLS impersonation nor User-Agent changes bypass this — a real browser or the official AWS WAF challenge-solver SDK is required. Sites stay ``disabled: true`` until a solver is integrated. Example: Dreamwidth.
- ``ddos_guard_challenge`` *(documentation-only; pair with ``disabled: true``)* — DDoS-Guard (ddos-guard.net) anti-bot page. Symptom: HTTP 403 with ``server: ddos-guard`` header; body contains "DDoS-Guard". DDoS-Guard fingerprints different UAs per source IP, so a single User-Agent override does not work across environments; a JS-capable bypass or DDoS-Guard-aware solver is required. Sites stay ``disabled: true`` until a solver is integrated. Example: ForumHouse.
- ``js_challenge`` *(documentation-only; pair with ``disabled: true``)* — **fallback** for JavaScript-challenge systems whose provider cannot be identified (custom in-house challenge pages that are not Cloudflare, AWS WAF, or any other recognized vendor). Prefer a provider-specific tag whenever the provider can be pinned down from response headers or body signatures.
- ``custom_bot_protection`` *(documentation-only; pair with ``disabled: true``)* — **fallback** for non-JS-challenge bot protection served by a custom/in-house system (not Cloudflare, not AWS WAF, not DDoS-Guard). Typical symptom: HTTP 403 from the site's own origin server (``server: nginx``, AWS ELB, etc.) with a branded block page, returned regardless of TLS fingerprint or residential IP. Not generically bypassable; investigate per site (cookies, session, proxy geography). Examples: Hackerearth ("HackerEarth Guardian"), FreelanceJob (nginx-level block).

**Rule: prefer provider-specific protection tags.** When a site is blocked by an identifiable anti-bot vendor, always record the vendor in the tag (``cf_js_challenge``, ``cf_firewall``, ``aws_waf_js_challenge``, ``ddos_guard_challenge``, and future additions such as ``sucuri_challenge``, ``incapsula_challenge``). The generic ``js_challenge`` and ``custom_bot_protection`` tags are reserved for custom/unknown systems. Rationale: bypass solvers are inherently provider-specific (a Cloudflare Turnstile solver does not help with AWS WAF); recording the provider in advance lets us fan out fixes the moment a per-provider solver is added, without re-auditing every disabled site. The same principle applies to other protection categories when the provider is identifiable.

Example:

.. code-block:: json

    "Instagram": {
        "url": "https://www.instagram.com/{username}/",
        "checkType": "message",
        "presenseStrs": ["\"routePath\":\"\\/"],
        "absenceStrs": ["\"routePath\":null"],
        "protection": ["tls_fingerprint"]
    }

``urlProbe`` (optional profile probe URL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default Maigret performs the HTTP request to the same URL as ``url`` (the public profile link pattern).

If you set ``urlProbe`` in ``data.json``, Maigret **fetches** that URL for the presence check (API, GraphQL, JSON endpoint, etc.), while **reports and ``url_user``** still use ``url`` — the human-readable profile page users should open.

Placeholders: ``{username}``, ``{urlMain}``, ``{urlSubpath}`` (same as for ``url``). Example: GitHub uses ``url`` ``https://github.com/{username}`` and ``urlProbe`` ``https://api.github.com/users/{username}``; Picsart uses the web profile ``https://picsart.com/u/{username}`` and probes ``https://api.picsart.com/users/show/{username}.json``.

Implementation: ``make_site_result`` in `checking.py <https://github.com/soxoj/maigret/blob/main/maigret/checking.py>`_.

Site check fixes using LLM
--------------------------

.. note::
   The ``LLM/`` directory at the root of the repository contains detailed instructions for editing site checks (in Markdown format): checklist, full guide to ``checkType`` / ``data.json`` / ``urlProbe``, handling false positives, searching for public JSON APIs, and the proposal log for ``socid_extractor``.

Main files:

- `site-checks-playbook.md <https://github.com/soxoj/maigret/blob/main/LLM/site-checks-playbook.md>`_ — short checklist
- `site-checks-guide.md <https://github.com/soxoj/maigret/blob/main/LLM/site-checks-guide.md>`_ — detailed guide
- `socid_extractor_improvements.log <https://github.com/soxoj/maigret/blob/main/LLM/socid_extractor_improvements.log>`_ — template and entries for identity extractor improvements

These files should be kept up-to-date whenever changes are made to the check logic in the code or in ``data.json``.

.. _activation-mechanism:

Activation mechanism
--------------------

The activation mechanism helps make requests to sites requiring additional authentication like cookies, JWT tokens, or custom headers.

Let's study the Vimeo site check record from the Maigret database:

.. code-block:: json

      "Vimeo": {
          "tags": [
              "us",
              "video"
          ],
          "headers": {
              "Authorization": "jwt eyJ0..."
          },
          "activation": {
              "url": "https://vimeo.com/_rv/viewer",
              "marks": [
                  "Something strange occurred. Please get in touch with the app's creator."
              ],
              "method": "vimeo"
          },
          "urlProbe": "https://api.vimeo.com/users/{username}?fields=name...",
          "checkType": "status_code",
          "alexaRank": 148,
          "urlMain": "https://vimeo.com/",
          "url": "https://vimeo.com/{username}",
          "usernameClaimed": "blue",
          "usernameUnclaimed": "noonewouldeverusethis7"
      },

The activation method is:

.. code-block:: python

    def vimeo(site, logger, cookies={}):
        headers = dict(site.headers)
        if "Authorization" in headers:
            del headers["Authorization"]
        import requests

        r = requests.get(site.activation["url"], headers=headers)
        jwt_token = r.json()["jwt"]
        site.headers["Authorization"] = "jwt " + jwt_token

Here's how the activation process works when a JWT token becomes invalid:

1. The site check makes an HTTP request to ``urlProbe`` with the invalid token
2. The response contains an error message specified in the ``activation``/``marks`` field
3. When this error is detected, the ``vimeo`` activation function is triggered
4. The activation function obtains a new JWT token and updates it in the site check record
5. On the next site check (either through retry or a new Maigret run), the valid token is used and the check succeeds

Examples of activation mechanism implementation are available in `activation.py <https://github.com/soxoj/maigret/blob/main/maigret/activation.py>`_ file.

How to publish new version of Maigret
-------------------------------------

**Collaborats rights are requires, write Soxoj to get them**.

For new version publishing you must create a new branch in repository
with a bumped version number and actual changelog first. After it you
must create a release, and GitHub action automatically create a new 
PyPi package. 

- New branch example: https://github.com/soxoj/maigret/commit/e520418f6a25d7edacde2d73b41a8ae7c80ddf39
- Release example: https://github.com/soxoj/maigret/releases/tag/v0.4.1

1. Make a new branch locally with a new version name. Check the current version number here: https://pypi.org/project/maigret/.
**Increase only patch version (third number)** if there are no breaking changes.

.. code-block:: console

  git checkout -b 0.4.0

2. Update Maigret version in three files manually:

- pyproject.toml
- maigret/__version__.py 
- docs/source/conf.py
- snapcraft.yaml

3. Create a new empty text section in the beginning of the file `CHANGELOG.md` with a current date:

.. code-block:: console

  ## [0.4.0] - 2022-01-03

4. Get auto-generate release notes:

- Open https://github.com/soxoj/maigret/releases/new
- Click `Choose a tag`, enter `v0.4.0` (your version)
- Click `Create new tag`
- Press `+ Auto-generate release notes`
- Copy all the text from description text field below
- Paste it to empty text section in `CHANGELOG.txt`
- Remove redundant lines `## What's Changed` and `## New Contributors` section if it exists
- *Close the new release page*

5. Commit all the changes, push, make pull request

.. code-block:: console

  git add -p
  git commit -m 'Bump to YOUR VERSION'
  git push origin head


6. Merge pull request

7. Create new release

- Open https://github.com/soxoj/maigret/releases/new again
- Click `Choose a tag`
- Enter actual version in format `v0.4.0`
- Also enter actual version in the field `Release title` 
- Click `Create new tag`
- Press `+ Auto-generate release notes`
- **Press "Publish release" button**

8. That's all, now you can simply wait push to PyPi. You can monitor it in Action page: https://github.com/soxoj/maigret/actions/workflows/python-publish.yml

Documentation updates
---------------------

Documentations is auto-generated and auto-deployed from the ``docs`` directory.

To manually update documentation:

1. Change something in the ``.rst`` files in the ``docs/source`` directory.
2. Install ``python -m pip install -e .`` in the docs directory.
3. Run ``make singlehtml`` in the terminal in the docs directory.
4. Open ``build/singlehtml/index.html`` in your browser to see the result.
5. If everything is ok, commit and push your changes to GitHub. 

Roadmap
-------

.. warning::
   This roadmap requires updating to reflect the current project status and future plans.

.. figure:: https://i.imgur.com/kk8cFdR.png   
   :target: https://i.imgur.com/kk8cFdR.png
   :align: center
