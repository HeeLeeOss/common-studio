"""The four ingest fixtures and their evidence records.

Each fixture is a short melody written for Common Studio as a test fixture, in the format it tests, and released
under the Unlicense with the rest of the repository. No earlier tune, edition or file was used. The gate's output for
each one is committed as ``fixtures/works/<work id>/work.yaml``; ``write_fixture_works`` regenerates those files.

Released under the Unlicense.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
WORKS_DIR = FIXTURES_DIR / "works"

CHECKER = "jdev1977"  # the maintainer named as checker; see the pull request's maintainer actions
CHECKED_AT = "2026-11-23"
ORIGIN = "authored: written for the Common Studio repository as a test fixture"

FILES = {
    "abc": "slate-roof-air.abc",
    "musicxml": "quarry-lane-hymn.musicxml",
    "midi": "mill-wheel-turning.mid",
    "lilypond": "lantern-path.ly",
}

_COMPOSITION_BASIS = (
    "An original melody written in 2026 for Common Studio as a test fixture, with no earlier tune as a model, and "
    "dedicated to the public domain worldwide under the Unlicense with the rest of the repository. No other author."
)
_EDITION_BASIS = (
    "The fixture file is the first and only text of the melody, written by the project in this format. No edition, "
    "score library or other file was consulted. Released under the Unlicense."
)
_NO_WORDS_BASIS = "Instrumental fixture: the file carries no lyric events, lyric elements or lyric lines."


def evidence(fmt: str) -> dict[str, Any]:
    """The complete evidence for the fixture of one format."""
    file = FILES[fmt]
    composition = {
        "source": f"authored: Common Studio fixture {file}",
        "basis": _COMPOSITION_BASIS,
        "checked_at": CHECKED_AT,
        "checker": CHECKER,
    }
    edition = {
        "source": f"authored: src/common_studio/ingest/fixtures/{file}",
        "basis": _EDITION_BASIS,
        "checked_at": CHECKED_AT,
        "checker": CHECKER,
    }
    if fmt == "abc":
        lyrics = {
            "value": "words",
            "source": f"authored: the w: line of src/common_studio/ingest/fixtures/{file}",
            "basis": ("Words written in 2026 for Common Studio with the melody, and dedicated to the public domain "
                      "worldwide under the Unlicense. No translation and no other author."),
            "checked_at": CHECKED_AT,
            "checker": CHECKER,
        }
    else:
        lyrics = {
            "value": "none",
            "source": f"authored: src/common_studio/ingest/fixtures/{file}",
            "basis": _NO_WORDS_BASIS,
            "checked_at": CHECKED_AT,
            "checker": CHECKER,
        }
    return {"composition": composition, "edition": edition, "lyrics": lyrics}


def fixture_bytes(fmt: str) -> bytes:
    return (FIXTURES_DIR / FILES[fmt]).read_bytes()


def write_fixture_works(out_dir: Union[str, Path] = WORKS_DIR) -> dict[str, Path]:
    """Run every fixture through the gate and write its work.yaml under ``out_dir``."""
    from .gate import ingest

    return {fmt: ingest(fixture_bytes(fmt), fmt, evidence(fmt), out_dir=out_dir, origin=ORIGIN).path
            for fmt in FILES}


if __name__ == "__main__":  # pragma: no cover
    for fmt, path in write_fixture_works().items():
        print(f"{fmt}: {path}")
