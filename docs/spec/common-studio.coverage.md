# Spec coverage: `docs/spec/common-studio.md`

Generated 2026-11-23T01:47:20.337Z from the spec at commit `23e75d770b123428c5bba93adee9d936586e935e`, over 1 merged pull request.

## Pull requests read

- https://github.com/HeeLeeOss/common-studio/pull/2 (merged 2026-11-22T14:38:38Z)

## Coverage

| AC | Status | Evidence |
| --- | --- | --- |
| AC-07 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/2, fixtures in \`src/common_studio/check_fixtures.py\` and tests in \`tests/test_checks.py\`. Harmony clash: \`test_clash_blocks_and_names_bar\` checks that \`passed\` is false, the check blocks, and the finding names bar 2; \`test_clash_corrected_passes\` ch... |
| AC-08 | COVERED | https://github.com/HeeLeeOss/common-studio/pull/2, \`tests/test_checks.py\`. Refused blocker: \`test_blocker_refused_without_waiver\` checks for a \`blocked\` verdict and that \`require_clear\` raises \`BlockedError\`. Written reason required: \`test_waiver_requires_reason\` and \`test_only_blockers_can_be_wa... |

## Uncovered

None.

## Notes

- checks on pull request 2 given to the reader: 1 of 1 succeeded

---

Advisory: this report blocks nothing; the gap-fix round is the lane's (`IgniteSpecCoverageFixRounds`).
