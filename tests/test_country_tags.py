"""Country-tag hygiene tests for maigret/resources/data.json.

Country tags are 2-letter codes (see maigret.utils.is_country_tag). These tests
keep them honest: every one must be an officially assigned ISO 3166-1 alpha-2
code, the reserved 'uk'/'eu' must not sneak in (use 'gb' / a real country), and
a handful of domain-hack mistags stay removed.
"""

import pytest

from maigret.utils import is_country_tag

# Officially assigned ISO 3166-1 alpha-2 codes. Deliberately excludes the
# exceptionally-reserved 'uk' and 'eu' — the DB uses 'gb' for the UK and no
# region code for the EU.
ISO_ALPHA2 = set(
    "ad ae af ag ai al am ao aq ar as at au aw ax az ba bb bd be bf bg bh bi bj "
    "bl bm bn bo bq br bs bt bv bw by bz ca cc cd cf cg ch ci ck cl cm cn co cr "
    "cu cv cw cx cy cz de dj dk dm do dz ec ee eg eh er es et fi fj fk fm fo fr "
    "ga gb gd ge gf gg gh gi gl gm gn gp gq gr gs gt gu gw gy hk hm hn hr ht hu "
    "id ie il im in io iq ir is it je jm jo jp ke kg kh ki km kn kp kr kw ky kz "
    "la lb lc li lk lr ls lt lu lv ly ma mc md me mf mg mh mk ml mm mn mo mp mq "
    "mr ms mt mu mv mw mx my mz na nc ne nf ng ni nl no np nr nu nz om pa pe pf "
    "pg ph pk pl pm pn pr ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si "
    "sj sk sl sm sn so sr ss st sv sx sy sz tc td tf tg th tj tk tl tm tn to tr "
    "tt tv tw tz ua ug um us uy uz va vc ve vg vi vn vu wf ws ye yt za zm zw".split()
)


def _country_tags(site):
    return [t for t in site.tags if is_country_tag(t) and t != "global"]


def test_country_tags_are_officially_assigned_iso(default_db):
    """Every country tag must be a real ISO 3166-1 alpha-2 code."""
    bad = {}
    for site in default_db.sites:
        for tag in _country_tags(site):
            if tag not in ISO_ALPHA2:
                bad.setdefault(tag, []).append(site.name)
    assert not bad, "non-ISO country tags: " + str({k: v[:5] for k, v in bad.items()})


def test_no_reserved_uk_or_eu(default_db):
    """'uk' -> use 'gb'; 'eu' is a region, not a country."""
    offenders = {
        s.name: s.tags for s in default_db.sites if "uk" in s.tags or "eu" in s.tags
    }
    assert not offenders, "use 'gb' not 'uk', and drop 'eu': " + str(offenders)


# Valid ISO codes that were mis-applied as country tags via domain hacks
# (megabravo.tk -> Tokelau, induste.com -> Réunion, etc.). Keep them gone.
REMOVED_HACKS = [
    ("megabravo.tk", "tk"),
    ("induste.com", "re"),
    ("Movieforums", "la"),
    ("Letsbeef", "vi"),
    ("OP.GG LoL Middle East", "me"),
]


@pytest.mark.parametrize("site_name,tag", REMOVED_HACKS)
def test_domain_hack_country_tags_removed(default_db, site_name, tag):
    site = next((s for s in default_db.sites if s.name == site_name), None)
    assert site is not None, f"{site_name} no longer in DB — update this test"
    assert tag not in site.tags, f"{site_name} must not carry domain-hack tag '{tag}'"
