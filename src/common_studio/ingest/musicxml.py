"""MusicXML reader (uncompressed, ``score-partwise``).

Reads the title (``work-title``, else ``movement-title``), the part list, and for each part its measures: divisions,
time signatures, pitched notes, rests, chords, ties, ``backup`` and ``forward``, and the first lyric verse. Grace and
cue notes are skipped. A document that declares entities or a document type with an internal subset is refused
before it is parsed, so entity expansion cannot be used against the reader.

Written new for Common Studio from the published MusicXML format, read as a reference. Released under the Unlicense.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from typing import Optional

from .common import DEFAULT_VELOCITY, ParseError, RawPart, Score, Source, as_bytes, build_score, guarded

FORMAT = "musicxml"

_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_DOCTYPE_SUBSET = re.compile(rb"<!DOCTYPE[^>\[]*\[", re.IGNORECASE)


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, name: str) -> Optional[ET.Element]:
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == name]


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def _int(text: str, what: str) -> int:
    t = text.strip()
    if not re.fullmatch(r"[+-]?[0-9]{1,9}", t):
        raise ParseError(FORMAT, f"{what} {text[:20]!r} is not a whole number")
    return int(t)


def _number(text: str, what: str) -> Fraction:
    t = text.strip()
    if not re.fullmatch(r"[+-]?[0-9]{1,9}(\.[0-9]{1,6})?", t):
        raise ParseError(FORMAT, f"{what} {text[:20]!r} is not a number")
    return Fraction(t)


def parse_musicxml(data: Source, *, work_id: Optional[str] = None, style: str = "source") -> Score:
    """Read an uncompressed partwise MusicXML document into the core model."""
    return guarded(FORMAT, lambda: _parse(as_bytes(FORMAT, data), work_id, style))


def _parse(raw: bytes, work_id: Optional[str], style: str) -> Score:
    if raw.startswith(b"PK"):
        raise ParseError(FORMAT, "compressed MusicXML (.mxl) is not read; give the uncompressed score")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw:
        raise ParseError(FORMAT, "only UTF-8 documents are read")
    if b"<!ENTITY" in raw.upper() or _DOCTYPE_SUBSET.search(raw):
        raise ParseError(FORMAT, "documents that declare entities are refused")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ParseError(FORMAT, f"not well-formed XML ({exc})") from None
    kind = _local(root.tag)
    if kind == "score-timewise":
        raise ParseError(FORMAT, "score-timewise is not read; convert to score-partwise")
    if kind != "score-partwise":
        raise ParseError(FORMAT, f"the root element is {kind!r}, not score-partwise")

    work_el = _child(root, "work")
    title = (_text(_child(work_el, "work-title")) if work_el is not None else "") or _text(_child(root, "movement-title"))

    names: dict[str, str] = {}
    part_list = _child(root, "part-list")
    if part_list is not None:
        for sp in _children(part_list, "score-part"):
            pid = sp.get("id") or ""
            names[pid] = _text(_child(sp, "part-name")) or pid

    meter: Optional[tuple[int, int]] = None
    parts: list[RawPart] = []
    for index, part_el in enumerate(_children(root, "part"), start=1):
        pid = part_el.get("id") or f"P{index}"
        part, part_meter = _read_part(part_el, names.get(pid) or pid)
        meter = meter or part_meter
        parts.append(part)
    if not parts:
        raise ParseError(FORMAT, "the score has no part")
    beat_unit = (meter or (4, 4))[1]
    for part in parts:
        # Positions were collected in quarter notes; the beat is the unit of the time signature's lower number.
        scale = Fraction(beat_unit, 4)
        part.notes = [(b * scale, p, d * scale, v) for b, p, d, v in part.notes]
    return build_score(FORMAT, title, parts, meter or (4, 4), work_id=work_id, style=style)


def _read_part(part_el: ET.Element, name: str) -> tuple[RawPart, Optional[tuple[int, int]]]:
    part = RawPart(name)
    divisions = Fraction(1)
    meter: Optional[tuple[int, int]] = None
    position = Fraction(0)  # in quarter notes
    measure_start = Fraction(0)
    measure_end = Fraction(0)
    last_start = Fraction(0)
    tied: dict[int, int] = {}  # pitch -> note index whose tie is open
    for measure in _children(part_el, "measure"):
        measure_start = measure_end
        position = measure_start
        for el in measure:
            tag = _local(el.tag)
            if tag == "attributes":
                d = _child(el, "divisions")
                if d is not None:
                    divisions = _number(_text(d), "divisions")
                    if divisions <= 0:
                        raise ParseError(FORMAT, "divisions must be greater than zero")
                t = _child(el, "time")
                if t is not None and meter is None:
                    beats, beat_type = _text(_child(t, "beats")), _text(_child(t, "beat-type"))
                    if beats and beat_type and re.fullmatch(r"[0-9+]{1,12}", beats) and beat_type.isdigit():
                        num = sum(int(x) for x in beats.split("+") if x)
                        meter = (num, int(beat_type[:3]))
            elif tag == "backup":
                position -= _number(_text(_child(el, "duration")) or "0", "duration") / divisions
                if position < measure_start:
                    position = measure_start
            elif tag == "forward":
                position += _number(_text(_child(el, "duration")) or "0", "duration") / divisions
            elif tag == "note":
                if _child(el, "grace") is not None or _child(el, "cue") is not None:
                    continue
                duration = _number(_text(_child(el, "duration")) or "0", "duration") / divisions
                if duration < 0:
                    raise ParseError(FORMAT, "a note has a negative duration")
                is_chord = _child(el, "chord") is not None
                start = last_start if is_chord else position
                pitch_el = _child(el, "pitch")
                if pitch_el is not None and duration > 0:
                    step = _text(_child(pitch_el, "step")).upper()
                    if step not in _STEP:
                        raise ParseError(FORMAT, f"a note has the step {step[:5]!r}")
                    alter_text = _text(_child(pitch_el, "alter")) or "0"
                    alter = _number(alter_text, "alter")
                    octave = _int(_text(_child(pitch_el, "octave")) or "4", "octave")
                    pitch = 12 * (octave + 1) + _STEP[step] + round(alter)
                    ties = {t.get("type") for t in _children(el, "tie")}
                    velocity = DEFAULT_VELOCITY
                    dyn = el.get("dynamics")
                    if dyn:
                        scaled = round(_number(dyn, "dynamics") * 90 / 100)
                        velocity = max(1, min(127, scaled))
                    if "stop" in ties and pitch in tied:
                        idx = tied.pop(pitch)
                        b, p, d, v = part.notes[idx]
                        part.notes[idx] = (b, p, d + duration, v)
                    else:
                        part.notes.append((start, pitch, duration, velocity))
                        part.lyrics.append(_lyric(el))
                        idx = len(part.notes) - 1
                    if "start" in ties:
                        tied[pitch] = idx
                if not is_chord:
                    last_start = position
                    position += duration
            measure_end = max(measure_end, position)
        measure_end = max(measure_end, position)
    return part, meter


def _lyric(note: ET.Element) -> str:
    lyrics = _children(note, "lyric")
    if not lyrics:
        return ""
    chosen = next((ly for ly in lyrics if (ly.get("number") or "1") == "1"), lyrics[0])
    return " ".join(_text(t) for t in _children(chosen, "text"))[:100]
