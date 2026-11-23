"""Ingest: read ABC, MusicXML, MIDI and LilyPond into the core model, behind the licence-evidence gate.

``ingest`` checks the work's evidence records and the class of every source before it parses anything, and writes
the evidence to ``work.yaml`` only for a work it accepts. The parsers can also be used on their own; each returns a
``Score`` (work, arrangement and meter) or raises ``ParseError``.

Released under the Unlicense.
"""

from .abc_notation import parse_abc
from .common import ParseError, Score
from .evidence import FIELDS, check_evidence, check_record
from .gate import (
    CONFIRMED, EXTENSIONS, FLAGGED, PARSERS, PASSED, WORK_SCHEMA, EvidenceRefused, IngestRefused, IngestResult,
    LyricsRefused, SourceRefused, classify_sources, detect_format, ingest, ingest_file,
)
from .lilypond import parse_lilypond
from .midi import parse_midi
from .musicxml import parse_musicxml
from .sources import (
    ALLOWED, BANNED, DEFAULT_REGISTRY, VERIFY_ONLY, Classification, SourceEntry, SourceRegistry,
)

__all__ = [
    "ALLOWED", "BANNED", "CONFIRMED", "Classification", "DEFAULT_REGISTRY", "EXTENSIONS", "EvidenceRefused", "FIELDS",
    "FLAGGED", "IngestRefused", "IngestResult", "LyricsRefused", "PARSERS", "PASSED", "ParseError", "Score",
    "SourceEntry", "SourceRefused", "SourceRegistry", "VERIFY_ONLY", "WORK_SCHEMA", "check_evidence", "check_record",
    "classify_sources", "detect_format", "ingest", "ingest_file", "parse_abc", "parse_lilypond", "parse_midi",
    "parse_musicxml",
]
