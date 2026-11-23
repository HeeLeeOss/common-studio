# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-23T00:00:05.715Z from the spec at commit `c6f538429e45454d5b99c79b0c11790c83828ce7`, over 4 merged pull requests.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/1 (merged 2026-11-22T05:06:16Z)
- https://github.com/HeeLeeOss/common-studio/pull/3 (merged 2026-11-22T14:59:45Z)
- https://github.com/HeeLeeOss/common-studio/pull/4 (merged 2026-11-22T15:07:36Z)
- https://github.com/HeeLeeOss/common-studio/pull/6 (merged 2026-11-22T19:06:57Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-01 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/1 adds \`src/common_studio/model.py\` \(Work, Arrangement, Part, Note, BeatGrid\) and \`src/common_studio/recording_id.py\`. The tests are in \`tests/test_model.py\` \(including \`test_beat_grid_names_bars_and_checks_the_grid\`, \`test_arrangement_is_identified... |
| AC-02 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/1 adds \`src/common_studio/ir.py\`. The tests are in \`tests/test_ir.py\`: \`test_round_trip_through_a_dictionary_and_through_text\`, \`test_round_trip_is_stable_after_a_second_pass\`, \`test_key_order_is_deterministic\`, \`test_note_order_is_deterministic_wha... |
| AC-09 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/4 adds \`policy/sourcing-and-asset-licence-policy.md\`, one plain Markdown document. Section 3 defines the three evidence records \(composition, edition, lyrics\) with source, basis, checked_at and checker. Section 4 says what counts as a basis for each... |
| AC-10 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/3 adds \`scripts/license_audit.py\`, which exits 1 on a copyleft licence. The fixtures are under \`tests/fixtures/licence/copyleft/\`, and \`tests/test_license_audit.py::test_copyleft_fixture_makes_the_audit_fail\` checks the exit code is 1. \`.github/work... |
| AC-11 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/6 adds \`policy/clean-room-review-M1.md\`. It names the reviewer \(Christine Carter\), the date and the commit, lists the files, says the comparison was made against a local copy of the private reference pipeline, records "Yes, authored new" for each fi... |

## Uncovered

None.

## Notes

- checks on pull request 1 given to the reader: 1 of 1 succeeded
- checks on pull request 3 given to the reader: 1 of 1 succeeded
- checks on pull request 4 given to the reader: 1 of 1 succeeded
- checks on pull request 6 given to the reader: 1 of 1 succeeded
- attestation by jdev1977 \(MEMBER\) for AC-11 on pull request 6 was given to the reader \(`https://github.com/HeeLeeOss/common-studio/pull/6#issuecomment-7087879569`\)

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
