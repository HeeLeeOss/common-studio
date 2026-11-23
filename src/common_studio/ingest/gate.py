"""The ingest gate: evidence first, then source classes, then the parse, then ``work.yaml``.

``ingest`` refuses a work, and writes nothing, when:

1. any of the ``composition``, ``edition`` and ``lyrics`` evidence records is missing or incomplete
   (``EvidenceRefused``; the message names each record);
2. the file's origin or any record's source is **banned** by the sourcing policy, even when the tune is in the public
   domain (``SourceRefused``);
3. the file cannot be read (``ParseError``);
4. the lyrics record says ``none`` but the score carries words (``LyricsRefused``).

Otherwise it writes ``<out_dir>/<work id>/work.yaml`` with the evidence and the class of every source. A work with a
**verify-only** source is written with ``gate.status: flagged`` and stays flagged until a maintainer who is not one of
the record's checkers confirms it (``confirmed_by``), as the policy asks.

Released under the Unlicense.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union

from .abc_notation import parse_abc
from .common import ParseError, Score, Source
from .evidence import FIELDS, check_evidence, describe, lyrics_are_none
from .lilypond import parse_lilypond
from .midi import parse_midi
from .musicxml import parse_musicxml
from .sources import BANNED, DEFAULT_REGISTRY, ORIGIN, RECORDS, VERIFY_ONLY, Classification, SourceRegistry
from .workyaml import dump

WORK_SCHEMA = "common-studio/work/1"
PASSED = "passed"
FLAGGED = "flagged"
CONFIRMED = "confirmed"

PARSERS: dict[str, Callable[..., Score]] = {
    "abc": parse_abc,
    "musicxml": parse_musicxml,
    "midi": parse_midi,
    "lilypond": parse_lilypond,
}
EXTENSIONS = {
    ".abc": "abc",
    ".musicxml": "musicxml",
    ".xml": "musicxml",
    ".mid": "midi",
    ".midi": "midi",
    ".ly": "lilypond",
}

HEADER = """work.yaml: written by the Common Studio ingest gate. Do not edit by hand; re-run the gate.
The evidence records follow policy/sourcing-and-asset-licence-policy.md, section 3."""


class IngestRefused(Exception):
    """The gate refused the work. Nothing was written."""


class EvidenceRefused(IngestRefused):
    def __init__(self, problems: Mapping[str, list[str]]) -> None:
        self.problems = dict(problems)
        self.records = tuple(name for name in RECORDS if name in self.problems)
        super().__init__(f"work refused: {describe(self.problems)}")


class SourceRefused(IngestRefused):
    def __init__(self, banned: list[Classification]) -> None:
        self.banned = tuple(banned)
        detail = "; ".join(f"the {c.record} source {c.source!r} is banned ({c.reason})" for c in banned)
        super().__init__(f"work refused even if the tune is in the public domain: {detail}")


class LyricsRefused(IngestRefused):
    pass


@dataclass(frozen=True)
class IngestResult:
    score: Score
    status: str
    sources: tuple[Classification, ...]
    path: Path
    sha256: str

    @property
    def flagged(self) -> bool:
        return self.status == FLAGGED

    @property
    def flags(self) -> tuple[Classification, ...]:
        return tuple(c for c in self.sources if c.source_class == VERIFY_ONLY)


def detect_format(path: Union[str, os.PathLike]) -> str:
    suffix = Path(path).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError(f"cannot tell the format of {Path(path).name!r}; give fmt= one of {', '.join(PARSERS)}")
    return EXTENSIONS[suffix]


def classify_sources(evidence: Mapping[str, Any], origin: Optional[str],
                     registry: SourceRegistry = DEFAULT_REGISTRY) -> list[Classification]:
    out = []
    if origin is not None:
        out.append(registry.classify(origin, ORIGIN))
    for name in RECORDS:
        out.append(registry.classify(str(evidence[name]["source"]), name))
    return out


def _record(record: Mapping[str, Any]) -> dict[str, Any]:
    """A record in its written order: value (lyrics only), the four required fields, then extras by name."""
    out: dict[str, Any] = {}
    if "value" in record:
        out["value"] = record["value"]
    for f in FIELDS:
        out[f] = record[f].strip()
    for key in sorted(k for k in record if k not in FIELDS and k != "value"):
        out[key] = record[key]
    return out


def ingest(
    data: Source,
    fmt: str,
    evidence: Mapping[str, Any],
    *,
    out_dir: Union[str, os.PathLike],
    origin: Optional[str] = None,
    registry: SourceRegistry = DEFAULT_REGISTRY,
    work_id: Optional[str] = None,
    style: str = "source",
    confirmed_by: Optional[str] = None,
) -> IngestResult:
    """Run the gate on one file and, if it passes, write its ``work.yaml``."""
    problems = check_evidence(evidence)
    if problems:
        raise EvidenceRefused(problems)

    sources = classify_sources(evidence, origin, registry)
    banned = [c for c in sources if c.source_class == BANNED]
    if banned:
        raise SourceRefused(banned)

    if fmt not in PARSERS:
        raise ValueError(f"format is one of {', '.join(PARSERS)}")
    score = PARSERS[fmt](data, work_id=work_id, style=style)

    if lyrics_are_none(evidence) and any(p.lyrics and any(p.lyrics) for p in score.arrangement.parts):
        raise LyricsRefused("work refused: the lyrics record is 'none' but the score carries words; "
                            "give a full lyrics record or remove the words")

    status = FLAGGED if any(c.source_class == VERIFY_ONLY for c in sources) else PASSED
    confirmer = (confirmed_by or "").strip() or None
    if confirmer is not None:
        checkers = {str(evidence[name]["checker"]).strip().lower() for name in RECORDS}
        if confirmer.lower() in checkers:
            raise IngestRefused("a flagged work is confirmed by a maintainer who is not one of its checkers")
        if status == FLAGGED:
            status = CONFIRMED

    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    digest = hashlib.sha256(raw).hexdigest()
    document = {
        "schema": WORK_SCHEMA,
        "work": score.work.id,
        "title": score.work.title,
        "ingest": {
            "format": score.format,
            "sha256": digest,
            "origin": origin,
            "arrangement": score.arrangement.id,
            "parts": [p.name for p in score.arrangement.parts],
            "meter": f"{score.meter[0]}/{score.meter[1]}",
        },
        "gate": {
            "status": status,
            "confirmed_by": confirmer if status == CONFIRMED else None,
            "sources": [c.to_dict() for c in sources],
        },
        "evidence": {name: _record(evidence[name]) for name in RECORDS},
    }
    text = dump(document, HEADER)
    folder = Path(out_dir) / score.work.id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "work.yaml"
    path.write_bytes(text.encode("utf-8"))
    return IngestResult(score, status, tuple(sources), path, digest)


def ingest_file(path: Union[str, os.PathLike], evidence: Mapping[str, Any], *, out_dir: Union[str, os.PathLike],
                fmt: Optional[str] = None, **kwargs: Any) -> IngestResult:
    """``ingest`` for a file on disk, with the format taken from its extension unless ``fmt`` is given."""
    the_format = fmt or detect_format(path)
    problems = check_evidence(evidence)
    if problems:  # refuse before reading the file at all
        raise EvidenceRefused(problems)
    return ingest(Path(path).read_bytes(), the_format, evidence, out_dir=out_dir, **kwargs)


__all__ = [
    "CONFIRMED", "EXTENSIONS", "EvidenceRefused", "FLAGGED", "IngestRefused", "IngestResult", "LyricsRefused",
    "PARSERS", "PASSED", "ParseError", "SourceRefused", "WORK_SCHEMA", "classify_sources", "detect_format", "ingest",
    "ingest_file",
]
