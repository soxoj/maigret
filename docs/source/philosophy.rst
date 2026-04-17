.. _philosophy:

Philosophy
==========

TL;DR: Username => Dossier

Maigret is designed to gather all the available information about person by his username.

What kind of information is this? First, links to person accounts. Secondly, all the machine-extractable
pieces of info, such as: other usernames, full name, URLs to people's images, birthday, location (country,
city, etc.), gender.

All this information forms some dossier, but it also useful for other tools and analytical purposes.
Each collected piece of data has a label of a certain format (for example, ``follower_count`` for the number
of subscribers or ``created_at`` for account creation time) so that it can be parsed and analyzed by various
systems and stored in databases.

Origins
-------

Maigret started from studying what OSINT investigators actually use in practice — and from
the realization that many popular tools do not deliver real investigative value. The original
research behind this observation is summarized in the article
`What's wrong with namecheckers <https://soxoj.medium.com/whats-wrong-with-namecheckers-981e5cba600e>`_.
For a broader landscape of username-checking tools, see the curated
`OSINT namecheckers list <https://github.com/soxoj/osint-namecheckers-list>`_.

Two ideas grew out of that research:

- `socid-extractor <https://github.com/soxoj/socid-extractor>`_ — a library focused on pulling
  structured identity data (user IDs, full names, linked accounts, bios, timestamps, etc.) out of
  account pages and public API responses, so that finding an account is not the end of the pipeline.
- **Maigret** itself — which started as a fork of
  `Sherlock <https://github.com/sherlock-project/sherlock>`_ but has long since outgrown the
  original project in coverage, extraction depth, and check reliability. Today Maigret is used
  as a component by major OSINT vendors in their commercial products.
