.. _settings:

Settings
==============

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
