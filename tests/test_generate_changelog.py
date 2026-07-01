"""Unit tests for the pure CHANGELOG-manipulation logic in utils/generate_changelog.

The GitHub-fetching part (fetch_release_notes) is intentionally not tested here —
it is a thin `gh api` wrapper. Everything that decides *what the file becomes* is
pure and covered below.
"""

from utils.generate_changelog import build_section, upsert_section

NOTES = (
    "## What's Changed\n"
    "* Fix site checks by @soxoj in https://github.com/soxoj/maigret/pull/2826\n"
    "* Add Neo4j export by @soxoj in https://github.com/soxoj/maigret/pull/2774\n\n"
    "**Full Changelog**: https://github.com/soxoj/maigret/compare/v0.6.1...v0.6.2"
)


def test_build_section_shape():
    section = build_section("0.6.2", "2026-07-01", NOTES)
    assert section.startswith("## [0.6.2] - 2026-07-01\n\n## What's Changed\n")
    assert section.endswith("compare/v0.6.1...v0.6.2\n")


def test_upsert_replaces_empty_placeholder():
    changelog = (
        "# Changelog\n\n"
        "## [0.6.2] - 2026-07-01\n\n"
        "## What's Changed\n\n"
        "## [0.6.1] - 2026-05-15\n\n"
        "## What's Changed\n"
        "* old release entry\n"
    )
    section = build_section("0.6.2", "2026-07-01", NOTES)
    out = upsert_section(changelog, "0.6.2", section)

    # The placeholder is filled with the real notes...
    assert "* Fix site checks by @soxoj" in out
    # ...exactly once (no duplicate heading)...
    assert out.count("## [0.6.2]") == 1
    # ...and the previous release entry is untouched.
    assert "* old release entry" in out
    assert out.count("## [0.6.1]") == 1
    # New entry precedes the old one.
    assert out.index("## [0.6.2]") < out.index("## [0.6.1]")


def test_upsert_inserts_when_absent():
    changelog = "# Changelog\n\n## [0.6.1] - 2026-05-15\n\n* old\n"
    section = build_section("0.7.0", "2026-08-01", NOTES)
    out = upsert_section(changelog, "0.7.0", section)

    assert out.startswith("# Changelog\n")
    assert out.index("## [0.7.0]") < out.index("## [0.6.1]")
    assert "* old" in out


def test_upsert_is_idempotent():
    changelog = "# Changelog\n\n## [0.6.1] - 2026-05-15\n\n* old\n"
    section = build_section("0.6.2", "2026-07-01", NOTES)
    once = upsert_section(changelog, "0.6.2", section)
    twice = upsert_section(once, "0.6.2", section)
    assert once == twice
    assert once.count("## [0.6.2]") == 1
