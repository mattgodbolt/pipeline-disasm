#!/usr/bin/env python3
"""dis6502.py for a binary that copies parts of itself elsewhere before running.

H.GAME loads at &3000 but its first act is to copy most of itself down to
&0131, &0400, &0880 and &0900 and jump there. Disassembling it at &3000 would
label everything at the wrong address; this disassembles each relocated piece
at the address it runs at, inside a nested baron SECTION with that `org` (baron
"rephases" it: labels at the run address, bytes left in place in the file).

usage: dis6502seg.py HINTS.toml > src/piece.6502

The hints are dis6502.py's (binary, org, section, entries, traces, labels,
data, symbols; addresses are run-time addresses) plus:

    [[segment]]              # one per relocated piece, in any order
    name = "event_handler"   # its nested SECTION's name
    load = 0x3100            # where the bytes sit when the file is loaded
    run = 0x0131             # where they're copied to and run
    length = 0x60
    trace_only = ["0x3000-0x30FF"]   # optional top level: only believe trace
                                     # PCs in the unrelocated part within these
                                     # (later programs reuse the load area)

    [[inline]]               # a routine that reads data placed after its JSR
    routine = 0x103E         # and returns past it: the bytes after each JSR
    terminator = 0xEA        # are data up to this byte, where code resumes
    # or: length = 6         # a fixed number of bytes of data

    [[table]]                # a table of code addresses (a jump table)
    start = 0x2351
    count = 12
    split = 0                # optional: low bytes here, high bytes `split` on
                             # (absent: little-endian words, as EQUW)

Relocated code is assumed to run after the loader has finished, so it never
refers to the unrelocated parts of the file: an operand from relocated code
that falls in the load area is something else living there later (for
H.GAME, the IO data file) and stays a number or a [symbols] name. The
unrelocated loader can refer to everything.
"""

import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dis6502 import ENDS_FLOW, Disassembler, hexn  # noqa: E402


class Piece:
    def __init__(self, load, run, data, name=None):
        self.load, self.run, self.data, self.name = load, run, data, name

    @property
    def end(self):
        return self.run + len(self.data)

    def __contains__(self, addr):
        return self.run <= addr < self.end


class SegmentedDisassembler(Disassembler):
    def __init__(self, hints: dict, base: Path):
        super().__init__(hints, base)
        whole = self.data
        segments = sorted(hints.get("segment", []), key=lambda s: s["load"])
        # Cut the file into pieces in file order: relocated segments and the
        # unrelocated stretches between them.
        self.pieces = []
        at = self.org
        for seg in segments:
            if seg["load"] > at:
                self.pieces.append(Piece(at, at, whole[at - self.org : seg["load"] - self.org]))
            lo = seg["load"] - self.org
            self.pieces.append(Piece(seg["load"], seg["run"], whole[lo : lo + seg["length"]], seg["name"]))
            at = seg["load"] + seg["length"]
        if at < self.end:
            self.pieces.append(Piece(at, at, whole[at - self.org :]))
        self.trace_only = []
        for rng in hints.get("trace_only", []):
            lo, hi = (int(x, 0) for x in rng.split("-"))
            self.trace_only.append((lo, hi))
        self.inline = {i["routine"]: i for i in hints.get("inline", [])}
        # Jump tables: entry address -> (kind, target), kind "word", "lo" or "hi".
        self.table_entries = {}
        self.word_high = set()  # second bytes of EQUW table entries
        for t in hints.get("table", []):
            for i in range(t["count"]):
                if t.get("split"):
                    lo, hi = t["start"] + i, t["start"] + t["split"] + i
                else:
                    lo, hi = t["start"] + 2 * i, t["start"] + 2 * i + 1
                target = self.byte(lo) | self.byte(hi) << 8
                if t.get("split"):
                    self.table_entries[lo] = ("lo", target)
                    self.table_entries[hi] = ("hi", target)
                else:
                    self.table_entries[lo] = ("word", target)
                    self.word_high.add(hi)
                self.forced[lo] = "table"
                self.forced[hi] = "table"
        self.used_symbols = set()
        self.context = None

    def piece(self, addr):
        for p in self.pieces:
            if addr in p:
                return p
        return None

    def inside(self, addr):
        return self.piece(addr) is not None

    def visible(self, src, addr):
        """Does an operand of the instruction at src that equals addr mean this file?"""
        target = self.piece(addr)
        if target is None:
            return False
        origin = self.piece(src) if src is not None else None
        return origin is None or origin.name is None or target.name is not None

    def byte(self, addr):
        p = self.piece(addr)
        return p.data[addr - p.run]

    def decode(self, addr):
        insn = super().decode(addr)
        if insn is None:
            return None
        # Every byte of the instruction must sit in the same piece.
        p = self.piece(addr)
        if addr + insn[3] > p.end:
            return None
        return insn

    def trace(self, entries):
        todo = list(entries)
        while todo:
            addr = todo.pop()
            while self.inside(addr) and addr not in self.code:
                insn = self.decode(addr)
                if insn is None:
                    break
                if any(a in self.code for a in range(addr + 1, addr + insn[3])):
                    break
                self.code[addr] = insn
                mnemonic, mode, operand, size = insn
                if (mode == "rel" or (mnemonic in ("JMP", "JSR") and mode == "abs")) \
                        and self.visible(addr, operand):
                    todo.append(operand)
                if mnemonic in ENDS_FLOW:
                    break
                addr += size
                if mnemonic == "JSR" and operand in self.inline:
                    addr = self.skip_inline(addr, self.inline[operand])

    def skip_inline(self, addr, spec):
        """Mark the data after an inline-data JSR; return where code resumes."""
        if "length" in spec:
            stop = addr + spec["length"]
        else:
            stop = addr
            while self.inside(stop) and self.byte(stop) != spec["terminator"]:
                stop += 1
        for a in range(addr, stop):
            self.forced.setdefault(a, "inline")
        return stop

    def executed(self):
        pcs = []
        for path in self.hints.get("traces", []):
            for name, (opcode, _count) in json.loads(Path(path).read_text())["executed"].items():
                pc = int(name[1:].split("/")[0], 16)
                p = self.piece(pc)
                if p is None or self.byte(pc) != opcode:
                    continue
                if p.name is None and self.trace_only and \
                        not any(lo <= pc <= hi for lo, hi in self.trace_only):
                    continue
                pcs.append(pc)
        return pcs

    def label_for(self, addr):
        if addr in self.word_high and addr not in self.labels:
            return f"{self.label_for(addr - 1)}+1"
        return super().label_for(addr)

    def collect_refs(self):
        for addr, (mnemonic, mode, operand, size) in self.code.items():
            if mode in ("imp", "acc", "imm") or operand is None:
                continue
            if self.visible(addr, operand):
                # A table's high bytes are reached as table+1.
                self.refs.add(operand - 1 if operand in self.word_high else operand)
                for back in (1, 2):
                    start = operand - back
                    if start in self.code and self.code[start][3] > back:
                        self.refs.add(start)

    def render_insn(self, addr):
        self.context = addr
        try:
            return super().render_insn(addr)
        finally:
            self.context = None

    def operand_text(self, operand, zp_mode):
        if self.visible(self.context, operand):
            return self.label_for(operand)
        if operand in self.local:
            self.used_symbols.add(operand)
            return self.local[operand]
        if operand in self.os:
            return self.os[operand]
        return hexn(operand)

    def emit(self):
        out = []
        uses_abs = False
        whole = self.data
        for p in self.pieces:
            if p.name:
                out.append(f".{p.name}_load")
                out.append(f"SECTION {p.name}, org={hexn(p.run)}")
            self.org, self.end, self.data = p.run, p.end, p.data
            body, abs_here = super().emit()
            out += body
            uses_abs |= abs_here
            if p.name:
                out.append("ENDSECTION")
        self.org, self.end, self.data = self.pieces[0].load, self.pieces[-1].load + len(self.pieces[-1].data), whole
        return out, uses_abs

    def render_data(self, start, stop):
        """As dis6502, but jump table entries as label expressions."""
        lines = []
        addr = start
        while addr < stop:
            if addr in self.table_entries:
                kind, target = self.table_entries[addr]
                name = self.label_for(target)
                if kind == "word":
                    lines.append((addr, f"EQUW {name}"))
                    addr += 2
                else:
                    lines.append((addr, f"EQUB {'LO' if kind == 'lo' else 'HI'}({name})"))
                    addr += 1
                continue
            run = addr
            while run < stop and run not in self.table_entries:
                run += 1
            lines += super().render_data(addr, run)
            addr = run
        return lines

    def run(self):
        entries = list(self.hints.get("entries", [])) + self.executed()
        entries += [target for _kind, target in self.table_entries.values() if self.inside(target)]
        self.refs |= {target for _kind, target in self.table_entries.values() if self.inside(target)}
        self.trace(entries)
        self.collect_refs()
        self.refs |= set(self.labels)
        body, uses_abs = self.emit()
        head = []
        used = {insn[2] for insn in self.code.values() if insn[1] not in ("imm", "rel", "imp", "acc")}
        if any(op in self.os and op not in self.local for op in used):
            head.append('INCLUDE "os.6502inc"')
        if uses_abs:
            head.append('INCLUDE "forceabs.6502inc"')
        for op in sorted(self.used_symbols):
            head.append(f"{self.local[op]} = {hexn(op)}")
        head.append(f"SECTION {self.hints['section']}")
        return "\n".join(head + body + ["ENDSECTION", ""])


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with open(sys.argv[1], "rb") as f:
        hints = tomllib.load(f)
    root = Path(__file__).resolve().parent.parent
    sys.stdout.write(SegmentedDisassembler(hints, root).run())


if __name__ == "__main__":
    main()
