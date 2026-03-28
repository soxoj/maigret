.. _tags:

Tags
====

The use of tags allows you to select a subset of the sites from big Maigret DB for search.

.. warning::
   Tags markup is still not stable.

There are several types of tags:

1. **Country codes**: ``us``, ``jp``, ``br``... (`ISO 3166-1 alpha-2 <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`_). A country tag means that having an account on the site implies a connection to that country — either origin or residence. The goal is attribution, not perfect accuracy.

   - **Global sites** (GitHub, YouTube, Reddit, Medium, etc.) get **no country tag** — an account there says nothing about where a person is from.
   - **Regional/local sites** where an account implies a specific country **must** have a country tag: ``VK`` → ``ru``, ``Naver`` → ``kr``, ``Zhihu`` → ``cn``.
   - Multiple country tags are allowed when a service is used predominantly in a few countries (e.g. ``Xing`` → ``de``, ``eu``).
   - Do **not** assign country tags based on traffic statistics alone — a site popular in India by traffic is not "Indian" if it is used globally.

2. **Site engines**. Most of them are forum engines now: ``uCoz``, ``vBulletin``, ``XenForo`` et al. Full list of engines stored in the Maigret database.

3. **Sites' subject/type and interests of its users**. Full list of "standard" tags is `present in the source code <https://github.com/soxoj/maigret/blob/main/maigret/sites.py#L13>`_ only for a moment. 

Usage
-----
``--tags us,jp`` -- search on US and Japanese sites (actually marked as such in the Maigret database)

``--tags coding`` -- search on sites related to software development.

``--tags ucoz`` -- search on uCoz sites only (mostly CIS countries)

Blacklisting (excluding) tags
------------------------------
You can exclude sites with certain tags from the search using ``--exclude-tags``:

``--exclude-tags porn,dating`` -- skip all sites tagged with ``porn`` or ``dating``.

``--exclude-tags ru`` -- skip all Russian sites.

You can combine ``--tags`` and ``--exclude-tags`` to fine-tune your search:

``--tags forum --exclude-tags ru`` -- search on forum sites, but skip Russian ones.

In the web interface, the tag cloud supports three states per tag:
click once to **include** (green), click again to **exclude** (dark/strikethrough),
and click once more to return to **neutral** (red).
