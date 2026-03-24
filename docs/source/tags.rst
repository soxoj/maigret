.. _tags:

Tags
====

The use of tags allows you to select a subset of the sites from big Maigret DB for search.

.. warning::
   Tags markup is still not stable.

There are several types of tags:

1. **Country codes**: ``us``, ``jp``, ``br``... (`ISO 3166-1 alpha-2 <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`_). These tags reflect the site language and regional origin of its users and are then used to locate the owner of a username. If the regional origin is difficult to establish or a site is positioned as worldwide, `no country code is given`. There could be multiple country code tags for one site.

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
