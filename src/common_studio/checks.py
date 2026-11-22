"""The pre-render checker stage.

One blocking check (harmony clash) and three warning checks (voice leading, instrument range, voicing) read an
arrangement and report findings that name the bar. The only way past a blocking finding is a recorded waiver with a
written reason, kept on the arrangement. ``run_stage`` returns a machine-readable ``StageResult``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Optional

from .model import Arrangement, Note, Part, Waiver

STAGE = "pre-render-check"
BLOCK = "block"
WARN = "warn"

# MIDI pitch ranges (lowest, highest) by instrument name. Authored for this project; an arrangement may pass its own.
INSTRUMENT_RANGES: dict[str, tuple[int, int]] = {
    "flute": (60, 96),
    "violin": (55, 103),
    "cello": (36, 76),
    "upright": (28, 67),
    "choir": (48, 84),
    "piano": (21, 108),
    "guitar": (40, 88),
}


@dataclass(frozen=True)
class Finding:
    check: str
    kind: str
    severity: str
    bar: int
    message: str
    parts: tuple[str, ...] = ()
    waived: bool = False

    def to_dict(self) -> dict:
        return {"check": self.check, "kind": self.kind, "severity": self.severity, "bar": self.bar,
                "message": self.message, "parts": list(self.parts), "waived": self.waived}


@dataclass(frozen=True)
class CheckResult:
    check: str
    severity: str
    findings: tuple[Finding, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict:
        return {"check": self.check, "severity": self.severity, "passed": self.passed,
                "findings": [f.to_dict() for f in self.findings]}


@dataclass(frozen=True)
class StageResult:
    """Verdict is ``blocked`` (an unwaived blocker), ``waived`` (blockers all waived), ``warn`` or ``pass``."""

    stage: str
    arrangement: str
    verdict: str
    checks: tuple[CheckResult, ...]
    waivers: tuple[Waiver, ...] = ()

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(f for c in self.checks for f in c.findings)

    @property
    def blocked(self) -> bool:
        return self.verdict == "blocked"

    def to_dict(self) -> dict:
        return {"stage": self.stage, "arrangement": self.arrangement, "verdict": self.verdict,
                "checks": [{"check": c.check, "severity": c.severity, "passed": c.passed} for c in self.checks],
                "findings": [f.to_dict() for f in self.findings],
                "waivers": [w.to_dict() for w in self.waivers]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class BlockedError(Exception):
    """Raised when the stage is blocked and no waiver covers the blocker."""

    def __init__(self, result: StageResult):
        self.result = result
        bars = sorted({f.bar for f in result.findings if f.severity == BLOCK and not f.waived})
        super().__init__(f"{result.arrangement}: blocked by harmony clash in bar(s) {', '.join(map(str, bars))}; "
                         "only a waiver with a written reason can pass it")


# ---------------------------------------------------------------- helpers

def _bar(arr: Arrangement, beat: Fraction) -> int:
    return arr.grid.bar_of(beat)


def _sounding(part: Part, t: Fraction) -> Optional[Note]:
    """The latest-started note of the part that is sounding at beat t."""
    hit = None
    for n in part.notes:
        if n.beat <= t < n.beat + n.duration and (hit is None or n.beat >= hit.beat):
            hit = n
    return hit


def _onsets(arr: Arrangement) -> list[Fraction]:
    return sorted({n.beat for p in arr.parts for n in p.notes})


def _dedupe(findings: list[Finding]) -> tuple[Finding, ...]:
    seen, out = set(), []
    for f in sorted(findings, key=lambda f: (f.bar, f.kind, f.parts, f.message)):
        key = (f.bar, f.kind, f.parts)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return tuple(out)


# ---------------------------------------------------------------- checks

def check_harmony_clash(arr: Arrangement) -> CheckResult:
    """Blocks when two different parts sound a semitone, major seventh or minor ninth apart at the same time."""
    found = []
    for i, a in enumerate(arr.parts):
        for b in arr.parts[i + 1:]:
            for x in a.notes:
                for y in b.notes:
                    start = max(x.beat, y.beat)
                    if start < min(x.beat + x.duration, y.beat + y.duration):
                        d = abs(x.pitch - y.pitch)
                        if d % 12 in (1, 11) and d != 0:
                            bar = _bar(arr, start)
                            found.append(Finding("harmony-clash", "harmony-clash", BLOCK, bar,
                                                 f"bar {bar}: {a.name} and {b.name} clash ({x.pitch} against {y.pitch})",
                                                 (a.name, b.name)))
    return CheckResult("harmony-clash", BLOCK, _dedupe(found))


def check_voice_leading(arr: Arrangement) -> CheckResult:
    """Warns on parallel fifths and octaves between two parts that both move in the same direction."""
    found = []
    onsets = _onsets(arr)
    for i, a in enumerate(arr.parts):
        for b in arr.parts[i + 1:]:
            prev = None
            for t in onsets:
                x, y = _sounding(a, t), _sounding(b, t)
                if x is None or y is None:
                    prev = None
                    continue
                cur = (x.pitch, y.pitch)
                if prev is not None:
                    da, db = cur[0] - prev[0], cur[1] - prev[1]
                    ip, ic = abs(prev[0] - prev[1]), abs(cur[0] - cur[1])
                    if da and db and (da > 0) == (db > 0) and ip % 12 == ic % 12 and ic % 12 in (0, 7):
                        kind = "parallel-fifths" if ic % 12 == 7 else "parallel-octaves"
                        bar = _bar(arr, t)
                        found.append(Finding("voice-leading", kind, WARN, bar,
                                             f"bar {bar}: {kind.replace('-', ' ')} between {a.name} and {b.name}",
                                             (a.name, b.name)))
                prev = cur
    return CheckResult("voice-leading", WARN, _dedupe(found))


def check_instrument_range(arr: Arrangement, ranges: Optional[dict[str, tuple[int, int]]] = None) -> CheckResult:
    """Warns on notes outside the range of the part's instrument (voice, else kit). Unknown instruments are skipped."""
    table = INSTRUMENT_RANGES if ranges is None else ranges
    found = []
    for p in arr.parts:
        name = (p.voice or p.kit or "").lower()
        if name not in table:
            continue
        lo, hi = table[name]
        for n in p.notes:
            if not lo <= n.pitch <= hi:
                bar = _bar(arr, n.beat)
                found.append(Finding("instrument-range", "out-of-range", WARN, bar,
                                     f"bar {bar}: {p.name} ({name}) plays {n.pitch}, outside {lo}-{hi}", (p.name,)))
    return CheckResult("instrument-range", WARN, _dedupe(found))


def check_voicing(arr: Arrangement) -> CheckResult:
    """Warns on chords of three or more notes with a gap over an octave between upper notes, or notes less than a
    minor third apart below C3 (MIDI 48)."""
    found = []
    for t in _onsets(arr):
        notes = sorted((n.pitch, p.name) for p in arr.parts if (n := _sounding(p, t)) is not None)
        if len(notes) < 3:
            continue
        bar = _bar(arr, t)
        names = tuple(sorted({nm for _, nm in notes}))
        for (lo, _), (hi, _) in zip(notes[1:], notes[2:]):
            if hi - lo > 12:
                found.append(Finding("voicing", "wide-spacing", WARN, bar,
                                     f"bar {bar}: upper notes {lo} and {hi} are more than an octave apart", names))
        for (lo, _), (hi, _) in zip(notes, notes[1:]):
            if lo < 48 and 0 < hi - lo < 3:
                found.append(Finding("voicing", "muddy-low-interval", WARN, bar,
                                     f"bar {bar}: notes {lo} and {hi} are too close in the low register", names))
    return CheckResult("voicing", WARN, _dedupe(found))


CHECKS: tuple[Callable[[Arrangement], CheckResult], ...] = (
    check_harmony_clash, check_voice_leading, check_instrument_range, check_voicing,
)


# ---------------------------------------------------------------- stage and waivers

def waive(arr: Arrangement, check: str, reason: str, bars: tuple[int, ...] = (), by: Optional[str] = None) -> Arrangement:
    """Return the arrangement with a recorded waiver. Refuses a missing reason and any check that cannot block."""
    if check != "harmony-clash":
        raise ValueError(f"only a blocking check can be waived, not {check!r}")
    return replace(arr, waivers=arr.waivers + (Waiver(check, reason, tuple(bars), by),))


def run_stage(arr: Arrangement) -> StageResult:
    """Run every check. Blocking findings covered by a waiver recorded on the arrangement are marked waived."""
    results = []
    for fn in CHECKS:
        r = fn(arr)
        findings = tuple(
            replace(f, waived=True) if f.severity == BLOCK and any(w.covers(f.check, f.bar) for w in arr.waivers) else f
            for f in r.findings)
        results.append(CheckResult(r.check, r.severity, findings))
    all_f = [f for r in results for f in r.findings]
    blockers = [f for f in all_f if f.severity == BLOCK]
    if any(not f.waived for f in blockers):
        verdict = "blocked"
    elif blockers:
        verdict = "waived"
    elif all_f:
        verdict = "warn"
    else:
        verdict = "pass"
    return StageResult(STAGE, arr.id, verdict, tuple(results), arr.waivers)


def require_clear(arr: Arrangement) -> StageResult:
    """Gate for the render step: return the result, or raise BlockedError when a blocker has no waiver."""
    result = run_stage(arr)
    if result.blocked:
        raise BlockedError(result)
    return result
