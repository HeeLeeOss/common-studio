import json

import pytest

from common_studio import BlockedError, Waiver, ir_hash, require_clear, run_stage, waive
from common_studio import check_fixtures as fx
from common_studio.checks import (
    check_harmony_clash, check_instrument_range, check_voice_leading, check_voicing,
)
import samples


def kinds(result):
    return {(f.kind, f.bar) for f in result.findings}


# AC-07 -------------------------------------------------------------------

def test_clash_blocks_and_names_bar():
    r = check_harmony_clash(fx.clash())
    assert not r.passed and r.severity == "block"
    assert [f.bar for f in r.findings] == [2]


def test_clash_corrected_passes():
    assert check_harmony_clash(fx.clash_corrected()).passed


def test_parallel_fifths_warn_with_bar():
    r = check_voice_leading(fx.parallel_fifths())
    assert r.severity == "warn"
    assert ("parallel-fifths", 2) in kinds(r)


def test_parallel_octaves_warn_with_bar():
    assert ("parallel-octaves", 2) in kinds(check_voice_leading(fx.parallel_octaves()))


def test_voice_leading_negative():
    assert check_voice_leading(fx.voice_leading_clean()).passed


def test_out_of_range_warns_with_bar():
    r = check_instrument_range(fx.out_of_range())
    assert kinds(r) == {("out-of-range", 2)}


def test_in_range_passes_and_unknown_instrument_skipped():
    assert check_instrument_range(fx.in_range()).passed
    assert check_instrument_range(fx.clash()).passed


def test_poor_voicing_warns_with_bar():
    assert kinds(check_voicing(fx.poor_voicing())) == {("wide-spacing", 2)}


def test_muddy_low_voicing_warns():
    from common_studio import Arrangement, Note, Part
    arr = Arrangement("x", "y", (Part("a", (Note(0, 40, 1, 80),)), Part("b", (Note(0, 42, 1, 80),)),
                                 Part("c", (Note(0, 52, 1, 80),))))
    assert ("muddy-low-interval", 1) in kinds(check_voicing(arr))


def test_good_voicing_passes():
    assert check_voicing(fx.good_voicing()).passed


def test_sample_arrangement_is_clean():
    assert run_stage(samples.arrangement()).verdict == "pass"


# AC-08 -------------------------------------------------------------------

def test_blocker_refused_without_waiver():
    assert run_stage(fx.clash()).verdict == "blocked"
    with pytest.raises(BlockedError, match="bar"):
        require_clear(fx.clash())


def test_waiver_requires_reason():
    for bad in ("", "   ", "short"):
        with pytest.raises(ValueError):
            waive(fx.clash(), "harmony-clash", bad)


def test_only_blockers_can_be_waived():
    with pytest.raises(ValueError):
        waive(fx.clash(), "voicing", "a perfectly long reason")


def test_waiver_accepted_and_recorded_with_arrangement():
    arr = waive(fx.clash(), "harmony-clash", "Deliberate bitonal bite in bar 2", by="reviewer")
    assert arr.waivers == (Waiver("harmony-clash", "Deliberate bitonal bite in bar 2", (), "reviewer"),)
    r = require_clear(arr)
    assert r.verdict == "waived"
    assert all(f.waived for f in r.findings if f.severity == "block")
    assert r.waivers == arr.waivers
    assert ir_hash(arr) == ir_hash(fx.clash())  # the waiver is not part of the score


def test_waiver_for_other_bar_does_not_cover():
    arr = waive(fx.clash(), "harmony-clash", "Bar 1 is intentional here", bars=(1,))
    assert run_stage(arr).blocked


def test_waiver_for_the_bar_covers():
    arr = waive(fx.clash(), "harmony-clash", "Bar 2 is intentional here", bars=(2,))
    assert run_stage(arr).verdict == "waived"


def test_result_format_machine_readable():
    d = json.loads(run_stage(fx.clash()).to_json())
    assert d["stage"] == "pre-render-check" and d["verdict"] == "blocked"
    f = next(f for f in d["findings"] if f["kind"] == "harmony-clash")
    assert f["bar"] == 2 and f["check"] == "harmony-clash" and f["waived"] is False
    assert [c["check"] for c in d["checks"]] == ["harmony-clash", "voice-leading", "instrument-range", "voicing"]
    assert run_stage(fx.clash()).to_json() == run_stage(fx.clash()).to_json()


def test_warnings_do_not_block():
    r = require_clear(fx.parallel_fifths())
    assert r.verdict == "warn"


def test_result_carries_schema_and_counts():
    d = run_stage(waive(fx.clash(), "harmony-clash", "Deliberate bitonal bite in bar 2")).to_dict()
    assert d["schema"] == "common-studio/check-result/1"
    assert d["counts"]["waived"] == 1 and d["counts"]["block"] == 0
    assert run_stage(fx.clash()).to_dict()["counts"]["block"] == 1


def test_waiver_record_round_trips_and_passes_blocker():
    from common_studio import waivers_to_json, with_recorded_waivers
    waived = waive(fx.clash(), "harmony-clash", "Deliberate bitonal bite in bar 2", bars=(2,), by="reviewer")
    restored = with_recorded_waivers(fx.clash(), waivers_to_json(waived))
    assert restored.waivers == waived.waivers
    assert run_stage(restored).verdict == "waived"


def test_waiver_record_refuses_tampering():
    from common_studio import waivers_to_json, with_recorded_waivers
    rec = json.loads(waivers_to_json(waive(fx.clash(), "harmony-clash", "Deliberate bitonal bite in bar 2")))
    other = json.dumps({**rec, "arrangement": "someone--else"})
    with pytest.raises(ValueError):
        with_recorded_waivers(fx.clash(), other)
    rec["waivers"][0]["reason"] = ""
    with pytest.raises(ValueError):
        with_recorded_waivers(fx.clash(), json.dumps(rec))
    assert run_stage(fx.clash()).blocked
