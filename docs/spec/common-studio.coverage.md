# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-24T04:56:22.809Z from the spec at commit `33fcb8538fdee18fab30e4f07e62921c4d0c8113`, over 1 merged pull request.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/12 (merged 2026-11-23T14:37:52Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-03 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12 adds one authored fixture per format under \`src/common_studio/ingest/fixtures/\`: \`slate-roof-air.abc\`, \`quarry-lane-hymn.musicxml\`, \`mill-wheel-turning.mid\` and \`lantern-path.ly\`. It also adds one test per format in \`tests/test_ingest_formats.py\`: \`test_abc_fixture_parses_onto_the_beat_grid\`, \`test_musicxml_fixture_parses_onto_the_beat_grid\`, \`test_midi_fixture_parses_onto_the_beat_grid\` and \`test_lilypond_fixture_parses_onto_the_beat_grid\`. Each test checks that the result is a \`Work\`, an \`Arrangement\` and a \`Part\` on a \`BeatGrid\`. GitHub reports one check, and it succeeded. |
| AC-04 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12, in \`tests/test_ingest_gate.py\`. \`test_missing_record_is_refused_and_named\` runs once each for composition, edition and lyrics. It checks that the refusal is \`EvidenceRefused\`, that the message says "the &lt;record&gt; evidence record is missing", and that nothing is written. \`test_record_without_a_field_is_refused_and_named\` does the same for each of the four fields. \`test_lyrics_may_be_none_but_still_needs_its_fields\` covers lyrics set to \`none\`. \`test_complete_record_writes_work_yaml_with_the_evidence\` is the passing case: it writes \`work.yaml\` with all three records, which matches policy sections 3 and 9. The code is in \`src/common_studio/ingest/evidence.py\` and \`gate.py\`. CI succeeded. |
| AC-05 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12, in \`tests/test_ingest_gate.py\`. \`test_banned_source_is_refused_even_for_a_public_domain_tune\` uses a public-domain composition record and tries seven banned edition sources: the private reference pipeline, a commercial edition, CC BY-SA, NonCommercial, an unidentified upload and "all rights reserved". It also has \`test_banned_origin_is_refused\` and \`test_banned_source_wins_over_an_allowed_registry_entry\`. \`test_verify_only_source_is_flagged\` covers a community library, a folk collection and an unregistered URL. \`test_unregistered_source_is_verify_only_until_a_maintainer_classifies_it\` and \`test_flag_is_confirmed_only_by_a_maintainer_other_than_the_checker\` cover the rest. These match policy section 5: |
| AC-06 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12, in \`tests/test_ingest_fuzz.py\`. \`test_parser_survives_fuzzed_input\` runs once for each of abc, musicxml, midi and lilypond. Each run feeds 400 or more seeded cases: random bytes, text from the format's own characters, and mutated copies of the fixture. Any exception other than \`ParseError\` fails the test. The file also has one hand-written hostile-input test per parser. GitHub reports one check, and it succeeded; its log lists the 8 tests in \`tests/test_ingest_fuzz.py\` as passed. |

## Uncovered

None.

## Notes

- checks on pull request 12 given to the reader: 1 of 1 succeeded
- commits of pull request 12 given to the reader: 1 of 1 signed off
- the CI log tail of 1 check\(s\) of pull request 12 was given to the reader
- attestation by jdev1977 \(MEMBER\) for AC-05 on pull request 12 was given to the reader \(`https://github.com/HeeLeeOss/common-studio/pull/12#issuecomment-7121884260`\)
- reference document given to the reader: policy/sourcing-and-asset-licence-policy.md

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
