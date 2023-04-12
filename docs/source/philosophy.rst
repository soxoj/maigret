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
