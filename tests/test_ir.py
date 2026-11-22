import json
from fractions import Fraction
from pathlib import Path

import pytest

from common_studio import Arrangement, Note, Part, canonical_json, fromIR, from_ir, ir_hash, toIR, to_ir

from samples import arrangement

GOLDEN = Path(__file__).parent / "fixtures" / "fixture-etude--plain.ir.json"


def test_round_trip_through_a_dictionary_and_through_text():
    a = arrangement()
    assert from_ir(to_ir(a)) == a
    assert from_ir(canonical_json(to_ir(a))) == a
    assert fromIR(toIR(a)) == a


def test_round_trip_is_stable_after_a_second_pass():
    a = arrangement()
    once = canonical_json(to_ir(a))
    assert canonical_json(to_ir(from_ir(once))) == once


def test_key_order_is_deterministic():
    text = canonical_json(to_ir(arrangement()))
    obj = json.loads(text)

    def sorted_everywhere(x):
        if isinstance(x, dict):
            assert list(x) == sorted(x)
            for v in x.values():
                sorted_everywhere(v)
        elif isinstance(x, list):
            for v in x:
                sorted_everywhere(v)

    sorted_everywhere(obj)
    assert text == json.dumps(obj, sort_keys=True, separators=(",", ":"))


def test_note_order_is_deterministic_whatever_order_notes_were_given_in():
    notes = [Note(2, 60, 1, 80), Note(0, 64, 1, 80), Note(0, 60, 1, 80), Note(1, 62, 1, 80)]
    a = Arrangement("w", "s", (Part("lead", tuple(notes), lyrics=("c", "a", "b", "d")),))
    b = Arrangement("w", "s", (Part("lead", tuple(reversed(notes)), lyrics=("d", "b", "a", "c")),))
    assert canonical_json(to_ir(a)) == canonical_json(to_ir(b))
    ir = to_ir(a)["parts"][0]
    assert [(n["beat"], n["pitch"]) for n in ir["notes"]] == [("0", 60), ("0", 64), ("1", 62), ("2", 60)]
    assert ir["lyrics"] == ["b", "a", "d", "c"]


def test_part_order_does_not_change_the_representation():
    a = arrangement()
    b = Arrangement(a.work, a.style, tuple(reversed(a.parts)), a.grid)
    assert ir_hash(a) == ir_hash(b)


def test_beats_are_written_in_lowest_terms():
    a = Arrangement("w", "s", (Part("p", (Note(Fraction(2, 4), 60, Fraction(6, 4), 80), Note(2, 62, 1, 80))),))
    notes = to_ir(a)["parts"][0]["notes"]
    assert (notes[0]["beat"], notes[0]["duration"]) == ("1/2", "3/2")
    assert (notes[1]["beat"], notes[1]["duration"]) == ("2", "1")


def test_an_identical_arrangement_has_the_same_hash():
    assert ir_hash(arrangement()) == ir_hash(arrangement())
    assert ir_hash(arrangement()) == ir_hash(to_ir(arrangement()))
    assert ir_hash(arrangement()).startswith("sha256:") and len(ir_hash(arrangement())) == len("sha256:") + 64


@pytest.mark.parametrize(
    "change",
    ["pitch", "beat", "duration", "velocity", "lyric", "voice", "kit", "sections", "style", "extra-note"],
)
def test_a_one_note_change_changes_the_hash(change):
    base = arrangement()
    melody = next(p for p in base.parts if p.name == "melody")
    n = list(melody.notes)
    lyrics = list(melody.lyrics)
    kw = dict(name="melody", voice=melody.voice, kit=melody.kit, sections=melody.sections)
    style = base.style
    if change == "pitch":
        n[3] = Note(n[3].beat, n[3].pitch + 1, n[3].duration, n[3].velocity)
    elif change == "beat":
        n[3] = Note(n[3].beat + Fraction(1, 4), n[3].pitch, n[3].duration, n[3].velocity)
    elif change == "duration":
        n[3] = Note(n[3].beat, n[3].pitch, n[3].duration / 2, n[3].velocity)
    elif change == "velocity":
        n[3] = Note(n[3].beat, n[3].pitch, n[3].duration, n[3].velocity - 1)
    elif change == "lyric":
        lyrics[3] = "ha"
    elif change == "voice":
        kw["voice"] = "alto"
    elif change == "kit":
        kw["kit"] = "strings"
    elif change == "sections":
        kw["sections"] = 3
    elif change == "style":
        style = "other"
    elif change == "extra-note":
        n.append(Note(8, 60, 1, 80))
        lyrics.append("la")
    changed = Part(notes=tuple(n), lyrics=tuple(lyrics), **kw)
    other = Arrangement(base.work, style, tuple(changed if p.name == "melody" else p for p in base.parts), base.grid)
    assert ir_hash(other) != ir_hash(base)


def test_the_golden_fixture_pins_the_format_and_the_hash():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    a = from_ir(golden["ir"])
    assert a == arrangement()
    assert canonical_json(to_ir(a)) == canonical_json(golden["ir"])
    assert ir_hash(a) == golden["hash"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema="other"),
        lambda d: d.update(version=2),
        lambda d: d.pop("parts"),
        lambda d: d.update(id="wrong--id"),
        lambda d: d["parts"][0]["notes"][0].update(pitch=200),
        lambda d: d["parts"][0]["notes"][0].update(beat=0.5),
        lambda d: d["grid"].update(beats_per_bar=0),
    ],
)
def test_malformed_representations_are_refused(mutate):
    d = to_ir(arrangement())
    mutate(d)
    with pytest.raises((ValueError, TypeError)):
        from_ir(d)


def test_from_ir_refuses_non_documents_and_bad_text():
    with pytest.raises(ValueError):
        from_ir("[]")
    with pytest.raises(ValueError):
        from_ir("{not json")
