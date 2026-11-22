# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-22T19:32:45.618Z from the spec at commit `c6f538429e45454d5b99c79b0c11790c83828ce7`, over 4 merged pull requests.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/1 (merged 2026-11-22T05:06:16Z)
- https://github.com/HeeLeeOss/common-studio/pull/3 (merged 2026-11-22T14:59:45Z)
- https://github.com/HeeLeeOss/common-studio/pull/4 (merged 2026-11-22T15:07:36Z)
- https://github.com/HeeLeeOss/common-studio/pull/6 (merged 2026-11-22T19:06:57Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-01 | UNVERIFIED | https://github.com/HeeLeeOss/common-studio/pull/1 adds the model and the tests. \`tests/test_model.py\` covers Note, Part, BeatGrid, Work and Arrangement, including \`test_arrangement_is_identified_as_work_double_hyphen_style\`. \`tests/test_recording_id.py::test_each_shape_parses_and_formats_back\` ch... |
| AC-02 | UNVERIFIED | https://github.com/HeeLeeOss/common-studio/pull/1 has the right tests in \`tests/test_ir.py\`. Round-trip: \`test_round_trip_through_a_dictionary_and_through_text\` and \`test_round_trip_is_stable_after_a_second_pass\`. Ordering: \`test_key_order_is_deterministic\` and \`test_note_order_is_deterministic_w... |
| AC-09 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/4, \`policy/sourcing-and-asset-licence-policy.md\`. Each item in the row maps to a section: |
| AC-10 | UNVERIFIED | https://github.com/HeeLeeOss/common-studio/pull/3 delivers \`scripts/license_audit.py\`, the CI step \`python scripts/license_audit.py\` in \`.github/workflows/ci.yml\`, and \`tests/test_license_audit.py::test_copyleft_fixture_makes_the_audit_fail\` using \`tests/fixtures/licence/copyleft/*\`. The row also... |
| AC-11 | UNVERIFIED | https://github.com/HeeLeeOss/common-studio/pull/6 adds \`policy/clean-room-review-M1.md\`, signed "Christine Carter", stating that all listed files were authored new. Four gaps stop it from settling the row: |

## Uncovered

None.

Unverified: AC-01, AC-02, AC-10, AC-11.

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
