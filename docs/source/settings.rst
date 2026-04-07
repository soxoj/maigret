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
