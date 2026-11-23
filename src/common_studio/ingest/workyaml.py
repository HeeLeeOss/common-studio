"""A small, deterministic YAML writer for ``work.yaml``.

The project keeps no YAML dependency, so this writes the subset ``work.yaml`` needs: nested mappings, lists, and
scalars. Every string is written double-quoted with escapes, so no value can be read back as a different type or
break the document. Keys keep the order they are given in, so the same evidence always gives the same bytes.

Released under the Unlicense.
"""

from __future__ import annotations

from typing import Any, Mapping


def quote(text: str) -> str:
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= code < 0x7F:
            out.append(ch)
        elif code <= 0xFFFF:
            out.append(f"\\u{code:04x}")
        else:
            out.append(f"\\U{code:08x}")
    out.append('"')
    return "".join(out)


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return quote(value)
    raise TypeError(f"work.yaml cannot hold a {type(value).__name__}")


def _key(key: str) -> str:
    if key and all(c.isalnum() or c in "_-" for c in key) and key.isascii() and not key[0] in "-":
        return key
    return quote(key)


def _emit(value: Any, indent: int, lines: list[str]) -> None:
    pad = " " * indent
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(v, Mapping) and v:
                lines.append(f"{pad}{_key(k)}:")
                _emit(v, indent + 2, lines)
            elif isinstance(v, (list, tuple)) and v:
                lines.append(f"{pad}{_key(k)}:")
                _emit(v, indent + 2, lines)
            elif isinstance(v, Mapping):
                lines.append(f"{pad}{_key(k)}: {{}}")
            elif isinstance(v, (list, tuple)):
                lines.append(f"{pad}{_key(k)}: []")
            else:
                lines.append(f"{pad}{_key(k)}: {_scalar(v)}")
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping) and item:
                sub: list[str] = []
                _emit(item, indent + 2, sub)
                sub[0] = f"{pad}- " + sub[0][indent + 2:]
                lines.extend(sub)
            elif isinstance(item, (list, tuple)) and item:
                sub = []
                _emit(item, indent + 2, sub)
                sub[0] = f"{pad}- " + sub[0][indent + 2:]
                lines.extend(sub)
            else:
                lines.append(f"{pad}- {_scalar(item) if not isinstance(item, (Mapping, list, tuple)) else ('{}' if isinstance(item, Mapping) else '[]')}")
    else:
        lines.append(f"{pad}{_scalar(value)}")


def dump(document: Mapping[str, Any], header: str = "") -> str:
    lines = [f"# {line}" if line else "#" for line in header.splitlines()]
    _emit(document, 0, lines)
    return "\n".join(lines) + "\n"
