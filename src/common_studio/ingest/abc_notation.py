"""ABC notation reader.

Reads the first tune of an ABC file: the ``T:`` title, ``M:`` meter, ``L:`` unit note length, ``K:`` key (with modes
and explicit accidentals), ``V:`` voices, ``w:`` lyric lines, and in the body notes, rests, chords, ties, broken
rhythm, tuplets, multi-bar rests and dynamics. Grace notes, decorations, chord symbols and annotations are skipped.
Repeats are read once: an arrangement says how many sections a part plays through, not the file.

Written new for Common Studio from the published ABC standard, read as a reference. Released under the Unlicense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional

from .common import DEFAULT_VELOCITY, ParseError, RawPart, Score, Source, as_text, build_score, guarded

FORMAT = "abc"

_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_FIFTHS = {"F": -1, "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5}
_MODE_SHIFT = {"": 0, "maj": 0, "ion": 0, "mix": -1, "dor": -2, "m": -3, "min": -3, "aeo": -3, "phr": -4,
               "loc": -5, "lyd": 1}
_SHARP_ORDER = "FCGDAEB"
_DYNAMICS = {"ppp": 25, "pp": 40, "p": 55, "mp": 70, "mf": 85, "f": 100, "ff": 115, "fff": 127}
_FIELD_LINE = re.compile(r"^([A-Za-z]):(.*)$")
_DECORATION_CHARS = set(".~HLMOPSTuv")
_BODY_FIELDS = set("IKLMNPQRSTUVWXwmrs")  # field letters that may stand on their own line inside a tune body
_MAX_DIGITS = 6


def _key_alterations(text: str) -> dict[str, int]:
    """Per-letter alterations for a ``K:`` value such as ``D``, ``Ebm``, ``A dor`` or ``D exp ^f _b``."""
    words = text.strip().split()
    alter = {letter: 0 for letter in _STEP}
    if not words or words[0].lower() in ("none", "hp"):
        return alter
    m = re.match(r"^([A-Ga-g])([#b]?)(.*)$", words[0])
    rest = words[1:]
    if m:
        tonic, sign, mode_text = m.group(1).upper(), m.group(2), m.group(3)
        if not mode_text and rest and re.match(r"^[A-Za-z]{1,10}$", rest[0]) and rest[0][:3].lower() in _MODE_SHIFT:
            mode_text, rest = rest[0], rest[1:]
        mode = mode_text.lower()
        key = mode if mode in ("m",) else mode[:3]
        if key not in _MODE_SHIFT:
            key = ""
        fifths = _FIFTHS[tonic] + (7 if sign == "#" else -7 if sign == "b" else 0) + _MODE_SHIFT[key]
        if not -7 <= fifths <= 7:
            raise ParseError(FORMAT, f"key {words[0]!r} needs more than seven sharps or flats")
        if fifths > 0:
            for letter in _SHARP_ORDER[:fifths]:
                alter[letter] = 1
        elif fifths < 0:
            for letter in _SHARP_ORDER[::-1][:-fifths]:
                alter[letter] = -1
    else:
        rest = words
    for word in rest:
        e = re.match(r"^(\^\^|\^|__|_|=)([A-Ga-g])$", word)
        if e:
            alter[e.group(2).upper()] = {"^^": 2, "^": 1, "__": -2, "_": -1, "=": 0}[e.group(1)]
    return alter


def _meter(text: str) -> Optional[tuple[int, int]]:
    t = text.strip().replace(" ", "")
    if t == "C":
        return (4, 4)
    if t == "C|":
        return (2, 2)
    m = re.match(r"^\(?([0-9+]{1,12})\)?/([0-9]{1,3})$", t)
    if not m:
        return None
    try:
        num = sum(int(x) for x in m.group(1).split("+") if x)
    except ValueError:
        return None
    den = int(m.group(2))
    if num < 1 or den < 1:
        return None
    return (num, den)


def _fraction(text: str) -> Optional[Fraction]:
    m = re.match(r"^\s*([0-9]{1,4})\s*/\s*([0-9]{1,4})\s*$", text)
    if not m or int(m.group(2)) == 0 or int(m.group(1)) == 0:
        return None
    return Fraction(int(m.group(1)), int(m.group(2)))


@dataclass
class _Voice:
    part: RawPart
    time: Fraction = Fraction(0)
    bar_alter: dict[tuple[str, int], int] = field(default_factory=dict)
    tied: dict[int, int] = field(default_factory=dict)  # pitch -> note index waiting for a tie
    last_event: list[int] = field(default_factory=list)  # note indices of the last note or chord
    last_length: Fraction = Fraction(0)  # length of the last event, notes or rest
    last_was_rest: bool = False
    pending_broken: Fraction = Fraction(1)
    tuplet_left: int = 0
    tuplet_factor: Fraction = Fraction(1)
    velocity: int = DEFAULT_VELOCITY
    slots: list[int] = field(default_factory=list)  # index of the first note of each sung event
    lyric_cursor: int = 0


class _Tune:
    def __init__(self) -> None:
        self.title: Optional[str] = None
        self.meter: Optional[tuple[int, int]] = None
        self.unit: Optional[Fraction] = None
        self.key: dict[str, int] = {letter: 0 for letter in _STEP}
        self.voices: dict[str, _Voice] = {}
        self.voice_names: dict[str, str] = {}
        self.current: Optional[_Voice] = None

    # -- units -------------------------------------------------------------------------------------------------

    def unit_length(self) -> Fraction:
        if self.unit is not None:
            return self.unit
        num, den = self.meter or (4, 4)
        return Fraction(1, 16) if Fraction(num, den) < Fraction(3, 4) else Fraction(1, 8)

    def beats(self, whole: Fraction) -> Fraction:
        """A length in whole notes as beats of the meter."""
        return whole * (self.meter or (4, 4))[1]

    def bar_beats(self) -> Fraction:
        return Fraction((self.meter or (4, 4))[0])

    # -- voices ------------------------------------------------------------------------------------------------

    def voice(self, ident: str = "") -> _Voice:
        if ident not in self.voices:
            if len(self.voices) >= 64:
                raise ParseError(FORMAT, "too many voices")
            name = self.voice_names.get(ident) or (ident if ident else "melody")
            self.voices[ident] = _Voice(RawPart(name))
        return self.voices[ident]

    def set_voice(self, text: str) -> None:
        words = text.strip().split(None, 1)
        ident = words[0][:40] if words else ""
        m = re.search(r'(?:name|nm)\s*=\s*"([^"]*)"', text)
        if m and m.group(1).strip():
            self.voice_names[ident] = m.group(1).strip()[:60]
            if ident in self.voices:
                self.voices[ident].part.name = self.voice_names[ident]
        self.current = self.voice(ident)

    def field(self, letter: str, value: str, in_body: bool) -> None:
        if letter == "T" and self.title is None and value.strip():
            self.title = value.strip()
        elif letter == "M":
            meter = _meter(value)
            if value.strip().lower() == "none":
                meter = None
            if meter is not None:
                self.meter = meter
        elif letter == "L":
            unit = _fraction(value)
            if unit is not None:
                self.unit = unit
        elif letter == "K":
            self.key = _key_alterations(value)
        elif letter == "V":
            self.set_voice(value)
        elif letter == "w" and in_body:
            self.lyrics(value)

    # -- lyrics ------------------------------------------------------------------------------------------------

    def lyrics(self, text: str) -> None:
        v = self.current or self.voice()
        text = text.replace("\\-", "\x00")
        tokens = re.findall(r"[^\s\-_*|]+-?|-|_|\*|\|", text)
        for token in tokens:
            if token == "|":
                continue
            if token == "-":
                continue
            if v.lyric_cursor >= len(v.slots):
                break
            if token not in ("_", "*"):
                syllable = token.rstrip("-").replace("~", " ").replace("\x00", "-")
                v.part.lyrics[v.slots[v.lyric_cursor]] = syllable
            v.lyric_cursor += 1

    # -- body --------------------------------------------------------------------------------------------------

    def body_line(self, line: str) -> None:
        v = self.current or self.voice()
        self.current = v
        i, n = 0, len(line)
        while i < n:
            c = line[i]
            if c in " \t`\\$":
                i += 1
            elif c == "%":
                break
            elif c == '"':
                end = line.find('"', i + 1)
                i = n if end < 0 else end + 1
            elif c == "!" or c == "+":
                end = line.find(c, i + 1)
                if end < 0:
                    i = n
                else:
                    word = line[i + 1:end]
                    if word in _DYNAMICS:
                        v.velocity = _DYNAMICS[word]
                    i = end + 1
            elif c == "{":
                end = line.find("}", i + 1)
                i = n if end < 0 else end + 1
            elif c in _DECORATION_CHARS:
                i += 1
            elif c == "[" and i + 2 < n and line[i + 1].isalpha() and line[i + 2] == ":":
                end = line.find("]", i)
                end = n if end < 0 else end
                self.field(line[i + 1], line[i + 3:end], True)
                v = self.current or v
                i = end + 1
            elif c == "[" and i + 1 < n and line[i + 1].isdigit():
                i += 2
            elif c in "|:[]":
                if c == "[" and i + 1 < n and line[i + 1] in "^_=ABCDEFGabcdefg":
                    i = self.chord(v, line, i)
                else:
                    v.bar_alter.clear()
                    i += 1
            elif c == "(":
                i = self.tuplet(v, line, i)
            elif c == ")":
                i += 1
            elif c == "-":
                for idx in v.last_event:
                    v.tied[v.part.notes[idx][1]] = idx
                i += 1
            elif c in "<>":
                j = i
                while j < n and line[j] == c and j - i < 3:
                    j += 1
                self.broken(v, c, j - i)
                i = j
            elif c in "zx":
                length, i = self.length(line, i + 1)
                self.rest(v, length)
            elif c in "ZX":
                count, i = self.digits(line, i + 1)
                bars = count if count is not None else 1
                self.advance_rest(v, self.bar_beats() * bars)
            elif c in "^_=" or c.upper() in _STEP:
                parsed = self.note(v, line, i)
                if parsed is None:
                    i += 1
                    continue
                pitch, length, i = parsed
                self.event(v, [pitch], length)
            else:
                i += 1

    @staticmethod
    def digits(line: str, i: int) -> tuple[Optional[int], int]:
        j = i
        while j < len(line) and line[j].isdigit():
            j += 1
        if j == i:
            return None, i
        if j - i > _MAX_DIGITS:
            raise ParseError(FORMAT, "a number in the tune is too long")
        return int(line[i:j]), j

    def length(self, line: str, i: int) -> tuple[Fraction, int]:
        num, i = self.digits(line, i)
        value = Fraction(num if num is not None else 1)
        while i < len(line) and line[i] == "/":
            i += 1
            den, i = self.digits(line, i)
            if den == 0:
                raise ParseError(FORMAT, "a note length divides by zero")
            value /= den if den is not None else 2
        if value <= 0:
            raise ParseError(FORMAT, "a note length must be greater than zero")
        return value, i

    def note(self, v: _Voice, line: str, i: int) -> Optional[tuple[int, Fraction, int]]:
        m = re.compile(r"(\^\^|\^|__|_|=)?([A-Ga-g])([',]*)").match(line, i)
        if not m:
            return None
        acc, letter, marks = m.groups()
        octave = (1 if letter.islower() else 0) + marks.count("'") - marks.count(",")
        upper = letter.upper()
        if acc:
            alteration = {"^^": 2, "^": 1, "__": -2, "_": -1, "=": 0}[acc]
            v.bar_alter[(upper, octave)] = alteration
        else:
            alteration = v.bar_alter.get((upper, octave), self.key[upper])
        pitch = 60 + 12 * octave + _STEP[upper] + alteration
        length, j = self.length(line, m.end())
        return pitch, length, j

    def chord(self, v: _Voice, line: str, i: int) -> int:
        end = line.find("]", i)
        if end < 0:
            raise ParseError(FORMAT, "a chord is not closed with ]")
        inner = line[i + 1:end]
        pitches: list[int] = []
        first_length: Optional[Fraction] = None
        j = 0
        while j < len(inner):
            parsed = self.note(v, inner, j)
            if parsed is None:
                j += 1
                continue
            pitch, length, j = parsed
            if pitch not in pitches:
                pitches.append(pitch)
            if first_length is None:
                first_length = length
            while j < len(inner) and inner[j] == "-":
                j += 1
        outer, k = self.length(line, end + 1)
        if pitches:
            self.event(v, pitches, (first_length or Fraction(1)) * outer)
        return k

    def tuplet(self, v: _Voice, line: str, i: int) -> int:
        m = re.compile(r"\(([2-9])(?::([0-9]?)(?::([0-9]?))?)?").match(line, i)
        if not m:
            return i + 1  # a slur
        p = int(m.group(1))
        compound = (self.meter or (4, 4))[0] % 3 == 0 and (self.meter or (4, 4))[0] > 3
        default_q = {2: 3, 3: 2, 4: 3, 6: 2, 8: 3}.get(p, 3 if compound else 2)
        q = int(m.group(2)) if m.group(2) else default_q
        r = int(m.group(3)) if m.group(3) else p
        if q == 0:
            raise ParseError(FORMAT, "a tuplet cannot last zero notes")
        v.tuplet_factor = Fraction(q, p)
        v.tuplet_left = r
        return m.end()

    def scaled(self, v: _Voice, length: Fraction) -> Fraction:
        beats = self.beats(length * self.unit_length()) * v.pending_broken
        v.pending_broken = Fraction(1)
        if v.tuplet_left > 0:
            beats *= v.tuplet_factor
            v.tuplet_left -= 1
        return beats

    def event(self, v: _Voice, pitches: list[int], length: Fraction) -> None:
        beats = self.scaled(v, length)
        indices = []
        first_new: Optional[int] = None
        tied = v.tied
        v.tied = {}
        for pitch in pitches:
            if pitch in tied:
                idx = tied[pitch]
                b, p, d, vel = v.part.notes[idx]
                v.part.notes[idx] = (b, p, d + beats, vel)
                indices.append(idx)
            else:
                v.part.notes.append((v.time, pitch, beats, v.velocity))
                v.part.lyrics.append("")
                idx = len(v.part.notes) - 1
                indices.append(idx)
                if first_new is None:
                    first_new = idx
        if first_new is not None:
            v.slots.append(first_new)
        v.last_event = indices
        v.last_length = beats
        v.last_was_rest = False
        v.time += beats

    def rest(self, v: _Voice, length: Fraction) -> None:
        beats = self.scaled(v, length)
        self.advance_rest(v, beats)

    def advance_rest(self, v: _Voice, beats: Fraction) -> None:
        v.tied = {}
        v.last_event = []
        v.last_length = beats
        v.last_was_rest = True
        v.time += beats

    def broken(self, v: _Voice, sign: str, count: int) -> None:
        shorter = Fraction(1, 2 ** count)
        longer = 2 - shorter
        first, second = (longer, shorter) if sign == ">" else (shorter, longer)
        old = v.last_length
        if old <= 0:
            return
        new = old * first
        for idx in v.last_event:
            b, p, d, vel = v.part.notes[idx]
            v.part.notes[idx] = (b, p, d - old + new, vel)
        v.time += new - old
        v.last_length = new
        v.pending_broken = second


def parse_abc(data: Source, *, work_id: Optional[str] = None, style: str = "source") -> Score:
    """Read the first tune of an ABC file into the core model."""
    return guarded(FORMAT, lambda: _parse(as_text(FORMAT, data), work_id, style))


def _parse(text: str, work_id: Optional[str], style: str) -> Score:
    tune = _Tune()
    in_body = False
    seen_tune = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("%"):
            continue
        fm = _FIELD_LINE.match(line)
        if fm and (not in_body or fm.group(1) in _BODY_FIELDS):
            letter, value = fm.group(1), fm.group(2)
            value = value.split("%", 1)[0]
            if letter == "X":
                if seen_tune and (in_body or tune.voices):
                    break  # the next tune starts: read only the first
                seen_tune = True
                continue
            tune.field(letter, value, in_body)
            if letter == "K" and not in_body:
                in_body = True
            continue
        if not line.strip():
            if in_body and any(v.part.notes for v in tune.voices.values()):
                break  # a blank line ends the tune
            continue
        if in_body:
            tune.body_line(line)
    if not in_body:
        raise ParseError(FORMAT, "no K: field, so no tune body was found")
    parts = [v.part for v in tune.voices.values()]
    return build_score(FORMAT, tune.title, parts, tune.meter or (4, 4), work_id=work_id, style=style)
