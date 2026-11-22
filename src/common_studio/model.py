"""The core model: works, arrangements and parts on a beat grid.

Beats and durations are exact fractions of a beat (``fractions.Fraction``), so a score never depends on
floating-point rounding and two equal scores are equal bit for bit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Optional, Union

from .recording_id import SLUG, arrangement_id

BeatLike = Union[Fraction, int, str]


def as_beat(value: BeatLike) -> Fraction:
    """Read a beat position or duration as an exact fraction.

    Floats are refused on purpose: ``0.1`` is not a tenth of a beat, and a score that silently rounds cannot be
    hashed or diffed.
    """
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("beats are exact: give an int, a Fraction or a string such as '3/2', not a float")
    return Fraction(value)


@dataclass(frozen=True, order=True)
class Note:
    """One note on the beat grid.

    ``beat`` is where it starts, in beats from the start of the part. ``pitch`` and ``velocity`` use the MIDI
    ranges: pitch 0 to 127, velocity 1 to 127.
    """

    beat: Fraction
    pitch: int
    duration: Fraction
    velocity: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "beat", as_beat(self.beat))
        object.__setattr__(self, "duration", as_beat(self.duration))
        if self.beat < 0:
            raise ValueError("a note cannot start before beat 0")
        if self.duration <= 0:
            raise ValueError("a note needs a duration greater than zero")
        if isinstance(self.pitch, bool) or not isinstance(self.pitch, int) or not 0 <= self.pitch <= 127:
            raise ValueError("pitch is a whole number from 0 to 127")
        if isinstance(self.velocity, bool) or not isinstance(self.velocity, int) or not 1 <= self.velocity <= 127:
            raise ValueError("velocity is a whole number from 1 to 127")


@dataclass(frozen=True)
class BeatGrid:
    """The grid a part sits on: how many beats make a bar, and the finest division of a beat.

    ``subdivision`` is how many equal steps a beat is cut into (4 means sixteenth notes when a beat is a quarter).
    It tells tools where notes are expected to fall; the notes themselves are exact fractions and are not forced
    onto it.
    """

    beats_per_bar: int = 4
    subdivision: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.beats_per_bar, int) or self.beats_per_bar < 1:
            raise ValueError("beats_per_bar is a whole number of at least 1")
        if not isinstance(self.subdivision, int) or self.subdivision < 1:
            raise ValueError("subdivision is a whole number of at least 1")

    def bar_of(self, beat: BeatLike) -> int:
        """The 1-based bar a beat falls in."""
        return int(as_beat(beat) // self.beats_per_bar) + 1

    def on_grid(self, beat: BeatLike) -> bool:
        """True when a beat position lands exactly on a subdivision."""
        return (as_beat(beat) * self.subdivision).denominator == 1


@dataclass(frozen=True)
class Part:
    """One part of an arrangement: notes on the beat grid, with optional lyrics and a sound.

    ``lyrics`` is one syllable or word per note, in note order, or ``None`` when there is nothing to sing.
    ``sections`` is how many sections the part plays through. ``voice`` and ``kit`` name the sound that will play
    the part; both are optional.
    """

    name: str
    notes: tuple[Note, ...] = ()
    lyrics: Optional[tuple[str, ...]] = None
    sections: int = 1
    voice: Optional[str] = None
    kit: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("a part needs a name")
        object.__setattr__(self, "notes", tuple(self.notes))
        if self.lyrics is not None:
            object.__setattr__(self, "lyrics", tuple(self.lyrics))
            if len(self.lyrics) != len(self.notes):
                raise ValueError("lyrics give one syllable or word per note")
        if isinstance(self.sections, bool) or not isinstance(self.sections, int) or self.sections < 1:
            raise ValueError("sections is a whole number of at least 1")
        for note in self.notes:
            if not isinstance(note, Note):
                raise TypeError("a part holds Note values")

    @property
    def length(self) -> Fraction:
        """Beats from the start of the part to the end of its last note."""
        return max((n.beat + n.duration for n in self.notes), default=Fraction(0))


@dataclass(frozen=True)
class Work:
    """A composition. It carries only what the core needs to name it."""

    id: str
    title: str

    def __post_init__(self) -> None:
        if not SLUG.fullmatch(self.id or ""):
            raise ValueError("a work id is lowercase letters and digits with single hyphens between groups")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("a work needs a title")


@dataclass(frozen=True)
class Waiver:
    """A recorded decision to go ahead despite a blocking finding of one check.

    ``reason`` is a written reason and is required. ``bars`` limits the waiver to those bars; empty means every bar
    of the check. A waiver is score metadata: it is kept with the arrangement but is not part of the score hash.
    """

    check: str
    reason: str
    bars: tuple[int, ...] = ()
    by: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.check, str) or not self.check.strip():
            raise ValueError("a waiver names the check it waives")
        if not isinstance(self.reason, str) or len(self.reason.strip()) < 10:
            raise ValueError("a waiver needs a written reason of at least 10 characters")
        object.__setattr__(self, "reason", self.reason.strip())
        bars = tuple(self.bars)
        if any(isinstance(b, bool) or not isinstance(b, int) or b < 1 for b in bars):
            raise ValueError("waiver bars are whole bar numbers from 1")
        object.__setattr__(self, "bars", tuple(sorted(set(bars))))

    def covers(self, check: str, bar: int) -> bool:
        return self.check == check and (not self.bars or bar in self.bars)

    def to_dict(self) -> dict:
        return {"check": self.check, "reason": self.reason, "bars": list(self.bars), "by": self.by}


@dataclass(frozen=True)
class Arrangement:
    """One arrangement of a work in a style, identified as ``work--style``."""

    work: str
    style: str
    parts: tuple[Part, ...] = ()
    grid: BeatGrid = field(default_factory=BeatGrid)
    waivers: tuple[Waiver, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", tuple(self.parts))
        object.__setattr__(self, "waivers", tuple(self.waivers))
        # arrangement_id checks both names against the grammar.
        arrangement_id(self.work, self.style)
        names = [p.name for p in self.parts]
        if len(set(names)) != len(names):
            raise ValueError("part names are unique within an arrangement")

    @property
    def id(self) -> str:
        return arrangement_id(self.work, self.style)


ArrangementGenerator = Callable[[Work], Arrangement]
"""An arrangement is built by a generator: a function that takes a work and returns an arrangement.

A generator module exposes one such function, so tools can discover and run arrangements without knowing how each
one builds its parts.
"""
