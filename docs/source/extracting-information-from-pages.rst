.. _extracting-information-from-pages:

Extracting information from pages
=================================
Maigret can parse URLs and content of web pages by URLs to extract info about account owner and other meta information.

You must specify the URL with the option ``--parse``, it's can be a link to an account or an online document. List of supported sites `see here <https://github.com/soxoj/socid-extractor#sites>`_.

After the end of the parsing phase, Maigret will start the search phase by :doc:`supported identifiers <supported-identifier-types>` found (usernames, ids, etc.).

Examples
--------
.. code-block:: console

  $ maigret --parse https://docs.google.com/spreadsheets/d/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw/edit\#gid\=0

  Scanning webpage by URL https://docs.google.com/spreadsheets/d/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw/edit#gid=0...
  ┣╸org_name: Gooten
  ┗╸mime_type: application/vnd.google-apps.ritz
  Scanning webpage by URL https://clients6.google.com/drive/v2beta/files/1HtZKMLRXNsZ0HjtBmo0Gi03nUPiJIA4CC4jTYbCAnXw?fields=alternateLink%2CcopyRequiresWriterPermission%2CcreatedDate%2Cdescription%2CdriveId%2CfileSize%2CiconLink%2Cid%2Clabels(starred%2C%20trashed)%2ClastViewedByMeDate%2CmodifiedDate%2Cshared%2CteamDriveId%2CuserPermission(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)%2Cpermissions(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)%2Cparents(id)%2Ccapabilities(canMoveItemWithinDrive%2CcanMoveItemOutOfDrive%2CcanMoveItemOutOfTeamDrive%2CcanAddChildren%2CcanEdit%2CcanDownload%2CcanComment%2CcanMoveChildrenWithinDrive%2CcanRename%2CcanRemoveChildren%2CcanMoveItemIntoTeamDrive)%2Ckind&supportsTeamDrives=true&enforceSingleParent=true&key=AIzaSyC1eQ1xj69IdTMeii5r7brs3R90eck-m7k...
  ┣╸created_at: 2016-02-16T18:51:52.021Z
  ┣╸updated_at: 2019-10-23T17:15:47.157Z
  ┣╸gaia_id: 15696155517366416778
  ┣╸fullname: Nadia Burgess
  ┣╸email: nadia@gooten.com
  ┣╸image: https://lh3.googleusercontent.com/a-/AOh14GheZe1CyNa3NeJInWAl70qkip4oJ7qLsD8vDy6X=s64
  ┗╸email_username: nadia

.. code-block:: console

  $ maigret.py --parse https://steamcommunity.com/profiles/76561199113454789
  Scanning webpage by URL https://steamcommunity.com/profiles/76561199113454789...
  ┣╸steam_id: 76561199113454789
  ┣╸nickname: Pok
  ┗╸username: Machine42
