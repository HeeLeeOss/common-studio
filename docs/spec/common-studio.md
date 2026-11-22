---
title: Common Studio
license: Unlicense
lifecycle: ai-full
---

## Problem

"Royalty-free" music catalogues are licensed, not free, and truly public-domain recordings are rare and old, while public-domain scores far outnumber public-domain recordings. Anyone who needs music that is free in every sense, such as a teacher who cannot clear rights for a school video or a film-maker, has no open, auditable way to turn a public-domain composition into a recording they own. The first step of any such chain is a correct core, a gate that refuses anything without licence evidence, and checks that catch musical errors before any audio is made.

## Beneficiary

Teachers, independent film-makers, game developers, podcasters, community bands and archives who need music that is free in every sense, and the public domain itself. A named partner organisation is still to be secured, so the project carries no verified last-mile need yet. The output of this run is code and one policy document, reached through this repository.

## Scope

The first slice of the studio's spine, for milestone M1 of this project:

- the core model (Work, Arrangement identified as `work--style`, Part with notes on a beat grid, lyrics, section count, voice and kit), a canonical hashable JSON score representation with round-trip conversion, and the recording-id grammar `work--style[@venue][+treatment]`;
- ingest of ABC, MusicXML, MIDI and LilyPond into the core model, with a licence-evidence gate that refuses a work whose record is incomplete and writes the evidence to `work.yaml`;
- pre-render checkers: a harmony-clash detector that blocks, and voice-leading, instrument-range and voicing checks that warn, each naming the bar;
- the sourcing policy and the asset licence policy as one plain Markdown document that the ingest gate enforces;
- a licence audit script that fails on a copyleft dependency.

## Non-goals

No rendering, mixing, mastering or audio output in this run, and no catalogue of recordings. No ingest of anything without licence evidence. No copying of any text, configuration value, arrangement source, skill or asset from the owner's private reference pipeline; every name, format and value is authored new. No copyleft tool is vendored into the tree. No streaming service, accounts or hosting.

## Acceptance criteria

| AC | Case | Required evidence |
|---|---|---|
| AC-01 | Work, Arrangement, Part, beat grid and the recording-id grammar `work--style[@venue][+treatment]` exist, and all four id shapes parse and format | Unit tests for the model and for each id shape, passing in CI |
| AC-02 | The score representation is canonical: `toIR` and `fromIR` round-trip on fixtures, key and note order are deterministic, a one-note change changes the hash and an identical arrangement does not | Round-trip and hash tests on fixtures, passing in CI |
| AC-03 | Ingest parses ABC, MusicXML, MIDI and LilyPond fixtures into the core model | One fixture and one passing test per format |
| AC-04 | Ingest refuses a work whose evidence record lacks composition, edition or lyrics (lyrics may be `none`), each needing source, basis, checked_at and checker, and the refusal names the missing record | A test per missing record that asserts the refusal and its message; a passing case that writes `work.yaml` with the evidence |
| AC-05 | A banned source is refused even for a public-domain tune, and a verify-only source is flagged, as the sourcing policy says | Tests for a banned and a verify-only source that follow the policy document |
| AC-06 | The parsers survive fuzzed malformed input without crashing the process | A fuzz test per parser, passing in CI |
| AC-07 | The harmony-clash check returns `passed=false` and names the bar on a clash fixture and passes on the corrected fixture; parallel fifths and octaves, out-of-range notes and poor voicing each warn with bar numbers; every check has a positive and a negative fixture | Fixture-based tests for each check, passing in CI |
| AC-08 | The only way past a blocker is a waiver with a written reason, recorded with the arrangement, and the stage result is machine-readable (stage name, verdict, findings with bar and kind) | Tests for a refused blocker, an accepted waiver and the result format |
| AC-09 | The sourcing policy and asset licence policy exist as one plain Markdown document: three evidence records and what counts as a basis for each, source classes (allowed, verify-only, banned) with reasons, the asset manifest entry and allowed licence set, and the clean-room rule | The document at the tip of the default branch, read against these items |
| AC-10 | No dependency with a copyleft licence is in the package tree, and a licence audit script runs in CI and fails on one | The audit script, a test with a copyleft fixture that makes it fail, and a passing CI run |
| AC-11 | Nothing is copied from the private reference pipeline | A recorded review by the clean-room reviewer (a named person) stating that the text, values and fixtures were authored new |

## Inputs and provenance

The project builds on the published MusicXML, Standard MIDI File, ABC and LilyPond format specifications, read as references and not copied. Fixtures are authored for the project, and any fixture composition is evidenced as public domain in its own `work.yaml`. No licensed or unlicensed third-party text, values or assets are used as inputs. The policy document is released under CC0-1.0; the code is released under the Unlicense.
