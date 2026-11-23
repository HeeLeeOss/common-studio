"""AC-03: one authored fixture per format parses into Work, Arrangement and Part on the beat grid."""

from fractions import Fraction as F

import pytest

from common_studio import Arrangement, BeatGrid, Part, Work
from common_studio.ingest import (
    EXTENSIONS, ParseError, detect_format, parse_abc, parse_lilypond, parse_midi, parse_musicxml,
)
from common_studio.ingest.fixture_evidence import fixture_bytes


def notes(part: Part) -> list[tuple]:
    return [(n.beat, n.pitch, n.duration) for n in part.notes]


def assert_model(score, work_id: str, title: str, grid: BeatGrid, part_names: list[str]) -> None:
    assert isinstance(score.work, Work) and score.work == Work(work_id, title)
    arr = score.arrangement
    assert isinstance(arr, Arrangement)
    assert arr.id == f"{work_id}--source"
    assert arr.grid == grid
    assert [p.name for p in arr.parts] == part_names
    for part in arr.parts:
        assert isinstance(part, Part)
        for n in part.notes:
            assert arr.grid.on_grid(n.beat), f"{part.name}: beat {n.beat} is off the grid"
            assert arr.grid.on_grid(n.beat + n.duration)


def test_abc_fixture_parses_onto_the_beat_grid():
    score = parse_abc(fixture_bytes("abc"))
    assert_model(score, "slate-roof-air", "Slate Roof Air", BeatGrid(3, 12), ["melody"])
    (melody,) = score.arrangement.parts
    # Key of D: f and c are sharp. e>d is broken rhythm; (3cBA is a triplet.
    assert notes(melody) == [
        (0, 69, 1), (1, 74, 1), (2, 78, 1),
        (3, 76, F(3, 4)), (F(15, 4), 74, F(1, 4)), (4, 73, 1), (5, 69, 1),
        (6, 71, 1), (7, 73, F(1, 3)), (F(22, 3), 71, F(1, 3)), (F(23, 3), 69, F(1, 3)), (8, 67, 1),
        (9, 66, 3),
    ]
    assert {n.velocity for n in melody.notes} == {85}  # !mf!
    assert melody.lyrics == ("Rain", "on", "the", "slate", "roof,", "ti", "ny", "drums", "a", "cross", "the",
                             "still", "night.")
    assert score.arrangement.grid.bar_of(9) == 4


def test_musicxml_fixture_parses_onto_the_beat_grid():
    score = parse_musicxml(fixture_bytes("musicxml"))
    assert_model(score, "quarry-lane-hymn", "Quarry Lane Hymn", BeatGrid(4, 1), ["Flute"])
    (flute,) = score.arrangement.parts
    # A chord in bar 2, a tie across the bar line into bar 3, a rest, a flat, and a second voice after <backup>.
    assert notes(flute) == [
        (0, 72, 1), (1, 76, 1), (2, 79, 2), (4, 77, 2), (4, 81, 2), (6, 76, 3), (9, 74, 1), (11, 70, 1),
        (12, 67, 4), (12, 72, 4),
    ]
    assert flute.lyrics is None


def test_midi_fixture_parses_onto_the_beat_grid():
    score = parse_midi(fixture_bytes("midi"))
    assert_model(score, "mill-wheel-turning", "Mill Wheel Turning", BeatGrid(4, 1), ["Melody", "Bass"])
    melody, bass = score.arrangement.parts
    assert notes(melody) == [(0, 67, 1), (1, 69, 1), (2, 71, 1), (3, 74, 1), (4, 71, 1), (5, 69, 1), (6, 67, 2)]
    assert {n.velocity for n in melody.notes} == {90}
    assert notes(bass) == [(0, 43, 4), (4, 50, 2), (6, 43, 2)]
    assert {n.velocity for n in bass.notes} == {70}


def test_lilypond_fixture_parses_onto_the_beat_grid():
    score = parse_lilypond(fixture_bytes("lilypond"))
    assert_model(score, "lantern-path", "Lantern Path", BeatGrid(6, 1), ["upper", "lower"])
    assert score.meter == (6, 8)
    upper, lower = score.arrangement.parts
    # 6/8: a beat is an eighth note. Variables, \relative, a tie, a chord and a volta repeat (read once).
    assert notes(upper) == [
        (0, 67, 1), (1, 69, 1), (2, 71, 1), (3, 74, 2), (5, 71, 1),
        (6, 72, 4), (10, 71, 1), (11, 69, 1),
        (12, 67, 3), (12, 71, 3), (15, 62, 3),
        (18, 64, 1), (19, 66, 1), (20, 67, 1), (21, 69, 2), (23, 66, 1),
        (24, 67, 6),
    ]
    assert notes(lower) == [(0, 43, 3), (3, 50, 3), (6, 45, 3), (9, 50, 3), (12, 43, 3), (15, 50, 3), (18, 48, 3),
                            (21, 50, 3), (24, 43, 6)]
    assert upper.length == lower.length == 30


def test_work_id_and_style_can_be_given():
    score = parse_abc(fixture_bytes("abc"), work_id="air-one", style="plain")
    assert score.arrangement.id == "air-one--plain"


# Smaller cases for features the fixtures do not cover.

def test_abc_voices_ties_rests_and_accidentals():
    text = """X:1
T:Two Voices
M:2/4
L:1/4
K:F
V:1 name="Top"
B ^B | B2- | B z |]
V:2 name="Low"
F,2 | Z | C,/C,/ x |]
"""
    score = parse_abc(text)
    top, low = score.arrangement.parts
    assert (top.name, low.name) == ("Top", "Low")
    # Key of F: B is flat; ^B is B sharp (72) and the sharp lasts to the bar line; the tie joins bars 2 and 3.
    assert notes(top) == [(0, 70, 1), (1, 72, 1), (2, 70, 3)]
    assert notes(low) == [(0, 53, 2), (4, 48, F(1, 2)), (F(9, 2), 48, F(1, 2))]


def test_musicxml_lyrics_and_beat_type():
    xml = b"""<?xml version="1.0"?>
<score-partwise><movement-title>Short Song</movement-title>
<part-list><score-part id="A"><part-name>Voice</part-name></score-part></part-list>
<part id="A"><measure number="1">
<attributes><divisions>1</divisions><time><beats>3</beats><beat-type>8</beat-type></time></attributes>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><lyric number="1"><text>sun</text></lyric></note>
<note><pitch><step>C</step><alter>1</alter><octave>5</octave></pitch><duration>1</duration></note>
</measure></part></score-partwise>"""
    score = parse_musicxml(xml)
    (voice,) = score.arrangement.parts
    assert score.work.title == "Short Song"
    assert notes(voice) == [(0, 69, 2), (2, 73, 2)]  # a quarter note is two eighth-note beats
    assert voice.lyrics == ("sun", "")


def test_lilypond_absolute_tuplet_unfold_and_lyrics():
    ly = r"""
\header { title = "Small Round" }
\new Staff = "tune" {
  \time 2/4
  c'4 \tuplet 3/2 { d'8 e' f' } | \repeat unfold 2 { g'4 } | <c' e'>2
}
\addlyrics { one two three four five six }
"""
    score = parse_lilypond(ly)
    (tune,) = score.arrangement.parts
    assert tune.name == "tune"
    assert notes(tune) == [
        (0, 60, 1), (1, 62, F(1, 3)), (F(4, 3), 64, F(1, 3)), (F(5, 3), 65, F(1, 3)),
        (2, 67, 1), (3, 67, 1), (4, 60, 2), (4, 64, 2),
    ]
    assert tune.lyrics == ("one", "two", "three", "four", "five", "six", "", "")


def test_format_detection():
    assert detect_format("a/b/tune.ABC") == "abc"
    assert detect_format("tune.ly") == "lilypond"
    assert detect_format("tune.mid") == "midi"
    assert detect_format("tune.musicxml") == "musicxml"
    assert set(EXTENSIONS.values()) == {"abc", "musicxml", "midi", "lilypond"}
    with pytest.raises(ValueError):
        detect_format("tune.pdf")


@pytest.mark.parametrize("parser, data", [
    (parse_abc, "X:1\nT:No body\n"),
    (parse_musicxml, b"<score-timewise/>"),
    (parse_musicxml, b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><score-partwise/>'),
    (parse_midi, b"MThd\x00\x00\x00\x06\x00\x02\x00\x01\x01\xe0"),
    (parse_midi, "MThd as text"),
    (parse_lilypond, r"\transpose c d { c' }"),
    (parse_lilypond, r"{ c' d'"),
])
def test_refusals_are_parse_errors(parser, data):
    with pytest.raises(ParseError):
        parser(data)
