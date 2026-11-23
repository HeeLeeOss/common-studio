"""Standard MIDI File reader (formats 0 and 1, ticks per quarter note).

Reads the header, then each track's events: note on and note off (a note on with velocity 0 is a note off), running
status, the track-name, lyric and time-signature meta events, and system-exclusive events, which are skipped. Each
track and channel that plays notes becomes one part. The title is the name of the first track, as is usual for a
format 1 file whose first track carries tempo and meter. Files timed in SMPTE frames, and format 2 files, are
refused.

Written new for Common Studio from the published Standard MIDI File format, read as a reference. Released under the
Unlicense.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from .common import MAX_NOTES, ParseError, RawPart, Score, Source, as_bytes, build_score, guarded

FORMAT = "midi"

# How many data bytes follow each channel-message status (by the high nibble).
_DATA_BYTES = {0x80: 2, 0x90: 2, 0xA0: 2, 0xB0: 2, 0xC0: 1, 0xD0: 1, 0xE0: 2}


class _Reader:
    def __init__(self, data: bytes, start: int = 0, end: Optional[int] = None) -> None:
        self.data = data
        self.pos = start
        self.end = len(data) if end is None else end

    def need(self, n: int) -> None:
        if n < 0 or self.pos + n > self.end:
            raise ParseError(FORMAT, f"unexpected end of data at byte {self.pos}")

    def byte(self) -> int:
        self.need(1)
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, n: int) -> bytes:
        self.need(n)
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def varlen(self) -> int:
        value = 0
        for _ in range(4):
            b = self.byte()
            value = (value << 7) | (b & 0x7F)
            if not b & 0x80:
                return value
        raise ParseError(FORMAT, "a variable-length number is longer than four bytes")


def _text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw.decode("latin-1").strip()


def parse_midi(data: Source, *, work_id: Optional[str] = None, style: str = "source") -> Score:
    """Read a Standard MIDI File into the core model."""
    if isinstance(data, str):
        raise ParseError(FORMAT, "a MIDI file is bytes, not text")
    return guarded(FORMAT, lambda: _parse(as_bytes(FORMAT, data), work_id, style))


def _parse(data: bytes, work_id: Optional[str], style: str) -> Score:
    r = _Reader(data)
    if r.take(4) != b"MThd":
        raise ParseError(FORMAT, "the file does not start with an MThd header")
    header_length = r.u32()
    if header_length < 6:
        raise ParseError(FORMAT, "the header is shorter than six bytes")
    header_end = r.pos + header_length
    fmt, ntracks, division = r.u16(), r.u16(), r.u16()
    r.need(header_end - r.pos)
    r.pos = header_end
    if fmt not in (0, 1):
        raise ParseError(FORMAT, f"format {fmt} is not read; only formats 0 and 1")
    if division & 0x8000:
        raise ParseError(FORMAT, "SMPTE frame timing is not read; only ticks per quarter note")
    if division == 0:
        raise ParseError(FORMAT, "the header gives zero ticks per quarter note")

    title: Optional[str] = None
    meter: Optional[tuple[int, int]] = None
    parts: list[RawPart] = []
    total = 0
    track_no = 0
    while track_no < ntracks and r.pos < len(data):
        chunk = r.take(4)
        length = r.u32()
        r.need(length)
        start, r.pos = r.pos, r.pos + length
        if chunk != b"MTrk":
            continue  # unknown chunks are skipped, as the format asks
        track_no += 1
        name, track_meter, track_parts = _read_track(data, start, start + length, track_no)
        if track_no == 1 and name:
            title = name
        meter = meter or track_meter
        for part in track_parts:
            total += len(part.notes)
            if total > MAX_NOTES:
                raise ParseError(FORMAT, f"the file holds more than {MAX_NOTES} notes")
        parts.extend(track_parts)
    if track_no == 0:
        raise ParseError(FORMAT, "the file has no MTrk chunk")

    num, den = meter or (4, 4)
    # Ticks count quarter notes; the beat is the unit of the time signature's lower number.
    scale = Fraction(den, 4 * division)
    for part in parts:
        part.notes = [(b * scale, p, d * scale, v) for b, p, d, v in part.notes]
    return build_score(FORMAT, title, parts, (num, den), work_id=work_id, style=style)


def _read_track(data: bytes, start: int, end: int, track_no: int) -> tuple[Optional[str], Optional[tuple[int, int]], list[RawPart]]:
    r = _Reader(data, start, end)
    tick = 0
    status = 0
    name: Optional[str] = None
    meter: Optional[tuple[int, int]] = None
    open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}  # (channel, pitch) -> [(start tick, velocity)]
    notes: dict[int, list[tuple[int, int, int, int]]] = {}  # channel -> [(start, pitch, length, velocity)]
    lyrics: dict[int, str] = {}  # tick -> lyric
    count = 0
    while r.pos < r.end:
        tick += r.varlen()
        first = r.byte()
        if first == 0xFF:
            kind = r.byte()
            payload = r.take(r.varlen())
            if kind == 0x2F:
                break
            if kind == 0x03 and name is None:
                name = _text(payload)[:60] or None
            elif kind == 0x05:
                lyrics.setdefault(tick, _text(payload)[:100])
            elif kind == 0x58 and len(payload) >= 2 and meter is None:
                if payload[0] >= 1 and payload[1] <= 6:
                    meter = (payload[0], 2 ** payload[1])
            continue
        if first in (0xF0, 0xF7):
            r.take(r.varlen())
            continue
        if first & 0x80:
            if first >= 0xF0:
                raise ParseError(FORMAT, f"system message 0x{first:02X} is not allowed in a file")
            status = first
            data_bytes = [r.byte() for _ in range(_DATA_BYTES[status & 0xF0])]
        else:
            if not status:
                raise ParseError(FORMAT, "running status is used before any status byte")
            data_bytes = [first] + [r.byte() for _ in range(_DATA_BYTES[status & 0xF0] - 1)]
        if any(b & 0x80 for b in data_bytes):
            raise ParseError(FORMAT, "a data byte has its top bit set")
        kind, channel = status & 0xF0, status & 0x0F
        if kind == 0x90 and data_bytes[1] > 0:
            open_notes.setdefault((channel, data_bytes[0]), []).append((tick, data_bytes[1]))
        elif kind == 0x80 or (kind == 0x90 and data_bytes[1] == 0):
            waiting = open_notes.get((channel, data_bytes[0]))
            if waiting:
                begin, velocity = waiting.pop(0)
                if tick > begin:
                    notes.setdefault(channel, []).append((begin, data_bytes[0], tick - begin, velocity))
                    count += 1
                    if count > MAX_NOTES:
                        raise ParseError(FORMAT, f"a track holds more than {MAX_NOTES} notes")
    for (channel, pitch), waiting in open_notes.items():  # notes never released end with the track
        for begin, velocity in waiting:
            if tick > begin:
                notes.setdefault(channel, []).append((begin, pitch, tick - begin, velocity))

    parts = []
    channels = sorted(notes)
    for channel in channels:
        base = name or f"track {track_no}"
        part = RawPart(base if len(channels) == 1 else f"{base} channel {channel + 1}")
        used: set[int] = set()
        for begin, pitch, length, velocity in sorted(notes[channel]):
            part.notes.append((Fraction(begin), pitch, Fraction(length), velocity))
            if begin in lyrics and begin not in used:
                part.lyrics.append(lyrics[begin])
                used.add(begin)
            else:
                part.lyrics.append("")
        parts.append(part)
    return name, meter, parts
