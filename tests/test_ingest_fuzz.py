"""AC-06: every parser survives fuzzed, malformed input without crashing the process.

Each parser gets random bytes, random text over the format's own alphabet, and mutations of its authored fixture
(bytes flipped, inserted, deleted, cut short and spliced). The only failure a parser may report is ``ParseError``;
any other exception fails the test. The seeds are fixed, so a failure reproduces exactly.
"""

import random

import pytest

from common_studio.ingest import ParseError, parse_abc, parse_lilypond, parse_midi, parse_musicxml
from common_studio.ingest.fixture_evidence import fixture_bytes

ROUNDS = 400

PARSERS = {
    "abc": parse_abc,
    "musicxml": parse_musicxml,
    "midi": parse_midi,
    "lilypond": parse_lilypond,
}

ALPHABETS = {
    "abc": b"XTMLKVwABCDEFGabcdefgzxZ^_=',/0123456789|:[]()<>-!+\"{}% \n",
    "musicxml": b"<>/=\"' ?!-abcdefghijklmnoprstuvwxyz0123456789\n",
    "midi": bytes(range(256)),
    "lilypond": b"\\{}<>~|'.,=#%\"abcdefgisr0123456789 \nnewStaffrelativetupletrepeatunfoldtime/",
}


def mutate(rng: random.Random, data: bytes) -> bytes:
    buf = bytearray(data)
    for _ in range(rng.randint(1, 8)):
        op = rng.randrange(6)
        pos = rng.randrange(len(buf) + 1)
        if op == 0 and buf:  # flip a byte
            buf[min(pos, len(buf) - 1)] = rng.randrange(256)
        elif op == 1:  # insert random bytes
            buf[pos:pos] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 8)))
        elif op == 2 and buf:  # delete a run
            del buf[pos:pos + rng.randint(1, 16)]
        elif op == 3:  # cut short
            del buf[pos:]
        elif op == 4 and buf:  # duplicate a slice somewhere else
            start = rng.randrange(len(buf))
            chunk = buf[start:start + rng.randint(1, 64)]
            buf[pos:pos] = chunk
        elif op == 5 and buf:  # set a byte to an edge value
            buf[min(pos, len(buf) - 1)] = rng.choice((0x00, 0x7F, 0x80, 0xFF, 0x3C, 0x7B, 0x22))
    return bytes(buf)


def cases(fmt: str):
    rng = random.Random(f"common-studio-fuzz-{fmt}")
    seed = fixture_bytes(fmt)
    alphabet = ALPHABETS[fmt]
    yield b""
    for _ in range(ROUNDS):
        kind = rng.randrange(3)
        if kind == 0:
            yield bytes(rng.randrange(256) for _ in range(rng.randint(0, 512)))
        elif kind == 1:
            yield bytes(rng.choice(alphabet) for _ in range(rng.randint(0, 512)))
        else:
            yield mutate(rng, seed)


def survive(parser, data) -> None:
    try:
        parser(data)
    except ParseError:
        pass


@pytest.mark.parametrize("fmt", sorted(PARSERS))
def test_parser_survives_fuzzed_input(fmt):
    parser = PARSERS[fmt]
    for data in cases(fmt):
        survive(parser, data)


# Hand-made hostile inputs that random mutation is unlikely to find.

def test_abc_parser_survives_hostile_input():
    for text in ["X:1\nK:C\n" + "c" + "'" * 500, "X:1\nK:C\nc999999999", "X:1\nK:C\nc/0", "X:1\nK:C#m\nc",
                 "X:1\nK:C\n" + "(3" * 5000 + "c", "X:1\nL:0/0\nM:0/0\nK:C\nc", "X:1\nK:C\n[" * 1000,
                 "X:1\nK:C\n" + "c>" * 3000, "X:1\nK:C\nZ999999"]:
        survive(parse_abc, text)


def test_musicxml_parser_survives_hostile_input():
    laughs = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><score-partwise/>'
    external = b'<!DOCTYPE x SYSTEM "file:///etc/passwd"><score-partwise>&x;</score-partwise>'
    deep = b"<score-partwise>" + b"<a>" * 50000 + b"</a>" * 50000 + b"</score-partwise>"
    zero = (b'<score-partwise><part id="P"><measure><attributes><divisions>0</divisions></attributes>'
            b'<note><pitch><step>C</step><octave>99</octave></pitch><duration>1</duration></note></measure></part>'
            b'</score-partwise>')
    for data in [laughs, external, deep, zero, "<score-partwise>".encode("utf-16"), b"PK\x03\x04"]:
        survive(parse_musicxml, data)


def test_midi_parser_survives_hostile_input():
    header = b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0"
    for data in [
        header + b"MTrk\xff\xff\xff\xff",  # a track that claims 4 GB
        header + b"MTrk\x00\x00\x00\x04\xff\xff\xff\xff",  # a variable-length number that never ends
        header + b"MTrk\x00\x00\x00\x03\x00\x40\x40",  # running status with no status byte
        b"MThd\x00\x00\x00\x06\x00\x01\xff\xff\x00\x00",  # zero ticks per quarter
        b"MThd\xff\xff\xff\xff",
    ]:
        survive(parse_midi, data)


def test_lilypond_parser_survives_hostile_input():
    for text in ["{" * 5000 + "c'" + "}" * 5000, "<<" * 300, "a = \\a \\a", "a = { \\b } b = { \\a } \\a",
                 "{ \\repeat unfold 32 { \\repeat unfold 32 { \\repeat unfold 32 { \\repeat unfold 32 { c } } } } }",
                 "{ c" + "'" * 300 + " }", "{ c3 }", "{ c4*0 }", "{ \\tuplet 0/0 { c } }", "#(" * 1000, "%{ open"]:
        survive(parse_lilypond, text)
