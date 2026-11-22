"""Licence audit: list the licence of every installed distribution and fail on copyleft.

Usage::

    python scripts/license_audit.py              # audit the interpreter's installed tree
    python scripts/license_audit.py --path DIR   # audit only the distributions found in DIR (repeatable)

The licence of each distribution is read from its own metadata, in this order:
``License-Expression`` (PEP 639), then the ``License`` field, then ``License ::`` trove classifiers.
Exit status is 1 when any distribution carries a copyleft licence, and 0 otherwise. A distribution
whose licence cannot be read is listed as ``UNKNOWN``; it is reported but does not change the exit status.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Patterns that mark a licence as copyleft. Matched case-insensitively against the licence text.
# Covers the GPL family (GPL, LGPL, AGPL, including GNU-spelled names), plus EUPL, MPL, EPL, CDDL,
# CPL and OSL, which are copyleft to a degree that matters for redistribution of a catalogue.
COPYLEFT_PATTERNS = (
    re.compile(r"gpl", re.IGNORECASE),
    re.compile(r"gnu\s+(lesser\s+|affero\s+)?general\s+public", re.IGNORECASE),
    re.compile(r"\beupl\b", re.IGNORECASE),
    re.compile(r"\bmpl\b", re.IGNORECASE),
    re.compile(r"mozilla\s+public", re.IGNORECASE),
    re.compile(r"\bepl\b", re.IGNORECASE),
    re.compile(r"\bcddl\b", re.IGNORECASE),
    re.compile(r"\bcpl\b", re.IGNORECASE),
    re.compile(r"\bosl\b", re.IGNORECASE),
)

UNKNOWN = "UNKNOWN"
CLASSIFIER_PREFIX = "License :: "


@dataclass(frozen=True)
class Finding:
    name: str
    version: str
    licence: str
    copyleft: bool


def is_copyleft(licence: str) -> bool:
    return any(pattern.search(licence) for pattern in COPYLEFT_PATTERNS)


def licence_of(meta) -> str:
    """Return the licence string for one distribution's metadata, or UNKNOWN."""
    expression = (meta.get("License-Expression") or "").strip()
    if expression:
        return expression

    field = (meta.get("License") or "").strip()
    # Some projects put the whole licence text in the License field; the first line names it.
    if field:
        return field.splitlines()[0].strip() or UNKNOWN

    classifiers = [
        c[len(CLASSIFIER_PREFIX):].strip()
        for c in (meta.get_all("Classifier") or [])
        if c.startswith(CLASSIFIER_PREFIX)
    ]
    if classifiers:
        return "; ".join(classifiers)
    return UNKNOWN


def audit(paths: list[str] | None = None) -> list[Finding]:
    """Audit the installed distributions, or only those found in ``paths`` when given."""
    if paths:
        distributions = metadata.distributions(path=[str(p) for p in paths])
    else:
        distributions = metadata.distributions()
    findings = {}
    for dist in distributions:
        meta = dist.metadata
        name = meta.get("Name") or dist.name or "?"
        version = meta.get("Version") or dist.version or "?"
        licence = licence_of(meta)
        key = (name.lower(), version)
        findings[key] = Finding(name, version, licence, is_copyleft(licence))
    return sorted(findings.values(), key=lambda f: (f.name.lower(), f.version))


def render(findings: list[Finding]) -> str:
    lines = [f"{'PACKAGE':<32} {'VERSION':<16} {'LICENCE':<48} VERDICT"]
    for f in findings:
        verdict = "COPYLEFT" if f.copyleft else ("unknown" if f.licence == UNKNOWN else "ok")
        lines.append(f"{f.name:<32} {f.version:<16} {f.licence[:48]:<48} {verdict}")
    copyleft = [f for f in findings if f.copyleft]
    lines.append("")
    lines.append(f"{len(findings)} distribution(s) audited, {len(copyleft)} copyleft.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--path",
        action="append",
        type=Path,
        default=None,
        help="audit distributions found in this directory instead of the installed tree (repeatable)",
    )
    args = parser.parse_args(argv)

    findings = audit(args.path)
    print(render(findings))

    offending = [f for f in findings if f.copyleft]
    if offending:
        names = ", ".join(f"{f.name} {f.version} ({f.licence})" for f in offending)
        print(f"FAIL: copyleft licence in: {names}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
