#!/usr/bin/env python3
"""Write a Mode 7 screen as baron source: one TT_ROW per 40-byte row.

Control codes are named from src/teletext.6502inc. Inside text (after an
alpha colour, and at the start of each row) runs of printable characters
become strings; inside graphics everything else stays hex, since those bytes
are sixel shapes rather than letters. A last, short row is written as far as
the data goes.

usage: mode7.py BINARY [OFFSET [LENGTH]] > rows.txt

The output is meant to be pasted into a source file that INCLUDEs
teletext.6502inc and defines `screen` as the address of row 0; edit by hand
from there.
"""

import re
import sys
from pathlib import Path

INCLUDE = Path(__file__).resolve().parent.parent / "src" / "teletext.6502inc"
COLUMNS = 40
WRAP = 100  # columns of source before a row continues on another EQUB


def control_names() -> dict:
    out = {}
    for line in INCLUDE.read_text().splitlines():
        m = re.match(r"\s*(TT_\w+)\s*=\s*&([0-9A-Fa-f]{2})\b", line)
        if m:
            out[int(m.group(2), 16)] = m.group(1)
    return out


def row_items(row: bytes, names: dict) -> list:
    """The row as EQUB operands: names, strings and hex bytes."""
    items = []
    graphics = False
    i = 0
    while i < len(row):
        b = row[i]
        if b in names:
            items.append(names[b])
            if 0x81 <= b <= 0x87:
                graphics = False
            elif 0x91 <= b <= 0x97:
                graphics = True
            i += 1
            continue
        if not graphics:
            j = i
            while j < len(row) and 0x20 <= row[j] < 0x7F:
                j += 1
            if j - i >= 3:
                text = row[i:j].decode("ascii").replace('"', '""')
                items.append(f'"{text}"')
                i = j
                continue
        items.append(f"&{b:02X}")
        i += 1
    return items


def render(data: bytes, names: dict) -> list:
    lines = []
    for n in range(0, len(data), COLUMNS):
        items = row_items(data[n : n + COLUMNS], names)
        lines.append(f"    TT_ROW {n // COLUMNS}")
        line = "    EQUB "
        for k, item in enumerate(items):
            piece = item + (", " if k < len(items) - 1 else "")
            if len(line) + len(piece) > WRAP and line.strip() != "EQUB":
                lines.append(line.rstrip().rstrip(","))
                line = "    EQUB "
            line += piece
        lines.append(line.rstrip())
    return lines


def main():
    if not 2 <= len(sys.argv) <= 4:
        raise SystemExit(__doc__)
    data = Path(sys.argv[1]).read_bytes()
    offset = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    length = int(sys.argv[3], 0) if len(sys.argv) > 3 else len(data) - offset
    print("\n".join(render(data[offset : offset + length], control_names())))


if __name__ == "__main__":
    main()
