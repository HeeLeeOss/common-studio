# Common Studio sourcing policy and asset licence policy

Status: version 1, milestone M1, acceptance row AC-09.
Licence: this document is released under CC0-1.0 (see [Licence of this document](#11-licence-of-this-document)).

This document covers two things:

1. **The sourcing policy.** It says which compositions, editions and lyrics Common Studio may ingest, from
   which sources, and what evidence must be recorded first.
2. **The asset licence policy.** It says which non-score assets (samples, instruments, impulse responses,
   fonts, test fixtures and similar) may enter the project, under which licences, and how each one is recorded.

The ingest gate (milestone M2) enforces the sourcing policy. The asset manifests enforce the asset licence
policy. Where this document and the code disagree, this document is the intended behaviour, and the code is
the thing to fix.

This document is an engineering policy. It is not legal advice. Copyright law changes, and a checker who is in
any doubt must refuse (see [The rule of doubt](#2-the-rule-of-doubt)) and ask a maintainer, who may ask a
qualified person.

---

## Contents

1. [Purpose and terms](#1-purpose-and-terms)
2. [The rule of doubt](#2-the-rule-of-doubt)
3. [Evidence records](#3-evidence-records)
4. [What counts as a basis](#4-what-counts-as-a-basis)
5. [Source classes](#5-source-classes)
6. [Asset manifest entries](#6-asset-manifest-entries)
7. [Allowed and refused asset licences](#7-allowed-and-refused-asset-licences)
8. [The clean-room rule for the private reference pipeline](#8-the-clean-room-rule-for-the-private-reference-pipeline)
9. [How the policy is enforced](#9-how-the-policy-is-enforced)
10. [Changing this policy](#10-changing-this-policy)
11. [Licence of this document](#11-licence-of-this-document)

---

## 1. Purpose and terms

Common Studio turns public-domain compositions into recordings that anyone may use for anything, including
commercially, with no permission and no payment. A single contaminated work or asset would undermine trust in the
whole catalogue. So the project asks for evidence before anything comes in, and it refuses anything that cannot
show evidence.

Terms used in this document:

- **Work**: one musical composition, as held by the core model (`Work`).
- **Composition**: the music itself (melody, harmony, form), as created by its composer or composers. This
  includes any arranger whose arrangement is the version being ingested.
- **Edition**: the specific printed, engraved, manuscript or digital text of the work that the project reads. An
  edition can add protected material of its own, such as editorial changes, a new typographical arrangement or a
  critical apparatus.
- **Lyrics**: words sung or spoken with the work, including any translation of them.
- **Source**: the place a file or a fact was obtained from.
- **Asset**: any file other than a score that the project ships, renders with or tests with, such as a sample,
  sound font, impulse response, instrument definition, font, image or fixture.
- **Checker**: the named person who verified a record and is accountable for it.
- **Certificate**: the provenance record that goes with each recording the studio produces. It lists the work's
  evidence records and every asset that contributed to the recording.
- **Private reference pipeline**: the project owner's earlier, private, unlicensed music pipeline (see
  [section 8](#8-the-clean-room-rule-for-the-private-reference-pipeline)).

## 2. The rule of doubt

If a checker cannot show, with a written basis, that a work, edition, lyric or asset is free for anyone to use,
adapt and sell, it is refused. "Probably fine", "everyone uses it", "it is old", "it was on a free site" and
"royalty-free" are not a basis. A refusal costs one tune. A mistake costs the catalogue.

---

## 3. Evidence records

Every work has exactly three evidence records: `composition`, `edition` and `lyrics`. The ingest gate refuses a
work if any of the three is missing or incomplete, and the refusal names each record that is missing or
incomplete. The gate writes complete records to the work's `work.yaml`.

### 3.1 Fields

Each record has these four fields. All four are required, and none may be empty.

| Field | Meaning | Form |
|---|---|---|
| `source` | Where the material or the fact came from: a stable URL, a library shelf mark or catalogue number, or a bibliographic citation precise enough for someone else to find the same item | Text. A URL must use `https` and must not contain a token or credentials |
| `basis` | Why the material is free to use: the specific facts and the rule applied to them, as set out in [section 4](#4-what-counts-as-a-basis) | Text, specific enough that another checker can repeat the check |
| `checked_at` | The day the checker made the check | A UTC date, `YYYY-MM-DD` |
| `checker` | The person who made the check and answers for it | A name or a stable project handle of a real person. Not a tool, a bot or "unknown" |

A record may carry extra fields, such as `notes` or `jurisdictions`. Extra fields do not replace any of the four
required fields.

### 3.2 The three records

- **`composition`** records why the music itself is in the public domain, or was dedicated to it.
- **`edition`** records why the specific text the project reads is free of the editor's, engraver's or
  publisher's own rights, or that it was made by the project itself from a free source.
- **`lyrics`** records why the words, and any translation of them, are free. A purely instrumental work still
  needs this record. Its value is `none`, which means the work has no words and the project adds none. When the
  value is `none`, `source`, `basis`, `checked_at` and `checker` record where the checker confirmed that the
  edition has no text. If lyrics are added later, the record must be replaced with a full lyrics record before
  anything is rendered.

### 3.3 Example

The example below is authored for this document. It shows the shape only. The work, people and citations are
placeholders.

```yaml
work: example-air
evidence:
  composition:
    source: "Placeholder citation: composer's entry in a national biographical dictionary"
    basis: "Sole composer died 1801. Life+70 rule: public domain since 1872 in EU and UK. First published 1790, before the US publication cut-off. No arranger."
    checked_at: "2026-11-22"
    checker: "a-named-person"
  edition:
    source: "Placeholder citation: facsimile scan of the 1790 first printing, library shelf mark 0000"
    basis: "Printed 1790; any typographical or editorial right has expired. Transcribed by the project from the facsimile; no later edition consulted."
    checked_at: "2026-11-22"
    checker: "a-named-person"
  lyrics:
    value: none
    source: "Same facsimile as the edition"
    basis: "Instrumental piece; the printing has no underlaid or attached text."
    checked_at: "2026-11-22"
    checker: "a-named-person"
```

---

## 4. What counts as a basis

A basis is a fact plus the rule that makes the fact sufficient. The project releases recordings for worldwide
use, so a basis must hold in every **required jurisdiction**:

- **The United States**, under its publication-date rule and its term for unpublished works.
- **Life-plus-70 jurisdictions**, including the European Union, the European Economic Area and the United Kingdom.

A checker must also record any longer term or extension that they know applies to the author, and must refuse if
one applies. Examples are countries with terms longer than life plus 70 years, and wartime extensions for some
authors in some countries. A basis that holds only in a shorter-term jurisdiction is not enough. For example,
"public domain in a life-plus-50 country" does not pass on its own.

The year rules below use the year in which `checked_at` falls. A term runs to the end of the calendar year, so a
work enters the public domain on 1 January of the following year.

### 4.1 Composition: author death dates by jurisdiction, and publication facts

Accepted bases, in order of preference:

1. **Death dates.** The death year of **every** author of the composition: the composer, every co-composer, and
   the arranger if the ingested version is an arrangement. Each death year must come from a cited reference. The
   latest death year decides.
   - Life-plus-70 jurisdictions: the death year must be at least 71 years before the year of the check. For
     example, a check in 2026 accepts authors who died in 1955 or earlier.
   - The United States: also meet the publication test in item 2. If the work was never published, apply life
     plus 70 to the latest death year.
2. **Publication facts.** The year and place of first publication, with a cited source such as a dated first
   printing, a catalogue entry or a legal-deposit record.
   - The United States: the work must have been published more than 95 years before 1 January of the year of the
     check. In 2026, that means published in 1930 or earlier.
   - Publication facts never replace death dates for the life-plus-70 jurisdictions. An old publication date for a
     composer who died recently does not pass.
3. **Anonymous or pseudonymous works** whose author cannot be identified: use the first-publication year, which
   must be more than 70 years before the year of the check. The record must say that, and how, the checker looked
   for the author's identity. If the author is later identified, the death-date rule replaces this basis.
4. **Traditional and folk material.** "Traditional" is not a basis on its own. The checker must cite the earliest
   publication fact that shows the tune already circulating, and that fact must meet item 2. The specific version
   the project uses must also pass the edition record. A collector's or arranger's own version is a new
   composition with its own author.
5. **A dedication by the rights holder.** A written, worldwide, irrevocable dedication to the public domain, such
   as CC0-1.0 or the Unlicense, made by every rights holder of the composition. The basis cites the dedication
   and shows that the person dedicating actually held the rights.

Not accepted: an undated year such as "c. 1800" with no source; a death year from an unsourced web page; a
licence label on a hosting site with no further fact; or "public domain" with no reason given.

### 4.2 Edition: edition provenance

The edition record must show where the specific text came from and why that text adds no live rights. Accepted
bases:

1. **Project transcription from an old printing.** The project transcribed the notes itself, directly from a
   facsimile of a printing or manuscript. That printing must meet the publication test in
   [section 4.1](#41-composition-author-death-dates-by-jurisdiction-and-publication-facts), item 2, and it must be
   old enough that any typographical-arrangement or editorial right has expired. Such rights typically last 25 to
   30 years from publication. The record names the exact printing, such as a shelf mark, scan identifier or
   edition statement. It must also state that the project consulted no later edition for notes, fingering,
   dynamics or corrections.
2. **An edition whose own contributor dedicated it.** A modern edition or transcription can be used when every
   editor and engraver dedicated their contribution under CC0-1.0, the Unlicense or an equivalent worldwide
   dedication. The record cites that dedication. Even then, the composition record must still pass on its own.
3. **An expired modern edition.** An edition whose editor died long enough ago to pass the death-date rule, and
   whose publication passes the publication test, judged as if the editor were an author.

Not accepted: a modern critical or urtext edition still in term, even when the music is old; a first
publication of a previously unpublished old work (editio princeps) that is still within its term; a file whose
licence label is shared-alike, non-commercial or no-derivatives; or a digital file of unknown origin.

### 4.3 Lyrics: lyric authorship

The lyrics record needs the death date of every author of the words, plus the same publication facts as the
composition. The rules are the same as in [section 4.1](#41-composition-author-death-dates-by-jurisdiction-and-publication-facts).
Specifically:

- **Lyricist separate from composer.** The lyricist is checked on their own. A public-domain tune with
  in-copyright words is refused unless the words are removed. In that case, the record becomes `none` for an
  instrumental version.
- **Translation.** Each translator is an author of the lyric that is used, and must pass on their own. The
  original-language author must also pass.
- **Added or altered verses.** Any modern addition, such as an extra verse, a modernised spelling with creative
  changes or a reworked refrain, has its own author and must pass. If it does not, the project uses only the
  verses with a basis.
- **Traditional words.** These follow [section 4.1](#41-composition-author-death-dates-by-jurisdiction-and-publication-facts),
  item 4. The checker cites the earliest publication of the exact words used.
- **Words written for the project.** The author dedicates them under CC0-1.0 in writing before import, and the
  record cites that dedication.

---

## 5. Source classes

Every source that a score, lyric or fact comes from belongs to one of three classes. The ingest gate reads the
class from the source registry kept with the gate. A source that is not in the registry is treated as
**verify-only** until a maintainer classifies it. Classes are kinds of source. A maintainer adds specific
sources to the registry under one of these kinds, giving the reason.

### 5.1 Allowed

The ingest gate accepts material from these sources once the three evidence records are complete.

| Source kind | Reason |
|---|---|
| Facsimile scans of printed or manuscript music that pass the publication test, transcribed by the project | The project creates the digital text itself, so no editor's or encoder's rights enter, and the printing date can be checked |
| Material written for the project and dedicated under CC0-1.0 or the Unlicense by its named author before import | The rights holder is known, and the dedication is written and on record |
| Holdings of national libraries and public archives, for **facts** such as death dates, publication dates and catalogue records | Facts are not protected, and these institutions are reliable, citable references |

### 5.2 Verify-only

Material from these sources may be ingested, but the gate **flags** each work. A maintainer, not the checker
who made the record, must confirm each file's basis before the work leaves the gate. A flagged work stays
flagged until the confirmation is recorded.

| Source kind | Reason |
|---|---|
| Community score libraries that host files under mixed licences | Licences vary per file, some files are free only in some countries, and the uploader may not be the rights holder |
| Community-contributed collections of folk and dance tunes in text notations such as ABC | Transcribers may not have dedicated their work, versions are often modern settings, and "traditional" labels are often unsourced |
| Digitised editions from libraries and archives where the scan is free but the edition's date or editor is unclear | The edition record cannot be completed without further research |
| Reference works and encyclopaedias, used for death dates and publication facts | Usually correct, but sometimes conflicting or unsourced, so each fact must be confirmed against a second source |
| A maintainer's own earlier transcriptions made outside the project | The maintainer must show what edition they worked from and dedicate the transcription before import |

### 5.3 Banned

The gate refuses material from these sources **even when the tune itself is in the public domain**. A public-domain
composition does not clean an edition, an encoding or a set of terms that carries rights or hides provenance. If
the tune is wanted, the project goes back to an allowed source, such as an old printing, and transcribes it.

| Source kind | Reason |
|---|---|
| The private reference pipeline, including its text, configuration values, arrangement sources, skills and assets | It carries no licence and includes copyleft and attribution-licensed material. See [section 8](#8-the-clean-room-rule-for-the-private-reference-pipeline) |
| Commercial or in-term modern editions, whether printed, digital or app-based | The editor's, engraver's and publisher's own rights are live, even when the music is old |
| Transcriptions made by ear or by software from recordings of in-term performances or arrangements | They copy the performer's or arranger's protected choices, and the recording itself may be protected |
| Files under shared-alike, non-commercial or no-derivatives terms, or with no stated licence | The project's output must be usable by anyone for anything, without conditions |
| Sites whose terms of use forbid copying, scraping or reuse, or that need a paid account to access | Using them breaches their terms, whatever the status of the music |
| Uploads with no identifiable source, such as file-sharing sites, unattributed reposts and "free sheet music" aggregators | Provenance cannot be shown, so no edition record is possible |
| Output of generative tools whose training data or terms of service do not clearly leave the output free of conditions | Provenance and rights in the output cannot be shown |

---

## 6. Asset manifest entries

Every asset in the repository, in a build or in a render is listed in an asset manifest, including assets used
only by tests. An asset that is not in a manifest may not be used. Each entry has these four required fields:

| Field | Meaning | Form |
|---|---|---|
| `source` | Where the asset came from: an `https` URL, a citation, or `authored` with the author's name if it was made for the project | Text, with no token or credentials |
| `licence` | The asset's licence, from the allowed set in [section 7.1](#71-allowed-licences) | An SPDX identifier where one exists, or `public-domain` together with a basis |
| `checked_at` | The day the checker confirmed the licence at the source | A UTC date, `YYYY-MM-DD` |
| `checker` | The named person who confirmed it | A name or stable project handle of a real person |

The following fields are needed when they apply:

- `path`: the asset's path in the repository or build, and `sha256`: a hash of the exact bytes checked, so a
  changed file is caught.
- `basis`: required when `licence` is `public-domain`. It gives a death date, publication fact or dedication, as
  in [section 4](#4-what-counts-as-a-basis).
- `attribution`: required when the licence asks for attribution. It gives the creator, the notice to reproduce,
  and whether the asset was modified.

Authored example (placeholders only):

```yaml
- path: assets/ir/small-room.wav
  sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  source: "authored: a-named-person"
  licence: CC0-1.0
  checked_at: "2026-11-22"
  checker: "a-named-person"
```

---

## 7. Allowed and refused asset licences

### 7.1 Allowed licences

An asset is allowed only if its licence lets anyone use it, modify it and sell works derived from it, with no
share-alike condition. These licences are allowed:

1. **Public domain**, with a recorded basis, as in [section 4](#4-what-counts-as-a-basis).
2. **Public-domain dedications**: CC0-1.0 and the Unlicense.
3. **Permissive licences that allow commercial derivatives**: for example MIT, BSD-2-Clause, BSD-3-Clause,
   Apache-2.0, ISC, Zlib and CC-BY-4.0. A maintainer may add a licence to this list only if it allows commercial
   use and modification and has no share-alike or field-of-use condition.

**Attribution-only assets.** When an allowed licence asks for attribution, as CC-BY-4.0, MIT, BSD and Apache-2.0
do, the manifest entry's `attribution` field holds the required notice. That notice is copied into the
**certificate** of every recording the asset contributes to, and into the release notes of any release that
ships the asset. A render that uses an attribution-only asset but whose certificate lacks the attribution is
refused.

### 7.2 Refused licences

These are refused for **every** purpose, including test fixtures, examples, development-only samples and
temporary local experiments that are committed:

- **Non-commercial** terms, for example any CC licence with NC or a "personal use only" licence.
- **No-derivatives** terms, for example any CC licence with ND.
- **Share-alike and copyleft** terms, for example any CC licence with SA, and the GPL, LGPL, AGPL and MPL
  families. This also keeps assets consistent with the dependency rule that the licence audit enforces.
- **Custom, "royalty-free" and end-user licences** that limit redistribution, the number of users or the field of
  use, or that need registration.
- **No licence, or an unknown licence.** The absence of a licence means that all rights are reserved.

Tests receive no exemption. A test fixture is shipped in the repository and copied by everyone who clones it, so
it must meet the same rule as a shipped asset. Fixtures should be authored for the project and dedicated under
the project's terms.

---

## 8. The clean-room rule for the private reference pipeline

The project owner has an earlier, private music pipeline. It carries no licence, and it includes material under
the GPL, the LGPL and CC-BY. The rule for it is:

1. **Ideas may be consulted.** Contributors may look at it to learn what problems exist and what approaches can
   work, such as "check voice leading before rendering".
2. **Nothing is copied.** No text, code, comments, configuration value, parameter value, name, file format,
   arrangement source, score, fixture, prompt, skill or asset may be copied from it, closely paraphrased from it
   or transcribed from it. Every name, format and value in Common Studio is authored new. Contributors write from
   their understanding, not with the private pipeline open beside the new work.
3. **Dedication before import.** If the owner wants to bring in something the owner personally wrote, the owner
   must first record a written, worldwide, irrevocable dedication of that specific item under CC0-1.0 or the
   Unlicense. The record must name the item, its hash and the date, and it must be committed to the repository
   **before** the item is imported. The dedication covers only what the owner actually holds rights in. It can
   never cover the GPL, LGPL or CC-BY material vendored in the pipeline, which stays banned.
4. **Review.** A named clean-room reviewer records, for each milestone, that the text, values and fixtures were
   authored new (acceptance row AC-11). A suspected copy is removed first and investigated afterwards.

---

## 9. How the policy is enforced

- **The ingest gate** refuses a work unless `composition`, `edition` and `lyrics` each have non-empty `source`,
  `basis`, `checked_at` and `checker` fields. `lyrics` may have the value `none`, but it still needs those four
  fields. The refusal message names every missing or incomplete record. The gate refuses any work from a banned
  source, even if the tune is in the public domain, and flags any work from a verify-only source. It writes
  complete evidence to `work.yaml`.
- **Asset manifests** are checked to make sure every asset has `source`, `licence`, `checked_at` and `checker`; its
  licence is in the allowed set; an attribution-only asset has its `attribution`; and its bytes match its
  `sha256` when one is given.
- **The certificate** of a recording carries the work's three evidence records and the attribution of every
  attribution-only asset used.
- **The licence audit** (`scripts/license_audit.py`) fails the build on a copyleft software dependency. This
  policy applies the same rule to assets.
- **Re-checks.** A record or manifest entry is checked again when its source changes, when its hash changes or
  when a maintainer asks for it. The check is recorded with a new `checked_at`.

## 10. Changing this policy

Changes come through a pull request that states the reason, and a maintainer reviews them. A change that loosens
a rule, such as adding an allowed licence, moving a source kind to a less strict class or shortening a term rule,
needs a written reason. A change never makes a previously refused item acceptable after the fact without a new
check under the new rule.

## 11. Licence of this document

To the extent possible under law, the authors have dedicated this document to the public domain worldwide under
the Creative Commons CC0 1.0 Universal Public Domain Dedication (CC0-1.0):
<https://creativecommons.org/publicdomain/zero/1.0/>. It was written new for Common Studio. No text was copied
from the private reference pipeline or from any other private source.
