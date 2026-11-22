---
title: Common Studio
riskTier: medium
license: Unlicense
lifecycle: ai-full
beneficiary: Teachers, film-makers, game developers, podcasters, community bands and archives who need music that is free in every sense (a named partner is still to be secured)
definitionOfShipped: Each milestone is a GitHub release on the project repository whose assets, fetched back from GitHub, match the bytes in the repository, with the licence gates and the clean-room review recorded; the studio is adopted by a partner only in a later milestone.
reviewPolicy:
  humanCheckpoints: [spec, plan, ship]
milestones:
  - { id: M1, title: "Core, licence audit and sourcing policy", rows: [AC-01, AC-02, AC-09, AC-10, AC-11] }
  - { id: M2, title: Ingest with the licence-evidence gate, rows: [AC-03, AC-04, AC-05, AC-06] }
  - { id: M3, title: Pre-render checkers and waivers, rows: [AC-07, AC-08] }
definitionOfShippedRecipe:
  kind: github-release
  params:
    paths: [src/, scripts/, policy/]
---

## Summary

Common Studio is an open, public-domain music production studio in software. This plan covers the first slice of its spine: a correct core model with a hashable score representation, a gate that refuses any work without licence evidence, checks that catch musical errors before any audio is made, and the sourcing and asset licence policy those gates enforce. It is a good deed because it is the licence-clean foundation for a catalogue of recordings anyone may use for anything.

## Scope

In scope: the core model and score representation with the recording-id grammar, a licence audit script, the sourcing and asset licence policy, ingest of ABC, MusicXML, MIDI and LilyPond with the evidence gate, and the pre-render checkers with waivers. The code lives under `src/`, the audit script under `scripts/` and the policy document under `policy/`. Out of scope: rendering, mixing, mastering, audio output, a catalogue of recordings, a studio application, and any copying from the owner's private reference pipeline.

## Risk

Medium. There is no personal data and no high-stakes advice, and the beneficiaries are the public. The dominant risk is licence contamination of a public-domain catalogue, which would destroy its credibility. The second risk is copying text, values or assets from the owner's private reference pipeline, which carries no licence and vendors GPL, LGPL and CC-BY assets. Both are handled by the licence audit script, the evidence gate, a written clean-room rule, and a named clean-room reviewer; the clean-room review is recorded in M1 and applies to the pull requests of M2 and M3 as well. The project opts into `ai-full` at medium because every deliverable is code or one plain document with a deterministic test or a stated check, and no outside beneficiary depends on it yet. It sets no `expertReview`.

## Approach

Three milestones, each a small set of code or document tasks worked on the donated lane and shipped as a GitHub release. M1 holds the core, the licence audit script and the policy, because every later gate depends on them. M2 adds ingest, which needs the core and the policy. M3 adds the checkers, which need the core. Each task's evidence is the acceptance row it covers: passing tests on authored fixtures, a fuzz test per parser, a copyleft fixture that makes the audit fail, and the policy document read against its checklist. The clean-room reviewer records a review that the text, values and fixtures were authored new. A person types the plan's digest at each `ship`, and the release asset is fetched back and compared.

## Definition of shipped

For each milestone, a GitHub release exists on the project repository, its assets fetched back from GitHub match the bytes in the repository, every acceptance row of the milestone is covered by recorded evidence, and `SHIPPED.md` records it. Adoption by a partner organisation is not part of this plan's three milestones and is recorded as an open outcome until one is secured.
