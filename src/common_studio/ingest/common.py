"""Shared pieces of the four parsers: the error type, input limits and the step from raw notes to the core model.

Each parser reads its format into a list of ``RawPart`` values, with beats measured in the unit of the time
signature's lower number (a 6/8 tune has six beats a bar, each an eighth note). ``build_score`` then turns them into
``Work``, ``Arrangement`` and ``Part`` values on a ``BeatGrid``.

A parser may only fail with ``ParseError``. Anything malformed, too large or out of the model's ranges is reported
that way, so a caller can refuse one file and keep going.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from math import lcm
from typing import Callable, Optional, TypeVar, Union

from ..model import Arrangement, BeatGrid, Note, Part, Work

# Limits on what one file may hold. They keep a hostile or broken file from using unbounded memory or time.
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_NOTES = 200_000
MAX_PARTS = 256
MAX_DENOMINATOR = 1 << 20
MAX_BEAT = 1 << 24

DEFAULT_VELOCITY = 80
DEFAULT_STYLE = "source"


class ParseError(ValueError):
    """The input is not a well-formed file of the format, or holds something the core model cannot."""

    def __init__(self, fmt: str, message: str) -> None:
        super().__init__(f"{fmt}: {message}")
        self.format = fmt
        self.reason = message


@dataclass
class RawPart:
    """A part as a parser collects it, before it is checked by the core model."""

    name: str
    notes: list[tuple[Fraction, int, Fraction, int]] = field(default_factory=list)  # beat, pitch, duration, velocity
    lyrics: list[str] = field(default_factory=list)  # one per note, "" when a note has no syllable


@dataclass(frozen=True)
class Score:
    """What a parser returns: the work, its arrangement and the meter read from the file."""

    work: Work
    arrangement: Arrangement
    format: str
    meter: tuple[int, int]


Source = Union[bytes, bytearray, str]


def as_bytes(fmt: str, data: Source) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, (bytes, bytearray)):
        raise ParseError(fmt, "input is bytes or text")
    if len(data) > MAX_INPUT_BYTES:
        raise ParseError(fmt, f"input is larger than {MAX_INPUT_BYTES} bytes")
    return bytes(data)


def as_text(fmt: str, data: Source) -> str:
    raw = as_bytes(fmt, data)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Older text files are often Latin-1; every byte decodes, so this cannot fail.
        return raw.decode("latin-1")


def slugify(text: str, fallback: str) -> str:
    """A slug for the recording-id grammar: lowercase ASCII letters and digits with single hyphens."""
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")[:64].strip("-")
    return slug or fallback


def clean_title(text: Optional[str], fallback: str) -> str:
    title = " ".join((text or "").split())[:200]
    return title or fallback


def unique_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for name in names:
        base = " ".join(name.split()) or "part"
        candidate = base
        n = seen.get(base, 0)
        while candidate in out:
            n += 1
            candidate = f"{base} {n + 1}"
        seen[base] = n
        out.append(candidate)
    return out


def check_value(fmt: str, value: Fraction, what: str) -> Fraction:
    if value.denominator > MAX_DENOMINATOR or abs(value) > MAX_BEAT:
        raise ParseError(fmt, f"{what} {value} is outside the supported range")
    return value


def build_score(
    fmt: str,
    title: Optional[str],
    parts: list[RawPart],
    meter: tuple[int, int],
    *,
    work_id: Optional[str] = None,
    style: str = DEFAULT_STYLE,
) -> Score:
    """Check the collected parts and build the core model from them."""
    num, den = meter
    if not (1 <= num <= 64) or den not in (1, 2, 4, 8, 16, 32, 64):
        num, den = 4, 4
    parts = [p for p in parts if p.notes]
    if not parts:
        raise ParseError(fmt, "the file holds no notes")
    if len(parts) > MAX_PARTS:
        raise ParseError(fmt, f"the file holds more than {MAX_PARTS} parts")
    if sum(len(p.notes) for p in parts) > MAX_NOTES:
        raise ParseError(fmt, f"the file holds more than {MAX_NOTES} notes")

    the_title = clean_title(title, "Untitled")
    wid = work_id if work_id is not None else slugify(the_title, "untitled")
    names = unique_names([p.name for p in parts])
    denominators = [1]
    built: list[Part] = []
    try:
        work = Work(wid, the_title)
        for raw, name in zip(parts, names):
            order = sorted(range(len(raw.notes)), key=lambda i: raw.notes[i])
            notes = []
            for i in order:
                beat, pitch, duration, velocity = raw.notes[i]
                check_value(fmt, beat, "beat")
                check_value(fmt, duration, "duration")
                notes.append(Note(beat, pitch, duration, velocity))
                denominators.extend((beat.denominator, duration.denominator))
            lyrics = None
            if any(raw.lyrics):
                lyrics = tuple(raw.lyrics[i] if i < len(raw.lyrics) else "" for i in order)
            built.append(Part(name, tuple(notes), lyrics=lyrics))
        subdivision = 1
        for d in set(denominators):
            subdivision = lcm(subdivision, d)
            if subdivision > MAX_DENOMINATOR:
                raise ParseError(fmt, "the rhythm needs a finer grid than is supported")
        grid = BeatGrid(num, subdivision)
        arrangement = Arrangement(work.id, style, tuple(built), grid)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ParseError):
            raise
        raise ParseError(fmt, str(exc)) from None
    return Score(work, arrangement, fmt, (num, den))


T = TypeVar("T")


def guarded(fmt: str, fn: Callable[[], T]) -> T:
    """Run a parser body, reporting every kind of malformed-input failure as ``ParseError``.

    Errors that come from bad input (a bad number, an index past the end, nesting that is too deep, a value the
    model refuses) are turned into ``ParseError``. Anything else is a bug in the parser and is left to surface.
    """
    try:
        return fn()
    except ParseError:
        raise
    except (ValueError, ArithmeticError, IndexError, KeyError, RecursionError, UnicodeError, MemoryError) as exc:
        raise ParseError(fmt, f"malformed input ({type(exc).__name__}: {exc})"[:300]) from None
