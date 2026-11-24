# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-24T04:19:53.220Z from the spec at commit `33fcb8538fdee18fab30e4f07e62921c4d0c8113`, over 1 merged pull request.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/12 (merged 2026-11-23T14:37:52Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-03 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12 adds one fixture per format under \`src/common_studio/ingest/fixtures/\`: \`slate-roof-air.abc\`, \`quarry-lane-hymn.musicxml\`, \`mill-wheel-turning.mid\` and \`lantern-path.ly\`. \`tests/test_ingest_formats.py\` has one test per format: \`test_abc_fixture_p... |
| AC-04 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12 \`tests/test_ingest_gate.py\`. \`test_missing_record_is_refused_and_named\`, run once each for composition, edition and lyrics, checks that \`EvidenceRefused\` is raised, that \`.records\` holds that one record, and that the message says "the &lt;record&gt; ev... |
| AC-05 | UNVERIFIED | The tests exist in https://github.com/HeeLeeOss/common-studio/pull/12 \`tests/test_ingest_gate.py\`: \`test_banned_source_is_refused_even_for_a_public_domain_tune\`, \`test_banned_origin_is_refused\`, \`test_verify_only_source_is_flagged\` and \`test_unregistered_source_is_verify_only_until_a_maintainer_c... |
| AC-06 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12 \`tests/test_ingest_fuzz.py::test_parser_survives_fuzzed_input\` runs once per parser \(abc, musicxml, midi, lilypond\). Each run feeds 401 seeded inputs of random bytes, random text over the format's own characters, and mutated copies of the fixture... |

## Uncovered

None.

Unverified: AC-05.

## Notes

- checks on pull request 12 given to the reader: 1 of 1 succeeded
- commits of pull request 12 given to the reader: 1 of 1 signed off
- the CI log tail of 1 check\(s\) of pull request 12 was given to the reader
- attestation by jdev1977 \(MEMBER\) for AC-05 on pull request 12 was given to the reader \(`https://github.com/HeeLeeOss/common-studio/pull/12#issuecomment-7121884260`\)

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
