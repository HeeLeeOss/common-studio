"""Authored fixtures: a small original melody and an arrangement of it. Nothing here comes from any other source."""

from fractions import Fraction

from common_studio import Arrangement, BeatGrid, Note, Part, Work

WORK = Work("fixture-etude", "Fixture Etude")


def melody() -> Part:
    pitches = [60, 62, 64, 65, 67, 65, 64, 62]
    notes = tuple(Note(Fraction(i), p, Fraction(1), 80) for i, p in enumerate(pitches))
    return Part("melody", notes, lyrics=("la",) * 8, voice="choir", sections=2)


def bass() -> Part:
    notes = (Note(0, 36, 2, 70), Note(Fraction(2), 43, Fraction(3, 2), 72), Note(Fraction(7, 2), 36, Fraction(1, 2), 64))
    return Part("bass", notes, kit="upright")


def arrangement(style: str = "plain") -> Arrangement:
    return Arrangement(WORK.id, style, (bass(), melody()), BeatGrid(4, 4))


def generate(work: Work) -> Arrangement:
    """A generator in the sense of ArrangementGenerator."""
    return Arrangement(work.id, "plain", (melody(),))
