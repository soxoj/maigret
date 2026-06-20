.. _use-case-scientists:

Academic & Research Investigations
==================================

Academic identity has a unique anchor that social-media identity does not: the **ORCID** (Open Researcher and Contributor ID). Every ORCID is verified, globally unique, and tied to a confirmed email — a single confirmed ORCID match between two platforms means the **same human**, with effectively zero false-positive rate.

Maigret uses ORCID as a first-class identifier: extract it once from a username-keyed profile (iNaturalist, GitHub bio, lab homepage), then pivot into the academic graph (ORCID, OpenAlex, arXiv, DBLP, Scholia) — a chain of HTTP calls that turns an anonymous handle into a CV with employer, education, publication list, citation count, co-author graph, and topical area.

Why it matters
--------------

Most OSINT work on academic targets stalls at the same bottleneck: people use one alias on a citizen-science site, a different alias on Twitter, a third in a forum signature, and only their real name on PubMed. Connecting the personas by hand means trawling Google Scholar, ResearchGate, university web pages, and old conference programmes. ORCID short-circuits this entirely — one verified identifier resolves all of them.

Common scenarios:

- **Researcher background check.** Before a collaboration, a preprint review, or a grant decision — verifying that a claimed h-index, employment history, and publication count actually match the public ORCID record.
- **Co-author graph reconstruction.** From a single ORCID, OpenAlex returns every co-author, their institutions, and topical clusters — useful for spotting undisclosed conflicts of interest.
- **Paper mill / fraud investigation.** When a suspicious paper's authors share an ORCID-claimed identity, the cross-platform footprint (or absence of one) is itself evidence.
- **Pseudonym deanonymisation.** A wildlife photographer posts naturalist observations under the handle ``kueda``. iNaturalist's public API returns their ORCID, and one further request reveals their real name, employer (California Academy of Sciences), education (UC Berkeley), and 700+ citable observations.
- **Award / appointment due diligence.** Confirming a Turing-Award claim, a tenure status, or a society fellowship via the DBLP and ORCID activity timelines rather than a CV PDF.

Supported sites
---------------

Maigret currently checks the following ORCID-keyed platforms (use ``--id-type orcid`` when starting from a bare ORCID, or rely on the recursive chain when starting from a username):

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Site
     - What it reveals
     - Notes
   * - **ORCID**
     - Full name, biography, employment, education, researcher URLs (homepages and social), keywords, country, linked external IDs (Scopus, ResearcherID, Loop), publication summary, email-verified status
     - All disciplines — ORCID is a field-agnostic identifier issued to any researcher.
   * - **OpenAlex**
     - Display name and name alternatives, works count, total citations, h-index, i10-index, last-known institutions (with country), topical areas, raw author-name variants from publications
     - All disciplines — indexes works across the entire scholarly literature, from humanities to medicine.
   * - **arXiv**
     - Author preprint listing — paper titles, IDs, dates
     - Strongly biased toward physics, math, CS (and quantitative biology, statistics, EE, quantitative finance, economics).
   * - **DBLP**
     - Full name, DBLP person ID, paper count, affiliation, awards (e.g. Turing Award), homepage URLs, links to Google Scholar / ResearchGate / Scopus
     - Computer science only — a biologist or pure economist will not be in the index.
   * - **Scholia**
     - Wikidata QID for the author, linked publications, co-author graph, employer/affiliation timeline, topical clusters
     - All disciplines, but only if the author has been curated in Wikidata — coverage is broadest for prominent figures (award winners, senior faculty, deceased researchers).

Workflow: from username to ORCID
--------------------------------

**Step 1: Find a profile that publishes ORCID**

The most reliable bridges from a username to an ORCID are platforms whose users *want* their academic identity discoverable. In practice:

- **iNaturalist** — biologists, naturalists, citizen scientists. Public API ``api.inaturalist.org/v1/users/{username}`` returns the ORCID directly in the ``orcid`` field. Maigret extracts it automatically.
- **GitHub** — scientists often paste their ORCID URL into the **bio** or **blog** field on their GitHub profile, or under a *generic* entry in ``/users/{u}/social_accounts``. A pattern like ``orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])`` matches both ``http://orcid.org/...`` and ``orcid.org/...`` variants.
- **Lab homepage / institutional bio.** Use ``--parse <URL>`` to scrape an arbitrary page for known identifiers — useful when the target's footprint lives at ``faculty.example.edu/~jdoe``.

**Step 2: Let the recursive search run**

.. code-block:: console

   maigret <username> --tags science -v

Recursive search is enabled by default. As soon as Maigret extracts an ``orcid`` field from any found profile, it queues an ``--id-type orcid`` second wave automatically. No manual chaining needed.

**Step 3: Start from a bare ORCID**

If you already have the ORCID (e.g. from a paper's author footer, a grant database, or a Wikidata entry):

.. code-block:: console

   maigret 0000-0002-9322-3515 --id-type orcid -a

This bypasses the username-bridge step entirely.

Workflow: from ORCID to mainstream identity
-------------------------------------------

The ORCID record itself contains the link back to ordinary social platforms:

1. **ORCID ``researcher-urls``** — a list of self-declared external links. Typical entries: lab homepage, Twitter/Bluesky/Mastodon profile, personal blog. These are entered by the researcher and therefore confirmed.
2. **ORCID ``external-identifiers``** — IDs from sibling academic systems (Scopus Author ID, ResearcherID/Publons, Loop profile). Each unlocks another extraction pipeline.
3. **OpenAlex ``last_known_institutions``** — current employer with country, ROR ID, and OpenAlex institution ID; useful for pivoting into the institution's directory.
4. **DBLP** ``<url>`` **tags** — DBLP records often embed direct links to Google Scholar, ResearchGate, and personal pages.
5. **Scholia ``wikidata_qid``** — once you have a Wikidata QID, the SPARQL endpoint unlocks the broadest external ID set in any single OSINT system: VIAF, LCCN, GND, Twitter handle, Mastodon handle, IMDb, GitHub, ORCID, and ~200 others.

Tips
----

- **Email comes from ORCID** — within the academic chain (ORCID, OpenAlex, arXiv, DBLP, Scholia) it is the only source that returns an email address, and only when the researcher has marked their primary email public. The same response also carries ``history.verified-primary-email``, an ORCID-confirmed flag that means the address was email-validated at registration. Use this as a strong pivot into email-keyed lookups (Holehe, HIBP, Gravatar, etc.).
- **Outside the academic chain, GitLab is the dev platform most likely to leak an email** via its public ``public_email`` field — relevant for scientists who self-host code on a CERN/research-institute GitLab. GitHub's REST API does not expose email by default.
- **Compare OpenAlex** ``raw_author_names`` **against the ORCID** ``other-names``. Discrepancies often expose pre-marriage names, transliterations from non-Latin scripts, or co-author misattributions worth flagging.
- **Anything fed into** ``--id-type orcid`` **must match** ``^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$``. The trailing character may legitimately be ``X`` (ISO checksum); strip ``https://orcid.org/`` prefixes before passing the bare ID.
