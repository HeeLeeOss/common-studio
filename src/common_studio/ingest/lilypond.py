"""LilyPond reader for a documented subset of the input language.

Read:

- ``\\header { title = "..." }`` for the title, and the first ``\\time n/d`` for the meter;
- notes in Dutch names (``c d e f g a b`` with ``is``/``es`` and ``isis``/``eses``), octave marks ``'`` and ``,``,
  durations with dots and ``*n/m`` multipliers, rests ``r`` and ``R``, skips ``s``, ties ``~`` and chords ``<c e g>4``;
- ``\\relative`` (with or without a start pitch), ``\\fixed``, sequential ``{ }`` and simultaneous ``<< >>`` music,
  ``\\\\`` voice separators, ``\\tuplet`` and ``\\times``, ``\\repeat unfold`` (unrolled) and other repeats (read once);
- ``\\new Staff``, ``\\new Voice`` and ``\\context`` (each staff or voice becomes a part, named from ``= "name"``);
- top-level variables such as ``melody = \\relative c'' { ... }`` and their use as ``\\melody``;
- lyrics from ``\\addlyrics``, ``\\lyricsto`` and ``\\lyricmode``, one syllable per note;
- dynamics ``\\ppp`` to ``\\fff`` for velocity.

Layout, markup, grace notes, chord names, drum mode and Scheme expressions are skipped. ``\\transpose`` and
``\\include`` are refused, because reading them correctly needs more than this reader does.

Written new for Common Studio from the published LilyPond notation reference, read as a reference. Released under the
Unlicense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Optional

from .common import DEFAULT_VELOCITY, ParseError, RawPart, Score, Source, as_text, build_score, guarded

FORMAT = "lilypond"

MAX_TOKENS = 400_000
MAX_DEPTH = 200

_SEMITONE = (0, 2, 4, 5, 7, 9, 11)
_STEPS = "cdefgab"
_DYNAMICS = {"ppp": 25, "pp": 40, "p": 55, "mp": 70, "mf": 85, "f": 100, "ff": 115, "fff": 127, "sf": 110,
             "sfz": 110, "fp": 100}
_PART_CONTEXTS = {"Staff", "Voice", "RhythmicStaff", "TabStaff", "TabVoice", "CueVoice"}
_GROUP_CONTEXTS = {"StaffGroup", "PianoStaff", "GrandStaff", "ChoirStaff", "Score"}
_SKIPPED_CONTEXTS = {"ChordNames", "FiguredBass", "DrumStaff", "DrumVoice", "Dynamics", "FretBoards"}
_SKIP_BLOCK = {"markup", "markuplist", "paper", "layout", "midi", "with", "chordmode", "chords", "figures",
               "figuremode", "drummode", "drums", "grace", "acciaccatura", "appoggiatura", "slashedGrace",
               "afterGrace", "book", "bookpart"}
_ONE_ARG = {"clef", "time", "partial", "bar", "version", "language", "mark", "tag", "skip", "numericTimeSignature",
            "ottava", "label", "barNumberCheck", "tweak", "keepWithTag", "removeWithTag", "omit", "hide", "unset"}

_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<block_comment>%\{.*?(?:%\}|\Z))
  | (?P<comment>%[^\n]*)
  | (?P<str>"(?:[^"\\]|\\.)*"?)
  | (?P<sep>\\\\)
  | (?P<cmd>\\[A-Za-z][A-Za-z-]*)
  | (?P<sym><<|>>|--|__|[{}<>|~=()\[\]])
  | (?P<scheme>\#)
  | (?P<num>[0-9]+(?:/[0-9]+)?\.*(?:\*[0-9]+(?:/[0-9]+)?)*)
  | (?P<word>[^\s{}<>"%\\|~=\#()\[\]]+)
    """,
    re.VERBOSE | re.DOTALL,
)
_NOTE = re.compile(
    r"(?P<name>[a-g](?:isis|eses|ses|is|es|s)?|r|R|s)(?P<marks>[',]*)[!?]?"
    r"(?P<dur>[0-9]+)?(?P<dots>\.*)(?P<mult>(?:\*[0-9]+(?:/[0-9]+)?)*)"
)
_PITCH = re.compile(r"(?P<name>[a-g](?:isis|eses|ses|is|es|s)?)(?P<marks>[',]*)")


@dataclass(frozen=True)
class _Tok:
    kind: str
    text: str


def _tokenize(text: str) -> list[_Tok]:
    out: list[_Tok] = []
    i, n = 0, len(text)
    while i < n:
        m = _TOKEN.match(text, i)
        if m is None:
            i += 1  # a stray character: skip it
            continue
        kind = m.lastgroup or "ws"
        if kind == "scheme":
            i = _skip_scheme(text, m.end())
            out.append(_Tok("scheme", "#"))
            continue
        i = m.end()
        if kind in ("ws", "comment", "block_comment"):
            continue
        out.append(_Tok(kind, m.group(0)))
        if len(out) > MAX_TOKENS:
            raise ParseError(FORMAT, "the file has too many tokens")
    return out


def _skip_scheme(text: str, i: int) -> int:
    """Skip one Scheme expression after ``#``: a balanced parenthesised form, a string, or a run of characters."""
    n = len(text)
    while i < n and text[i] in "#'`,":
        i += 1
    if i < n and text[i] == "(":
        depth = 0
        while i < n:
            c = text[i]
            if c == '"':
                end = text.find('"', i + 1)
                i = n if end < 0 else end + 1
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return n
    if i < n and text[i] == '"':
        end = text.find('"', i + 1)
        return n if end < 0 else end + 1
    while i < n and not text[i].isspace() and text[i] not in "{}<>\\":
        i += 1
    return i


def _alteration(name: str) -> int:
    letter, suffix = name[0], name[1:]
    if suffix in ("s", "es") and letter in "ae":
        return -1
    if suffix == "ses" and letter in "ae":
        return -2
    return {"": 0, "is": 1, "isis": 2, "es": -1, "eses": -2}.get(suffix, 0)


def _diatonic(letter: str, marks: str, base_octave: int = 3) -> int:
    """A staff position: octave * 7 + step, with ``c`` (no marks) in octave 3, so ``c'`` is middle C."""
    return (base_octave + marks.count("'") - marks.count(",")) * 7 + _STEPS.index(letter)


def _midi(diatonic: int, alteration: int) -> int:
    return 12 * (diatonic // 7 + 1) + _SEMITONE[diatonic % 7] + alteration


def _relative(ref: int, letter: str, marks: str) -> int:
    step = _STEPS.index(letter)
    diff = (step - ref % 7) % 7
    if diff > 3:
        diff -= 7
    return ref + diff + 7 * (marks.count("'") - marks.count(","))


@dataclass
class _Ctx:
    part: RawPart
    time: Fraction = Fraction(0)
    dur: Fraction = Fraction(1, 4)  # in whole notes
    rel: Optional[int] = None  # reference staff position in relative mode
    fixed: int = 3  # octave of an unmarked note in absolute or fixed mode
    factor: Fraction = Fraction(1)
    velocity: int = DEFAULT_VELOCITY


@dataclass
class _Frame:
    kind: str  # "seq" or "sim"
    parent: _Ctx
    start: Fraction = Fraction(0)
    end: Fraction = Fraction(0)
    restores_rel: bool = False
    restores_part: bool = False
    restores_factor: bool = False


@dataclass
class _Pending:
    part: Optional[RawPart] = None
    rel: Optional[int] = None
    set_rel: bool = False
    fixed: Optional[int] = None
    factor: Fraction = Fraction(1)
    unfold: int = 0


@dataclass
class _Reader:
    tokens: list[_Tok]
    title: Optional[str] = None
    meter: Optional[tuple[int, int]] = None
    parts: list[RawPart] = field(default_factory=list)
    named: dict[str, RawPart] = field(default_factory=dict)
    slots: dict[int, list[int]] = field(default_factory=dict)  # id(part) -> note index of each sung event
    cursor: dict[int, int] = field(default_factory=dict)
    last_part: Optional[RawPart] = None
    staff_count: int = 0

    def new_part(self, name: Optional[str], fallback: str) -> RawPart:
        if len(self.parts) >= 256:
            raise ParseError(FORMAT, "too many staves and voices")
        part = RawPart((name or fallback)[:60])
        self.parts.append(part)
        if name:
            self.named[name] = part
        return part


def parse_lilypond(data: Source, *, work_id: Optional[str] = None, style: str = "source") -> Score:
    """Read a LilyPond file, in the subset this module documents, into the core model."""
    return guarded(FORMAT, lambda: _parse(as_text(FORMAT, data), work_id, style))


def _parse(text: str, work_id: Optional[str], style: str) -> Score:
    tokens = _tokenize(text)
    tokens, variables = _split_variables(tokens)
    reader = _Reader(_expand(tokens, variables))
    _run(reader)
    num, den = reader.meter or (4, 4)
    for part in reader.parts:
        # Positions were collected in whole notes; the beat is the unit of the time signature's lower number.
        part.notes = [(b * den, p, d * den, v) for b, p, d, v in part.notes]
    return build_score(FORMAT, reader.title, reader.parts, (num, den), work_id=work_id, style=style)


def _block_end(tokens: list[_Tok], i: int) -> int:
    """Given the index of ``{`` or ``<<``, the index just after its matching close."""
    opener = tokens[i].text
    closer = "}" if opener == "{" else ">>"
    depth = 0
    for j in range(i, len(tokens)):
        t = tokens[j]
        if t.kind == "sym" and t.text == opener:
            depth += 1
        elif t.kind == "sym" and t.text == closer:
            depth -= 1
            if depth == 0:
                return j + 1
    raise ParseError(FORMAT, f"{opener!r} is never closed")


def _element_end(tokens: list[_Tok], i: int) -> int:
    """The index just after one music element starting at ``i``: a block, a chord, or one token."""
    while i < len(tokens) and tokens[i].kind in ("cmd", "scheme") and tokens[i].text not in ("\\markup",):
        i += 1  # prefixes such as \new Staff or \relative c' belong to the element
        if i < len(tokens) and tokens[i].kind == "word" and tokens[i - 1].text in ("\\new", "\\context"):
            i += 1
    if i >= len(tokens):
        return i
    t = tokens[i]
    if t.kind == "sym" and t.text in ("{", "<<"):
        return _block_end(tokens, i)
    if t.kind == "sym" and t.text == "<":
        while i < len(tokens) and not (tokens[i].kind == "sym" and tokens[i].text == ">"):
            i += 1
        i += 1
        if i < len(tokens) and tokens[i].kind == "num":
            i += 1
        return i
    return i + 1


def _value_end(tokens: list[_Tok], i: int) -> int:
    """The end of a variable's value: prefixes such as ``\\relative c''`` and the block that follows them."""
    j = i
    while j < len(tokens) and j - i < 12:
        t = tokens[j]
        if t.kind == "sym" and t.text in ("{", "<<"):
            return _block_end(tokens, j)
        if t.kind in ("cmd", "word", "num", "str", "scheme") or (t.kind == "sym" and t.text == "="):
            j += 1
            continue
        break
    return _element_end(tokens, i)


def _split_variables(tokens: list[_Tok]) -> tuple[list[_Tok], dict[str, list[_Tok]]]:
    """Take top-level ``name = value`` assignments out of the token list."""
    out: list[_Tok] = []
    variables: dict[str, list[_Tok]] = {}
    i, depth = 0, 0
    while i < len(tokens):
        t = tokens[i]
        after_context = i > 0 and tokens[i - 1].text in ("\\new", "\\context")
        if (depth == 0 and not after_context and t.kind == "word" and re.fullmatch(r"[A-Za-z]+", t.text)
                and i + 1 < len(tokens)
                and tokens[i + 1].kind == "sym" and tokens[i + 1].text == "="):
            j = i + 2
            if j < len(tokens) and tokens[j].kind in ("str", "num", "scheme", "word"):
                i = j + 1
                continue
            end = _value_end(tokens, j)
            variables[t.text] = tokens[j:end]
            i = end
            continue
        if t.kind == "sym" and t.text in ("{", "<<"):
            depth += 1
        elif t.kind == "sym" and t.text in ("}", ">>"):
            depth = max(0, depth - 1)
        out.append(t)
        i += 1
    return out, variables


def _expand(tokens: list[_Tok], variables: dict[str, list[_Tok]], depth: int = 0) -> list[_Tok]:
    if depth > 20:
        raise ParseError(FORMAT, "variables refer to each other too deeply")
    out: list[_Tok] = []
    for t in tokens:
        name = t.text[1:] if t.kind == "cmd" else None
        if name is not None and name in variables:
            out.extend(_expand(variables[name], variables, depth + 1))
        else:
            out.append(t)
        if len(out) > MAX_TOKENS:
            raise ParseError(FORMAT, "the file expands to too many tokens")
    return out


def _duration(dur: str, dots: str, mult: str) -> Fraction:
    d = int(dur) if len(dur) <= 4 else 0
    if d not in (1, 2, 4, 8, 16, 32, 64, 128):
        raise ParseError(FORMAT, f"{dur[:6]} is not a note length")
    return _apply_dots(Fraction(1, d), dots, mult)


def _apply_dots(value: Fraction, dots: str, mult: str) -> Fraction:
    total, add = value, value
    for _ in dots[:8]:
        add /= 2
        total += add
    for m in re.findall(r"\*([0-9]+)(?:/([0-9]+))?", mult):
        num, den = int(m[0][:6]), int((m[1] or "1")[:6])
        if num == 0 or den == 0:
            raise ParseError(FORMAT, "a length multiplier is zero")
        total *= Fraction(num, den)
    return total


def _run(r: _Reader) -> None:
    tokens = r.tokens
    default = r.new_part(None, "melody")
    cur = _Ctx(default)
    stack: list[_Frame] = []
    pending = _Pending()
    tied: dict[tuple[int, int], int] = {}  # (id(part), pitch) -> note index waiting for a tie
    last_event: list[int] = []
    i = 0

    def event(ctx: _Ctx, pitches: list[int], length: Fraction, rest: bool) -> None:
        nonlocal tied, last_event
        beats = length * ctx.factor
        if beats <= 0:
            raise ParseError(FORMAT, "a note length must be greater than zero")
        part = ctx.part
        if not rest:
            waiting = tied
            tied = {}
            indices: list[int] = []
            first_new: Optional[int] = None
            for pitch in pitches:
                key = (id(part), pitch)
                if key in waiting:
                    idx = waiting[key]
                    b, p, d, v = part.notes[idx]
                    part.notes[idx] = (b, p, d + beats, v)
                else:
                    part.notes.append((ctx.time, pitch, beats, ctx.velocity))
                    part.lyrics.append("")
                    idx = len(part.notes) - 1
                    if first_new is None:
                        first_new = idx
                indices.append(idx)
            if first_new is not None:
                r.slots.setdefault(id(part), []).append(first_new)
            last_event = indices
            r.last_part = part
        else:
            tied = {}
            last_event = []
        ctx.time += beats
        if stack and stack[-1].kind == "sim":
            frame = stack[-1]
            frame.end = max(frame.end, ctx.time)
            ctx.time = frame.start

    def pitch_of(ctx: _Ctx, name: str, marks: str) -> int:
        letter = name[0]
        if ctx.rel is not None:
            pos = _relative(ctx.rel, letter, marks)
            ctx.rel = pos
        else:
            pos = _diatonic(letter, marks, ctx.fixed)
        return _midi(pos, _alteration(name))

    def open_block(kind: str) -> None:
        nonlocal cur, pending
        if len(stack) >= MAX_DEPTH:
            raise ParseError(FORMAT, "music is nested too deeply")
        child = replace(cur)
        frame = _Frame(kind, cur, start=cur.time, end=cur.time)
        if pending.part is not None:
            child.part = pending.part
            frame.restores_part = True
        if pending.set_rel:
            child.rel = pending.rel
            frame.restores_rel = True
        if pending.fixed is not None:
            child.fixed = pending.fixed
            child.rel = None
            frame.restores_rel = True
        if pending.factor != 1:
            child.factor = cur.factor * pending.factor
            frame.restores_factor = True
        stack.append(frame)
        cur = child
        pending = _Pending()

    def close_block(kind: str) -> None:
        nonlocal cur
        if not stack or stack[-1].kind != kind:
            raise ParseError(FORMAT, f"unbalanced {'}' if kind == 'seq' else '>>'}")
        frame = stack.pop()
        child = cur
        end = max(frame.end, child.time) if kind == "sim" else child.time
        parent = frame.parent
        parent.time = end
        parent.dur = child.dur
        parent.velocity = child.velocity
        if not frame.restores_rel and not frame.restores_part:
            parent.rel = child.rel
        cur = parent
        if stack and stack[-1].kind == "sim":
            outer = stack[-1]
            outer.end = max(outer.end, cur.time)
            cur.time = outer.start

    def read_pitch_arg(j: int) -> tuple[Optional[int], int]:
        if j < len(tokens) and tokens[j].kind == "word":
            m = _PITCH.fullmatch(tokens[j].text)
            if m:
                return _diatonic(m.group("name")[0], m.group("marks")), j + 1
        return None, j

    while i < len(tokens):
        t = tokens[i]
        if t.kind == "sym":
            if t.text == "{":
                if pending.unfold > 1:
                    end = _block_end(tokens, i)
                    block = tokens[i:end]
                    if len(tokens) + len(block) * (pending.unfold - 1) > MAX_TOKENS:
                        raise ParseError(FORMAT, "repeats unfold to too many tokens")
                    # The copies follow the block and are read in turn, as an unfolded repeat plays.
                    tokens[end:end] = block * (pending.unfold - 1)
                    pending.unfold = 0
                open_block("seq")
            elif t.text == "}":
                close_block("seq")
            elif t.text == "<<":
                open_block("sim")
            elif t.text == ">>":
                close_block("sim")
            elif t.text == "<":
                j = i + 1
                pitches: list[int] = []
                first_ref: Optional[int] = None
                while j < len(tokens) and not (tokens[j].kind == "sym" and tokens[j].text == ">"):
                    m = _PITCH.match(tokens[j].text) if tokens[j].kind == "word" else None
                    if m:
                        pitch = pitch_of(cur, m.group("name"), m.group("marks"))
                        if first_ref is None:
                            first_ref = cur.rel
                        if pitch not in pitches:
                            pitches.append(pitch)
                    j += 1
                if j >= len(tokens):
                    raise ParseError(FORMAT, "a chord is not closed with >")
                j += 1
                length = cur.dur
                if j < len(tokens) and tokens[j].kind == "num":
                    m2 = re.fullmatch(r"([0-9]+)(\.*)((?:\*[0-9]+(?:/[0-9]+)?)*)", tokens[j].text)
                    if m2:
                        length = _duration(m2.group(1), m2.group(2), m2.group(3))
                        cur.dur = length
                    j += 1
                if cur.rel is not None and first_ref is not None:
                    cur.rel = first_ref
                if pitches:
                    event(cur, pitches, length, False)
                i = j
                continue
            elif t.text == "~":
                for idx in last_event:
                    part = r.last_part
                    if part is not None:
                        tied[(id(part), part.notes[idx][1])] = idx
            i += 1
            continue

        if t.kind == "sep":
            if stack and stack[-1].kind == "sim":
                frame = stack[-1]
                frame.end = max(frame.end, cur.time)
                cur.time = frame.start
            i += 1
            continue

        if t.kind == "cmd":
            name = t.text[1:]
            i += 1
            if name in _DYNAMICS:
                cur.velocity = _DYNAMICS[name]
            elif name == "header":
                i = _read_header(r, tokens, i)
            elif name in _SKIP_BLOCK:
                i = _element_end(tokens, i)
            elif name in _ONE_ARG:
                if name == "time" and i < len(tokens) and tokens[i].kind == "num" and r.meter is None:
                    m = re.fullmatch(r"([0-9]{1,3})/([0-9]{1,3})", tokens[i].text)
                    if m and int(m.group(1)) >= 1:
                        r.meter = (int(m.group(1)), int(m.group(2)))
                if i < len(tokens) and tokens[i].kind in ("num", "str", "word", "scheme"):
                    i += 1
            elif name == "key":
                _, i = read_pitch_arg(i)
                if i < len(tokens) and tokens[i].kind == "cmd":
                    i += 1
            elif name == "tempo":
                if i < len(tokens) and tokens[i].kind == "str":
                    i += 1
                if i < len(tokens) and tokens[i].kind == "num":
                    i += 1
                    if i + 1 < len(tokens) and tokens[i].text == "=":
                        i += 2
                        if i + 1 < len(tokens) and tokens[i].kind == "word" and tokens[i].text.startswith("-"):
                            i += 1
            elif name in ("set", "override", "once", "revert"):
                if i < len(tokens) and tokens[i].kind == "word":
                    i += 1
                    if i < len(tokens) and tokens[i].text == "=":
                        i += 2
            elif name == "relative":
                pos, i = read_pitch_arg(i)
                pending.set_rel = True
                pending.rel = pos if pos is not None else _diatonic("f", "")
            elif name == "fixed":
                pos, i = read_pitch_arg(i)
                pending.fixed = (pos // 7) if pos is not None else 3
            elif name in ("tuplet", "times"):
                if i < len(tokens) and tokens[i].kind == "num":
                    m = re.fullmatch(r"([0-9]{1,4})/([0-9]{1,4})", tokens[i].text)
                    i += 1
                    if m and int(m.group(1)) and int(m.group(2)):
                        a, b = int(m.group(1)), int(m.group(2))
                        pending.factor = Fraction(b, a) if name == "tuplet" else Fraction(a, b)
                    if name == "tuplet" and i < len(tokens) and tokens[i].kind == "num" and "/" not in tokens[i].text:
                        i += 1  # an optional grouping length
            elif name == "repeat":
                kind = tokens[i].text if i < len(tokens) and tokens[i].kind == "word" else ""
                if kind:
                    i += 1
                count = 1
                if i < len(tokens) and tokens[i].kind == "num" and tokens[i].text.isdigit():
                    count = min(int(tokens[i].text[:3]), 32)
                    i += 1
                if kind == "unfold" and count > 1:
                    pending.unfold = count
            elif name in ("new", "context"):
                ctx_type = tokens[i].text if i < len(tokens) and tokens[i].kind == "word" else ""
                if ctx_type:
                    i += 1
                label: Optional[str] = None
                if i + 1 < len(tokens) and tokens[i].text == "=" and tokens[i + 1].kind in ("str", "word"):
                    label = tokens[i + 1].text.strip('"')[:60] or None
                    i += 2
                if i < len(tokens) and tokens[i].text == "\\with":
                    i = _element_end(tokens, i + 1)
                if ctx_type in _PART_CONTEXTS:
                    if name == "context" and label and label in r.named:
                        pending.part = r.named[label]
                    elif ctx_type.endswith("Voice") and not cur.part.notes and cur.part is not default:
                        pending.part = cur.part
                        if label:
                            r.named[label] = cur.part
                    else:
                        r.staff_count += 1
                        fallback = f"{'staff' if ctx_type.endswith('Staff') else 'voice'} {r.staff_count}"
                        pending.part = r.new_part(label, fallback)
                elif ctx_type == "Lyrics":
                    target = r.last_part
                    if i < len(tokens) and tokens[i].text == "\\lyricsto":
                        i += 1
                        if i < len(tokens) and tokens[i].kind in ("str", "word"):
                            target = r.named.get(tokens[i].text.strip('"'), target)
                            i += 1
                    if i < len(tokens) and tokens[i].text == "\\lyricmode":
                        i += 1
                    i = _read_lyrics(r, tokens, i, target)
                elif ctx_type in _SKIPPED_CONTEXTS:
                    i = _element_end(tokens, i)
            elif name in ("addlyrics", "lyricmode"):
                i = _read_lyrics(r, tokens, i, r.last_part)
            elif name == "lyricsto":
                target = r.last_part
                if i < len(tokens) and tokens[i].kind in ("str", "word"):
                    target = r.named.get(tokens[i].text.strip('"'), target)
                    i += 1
                i = _read_lyrics(r, tokens, i, target)
            elif name in ("transpose", "transposition"):
                raise ParseError(FORMAT, f"\\{name} is not read; write the music at sounding pitch")
            elif name == "include":
                raise ParseError(FORMAT, "\\include is not read; give one self-contained file")
            # Any other command (\score, \voiceOne, \break, articulations ...) changes nothing this reader keeps.
            continue

        if t.kind == "word":
            m = _NOTE.fullmatch(t.text)
            if m:
                name = m.group("name")
                length = cur.dur
                if m.group("dur") is not None:
                    length = _duration(m.group("dur"), m.group("dots"), m.group("mult"))
                    cur.dur = length
                elif m.group("dots") or m.group("mult"):
                    length = _apply_dots(cur.dur, m.group("dots"), m.group("mult"))
                if name == "R" or name == "r" or name == "s":
                    if m.group("marks"):
                        raise ParseError(FORMAT, f"{t.text[:20]!r}: a rest takes no octave marks")
                    event(cur, [], length, True)
                else:
                    event(cur, [pitch_of(cur, name, m.group("marks"))], length, False)
            i += 1
            continue

        i += 1  # strings, numbers and Scheme outside their commands change nothing here

    if stack:
        raise ParseError(FORMAT, "a { or << is never closed")


def _read_header(r: _Reader, tokens: list[_Tok], i: int) -> int:
    if i >= len(tokens) or tokens[i].text != "{":
        return i
    end = _block_end(tokens, i)
    for j in range(i + 1, end - 3):
        if tokens[j].kind == "word" and tokens[j].text == "title" and tokens[j + 1].text == "=":
            value = tokens[j + 2]
            if value.kind == "str" and r.title is None:
                r.title = value.text[1:-1] if value.text.endswith('"') and len(value.text) > 1 else value.text[1:]
                r.title = r.title.replace('\\"', '"')
    return end


def _read_lyrics(r: _Reader, tokens: list[_Tok], i: int, target: Optional[RawPart]) -> int:
    if i < len(tokens) and tokens[i].text == "\\lyricmode":
        i += 1
    if i >= len(tokens) or tokens[i].text not in ("{", "<<"):
        return i
    end = _block_end(tokens, i)
    if target is None:
        return end
    slots = r.slots.get(id(target), [])
    cursor = r.cursor.get(id(target), 0)
    for t in tokens[i + 1:end - 1]:
        if t.kind == "cmd" or t.kind == "scheme" or t.kind == "num" or t.text in ("{", "}", "<<", ">>", "--", "__", "|", "~", "=", "\\\\"):
            continue
        if cursor >= len(slots):
            break
        text = t.text
        if t.kind == "str":
            text = text[1:-1] if text.endswith('"') and len(text) > 1 else text[1:]
        else:
            text = re.sub(r"[0-9]+\.*$", "", text)
        if text != "_":
            target.lyrics[slots[cursor]] = text.replace("~", " ")[:100]
        cursor += 1
    r.cursor[id(target)] = cursor
    return end
