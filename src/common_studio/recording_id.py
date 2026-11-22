"""The recording-id grammar: ``work--style[@venue][+treatment]``.

Each part is a slug: lowercase letters and digits, with single hyphens between groups. A slug never holds a double
hyphen, which is what lets ``--`` separate the work from the style.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_RECORDING = re.compile(
    r"(?P<work>[a-z0-9]+(?:-[a-z0-9]+)*)--(?P<style>[a-z0-9]+(?:-[a-z0-9]+)*)"
    r"(?:@(?P<venue>[a-z0-9]+(?:-[a-z0-9]+)*))?"
    r"(?:\+(?P<treatment>[a-z0-9]+(?:-[a-z0-9]+)*))?"
)


def _check(label: str, value: Optional[str]) -> None:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ValueError(f"{label} must be lowercase letters and digits with single hyphens between groups")


def arrangement_id(work: str, style: str) -> str:
    """The id of an arrangement: ``work--style``."""
    _check("work", work)
    _check("style", style)
    return f"{work}--{style}"


@dataclass(frozen=True)
class RecordingId:
    """A parsed recording id."""

    work: str
    style: str
    venue: Optional[str] = None
    treatment: Optional[str] = None

    def __post_init__(self) -> None:
        _check("work", self.work)
        _check("style", self.style)
        if self.venue is not None:
            _check("venue", self.venue)
        if self.treatment is not None:
            _check("treatment", self.treatment)

    @property
    def arrangement(self) -> str:
        return arrangement_id(self.work, self.style)

    def __str__(self) -> str:
        return format_recording_id(self)


def format_recording_id(rid: RecordingId) -> str:
    """Write ``work--style``, then ``@venue`` if there is one, then ``+treatment`` if there is one."""
    text = f"{rid.work}--{rid.style}"
    if rid.venue is not None:
        text += f"@{rid.venue}"
    if rid.treatment is not None:
        text += f"+{rid.treatment}"
    return text


def parse_recording_id(text: str) -> RecordingId:
    """Read a recording id. Raises ``ValueError`` when the text does not match the grammar."""
    if not isinstance(text, str):
        raise ValueError("a recording id is text")
    match = _RECORDING.fullmatch(text)
    if match is None:
        raise ValueError(f"not a recording id (work--style[@venue][+treatment]): {text!r}")
    return RecordingId(match["work"], match["style"], match["venue"], match["treatment"])
