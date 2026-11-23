"""Evidence records: the check that a work has a complete ``composition``, ``edition`` and ``lyrics`` record.

The sourcing policy (``policy/sourcing-and-asset-licence-policy.md``, sections 3 and 9) says each of the three records
needs non-empty ``source``, ``basis``, ``checked_at`` and ``checker`` fields. ``lyrics`` may carry ``value: none`` for a
work with no words, and still needs the four fields. ``check_evidence`` returns every problem it finds, by record, so a
refusal names each record that is missing or incomplete.

Released under the Unlicense.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

from .sources import RECORDS

FIELDS = ("source", "basis", "checked_at", "checker")
LYRICS_VALUES = ("none", "words")

# A checker is a real person: the policy rules out tools, bots and "unknown".
_NOT_A_PERSON = re.compile(r"^(?:unknown|n/?a|none|nobody|anonymous|anon|tbd|todo|bot|tool|script|ci|auto(?:mated)?)$"
                           r"|\[bot\]$|-bot$", re.I)
_SECRET_PARAM = re.compile(r"token|key|secret|passw|sig|auth|credential|session", re.I)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _check_source(source: str) -> list[str]:
    text = source.strip()
    if "://" not in text:
        return []
    try:
        url = urlsplit(text)
        url.port  # noqa: B018 - raises on a malformed port
    except ValueError:
        return ["source is not a readable URL"]
    problems = []
    if url.scheme.lower() != "https":
        problems.append("source URL must use https")
    if url.username or url.password or "@" in url.netloc:
        problems.append("source URL must not carry credentials")
    if any(_SECRET_PARAM.search(k) for k, _ in parse_qsl(url.query, keep_blank_values=True)):
        problems.append("source URL must not carry a token or key")
    return problems


def _plain(value: Any, depth: int = 0) -> bool:
    """True when a value can be written to work.yaml: text, numbers, booleans, lists and mappings of those."""
    if depth > 8:
        return False
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_plain(v, depth + 1) for v in value)
    if isinstance(value, Mapping):
        return all(isinstance(k, str) and _plain(v, depth + 1) for k, v in value.items())
    return False


def check_record(name: str, record: Any) -> list[str]:
    """The problems with one evidence record; empty when it is complete."""
    if record is None:
        return ["missing"]
    if not isinstance(record, Mapping):
        return ["is not a record of fields"]
    problems = []
    for f in FIELDS:
        value = record.get(f)
        if _blank(value):
            problems.append(f"{f} is missing or empty")
        elif not isinstance(value, str):
            problems.append(f"{f} must be text")
    checked_at = record.get("checked_at")
    if isinstance(checked_at, str) and checked_at.strip():
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_at.strip()):
                raise ValueError
            _dt.date.fromisoformat(checked_at.strip())
        except ValueError:
            problems.append("checked_at must be a UTC date written YYYY-MM-DD")
    checker = record.get("checker")
    if isinstance(checker, str) and checker.strip() and _NOT_A_PERSON.search(checker.strip()):
        problems.append("checker must name a real person, not a tool, a bot or 'unknown'")
    source = record.get("source")
    if isinstance(source, str) and source.strip():
        problems.extend(_check_source(source))
    if "value" in record:
        value = record.get("value")
        if name != "lyrics":
            problems.append("only the lyrics record takes a value")
        elif value not in LYRICS_VALUES:
            problems.append("lyrics value is 'none' for a work with no words, or 'words'")
    for key, value in record.items():
        if not isinstance(key, str) or not _plain(value):
            problems.append(f"field {str(key)[:40]!r} holds a value that cannot be recorded")
    return problems


def check_evidence(evidence: Any) -> dict[str, list[str]]:
    """Every problem with a work's evidence, by record name. An empty result means the evidence is complete."""
    if not isinstance(evidence, Mapping):
        return {name: ["missing"] for name in RECORDS}
    problems: dict[str, list[str]] = {}
    for name in RECORDS:
        found = check_record(name, evidence.get(name))
        if found:
            problems[name] = found
    return problems


def describe(problems: Mapping[str, list[str]]) -> str:
    parts = []
    for name in RECORDS:
        if name not in problems:
            continue
        found = problems[name]
        if found == ["missing"]:
            parts.append(f"the {name} evidence record is missing")
        else:
            parts.append(f"the {name} evidence record is incomplete: {'; '.join(found)}")
    return "; ".join(parts)


def lyrics_are_none(evidence: Mapping[str, Any]) -> bool:
    record = evidence.get("lyrics")
    return isinstance(record, Mapping) and record.get("value") == "none"
