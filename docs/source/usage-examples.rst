.. _usage-examples:

Usage examples
==============

You can use Maigret as:

- a command line tool: initial and a default mode
- a `web interface <#web-interface>`_: view the graph with results and download all report formats on a single page
- a library: integrate Maigret into your own project

Use Cases
---------


1. Search for accounts with username ``machine42`` on top 500 sites (by default, according to Alexa rank) from the Maigret DB.

.. code-block:: console

  maigret machine42

2. Search for accounts with username ``machine42`` on **all sites** from the Maigret DB.

.. code-block:: console

  maigret machine42 -a

.. note::
   Maigret will search for accounts on a huge number of sites,
   and some of them may return false positive results. At the moment, we are working on autorepair mode to deliver 
   the most accurate results. 
   
   If you experience many false positives, you can do the following:

   - Install the last development version of Maigret from GitHub
   - Run Maigret with ``--self-check`` flag and agree on disabling of problematic sites

3. Search for accounts with username ``machine42`` and generate HTML and PDF reports.

.. code-block:: console

  maigret machine42 -HP

or

.. code-block:: console

  maigret machine42 -a --html --pdf


4. Search for accounts with username ``machine42`` on Facebook only.

.. code-block:: console

  maigret machine42 --site Facebook

5. Extract information from the Steam page by URL and start a search for accounts with found username ``machine42``.

.. code-block:: console

  maigret --parse https://steamcommunity.com/profiles/76561199113454789 

6. Search for accounts with username ``machine42`` only on US and Japanese sites.

.. code-block:: console

  maigret machine42 --tags us,jp

7. Search for accounts with username ``machine42`` only on sites related to software development.

.. code-block:: console

  maigret machine42 --tags coding

8. Search for accounts with username ``machine42`` on uCoz sites only (mostly CIS countries).

.. code-block:: console

  maigret machine42 --tags ucoz

