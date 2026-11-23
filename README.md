# Common Studio

An open, public-domain music production studio in software. This package holds the core model: works,
arrangements, parts on a beat grid, a canonical hashable score representation, and the recording-id grammar.
Code is released under the Unlicense; see `LICENSE`.

```
pip install -e ".[dev]"
pytest
```

## Core model

- `Work` — a composition (`id`, `title`).
- `Arrangement` — one arrangement of a work in a style, identified as `work--style`. It holds `Part`s.
- `Part` — notes on a beat grid (`beat`, `pitch`, `duration`, `velocity`), optional lyrics, a section count, a
  voice and a kit. Beats and durations are exact fractions of a beat, so nothing depends on floating point.
- An arrangement is built by a generator: any callable matching `ArrangementGenerator` that takes a `Work` and returns
  an `Arrangement`.

## Score representation

`to_ir(arrangement)` returns a plain dictionary in a canonical form: parts sorted by name, notes sorted by
`(beat, pitch, duration, velocity)`, beats and durations written as exact fractions in lowest terms. `canonical_json`
writes it with sorted keys and fixed separators, and `ir_hash` is the SHA-256 of that text. `from_ir` reads it back.
`toIR` and `fromIR` are aliases.

## Recording ids

`work--style[@venue][+treatment]`, where each part is lowercase letters and digits with single hyphens between
groups. `parse_recording_id` and `format_recording_id` are inverses.

## Pre-render checks

`run_stage(arrangement)` runs four checks and returns a `StageResult` (`to_dict()` / `to_json()`: stage name, verdict,
findings with `bar` and `kind`). `harmony-clash` blocks; `voice-leading` (parallel fifths and octaves),
`instrument-range` and `voicing` warn. The verdict is `blocked`, `waived`, `warn` or `pass`. The only way past a
blocker is `waive(arrangement, "harmony-clash", reason, bars=())`, which needs a written reason and records a `Waiver`
on the arrangement (not part of the score hash). `require_clear` raises `BlockedError` for an unwaived blocker.
Authored fixtures for every check are in `common_studio.check_fixtures`.

## Ingest and the licence-evidence gate

`common_studio.ingest` reads ABC (`parse_abc`), uncompressed partwise MusicXML (`parse_musicxml`), Standard MIDI
Files of format 0 or 1 (`parse_midi`) and a documented subset of LilyPond (`parse_lilypond`) into `Work`,
`Arrangement` and `Part` on a `BeatGrid`. A beat is the unit of the time signature's lower number. A parser fails only
with `ParseError`; each one is fuzz-tested.

`ingest(data, fmt, evidence, out_dir=..., origin=...)` (or `ingest_file(path, evidence, out_dir=...)`) enforces the
sourcing policy in `policy/sourcing-and-asset-licence-policy.md`:

- `composition`, `edition` and `lyrics` each need `source`, `basis`, `checked_at` and `checker`; `lyrics` may say
  `value: none` and still needs the four fields. Otherwise `EvidenceRefused` names every missing or incomplete record.
- A banned source (`SourceRefused`) is refused even when the tune is in the public domain. A verify-only or
  unregistered source is written with `gate.status: flagged` until a maintainer who is not one of the checkers
  confirms it (`confirmed_by=`). Sources are classified by `SourceRegistry`; maintainers add entries with
  `DEFAULT_REGISTRY.with_entries(SourceEntry(...))`.
- An accepted work is written to `<out_dir>/<work id>/work.yaml` with its evidence and the class of every source.

Authored fixtures for all four formats, and the `work.yaml` the gate writes for each, are in
`src/common_studio/ingest/fixtures/`; `python -m common_studio.ingest.fixture_evidence` regenerates the `work.yaml`
files.
