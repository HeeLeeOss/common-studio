"""The canonical score representation (IR): a plain dictionary that hashes and diffs.

Canonical means one arrangement has exactly one representation: parts are sorted by name, notes by
``(beat, pitch, duration, velocity)``, beats and durations are written as exact fractions in lowest terms, and the
text form has sorted keys and fixed separators. Equal arrangements give equal text and an equal hash; a change to
one note changes the hash.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Union

from .model import Arrangement, BeatGrid, Note, Part

SCHEMA = "common-studio/score-ir"
VERSION = 1


def _frac(value: Fraction) -> str:
    return str(value)  # "3/2", or "2" for a whole number: always lowest terms


def _part_ir(part: Part) -> dict[str, Any]:
    order = sorted(range(len(part.notes)), key=lambda i: part.notes[i])
    out: dict[str, Any] = {
        "name": part.name,
        "sections": part.sections,
        "voice": part.voice,
        "kit": part.kit,
        "notes": [
            {
                "beat": _frac(part.notes[i].beat),
                "pitch": part.notes[i].pitch,
                "duration": _frac(part.notes[i].duration),
                "velocity": part.notes[i].velocity,
            }
            for i in order
        ],
        "lyrics": None if part.lyrics is None else [part.lyrics[i] for i in order],
    }
    return out


def to_ir(arrangement: Arrangement) -> dict[str, Any]:
    """The canonical representation of an arrangement, as a plain dictionary."""
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "id": arrangement.id,
        "work": arrangement.work,
        "style": arrangement.style,
        "grid": {
            "beats_per_bar": arrangement.grid.beats_per_bar,
            "subdivision": arrangement.grid.subdivision,
        },
        "parts": [_part_ir(p) for p in sorted(arrangement.parts, key=lambda p: p.name)],
    }


def canonical_json(ir: dict[str, Any]) -> str:
    """The one text form of a representation: sorted keys, no spaces, ASCII only."""
    return json.dumps(ir, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def ir_hash(source: Union[Arrangement, dict[str, Any]]) -> str:
    """``sha256:`` and the hex digest of the canonical text of an arrangement or its representation."""
    ir = to_ir(source) if isinstance(source, Arrangement) else source
    return "sha256:" + hashlib.sha256(canonical_json(ir).encode("utf-8")).hexdigest()


def from_ir(source: Union[str, dict[str, Any]]) -> Arrangement:
    """Read a representation (a dictionary or its JSON text) back into an arrangement.

    Raises ``ValueError`` when the schema, version or any field is wrong.
    """
    ir = json.loads(source) if isinstance(source, str) else source
    if not isinstance(ir, dict) or ir.get("schema") != SCHEMA:
        raise ValueError(f"not a {SCHEMA} document")
    if ir.get("version") != VERSION:
        raise ValueError(f"unsupported version {ir.get('version')!r}; this reader handles version {VERSION}")
    try:
        grid = BeatGrid(ir["grid"]["beats_per_bar"], ir["grid"]["subdivision"])
        parts = []
        for p in ir["parts"]:
            notes = tuple(Note(n["beat"], n["pitch"], n["duration"], n["velocity"]) for n in p["notes"])
            lyrics = None if p["lyrics"] is None else tuple(p["lyrics"])
            parts.append(Part(p["name"], notes, lyrics, p["sections"], p["voice"], p["kit"]))
        arrangement = Arrangement(ir["work"], ir["style"], tuple(parts), grid)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"malformed score representation: {exc}") from exc
    if arrangement.id != ir["id"]:
        raise ValueError("the id does not match the work and style")
    return arrangement


toIR = to_ir
fromIR = from_ir
