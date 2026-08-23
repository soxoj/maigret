# coding: utf8
"""Identifier extraction from search results.

The point of a name search is not the links themselves but the identifiers
hidden in them: profile usernames, emails, phones. Those are what maigret can
pivot on afterwards.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# (platform, compiled regexp with a `username` group)
_PROFILE_PATTERNS_RAW: List[Tuple[str, str]] = [
    ("LinkedIn", r"linkedin\.com/in/(?P<username>[\w\-%.]+)"),
    ("GitHub", r"github\.com/(?P<username>[\w\-]+)/?$"),
    ("GitLab", r"gitlab\.com/(?P<username>[\w\-.]+)/?$"),
    ("X (Twitter)", r"(?:twitter|x)\.com/(?P<username>[A-Za-z0-9_]{2,15})/?(?:$|\?)"),
    ("Instagram", r"instagram\.com/(?P<username>[\w\-.]+)/?"),
    ("Facebook", r"facebook\.com/(?P<username>[\w\-.]+)/?"),
    ("VK", r"vk\.com/(?P<username>[\w\-.]+)/?"),
    ("Odnoklassniki", r"ok\.ru/(?:profile/)?(?P<username>[\w\-.]+)/?"),
    ("Telegram", r"t\.me/(?P<username>[\w\-]+)/?$"),
    ("Habr", r"habr\.com/[\w\-]+/users/(?P<username>[\w\-.]+)/?"),
    ("Medium", r"medium\.com/@(?P<username>[\w\-.]+)/?$"),
    ("Reddit", r"reddit\.com/u(?:ser)?/(?P<username>[\w\-]+)/?"),
    ("YouTube", r"youtube\.com/@(?P<username>[\w\-.]+)/?"),
    ("Behance", r"behance\.net/(?P<username>[\w\-]+)/?$"),
    ("Dribbble", r"dribbble\.com/(?P<username>[\w\-]+)/?$"),
    ("SoundCloud", r"soundcloud\.com/(?P<username>[\w\-]+)/?$"),
    ("Keybase", r"keybase\.io/(?P<username>[\w\-]+)/?$"),
    ("About.me", r"about\.me/(?P<username>[\w\-.]+)/?$"),
    ("Gravatar", r"gravatar\.com/(?P<username>[\w\-]+)/?$"),
    ("Stack Overflow", r"stackoverflow\.com/users/\d+/(?P<username>[\w\-]+)/?"),
    ("Speakerdeck", r"speakerdeck\.com/(?P<username>[\w\-]+)/?$"),
    ("Telegra.ph", r"telegra\.ph/(?P<username>[\w\-]+)"),
]

PROFILE_PATTERNS = [
    (platform, re.compile(pattern, re.IGNORECASE))
    for platform, pattern in _PROFILE_PATTERNS_RAW
]

# URL path segments that look like usernames but are not.
RESERVED_SLUGS = {
    "about",
    "home",
    "login",
    "search",
    "explore",
    "help",
    "settings",
    "privacy",
    "terms",
    "pages",
    "groups",
    "events",
    "watch",
    "share",
    "profile",
    "people",
    "company",
    "jobs",
    "posts",
    "feed",
    "topic",
    "tag",
    "user",
    "users",
    "index",
    "sitemap",
    "hashtag",
    "story",
    "stories",
    "video",
    "channel",
}

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
PHONE_RE = re.compile(r"(?:(?<=^)|(?<=[^\d]))\+?\d[\d\s\-().]{8,18}\d(?=$|[^\d])")

# Aggregators that resell scraped name data — high volume, near-zero value.
NOISE_DOMAINS = {
    "spokeo.com",
    "whitepages.com",
    "peoplefinders.com",
    "radaris.com",
    "truepeoplesearch.com",
    "beenverified.com",
    "fastpeoplesearch.com",
    "clustrmaps.com",
    "zoominfo.com",
    "rocketreach.co",
    "signalhire.com",
    "lusha.com",
}


@dataclass
class Identifier:
    """One extracted identifier plus where it came from."""

    kind: str  # username | email | phone
    value: str
    platform: Optional[str] = None
    source_url: str = ""
    confidence: float = 0.5

    @property
    def key(self) -> Tuple[str, str, Optional[str]]:
        return (self.kind, self.value.lower(), self.platform)

    def to_dict(self) -> Dict[str, object]:
        return {
            "kind": self.kind,
            "value": self.value,
            "platform": self.platform,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def is_noise(url: str) -> bool:
    """True for people-data aggregators that pollute every name search."""
    domain = domain_of(url)
    return any(
        domain == noise or domain.endswith("." + noise) for noise in NOISE_DOMAINS
    )


def extract_profile(url: str) -> Optional[Tuple[str, str]]:
    """Return (platform, username) if the URL is a recognizable profile."""
    for platform, pattern in PROFILE_PATTERNS:
        match = pattern.search(url)
        if not match:
            continue
        username = (match.group("username") or "").strip("/.")
        if not username or username.lower() in RESERVED_SLUGS:
            continue
        if len(username) < 2 or username.isdigit():
            continue
        return platform, username
    return None


def extract_emails(text: str) -> List[str]:
    found = []
    for candidate in EMAIL_RE.findall(text or ""):
        lowered = candidate.lower()
        # Image and asset filenames occasionally match the pattern.
        if lowered.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            continue
        found.append(lowered)
    return found


def extract_phones(text: str) -> List[str]:
    """Conservative phone extraction: 10-15 digits, no year/id look-alikes."""
    found = []
    for candidate in PHONE_RE.findall(text or ""):
        digits = re.sub(r"\D", "", candidate)
        if not 10 <= len(digits) <= 15:
            continue
        if len(set(digits)) <= 2:  # 0000000000 and friends
            continue
        found.append("+" + digits if candidate.strip().startswith("+") else digits)
    return found


def extract_identifiers(
    url: str, text: str, confidence: float = 0.5
) -> List[Identifier]:
    """Pull every identifier out of one result (URL + title + snippet)."""
    identifiers: List[Identifier] = []

    profile = extract_profile(url)
    if profile:
        platform, username = profile
        identifiers.append(
            Identifier(
                kind="username",
                value=username,
                platform=platform,
                source_url=url,
                # A username coming from a URL that also matched the name well
                # is the strongest signal this pipeline produces.
                confidence=round(min(1.0, 0.5 + confidence / 2), 2),
            )
        )

    for email in extract_emails(text):
        identifiers.append(
            Identifier(kind="email", value=email, source_url=url, confidence=confidence)
        )

    for phone in extract_phones(text):
        identifiers.append(
            Identifier(
                kind="phone", value=phone, source_url=url, confidence=confidence * 0.8
            )
        )

    return identifiers


def merge_identifiers(identifiers: List[Identifier]) -> List[Identifier]:
    """Deduplicate, keeping the highest-confidence occurrence of each."""
    best: Dict[Tuple[str, str, Optional[str]], Identifier] = {}
    for identifier in identifiers:
        existing = best.get(identifier.key)
        if existing is None or identifier.confidence > existing.confidence:
            best[identifier.key] = identifier

    return sorted(best.values(), key=lambda i: (-i.confidence, i.kind, i.value))


def usernames_from(
    identifiers: List[Identifier], min_confidence: float = 0.6
) -> List[str]:
    """Confident usernames, ready to be handed to maigret."""
    seen: Set[str] = set()
    result = []
    for identifier in identifiers:
        if identifier.kind != "username" or identifier.confidence < min_confidence:
            continue
        lowered = identifier.value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(identifier.value)
    return result
