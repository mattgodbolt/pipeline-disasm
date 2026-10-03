#!/usr/bin/env python3
"""Turn a binary into baron source: the first draft of a disassembly.

Code is found by tracing control flow from entry points, and from any PCs a
jsbeeb execution trace (tools/beeb.mjs `trace`) saw run with the same opcode
there. Everything else is data. Addresses referenced inside the binary get
labels; everything outside stays numeric unless the hints name it. The output
reassembles to the same bytes - check with `make verify` - and is meant to be
annotated by hand from there, not regenerated.

usage: dis6502.py HINTS.toml > src/piece.6502

The hints file (TOML):

    binary = "data/hidden_game.bin"
    org = 0x3000
    section = 'hidden_game, filename="H.GAME", org=&3000'   # SECTION line
    entries = [0x3000]
    traces = ["build/trace/game.json"]     # optional
    [labels]                               # optional: address -> name
    0x3000 = "start"
    [data]                                 # optional: forced data ranges
    "0x3100-0x31FF" = "bytes"              # bytes | words | text
    [symbols]                              # optional: names for outside addresses
    0x70 = "zp_temp"
"""

import json
import re
import sys
import tomllib
from pathlib import Path

# (mnemonic, mode) per opcode; NMOS documented set only.
# Modes: imp acc imm zp zpx zpy abs abx aby ind izx izy rel
OPS = {}


def _ops(mnemonic, **modes):
    for mode, opcode in modes.items():
        OPS[opcode] = (mnemonic, mode)


_ops("ADC", imm=0x69, zp=0x65, zpx=0x75, abs=0x6D, abx=0x7D, aby=0x79, izx=0x61, izy=0x71)
_ops("AND", imm=0x29, zp=0x25, zpx=0x35, abs=0x2D, abx=0x3D, aby=0x39, izx=0x21, izy=0x31)
_ops("ASL", acc=0x0A, zp=0x06, zpx=0x16, abs=0x0E, abx=0x1E)
_ops("BIT", zp=0x24, abs=0x2C)
_ops("CMP", imm=0xC9, zp=0xC5, zpx=0xD5, abs=0xCD, abx=0xDD, aby=0xD9, izx=0xC1, izy=0xD1)
_ops("CPX", imm=0xE0, zp=0xE4, abs=0xEC)
_ops("CPY", imm=0xC0, zp=0xC4, abs=0xCC)
_ops("DEC", zp=0xC6, zpx=0xD6, abs=0xCE, abx=0xDE)
_ops("EOR", imm=0x49, zp=0x45, zpx=0x55, abs=0x4D, abx=0x5D, aby=0x59, izx=0x41, izy=0x51)
_ops("INC", zp=0xE6, zpx=0xF6, abs=0xEE, abx=0xFE)
_ops("JMP", abs=0x4C, ind=0x6C)
_ops("JSR", abs=0x20)
_ops("LDA", imm=0xA9, zp=0xA5, zpx=0xB5, abs=0xAD, abx=0xBD, aby=0xB9, izx=0xA1, izy=0xB1)
_ops("LDX", imm=0xA2, zp=0xA6, zpy=0xB6, abs=0xAE, aby=0xBE)
_ops("LDY", imm=0xA0, zp=0xA4, zpx=0xB4, abs=0xAC, abx=0xBC)
_ops("LSR", acc=0x4A, zp=0x46, zpx=0x56, abs=0x4E, abx=0x5E)
_ops("ORA", imm=0x09, zp=0x05, zpx=0x15, abs=0x0D, abx=0x1D, aby=0x19, izx=0x01, izy=0x11)
_ops("ROL", acc=0x2A, zp=0x26, zpx=0x36, abs=0x2E, abx=0x3E)
_ops("ROR", acc=0x6A, zp=0x66, zpx=0x76, abs=0x6E, abx=0x7E)
_ops("SBC", imm=0xE9, zp=0xE5, zpx=0xF5, abs=0xED, abx=0xFD, aby=0xF9, izx=0xE1, izy=0xF1)
_ops("STA", zp=0x85, zpx=0x95, abs=0x8D, abx=0x9D, aby=0x99, izx=0x81, izy=0x91)
_ops("STX", zp=0x86, zpy=0x96, abs=0x8E)
_ops("STY", zp=0x84, zpx=0x94, abs=0x8C)
for _m, _o in [("BPL", 0x10), ("BMI", 0x30), ("BVC", 0x50), ("BVS", 0x70),
               ("BCC", 0x90), ("BCS", 0xB0), ("BNE", 0xD0), ("BEQ", 0xF0)]:
    OPS[_o] = (_m, "rel")
for _m, _o in [("BRK", 0x00), ("PHP", 0x08), ("CLC", 0x18), ("PLP", 0x28), ("SEC", 0x38),
               ("RTI", 0x40), ("PHA", 0x48), ("CLI", 0x58), ("RTS", 0x60), ("PLA", 0x68),
               ("SEI", 0x78), ("DEY", 0x88), ("TXA", 0x8A), ("TYA", 0x98), ("TXS", 0x9A),
               ("TAY", 0xA8), ("TAX", 0xAA), ("CLV", 0xB8), ("TSX", 0xBA), ("INY", 0xC8),
               ("DEX", 0xCA), ("CLD", 0xD8), ("INX", 0xE8), ("NOP", 0xEA), ("SED", 0xF8)]:
    OPS[_o] = (_m, "imp")

MODES = set(OPS.values())

SIZE = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "rel": 2, "izx": 2,
        "izy": 2, "abs": 3, "abx": 3, "aby": 3, "ind": 3}
# Absolute modes baron would shrink to zero page given an operand under &100.
SHRINKS = {"abs": "zp", "abx": "zpx", "aby": "zpy"}
ENDS_FLOW = {"RTS", "RTI", "JMP", "BRK"}

# Names for the OS and hardware, shared with the assembly.
OS_INCLUDE = Path(__file__).resolve().parent.parent / "src" / "os.6502inc"


def os_symbols() -> dict:
    """address -> name, from the `NAME = &HEX` lines of src/os.6502inc.

    Zero page is left out: the MOS's bytes there are fair game for a program
    that has taken the machine over, so naming them would mislead."""
    out = {}
    for line in OS_INCLUDE.read_text().splitlines():
        m = re.match(r"\s*(\w+)\s*=\s*&([0-9A-Fa-f]+)", line)
        if m and int(m.group(2), 16) >= 0x100:
            out[int(m.group(2), 16)] = m.group(1)
    return out


def hexn(n: int) -> str:
    return f"&{n:02X}" if n < 0x100 else f"&{n:04X}"


class Disassembler:
    def __init__(self, hints: dict, base: Path):
        self.data = (base / hints["binary"]).read_bytes()
        self.org = hints["org"]
        self.end = self.org + len(self.data)
        self.hints = hints
        self.labels = {int(k, 0) if isinstance(k, str) else k: v
                       for k, v in hints.get("labels", {}).items()}
        self.os = os_symbols()
        self.local = {int(k, 0): v for k, v in hints.get("symbols", {}).items()}
        self.symbols = {**self.os, **self.local}
        self.forced = {}  # address -> kind for forced data
        for rng, kind in hints.get("data", {}).items():
            lo, hi = (int(x, 0) for x in rng.split("-"))
            for a in range(lo, hi + 1):
                self.forced[a] = kind
        self.code = {}  # address -> (mnemonic, mode, operand, size)
        self.refs = set()  # addresses inside the binary something refers to

    def byte(self, addr):
        return self.data[addr - self.org]

    def inside(self, addr):
        return self.org <= addr < self.end

    def decode(self, addr):
        if not self.inside(addr) or addr in self.forced:
            return None
        opcode = self.byte(addr)
        if opcode not in OPS:
            return None
        mnemonic, mode = OPS[opcode]
        size = SIZE[mode]
        if addr + size > self.end:
            return None
        if size == 1:
            operand = None
        elif size == 2:
            operand = self.byte(addr + 1)
            if mode == "rel":
                operand = (addr + 2 + (operand - 256 if operand >= 128 else operand)) & 0xFFFF
        else:
            operand = self.byte(addr + 1) | self.byte(addr + 2) << 8
        return mnemonic, mode, operand, size

    def trace(self, entries):
        todo = list(entries)
        while todo:
            addr = todo.pop()
            while self.inside(addr) and addr not in self.code:
                insn = self.decode(addr)
                if insn is None:
                    break
                # Don't let a guess overlap code already found.
                if any(a in self.code for a in range(addr + 1, addr + insn[3])):
                    break
                self.code[addr] = insn
                mnemonic, mode, operand, size = insn
                if mode == "rel" or (mnemonic in ("JMP", "JSR") and mode == "abs"):
                    todo.append(operand)
                if mnemonic in ENDS_FLOW:
                    break
                addr += size

    def executed(self):
        """PCs a jsbeeb trace saw run with the opcode this binary has there."""
        pcs = []
        for path in self.hints.get("traces", []):
            for name, (opcode, _count) in json.loads(Path(path).read_text())["executed"].items():
                pc = int(name[1:].split("/")[0], 16)
                if self.inside(pc) and self.byte(pc) == opcode:
                    pcs.append(pc)
        return pcs

    def collect_refs(self):
        for addr, (mnemonic, mode, operand, size) in self.code.items():
            if mode in ("imp", "acc", "imm") or operand is None:
                continue
            if self.inside(operand):
                self.refs.add(operand)
                # Self-modifying code points into an instruction; it's the
                # instruction that needs the label.
                for back in (1, 2):
                    start = operand - back
                    if start in self.code and self.code[start][3] > back:
                        self.refs.add(start)

    def label_for(self, addr):
        """A label, or label+offset into whatever instruction or data covers addr."""
        if addr in self.labels:
            return self.labels[addr]
        for back in (1, 2):
            start = addr - back
            if start in self.code and self.code[start][3] > back:
                return f"{self.label_for(start)}+{back}"
        prefix = "L" if addr in self.code else "D"
        return f"{prefix}{addr:04X}"

    def operand_text(self, operand, zp_mode):
        if self.inside(operand):
            return self.label_for(operand)
        if operand in self.symbols:
            return self.symbols[operand]
        return hexn(operand)

    def render_insn(self, addr):
        mnemonic, mode, operand, size = self.code[addr]
        if mode == "imp":
            return mnemonic
        if mode == "acc":
            return f"{mnemonic} A"
        if mode == "imm":
            return f"{mnemonic} #{hexn(operand)}"
        text = self.operand_text(operand, mode)
        if mode in SHRINKS and operand < 0x100 and (mnemonic, SHRINKS[mode]) in MODES:
            # Baron would pick the zero-page form; force the original's width.
            suffix = {"abs": "", "abx": ", X", "aby": ", Y"}[mode]
            return f"{mnemonic}_ABS {text}{suffix}"
        return {
            "zp": f"{mnemonic} {text}", "abs": f"{mnemonic} {text}", "rel": f"{mnemonic} {text}",
            "zpx": f"{mnemonic} {text}, X", "abx": f"{mnemonic} {text}, X",
            "zpy": f"{mnemonic} {text}, Y", "aby": f"{mnemonic} {text}, Y",
            "ind": f"{mnemonic} ({text})", "izx": f"{mnemonic} ({text}, X)",
            "izy": f"{mnemonic} ({text}), Y",
        }[mode]

    def render_data(self, start, stop):
        """EQUB lines for start..stop, with printable runs as strings."""
        lines = []
        addr = start
        while addr < stop:
            run = addr
            while run < stop and 0x20 <= self.byte(run) < 0x7F and (run == addr or run not in self.refs):
                run += 1
            if run - addr >= 4:
                text = bytes(self.data[addr - self.org : run - self.org]).decode("latin1")
                lines.append((addr, 'EQUS "' + text.replace('"', '""') + '"'))
                addr = run
                continue
            chunk = []
            while addr < stop and len(chunk) < 8:
                if chunk and addr in self.refs:
                    break
                chunk.append(self.byte(addr))
                addr += 1
                # Stop a byte run where a string starts.
                if all(0x20 <= self.byte(a) < 0x7F for a in range(addr, min(addr + 4, stop))) \
                        and addr + 4 <= stop:
                    break
            lines.append((addr - len(chunk), "EQUB " + ", ".join(hexn(b) for b in chunk)))
        return lines

    def emit(self):
        out = []
        uses_abs = False
        addr = self.org
        while addr < self.end:
            if addr in self.code:
                if addr in self.refs or addr in self.labels:
                    out.append(f".{self.label_for(addr)}")
                text = self.render_insn(addr)
                uses_abs |= "_ABS" in text
                raw = " ".join(f"{self.byte(a):02X}" for a in range(addr, addr + self.code[addr][3]))
                out.append(f"    {text:<32}; {addr:04X}: {raw}")
                addr += self.code[addr][3]
                continue
            stop = addr + 1
            while stop < self.end and stop not in self.code and stop not in self.refs \
                    and stop not in self.labels:
                stop += 1
            if addr in self.refs or addr in self.labels:
                out.append(f".{self.label_for(addr)}")
            for a, line in self.render_data(addr, stop):
                out.append(f"    {line:<32}; {a:04X}")
            addr = stop
        return out, uses_abs

    def run(self):
        entries = list(self.hints.get("entries", [])) + self.executed()
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
        for op in sorted(op for op in self.local if op in used and not self.inside(op)):
            head.append(f"{self.local[op]} = {hexn(op)}")
        head.append(f"SECTION {self.hints['section']}")
        return "\n".join(head + body + ["ENDSECTION", ""])


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    hints_path = Path(sys.argv[1])
    with open(hints_path, "rb") as f:
        hints = tomllib.load(f)
    root = Path(__file__).resolve().parent.parent
    sys.stdout.write(Disassembler(hints, root).run())


if __name__ == "__main__":
    main()
