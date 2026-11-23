"""Authored fixtures for the checkers: each check has a positive (flagged) and a negative (clean) arrangement."""

from __future__ import annotations

from .model import Arrangement, BeatGrid, Note, Part


def _arr(*parts: Part) -> Arrangement:
    return Arrangement("check-fixture", "plain", parts, BeatGrid(4, 4))


def _part(name: str, pitches: list[int], start: int = 0, dur: int = 1, **kw) -> Part:
    return Part(name, tuple(Note(start + i * dur, p, dur, 80) for i, p in enumerate(pitches)), **kw)


def clash() -> Arrangement:
    """Bar 2 has C against C-sharp."""
    return _arr(_part("lead", [60, 64, 67, 64, 72, 71, 67, 64]), _part("pad", [48, 52, 55, 52, 61, 55, 55, 52]))


def clash_corrected() -> Arrangement:
    return _arr(_part("lead", [60, 64, 67, 64, 72, 71, 67, 64]), _part("pad", [48, 52, 55, 52, 64, 55, 55, 52]))


def parallel_fifths() -> Arrangement:
    """Upper and lower part move up together a fifth apart, arriving in bar 2."""
    return _arr(_part("upper", [67, 69, 71, 72, 74]), _part("lower", [60, 62, 64, 65, 67]))


def parallel_octaves() -> Arrangement:
    return _arr(_part("upper", [72, 74, 76, 77, 79]), _part("lower", [60, 62, 64, 65, 67]))


def voice_leading_clean() -> Arrangement:
    """Contrary motion, no perfect parallels."""
    return _arr(_part("upper", [72, 74, 76, 77, 79]), _part("lower", [64, 62, 60, 59, 57]))


def out_of_range() -> Arrangement:
    """A flute note at 40 in bar 2."""
    return _arr(_part("solo", [72, 74, 76, 77, 40, 72], voice="flute"))


def in_range() -> Arrangement:
    return _arr(_part("solo", [72, 74, 76, 77, 72, 72], voice="flute"))


def poor_voicing() -> Arrangement:
    """Bar 2: 48, 55 and 79 leave a two-octave hole above the lowest note."""
    return _arr(_part("low", [48] * 5, dur=1), _part("mid", [55] * 5), _part("high", [64, 64, 64, 64, 79]))


def good_voicing() -> Arrangement:
    return _arr(_part("low", [48] * 5), _part("mid", [55] * 5), _part("high", [64] * 5))
