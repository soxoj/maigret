.. _privacy:

Privacy
=======

Maigret runs entirely on your machine. It has no telemetry, no analytics and no
update pings, and it sends nothing to the project maintainers.

The usernames you search for are sent to the websites being checked, because
that is how the check works: Maigret requests public profile URLs the same way a
browser would. Reports are written to local files only.

One feature is opt-in and involves a third party: the AI analysis of a report is
sent to the OpenAI API, and only if you supply your own API key. Without a key
the feature is inactive.
