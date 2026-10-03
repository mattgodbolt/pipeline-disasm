#!/usr/bin/env python3
"""dis6502.py for a binary that copies parts of itself elsewhere before running.

A program loaded in one piece often moves pieces of itself (code to page 8,
a font to page 4, initial values to zero page) and runs them there. This
disassembles such a binary with each moved piece as a nested, rephased baron
section, so its labels are its runtime addresses while its bytes stay where
they are in the file.

usage: dis6502seg.py HINTS.toml > src/piece.6502

The hints are dis6502.py's, plus one table per moved piece, and every address
in them (entries, labels, data ranges) is a runtime address:

    [[segment]]
    load = 0x25E1          # where the piece sits in the loaded binary
    length = 0x440
    org = 0x0880           # where it runs
    name = "low_code"      # its nested SECTION's name

Bytes outside every segment run where they load. An address inside a
segment's load range but not its runtime range is outside the program as
far as labels go (it is stale once the piece has moved).
"""

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dis6502 import Disassembler  # noqa: E402


class Piece:
    def __init__(self, load, length, org, name=None):
        self.load, self.length, self.org, self.name = load, length, org, name

    @property
    def end(self):
        return self.org + self.length


class SegmentedDisassembler(Disassembler):
    def __init__(self, hints, base):
        super().__init__(hints, base)
        self.load = self.org
        self.raw = self.data
        moved = sorted((Piece(s["load"], s["length"], s["org"], s["name"])
                        for s in hints.get("segment", [])), key=lambda p: p.load)
        # Everything between the moved pieces runs where it loads.
        self.pieces = []
        at = self.load
        for p in moved + [Piece(self.load + len(self.raw), 0, 0)]:
            if p.load < at:
                raise SystemExit(f"segment at &{p.load:04X} overlaps the one before")
            if p.load > at:
                self.pieces.append(Piece(at, p.load - at, at))
            if p.length:
                self.pieces.append(p)
            at = p.load + p.length

    def where(self, addr):
        for p in self.pieces:
            if p.org <= addr < p.end:
                return p
        return None

    def byte(self, addr):
        p = self.where(addr)
        return self.raw[p.load - self.load + addr - p.org]

    def inside(self, addr):
        return self.where(addr) is not None

    def decode(self, addr):
        # An instruction can't run off the end of its own piece.
        p = self.where(addr)
        if p is None:
            return None
        saved = self.end
        self.end = p.end
        try:
            return super().decode(addr)
        finally:
            self.end = saved

    def emit(self):
        out, uses_abs = [], False
        saved = self.org, self.end, self.data
        try:
            for p in self.pieces:
                self.org, self.end = p.org, p.end
                self.data = self.raw[p.load - self.load : p.load - self.load + p.length]
                body, abs_here = super().emit()
                uses_abs |= abs_here
                if p.name:
                    out.append(f".{p.name}_load")
                    out.append(f"SECTION {p.name}, org=&{p.org:04X}")
                    out += body
                    out.append("ENDSECTION")
                else:
                    out += body
        finally:
            self.org, self.end, self.data = saved
        return out, uses_abs


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with open(sys.argv[1], "rb") as f:
        hints = tomllib.load(f)
    root = Path(__file__).resolve().parent.parent
    sys.stdout.write(SegmentedDisassembler(hints, root).run())


if __name__ == "__main__":
    main()
