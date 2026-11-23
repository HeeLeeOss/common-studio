"""The source registry: which class of the sourcing policy each source belongs to.

The sourcing policy (``policy/sourcing-and-asset-licence-policy.md``, section 5) puts every source in one of three
classes: **allowed**, **verify-only** and **banned**. The gate reads the class from this registry. A source that is
not registered is **verify-only** until a maintainer classifies it.

A registry entry names a source by one of:

- a **tag prefix** such as ``authored:``: a source text that starts with it (case does not matter);
- a **URL prefix** such as ``https://archive.example/scans/``: an ``https`` source that starts with it;
- a **host** such as ``host:scores.example``: any URL on that host or a subdomain of it.

The longest matching entry wins. Some kinds are allowed only for some records: the policy allows national-library
holdings for facts (composition and lyrics), so used as the edition they are verify-only.

Separately, a source text that states share-alike, non-commercial or no-derivatives terms, "all rights reserved" or no
licence, or that names the private reference pipeline, is **banned** whatever the registry says: the policy bans
those even for a public-domain tune.

Every tag, kind and reason below was written new for Common Studio. Released under the Unlicense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlsplit

ALLOWED = "allowed"
VERIFY_ONLY = "verify-only"
BANNED = "banned"
CLASSES = (ALLOWED, VERIFY_ONLY, BANNED)

RECORDS = ("composition", "edition", "lyrics")
ORIGIN = "origin"  # where the score file itself came from


@dataclass(frozen=True)
class SourceEntry:
    match: str
    source_class: str
    kind: str
    reason: str
    records: tuple[str, ...] = ()  # empty: the class holds for every record

    def __post_init__(self) -> None:
        if self.source_class not in CLASSES:
            raise ValueError(f"source class is one of {', '.join(CLASSES)}")
        if not self.match.strip() or not self.kind.strip() or not self.reason.strip():
            raise ValueError("a registry entry needs a match, a kind and a reason")
        if self.match.lower().startswith("http://"):
            raise ValueError("registry URLs use https")

    def matches(self, source: str) -> int:
        """How specific the match is (its length), or 0 when the entry does not match."""
        text = source.strip()
        m = self.match
        if m.lower().startswith("https://"):
            return len(m) if text.lower().startswith(m.lower()) else 0
        if m.lower().startswith("host:"):
            host = m[5:].strip().lower().rstrip(".")
            found = _host(text)
            return len(m) if found and (found == host or found.endswith("." + host)) else 0
        return len(m) if text.lower().startswith(m.lower()) else 0


@dataclass(frozen=True)
class Classification:
    record: str
    source: str
    source_class: str
    kind: str
    reason: str

    def to_dict(self) -> dict:
        return {"record": self.record, "source": self.source, "class": self.source_class, "kind": self.kind,
                "reason": self.reason}


def _host(text: str) -> Optional[str]:
    if "://" not in text:
        return None
    try:
        return (urlsplit(text.strip()).hostname or "").lower().rstrip(".") or None
    except ValueError:
        return None


# Terms that the policy bans in the source of any score, edition or lyric (section 5.3 and section 7.2).
_BANNED_TERMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"private[\s_-]+reference", re.I),
     "the private reference pipeline is banned, including its text, values, arrangement sources and assets"),
    (re.compile(r"\bcc[\s_-]*by(?:[\s_-]*(?:nc|nd|sa)){1,3}\b", re.I),
     "files under share-alike, non-commercial or no-derivatives terms are banned"),
    (re.compile(r"share[\s_-]*alike|non[\s_-]*commercial|no[\s_-]*deriv", re.I),
     "files under share-alike, non-commercial or no-derivatives terms are banned"),
    (re.compile(r"\b(?:a|l)?gpl\b|general public licen[cs]e", re.I),
     "copyleft terms are banned"),
    (re.compile(r"all rights reserved|no (?:stated )?licen[cs]e|unknown licen[cs]e|personal use only", re.I),
     "a file with no licence, or one that limits use, is banned"),
)


DEFAULT_ENTRIES: tuple[SourceEntry, ...] = (
    # Allowed (policy section 5.1)
    SourceEntry("authored:", ALLOWED, "written-for-the-project",
                "written for Common Studio by a named author who dedicated it under CC0-1.0 or the Unlicense"),
    SourceEntry("facsimile:", ALLOWED, "project-transcription-from-facsimile",
                "the project transcribed the notes itself from a facsimile of an old printing or manuscript"),
    SourceEntry("library-facts:", ALLOWED, "public-library-facts",
                "a national library or public archive record, used for facts such as dates and catalogue data",
                records=("composition", "lyrics")),
    # Verify-only (policy section 5.2)
    SourceEntry("community-library:", VERIFY_ONLY, "community-score-library",
                "hosts files under mixed licences; the uploader may not hold the rights"),
    SourceEntry("folk-collection:", VERIFY_ONLY, "community-folk-collection",
                "transcribers may not have dedicated their settings, and 'traditional' labels are often unsourced"),
    SourceEntry("library-scan:", VERIFY_ONLY, "digitised-edition-unclear-date",
                "the scan is free but the edition's date or editor still needs research"),
    SourceEntry("reference-work:", VERIFY_ONLY, "reference-work",
                "dates and facts must be confirmed against a second source"),
    SourceEntry("maintainer-transcription:", VERIFY_ONLY, "earlier-maintainer-transcription",
                "the maintainer must show the edition used and dedicate the transcription before import"),
    # Banned (policy section 5.3)
    SourceEntry("private-reference:", BANNED, "private-reference-pipeline",
                "the private reference pipeline carries no licence and includes copyleft and attribution material"),
    SourceEntry("commercial-edition:", BANNED, "in-term-modern-edition",
                "the editor's, engraver's and publisher's own rights are live even when the music is old"),
    SourceEntry("recording-transcription:", BANNED, "transcription-of-in-term-recording",
                "it copies a performer's or arranger's protected choices"),
    SourceEntry("restricted-site:", BANNED, "site-terms-forbid-reuse",
                "the site's terms forbid copying or reuse, or need a paid account"),
    SourceEntry("unidentified-upload:", BANNED, "unidentified-upload",
                "provenance cannot be shown, so no edition record is possible"),
    SourceEntry("generated:", BANNED, "generative-tool-output",
                "the rights in the output cannot be shown"),
)


class SourceRegistry:
    """A list of entries that classify sources, with the policy's banned terms checked first."""

    def __init__(self, entries: Iterable[SourceEntry] = DEFAULT_ENTRIES) -> None:
        self.entries: tuple[SourceEntry, ...] = tuple(entries)

    def with_entries(self, *entries: SourceEntry) -> "SourceRegistry":
        """A new registry with more entries, as a maintainer adds specific sources."""
        return SourceRegistry(self.entries + tuple(entries))

    def classify(self, source: str, record: str) -> Classification:
        text = (source or "").strip()
        for pattern, reason in _BANNED_TERMS:
            if pattern.search(text):
                return Classification(record, text, BANNED, "banned-terms", reason)
        best: Optional[SourceEntry] = None
        best_len = 0
        for entry in self.entries:
            n = entry.matches(text)
            if n > best_len or (n and n == best_len and best is not None and _rank(entry) > _rank(best)):
                best, best_len = entry, n
        if best is None:
            return Classification(record, text, VERIFY_ONLY, "unregistered",
                                  "the source is not in the registry, so a maintainer must classify or confirm it")
        if best.records and record not in best.records and best.source_class == ALLOWED:
            return Classification(record, text, VERIFY_ONLY, best.kind,
                                  f"this kind is allowed only for the {', '.join(best.records)} record")
        return Classification(record, text, best.source_class, best.kind, best.reason)


def _rank(entry: SourceEntry) -> int:
    return {ALLOWED: 0, VERIFY_ONLY: 1, BANNED: 2}[entry.source_class]


DEFAULT_REGISTRY = SourceRegistry()
