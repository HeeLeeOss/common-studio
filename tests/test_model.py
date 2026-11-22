from fractions import Fraction

import pytest

from common_studio import Arrangement, BeatGrid, Note, Part, Work, as_beat

from samples import WORK, arrangement, generate


def test_note_holds_beat_pitch_duration_velocity():
    n = Note(Fraction(3, 2), 60, Fraction(1, 2), 90)
    assert (n.beat, n.pitch, n.duration, n.velocity) == (Fraction(3, 2), 60, Fraction(1, 2), 90)


def test_beats_accept_ints_and_strings_and_refuse_floats():
    assert as_beat(2) == Fraction(2)
    assert as_beat("3/2") == Fraction(3, 2)
    with pytest.raises(TypeError):
        as_beat(0.5)
    with pytest.raises(TypeError):
        Note(0.5, 60, 1, 80)


@pytest.mark.parametrize(
    "args",
    [(-1, 60, 1, 80), (0, 60, 0, 80), (0, 128, 1, 80), (0, -1, 1, 80), (0, 60, 1, 0), (0, 60, 1, 128), (0, True, 1, 80)],
)
def test_note_refuses_values_out_of_range(args):
    with pytest.raises(ValueError):
        Note(*args)


def test_part_carries_lyrics_sections_voice_and_kit():
    p = Part("lead", (Note(0, 60, 1, 80), Note(1, 62, 1, 80)), lyrics=("do", "re"), sections=3, voice="alto", kit="strings")
    assert p.lyrics == ("do", "re") and p.sections == 3 and p.voice == "alto" and p.kit == "strings"
    assert p.length == Fraction(2)


def test_part_defaults_have_no_lyrics_voice_or_kit():
    p = Part("pad")
    assert p.lyrics is None and p.voice is None and p.kit is None and p.sections == 1 and p.length == 0


def test_lyrics_must_match_the_notes_one_for_one():
    with pytest.raises(ValueError):
        Part("lead", (Note(0, 60, 1, 80),), lyrics=("do", "re"))


@pytest.mark.parametrize("bad", [0, -1, True])
def test_sections_must_be_a_positive_whole_number(bad):
    with pytest.raises(ValueError):
        Part("lead", sections=bad)


def test_part_needs_a_name():
    with pytest.raises(ValueError):
        Part(" ")


def test_beat_grid_names_bars_and_checks_the_grid():
    g = BeatGrid(beats_per_bar=3, subdivision=2)
    assert g.bar_of(0) == 1 and g.bar_of(Fraction(5, 2)) == 1 and g.bar_of(3) == 2 and g.bar_of(7) == 3
    assert g.on_grid(Fraction(3, 2)) is True
    assert g.on_grid(Fraction(1, 3)) is False
    with pytest.raises(ValueError):
        BeatGrid(0, 4)
    with pytest.raises(ValueError):
        BeatGrid(4, 0)


def test_arrangement_is_identified_as_work_double_hyphen_style():
    a = arrangement("plain")
    assert a.id == "fixture-etude--plain" and a.work == WORK.id and a.style == "plain"


def test_arrangement_refuses_duplicate_part_names_and_bad_names():
    with pytest.raises(ValueError):
        Arrangement("w", "s", (Part("a"), Part("a")))
    with pytest.raises(ValueError):
        Arrangement("Not Valid", "s")


def test_work_checks_its_id_and_title():
    with pytest.raises(ValueError):
        Work("Bad Id", "x")
    with pytest.raises(ValueError):
        Work("ok", " ")


def test_a_generator_builds_an_arrangement_from_a_work():
    a = generate(WORK)
    assert isinstance(a, Arrangement) and a.work == WORK.id and [p.name for p in a.parts] == ["melody"]
