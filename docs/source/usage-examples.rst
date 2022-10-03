.. _usage-examples:

Usage examples
==============

Start a search for accounts with username ``machine42`` on top 500 sites from the Maigret DB.

.. code-block:: console

  maigret machine42

Start a search for accounts with username ``machine42`` on **all sites** from the Maigret DB.

.. code-block:: console

  maigret machine42 -a

Start a search [...] and generate HTML and PDF reports.

.. code-block:: console

  maigret machine42 -a -HP

Start a search for accounts with username ``machine42`` only on Facebook.

.. code-block:: console

  maigret machine42 --site Facebook

Extract information from the Steam page by URL and start a search for accounts with found username ``machine42``.

.. code-block:: console

  maigret --parse https://steamcommunity.com/profiles/76561199113454789 

Start a search for accounts with username ``machine42`` only on US and Japanese sites.

.. code-block:: console

  maigret machine42 --tags en,jp

Start a search for accounts with username ``machine42`` only on sites related to software development.

.. code-block:: console

  maigret machine42 --tags coding

Start a search for accounts with username ``machine42`` on uCoz sites only (mostly CIS countries).

.. code-block:: console

  maigret machine42 --tags ucoz

