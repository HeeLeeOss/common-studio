"""AC-04 and AC-05: the licence-evidence gate and the sourcing policy's source classes."""

import copy

import pytest

from common_studio.ingest import (
    ALLOWED, BANNED, CONFIRMED, DEFAULT_REGISTRY, FLAGGED, PASSED, VERIFY_ONLY, EvidenceRefused, IngestRefused,
    LyricsRefused, SourceEntry, SourceRefused, check_evidence, ingest, ingest_file,
)
from common_studio.ingest.fixture_evidence import FILES, FIXTURES_DIR, ORIGIN, WORKS_DIR, evidence, fixture_bytes

RECORDS = ("composition", "edition", "lyrics")
FIELDS = ("source", "basis", "checked_at", "checker")

# A tune whose composition is plainly public domain, used to show that a banned source is refused all the same.
PD_COMPOSITION = {
    "source": "library-facts: national biographical dictionary, entry for the composer (placeholder citation)",
    "basis": "Sole composer died 1790; life plus 70 passed in 1861. First published 1785, before the US cut-off.",
    "checked_at": "2026-11-23",
    "checker": "a-named-person",
}


def complete(fmt: str = "musicxml") -> dict:
    return copy.deepcopy(evidence(fmt))


def run(ev, tmp_path, fmt="musicxml", **kwargs):
    return ingest(fixture_bytes(fmt), fmt, ev, out_dir=tmp_path, **kwargs)


# --- AC-04: incomplete evidence is refused, and the refusal names the record --------------------------------------

@pytest.mark.parametrize("record", RECORDS)
def test_missing_record_is_refused_and_named(record, tmp_path):
    ev = complete()
    del ev[record]
    with pytest.raises(EvidenceRefused) as info:
        run(ev, tmp_path)
    assert info.value.records == (record,)
    assert f"the {record} evidence record is missing" in str(info.value)
    for other in RECORDS:
        if other != record:
            assert other not in str(info.value)
    assert not any(tmp_path.iterdir()), "a refused work writes nothing"


@pytest.mark.parametrize("record", RECORDS)
@pytest.mark.parametrize("field", FIELDS)
def test_record_without_a_field_is_refused_and_named(record, field, tmp_path):
    ev = complete()
    ev[record][field] = "   " if field == "basis" else None
    with pytest.raises(EvidenceRefused) as info:
        run(ev, tmp_path)
    assert info.value.records == (record,)
    message = str(info.value)
    assert f"the {record} evidence record is incomplete" in message
    assert f"{field} is missing or empty" in message
    assert not any(tmp_path.iterdir())


def test_every_bad_record_is_named_at_once(tmp_path):
    ev = complete()
    del ev["composition"]
    del ev["lyrics"]["checker"]
    with pytest.raises(EvidenceRefused) as info:
        run(ev, tmp_path)
    assert info.value.records == ("composition", "lyrics")
    assert "composition evidence record is missing" in str(info.value)
    assert "lyrics evidence record is incomplete: checker is missing or empty" in str(info.value)


def test_no_evidence_at_all_names_all_three(tmp_path):
    with pytest.raises(EvidenceRefused) as info:
        run({}, tmp_path)
    assert info.value.records == RECORDS


@pytest.mark.parametrize("change, expected", [
    ({"checked_at": "23/11/2026"}, "checked_at must be a UTC date"),
    ({"checked_at": "2026-02-30"}, "checked_at must be a UTC date"),
    ({"checker": "unknown"}, "checker must name a real person"),
    ({"checker": "ingest-bot"}, "checker must name a real person"),
    ({"source": "http://scans.example/item/1"}, "must use https"),
    ({"source": "https://user:pw@scans.example/item/1"}, "must not carry credentials"),
    ({"source": "https://scans.example/item/1?access_token=abc"}, "must not carry a token"),
])
def test_record_fields_must_be_valid(change, expected, tmp_path):
    ev = complete()
    ev["edition"].update(change)
    with pytest.raises(EvidenceRefused) as info:
        run(ev, tmp_path)
    assert info.value.records == ("edition",)
    assert expected in str(info.value)


def test_lyrics_may_be_none_but_still_needs_its_fields(tmp_path):
    ev = complete()
    assert ev["lyrics"]["value"] == "none"
    assert run(ev, tmp_path).status == PASSED
    ev["lyrics"] = {"value": "none"}
    problems = check_evidence(ev)
    assert set(problems) == {"lyrics"}
    assert len(problems["lyrics"]) == 4


def test_lyrics_none_is_refused_when_the_score_has_words(tmp_path):
    ev = complete("abc")
    ev["lyrics"]["value"] = "none"
    with pytest.raises(LyricsRefused, match="lyrics record is 'none' but the score carries words"):
        run(ev, tmp_path, "abc")


def test_complete_record_writes_work_yaml_with_the_evidence(tmp_path):
    ev = complete()
    ev["composition"]["notes"] = "An extra field is kept beside the four required ones."
    result = run(ev, tmp_path, origin=ORIGIN)
    assert result.status == PASSED
    assert result.path == tmp_path / "quarry-lane-hymn" / "work.yaml"
    text = result.path.read_text(encoding="utf-8")
    assert 'work: "quarry-lane-hymn"' in text
    assert 'status: "passed"' in text
    assert f'sha256: "{result.sha256}"' in text
    assert "\nevidence:\n  composition:\n" in text
    for record in RECORDS:
        assert f"\n  {record}:\n" in text
        for field in FIELDS:
            assert f'    {field}: "{ev[record][field]}"' in text
    assert '    value: "none"' in text
    assert '    notes: "An extra field is kept beside the four required ones."' in text


def test_ingest_file_refuses_before_reading(tmp_path):
    with pytest.raises(EvidenceRefused):
        ingest_file(tmp_path / "does-not-exist.abc", {}, out_dir=tmp_path)


@pytest.mark.parametrize("fmt", sorted(FILES))
def test_committed_fixture_work_yaml_matches_the_gate(fmt, tmp_path):
    """Each fixture composition is evidenced in its own work.yaml, and the gate writes exactly that file."""
    result = ingest_file(FIXTURES_DIR / FILES[fmt], evidence(fmt), out_dir=tmp_path, origin=ORIGIN)
    assert result.status == PASSED
    committed = WORKS_DIR / result.score.work.id / "work.yaml"
    assert committed.read_bytes() == result.path.read_bytes()


# --- AC-05: banned sources are refused even for a public-domain tune; verify-only sources are flagged -------------

@pytest.mark.parametrize("source", [
    "private-reference: arrangement source from the owner's pipeline",
    "a file copied from the private reference pipeline",
    "commercial-edition: a modern urtext edition, 2011",
    "https://scores.example/item/77 (licence: CC BY-SA 4.0)",
    "https://scores.example/item/78, Creative Commons Attribution-NonCommercial",
    "unidentified-upload: free sheet music aggregator, no uploader named",
    "https://scores.example/item/79, all rights reserved",
])
def test_banned_source_is_refused_even_for_a_public_domain_tune(source, tmp_path):
    ev = complete()
    ev["composition"] = dict(PD_COMPOSITION)
    ev["edition"]["source"] = source
    with pytest.raises(SourceRefused) as info:
        run(ev, tmp_path)
    assert "even if the tune is in the public domain" in str(info.value)
    assert [c.record for c in info.value.banned] == ["edition"]
    assert info.value.banned[0].source_class == BANNED
    assert not any(tmp_path.iterdir())


def test_banned_origin_is_refused(tmp_path):
    with pytest.raises(SourceRefused) as info:
        run(complete(), tmp_path, origin="private-reference: pipeline/arrangements/tune.xml")
    assert info.value.banned[0].record == "origin"


def test_banned_source_wins_over_an_allowed_registry_entry(tmp_path):
    ev = complete()
    ev["edition"]["source"] = "authored: re-typed from a CC BY-NC-SA edition"
    with pytest.raises(SourceRefused):
        run(ev, tmp_path)


@pytest.mark.parametrize("source", [
    "community-library: a score library page for the tune",
    "folk-collection: a community ABC collection entry",
    "https://scores.example/files/air.xml",
])
def test_verify_only_source_is_flagged(source, tmp_path):
    ev = complete()
    ev["composition"] = dict(PD_COMPOSITION)
    ev["edition"]["source"] = source
    result = run(ev, tmp_path)
    assert result.status == FLAGGED and result.flagged
    assert [(c.record, c.source_class) for c in result.flags] == [("edition", VERIFY_ONLY)]
    text = result.path.read_text(encoding="utf-8")
    assert 'status: "flagged"' in text
    assert 'class: "verify-only"' in text


def test_unregistered_source_is_verify_only_until_a_maintainer_classifies_it(tmp_path):
    ev = complete()
    ev["edition"]["source"] = "https://archive.example/scans/1790/air"
    assert run(ev, tmp_path).status == FLAGGED
    registry_entry = SourceEntry("https://archive.example/scans/", ALLOWED, "public-archive-facsimile",
                                 "facsimiles of old printings held by a public archive")
    result = run(ev, tmp_path, registry=DEFAULT_REGISTRY.with_entries(registry_entry))
    assert result.status == PASSED
    banned_host = SourceEntry("host:archive.example", BANNED, "site-terms-forbid-reuse", "terms forbid reuse")
    with pytest.raises(SourceRefused):
        run(ev, tmp_path, registry=DEFAULT_REGISTRY.with_entries(banned_host))


def test_facts_source_is_allowed_for_composition_but_flagged_as_an_edition(tmp_path):
    ev = complete()
    ev["composition"] = dict(PD_COMPOSITION)
    assert run(ev, tmp_path).status == PASSED
    ev["edition"]["source"] = PD_COMPOSITION["source"]
    assert run(ev, tmp_path).status == FLAGGED


def test_flag_is_confirmed_only_by_a_maintainer_other_than_the_checker(tmp_path):
    ev = complete()
    ev["edition"]["source"] = "community-library: a score library page"
    with pytest.raises(IngestRefused, match="not one of its checkers"):
        run(ev, tmp_path, confirmed_by=ev["edition"]["checker"])
    result = run(ev, tmp_path, confirmed_by="another-maintainer")
    assert result.status == CONFIRMED
    text = result.path.read_text(encoding="utf-8")
    assert 'status: "confirmed"' in text and 'confirmed_by: "another-maintainer"' in text


def test_work_yaml_quotes_hostile_text(tmp_path):
    ev = complete()
    ev["composition"]["basis"] = 'Line one\nkey: "injected"   café \U0001f3b5'
    text = run(ev, tmp_path).path.read_text(encoding="utf-8")
    assert '    basis: "Line one\\u000akey: \\"injected\\" \\u2028 caf\\u00e9 \\U0001f3b5"' in text
    assert all(ord(c) < 128 for c in text)
