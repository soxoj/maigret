# coding: utf8
"""Name parsing, spelling variants and username candidates.

A full name is a much weaker identifier than a username: the same person is
spelled `Dmitrii Danilov`, `Dmitry Danilov`, `Danilov D.` and `Дмитрий Данилов`
across sites. This module expands one input string into the set of spellings
worth querying, and into the username candidates worth feeding to maigret
afterwards.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List

from ..permutator import Permute

# Kinds of generated spellings, ordered by how much we trust them.
KIND_WEIGHTS = {
    "canonical": 1.0,
    "translit": 0.8,
    "reordered": 0.6,
    "cyrillic": 0.7,
    "diminutive": 0.4,
    "initials": 0.3,
}


@dataclass
class NameVariant:
    """One spelling of the target's name."""

    text: str
    kind: str
    script: str = "latin"

    @property
    def weight(self) -> float:
        return KIND_WEIGHTS.get(self.kind, 0.5)

    @property
    def tokens(self) -> List[str]:
        return [t for t in re.split(r"[\s\-]+", self.text.lower()) if t]

    def __str__(self) -> str:
        return self.text


@dataclass
class NameParts:
    """Structured view of the input name."""

    given: str = ""
    middle: str = ""
    family: str = ""
    raw: str = ""
    extra: List[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return bool(self.given and self.family)


# Latin spelling aliases of common Slavic given names, plus their Cyrillic
# forms. Deliberately small: this is the extension point where a bigger
# dictionary (or an LLM call) would plug in.
GIVEN_NAME_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "dmitrii": {
        "latin": ["dmitrii", "dmitry", "dmitriy", "dmitri", "dimitri"],
        "short": ["dima", "mitya", "dimon"],
        "cyrillic": ["Дмитрий", "Дима", "Митя"],
    },
    "aleksei": {
        "latin": ["aleksei", "alexey", "alexei", "aleksey", "alex"],
        "short": ["lesha", "alyosha"],
        "cyrillic": ["Алексей", "Лёша"],
    },
    "aleksandr": {
        "latin": ["aleksandr", "alexander", "alexandr", "aleksander"],
        "short": ["sasha", "sanya", "alex"],
        "cyrillic": ["Александр", "Саша"],
    },
    "andrei": {
        "latin": ["andrei", "andrey", "andrew"],
        "short": ["andryusha"],
        "cyrillic": ["Андрей"],
    },
    "anton": {"latin": ["anton"], "short": ["tosha"], "cyrillic": ["Антон"]},
    "artem": {
        "latin": ["artem", "artyom", "artiom"],
        "short": ["tyoma"],
        "cyrillic": ["Артём", "Артем"],
    },
    "boris": {"latin": ["boris"], "short": ["borya"], "cyrillic": ["Борис"]},
    "denis": {"latin": ["denis", "denys"], "short": [], "cyrillic": ["Денис"]},
    "evgenii": {
        "latin": ["evgenii", "evgeny", "evgeniy", "eugene", "yevgeny"],
        "short": ["zhenya"],
        "cyrillic": ["Евгений", "Женя"],
    },
    "ivan": {"latin": ["ivan"], "short": ["vanya"], "cyrillic": ["Иван", "Ваня"]},
    "igor": {"latin": ["igor"], "short": [], "cyrillic": ["Игорь"]},
    "kirill": {"latin": ["kirill", "cyril"], "short": [], "cyrillic": ["Кирилл"]},
    "maksim": {
        "latin": ["maksim", "maxim", "max"],
        "short": ["maks"],
        "cyrillic": ["Максим", "Макс"],
    },
    "mikhail": {
        "latin": ["mikhail", "michail", "michael"],
        "short": ["misha"],
        "cyrillic": ["Михаил", "Миша"],
    },
    "nikolai": {
        "latin": ["nikolai", "nikolay", "nicolay"],
        "short": ["kolya"],
        "cyrillic": ["Николай", "Коля"],
    },
    "pavel": {
        "latin": ["pavel", "paul"],
        "short": ["pasha"],
        "cyrillic": ["Павел", "Паша"],
    },
    "petr": {
        "latin": ["petr", "pyotr", "peter"],
        "short": ["petya"],
        "cyrillic": ["Пётр", "Петр"],
    },
    "roman": {"latin": ["roman"], "short": ["roma"], "cyrillic": ["Роман", "Рома"]},
    "sergei": {
        "latin": ["sergei", "sergey", "sergej", "serge"],
        "short": ["seryoga"],
        "cyrillic": ["Сергей"],
    },
    "vladimir": {
        "latin": ["vladimir", "wladimir"],
        "short": ["vova", "volodya"],
        "cyrillic": ["Владимир", "Вова"],
    },
    "vladislav": {
        "latin": ["vladislav"],
        "short": ["vlad"],
        "cyrillic": ["Владислав", "Влад"],
    },
    "anna": {"latin": ["anna", "ann"], "short": ["anya"], "cyrillic": ["Анна", "Аня"]},
    "ekaterina": {
        "latin": ["ekaterina", "katerina", "catherine"],
        "short": ["katya", "kate"],
        "cyrillic": ["Екатерина", "Катя"],
    },
    "elena": {
        "latin": ["elena", "yelena", "helen"],
        "short": ["lena"],
        "cyrillic": ["Елена", "Лена"],
    },
    "irina": {
        "latin": ["irina", "irene"],
        "short": ["ira"],
        "cyrillic": ["Ирина", "Ира"],
    },
    "maria": {
        "latin": ["maria", "mariya", "marya"],
        "short": ["masha"],
        "cyrillic": ["Мария", "Маша"],
    },
    "natalia": {
        "latin": ["natalia", "natalya", "nataliya", "natalie"],
        "short": ["natasha"],
        "cyrillic": ["Наталья", "Наталия", "Наташа"],
    },
    "olga": {"latin": ["olga"], "short": ["olya"], "cyrillic": ["Ольга", "Оля"]},
    "tatiana": {
        "latin": ["tatiana", "tatyana"],
        "short": ["tanya"],
        "cyrillic": ["Татьяна", "Таня"],
    },
}

# Reverse index: every known latin/short spelling -> canonical key.
_ALIAS_INDEX: Dict[str, str] = {}
for _key, _data in GIVEN_NAME_ALIASES.items():
    for _alias in _data["latin"] + _data["short"]:
        _ALIAS_INDEX.setdefault(_alias, _key)

# Ordered latin -> Cyrillic rules. Longest digraphs first so that `shch` is not
# eaten by `sh`. The result is approximate on purpose — search engines are
# tolerant, and a wrong-ish Cyrillic guess simply returns nothing.
_TRANSLIT_ENDINGS = [
    ("skiy", "ский"),
    ("skii", "ский"),
    ("skaya", "ская"),
    ("sky", "ский"),
    ("ski", "ский"),
    ("ova", "ова"),
    ("eva", "ева"),
    ("ina", "ина"),
    ("ov", "ов"),
    ("ev", "ев"),
    ("yev", "ев"),
    ("in", "ин"),
    ("yn", "ын"),
]

_TRANSLIT_RULES = [
    ("shch", "щ"),
    ("sch", "щ"),
    ("zh", "ж"),
    ("kh", "х"),
    ("ts", "ц"),
    ("ch", "ч"),
    ("sh", "ш"),
    ("yu", "ю"),
    ("iu", "ю"),
    ("ya", "я"),
    ("ia", "я"),
    ("yo", "ё"),
    ("ye", "е"),
    ("je", "е"),
    ("ii", "ий"),
    ("iy", "ий"),
    ("ij", "ий"),
    ("ee", "е"),
    ("a", "а"),
    ("b", "б"),
    ("c", "к"),
    ("d", "д"),
    ("e", "е"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "х"),
    ("i", "и"),
    ("j", "й"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "к"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("w", "в"),
    ("x", "кс"),
    ("y", "й"),
    ("z", "з"),
    ("'", "ь"),
]

CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")

PATRONYMIC_SUFFIXES = (
    "ovich",
    "evich",
    "ievich",
    "ovna",
    "evna",
    "ichna",
    "ович",
    "евич",
    "овна",
    "евна",
)


def is_cyrillic(text: str) -> bool:
    return bool(CYRILLIC_RE.search(text))


def to_cyrillic(word: str) -> str:
    """Approximate latin -> Cyrillic transliteration of a single word."""
    if not word or is_cyrillic(word):
        return word

    lowered = word.lower()
    suffix = ""
    for ending, replacement in _TRANSLIT_ENDINGS:
        if lowered.endswith(ending) and len(lowered) > len(ending):
            suffix = replacement
            lowered = lowered[: -len(ending)]
            break

    result = ""
    i = 0
    while i < len(lowered):
        for src, dst in _TRANSLIT_RULES:
            if lowered.startswith(src, i):
                result += dst
                i += len(src)
                break
        else:  # unknown symbol, keep as is
            result += lowered[i]
            i += 1

    result += suffix
    return result.capitalize()


def parse_name(full_name: str) -> NameParts:
    """Split a free-form full name into given / middle / family parts.

    Handles `Given Family`, `Given Patronymic Family` and the `Family Given`
    order produced by many databases (detected by the Slavic patronymic suffix
    in the second token).
    """
    raw = " ".join(full_name.split())
    tokens = [t for t in re.split(r"[\s,]+", raw) if t]
    parts = NameParts(raw=raw)

    if not tokens:
        return parts

    if len(tokens) == 1:
        parts.given = tokens[0]
        return parts

    if len(tokens) == 2:
        parts.given, parts.family = tokens
        return parts

    if tokens[2].lower().endswith(PATRONYMIC_SUFFIXES):
        # `Danilov Dmitrii Sergeevich` -> family comes first
        parts.family, parts.given, parts.middle = tokens[0], tokens[1], tokens[2]
    else:
        # `Dmitrii Sergeevich Danilov` and everything else -> given comes first
        parts.given, parts.middle, parts.family = tokens[0], tokens[1], tokens[2]

    parts.extra = tokens[3:]
    return parts


def _dedup(variants: List[NameVariant]) -> List[NameVariant]:
    seen = set()
    result = []
    for variant in sorted(variants, key=lambda v: -v.weight):
        key = variant.text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(variant)
    return result


def name_variants(parts: NameParts, with_cyrillic: bool = True) -> List[NameVariant]:
    """Expand parsed name parts into spellings worth querying."""
    if not parts.is_usable:
        text = parts.raw or parts.given or parts.family
        return [NameVariant(text=text, kind="canonical")] if text else []

    given, family = parts.given, parts.family
    variants = [
        NameVariant(text=f"{given} {family}", kind="canonical"),
        NameVariant(text=f"{family} {given}", kind="reordered"),
        NameVariant(text=f"{given[0]}. {family}", kind="initials"),
    ]

    if parts.middle:
        variants.append(
            NameVariant(text=f"{given} {parts.middle} {family}", kind="canonical")
        )

    canonical_key = _ALIAS_INDEX.get(given.lower())
    if canonical_key:
        data = GIVEN_NAME_ALIASES[canonical_key]
        for alias in data["latin"]:
            if alias != given.lower():
                variants.append(
                    NameVariant(text=f"{alias.capitalize()} {family}", kind="translit")
                )
        for short in data["short"]:
            variants.append(
                NameVariant(text=f"{short.capitalize()} {family}", kind="diminutive")
            )

    if with_cyrillic:
        family_cyr = to_cyrillic(family)
        cyrillic_givens = []
        if canonical_key:
            cyrillic_givens = GIVEN_NAME_ALIASES[canonical_key]["cyrillic"]
        else:
            cyrillic_givens = [to_cyrillic(given)]
        for given_cyr in cyrillic_givens[:2]:
            variants.append(
                NameVariant(
                    text=f"{given_cyr} {family_cyr}", kind="cyrillic", script="cyrillic"
                )
            )
            variants.append(
                NameVariant(
                    text=f"{family_cyr} {given_cyr}", kind="cyrillic", script="cyrillic"
                )
            )

    return _dedup(variants)


def username_candidates(parts: NameParts, limit: int = 40) -> List[str]:
    """Username candidates to hand over to maigret's username search."""
    if not parts.is_usable:
        return []

    given, family = parts.given.lower(), parts.family.lower()
    elements = {given: "first", family: "last"}
    candidates = list(Permute(elements).gather(method="strict").keys())

    initial = given[0]
    candidates += [
        f"{initial}{family}",
        f"{initial}.{family}",
        f"{initial}_{family}",
        f"{family}{initial}",
        f"{given}{family[0]}",
    ]

    canonical_key = _ALIAS_INDEX.get(given)
    if canonical_key:
        data = GIVEN_NAME_ALIASES[canonical_key]
        for alias in data["latin"][:3] + data["short"][:2]:
            if alias == given:
                continue
            candidates += [f"{alias}{family}", f"{alias}_{family}", f"{alias}.{family}"]

    seen = set()
    result = []
    for candidate in candidates:
        candidate = candidate.strip("_.-")
        if not candidate or candidate in seen or len(candidate) < 3:
            continue
        seen.add(candidate)
        result.append(candidate)

    return result[:limit]


def match_score(text: str, variants: List[NameVariant]) -> float:
    """How strongly a piece of text (title/snippet/url) matches the target name.

    Returns 0..1. Full phrase hits score highest; an all-tokens-present hit in
    any order still counts, which is what catches `Danilov, Dmitrii S.` styled
    listings.
    """
    if not text:
        return 0.0

    lowered = text.lower()
    best = 0.0

    for variant in variants:
        phrase = variant.text.lower()
        if phrase in lowered:
            best = max(best, variant.weight)
            continue

        tokens = [t for t in variant.tokens if len(t) > 1]
        if tokens and all(re.search(rf"\b{re.escape(t)}", lowered) for t in tokens):
            best = max(best, variant.weight * 0.7)

    return round(min(best, 1.0), 2)
