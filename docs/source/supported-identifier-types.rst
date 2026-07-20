.. _supported-identifier-types:

Supported identifier types
==========================

Maigret can search against not only ordinary usernames, but also through certain common identifiers. There is a list of all currently supported identifiers.

- **gaia_id** - Google inner numeric user identifier, in former times was placed in a Google Plus account URL. 
- **steam_id** - Steam inner numeric user identifier.
- **wikimapia_uid** - Wikimapia.org inner numeric user identifier.
- **uidme_uguid** - uID.me inner numeric user identifier.
- **yandex_public_id** - Yandex sites inner letter user identifier. See also: `YaSeeker <https://github.com/HowToFind-bot/YaSeeker>`_. 
- **vk_id** - VK.com inner numeric user identifier.
- **ok_id** - OK.ru inner numeric user identifier.
- **yelp_userid** - Yelp inner user identifier.
- **qq_id** - QQ (Tencent) numeric account number, also used as the Qzone profile id.

Example
-------

Pass the identifier as the target and select its type with ``--id-type``. For example, to look up the QQ number ``10001``:

.. code-block:: console

   $ maigret 10001 --id-type qq_id

Maigret resolves the account via the Qzone portrait API and, when found, extracts the nickname and avatar. Any site whose ``type`` does not match the given ``--id-type`` is skipped, so a plain ``maigret 10001`` (default ``username``) will not query QQ.
