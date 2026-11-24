# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-24T04:08:25.797Z from the spec at commit `33fcb8538fdee18fab30e4f07e62921c4d0c8113`, over 1 merged pull request.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/12 (merged 2026-11-23T14:37:52Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-03 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12 adds one fixture per format under \`src/common_studio/ingest/fixtures/\` \(\`slate-roof-air.abc\`, \`quarry-lane-hymn.musicxml\`, \`mill-wheel-turning.mid\`, \`lantern-path.ly\`\). Each has its own test in \`tests/test_ingest_formats.py\`: \`test_abc_fixture_pa... |
| AC-04 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12, \`tests/test_ingest_gate.py\`. \`test_missing_record_is_refused_and_named\` runs once for each of composition, edition and lyrics. It asserts \`EvidenceRefused\`, that the message says "the &lt;record&gt; evidence record is missing" and that nothing was wri... |
| AC-05 | UNVERIFIED | \`tests/test_ingest_gate.py\` in https://github.com/HeeLeeOss/common-studio/pull/12 does have tests for both cases. \`test_banned_source_is_refused_even_for_a_public_domain_tune\` and \`test_banned_origin_is_refused\` cover banned sources, and \`test_verify_only_source_is_flagged\` covers verify-only one... |
| AC-06 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/12, \`tests/test_ingest_fuzz.py\`. \`test_parser_survives_fuzzed_input\` runs once for each of abc, musicxml, midi and lilypond. Each run feeds about 400 seeded cases of random bytes, text from the format's own alphabet and mutated fixtures, and any exc... |

## Uncovered

None.

Unverified: AC-05.

## Notes

- checks on pull request 12 given to the reader: 1 of 1 succeeded
- commits of pull request 12 given to the reader: 1 of 1 signed off
- the CI log tail of 1 check\(s\) of pull request 12 was given to the reader

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
