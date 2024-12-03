.. _quick-start:

Quick start
===========

After :doc:`installing Maigret <installation>`, you can begin searching by providing one or more usernames to look up:

``maigret username1 username2 ...``

Maigret will search for accounts with the specified usernames across a vast number of websites. It will provide you with a list 
of URLs to any discovered accounts, along with relevant information extracted from those profiles.

.. note::
   Maigret will search for accounts on a huge number of sites,
   and some of them may return false positive results. At the moment, we are working on autorepair mode to deliver 
   the most accurate results. 
   
   If you experience many false positives, you can do the following:

   - Install the last development version of Maigret from GitHub
   - Run Maigret with ``--self-check`` flag and agree on disabling of problematic sites
