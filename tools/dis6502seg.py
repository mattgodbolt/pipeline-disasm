#!/usr/bin/env python3
"""dis6502.py for a binary that copies parts of itself elsewhere before running,
grown into a source generator driven by an annotation file.

H.GAME loads at &3000 but its first act is to copy most of itself down to
&0131, &0400, &0880 and &0900 and jump there. Disassembling it at &3000 would
label everything at the wrong address; this disassembles each relocated piece
at the address it runs at, inside a nested baron SECTION with that `org` (baron
"rephases" it: labels at the run address, bytes left in place in the file).

The hints file also carries the annotation - names, comments, operand
expressions, hand-written replacements for data - so the source can be
regenerated as understanding improves without losing anything. Whatever it
produces must still reassemble to the same bytes: `make verify` checks.

usage: dis6502seg.py HINTS.toml > src/piece.6502

The hints are dis6502.py's (binary, org, section, entries, traces, labels,
data, symbols; addresses are run-time addresses) plus:

    scope = "game"           # wrap everything in a named baron scope
    include = ["io.6502inc"] # extra INCLUDEs
    clean = true             # no "; addr: bytes" comments on every line
    header = '''...'''       # comment block at the top of the file
    trace_only = ["0x3000-0x30FF"]   # only believe trace PCs in the
                             # unrelocated part within these (later
                             # programs reuse the load area)

    [[segment]]              # one per relocated piece, in any order
    name = "event_handler"   # its nested SECTION's name
    load = 0x3100            # where the bytes sit when the file is loaded
    run = 0x0131             # where they're copied to and run
    length = 0x60
    comment = '''...'''      # optional, above its SECTION
    end = "event_handler_end"  # optional: a label just past its last byte

    [[inline]]               # a routine that reads data placed after its JSR
    routine = 0x103E         # and returns past it: the bytes after each JSR
    terminator = 0xEA        # are data up to this byte, where code resumes
    # or: length = 6         # a fixed number of bytes of data

    [[table]]                # a table of code addresses (a jump table)
    start = 0x2351
    count = 12
    split = 0                # optional: low bytes here, high bytes `split` on

    [[source]]               # hand-written source for a stretch of data
    start = 0x3015
    length = 6
    text = '''    EQUW a, b, c'''

    [symbols]                # names for addresses outside the file (zero
    0x70 = "map_x"           # page...), defined at the top of the scope;
    0x71 = { name = "map_y", note = "comment" }
    [constants]              # more definitions, name = expression text, for
    copy_from = "&02"        # [operands] to use (a second name for an address)
    [external]               # names for outside addresses defined elsewhere
    0x257F = "io_time_rate"  # (an INCLUDE): used, not defined
    [symbol_comments]        # block comment above a [symbols] definition
    [comments]               # block comment above the line at an address
    [remarks]                # comment at the end of the line at an address
    [operands]               # operand text for the instruction at an address
    0x0C9D = "#HI(restore - 1)"
    [rows]                   # data ranges laid out N bytes to a line
    "0x0880-0x08BF" = 32

    annotations = ["hints/x/a.toml"]  # more files of any of the above, merged
                             # in: tables combined, arrays of tables appended

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
from dis6502 import ENDS_FLOW, MODES, SHRINKS, Disassembler, hexn  # noqa: E402

REMARK_COLUMN = 40


def addr_key(k):
    return int(k, 0) if isinstance(k, str) else k


def ranges(spec):
    """{"lo-hi": value} -> [(lo, hi, value)], inclusive."""
    out = []
    for rng, value in spec.items():
        lo, hi = (int(x, 0) for x in rng.split("-"))
        out.append((lo, hi, value))
    return out


class Piece:
    def __init__(self, load, run, data, name=None, comment=None, end=None):
        self.load, self.run, self.data, self.name, self.comment = load, run, data, name, comment
        self.end_label = end

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
            self.pieces.append(Piece(seg["load"], seg["run"], whole[lo : lo + seg["length"]],
                                     seg["name"], seg.get("comment"), seg.get("end")))
            at = seg["load"] + seg["length"]
        if at < self.end:
            self.pieces.append(Piece(at, at, whole[at - self.org :]))
        # A relocated piece is named by its section's name where it runs,
        # unless the hints give it another.
        for p in self.pieces:
            if p.name:
                self.labels.setdefault(p.run, p.name)
        self.trace_only = [(lo, hi) for lo, hi, _ in ranges({r: None for r in hints.get("trace_only", [])})]
        self.inline = {i["routine"]: i for i in hints.get("inline", [])}

        # Names. [symbols] are defined here; [external] are defined elsewhere.
        self.local = {}
        self.notes = {}
        for k, v in hints.get("symbols", {}).items():
            if isinstance(v, dict):
                self.local[addr_key(k)] = v["name"]
                self.notes[addr_key(k)] = v.get("note")
            else:
                self.local[addr_key(k)] = v
        self.external = {addr_key(k): v for k, v in hints.get("external", {}).items()}
        self.symbols = {**self.os, **self.external, **self.local}

        self.comments = {addr_key(k): v for k, v in hints.get("comments", {}).items()}
        self.remarks = {addr_key(k): v for k, v in hints.get("remarks", {}).items()}
        self.operands = {addr_key(k): v for k, v in hints.get("operands", {}).items()}
        self.rows = ranges(hints.get("rows", {}))
        self.replacements = {r["start"]: r for r in hints.get("source", [])}
        for r in self.replacements.values():
            for a in range(r["start"], r["start"] + r["length"]):
                self.forced.setdefault(a, "source")

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
        self.used_annotations = set()
        self.context = None
        self.clean = hints.get("clean", False)

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
            if not Path(path).exists():
                continue
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
            if addr in self.operands:
                self.used_annotations.add(("operands", addr))
                mnemonic, mode, operand, size = self.code[addr]
                text = self.operands[addr]
                if mode in SHRINKS and operand < 0x100 and (mnemonic, SHRINKS[mode]) in MODES:
                    suffix = {"abs": "", "abx": ", X", "aby": ", Y"}[mode]
                    return f"{mnemonic}_ABS {text}{suffix}"
                return {
                    "imm": f"{mnemonic} {text}", "zp": f"{mnemonic} {text}",
                    "abs": f"{mnemonic} {text}", "rel": f"{mnemonic} {text}",
                    "zpx": f"{mnemonic} {text}, X", "abx": f"{mnemonic} {text}, X",
                    "zpy": f"{mnemonic} {text}, Y", "aby": f"{mnemonic} {text}, Y",
                    "ind": f"{mnemonic} ({text})", "izx": f"{mnemonic} ({text}, X)",
                    "izy": f"{mnemonic} ({text}), Y",
                }[mode]
            return super().render_insn(addr)
        finally:
            self.context = None

    def operand_text(self, operand, zp_mode):
        if self.visible(self.context, operand):
            return self.label_for(operand)
        if operand in self.local:
            self.used_symbols.add(operand)
            return self.local[operand]
        if operand in self.external:
            return self.external[operand]
        if operand in self.os:
            return self.os[operand]
        return hexn(operand)

    def row_length(self, addr):
        for lo, hi, n in self.rows:
            if lo <= addr <= hi:
                return lo, hi, n
        return None

    def render_data(self, start, stop):
        """As dis6502, but jump table entries as label expressions and rows."""
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
            row = self.row_length(addr)
            if row:
                lo, hi, n = row
                end = min(stop, hi + 1, addr + n - (addr - lo) % n)
                lines.append((addr, "EQUB " + ", ".join(hexn(self.byte(a)) for a in range(addr, end))))
                addr = end
                continue
            run = addr
            while run < stop and run not in self.table_entries and not self.row_length(run):
                run += 1
            lines += super().render_data(addr, run)
            addr = run
        return lines

    def breaks(self, addr):
        """Must a data run stop before addr?"""
        return (addr in self.code or addr in self.refs or addr in self.labels
                or addr in self.comments or addr in self.remarks or addr in self.replacements)

    def line(self, text, addr, raw=None):
        self.used_annotations.add(("remarks", addr))
        if addr in self.remarks:
            return f"    {text:<{REMARK_COLUMN - 4}}; {self.remarks[addr]}"
        if self.clean:
            return f"    {text}"
        tail = f"{addr:04X}: {raw}" if raw is not None else f"{addr:04X}"
        return f"    {text:<32}; {tail}"

    def comment(self, out, addr):
        self.used_annotations.add(("comments", addr))
        if addr in self.comments:
            if out and out[-1] != "":
                out.append("")
            for text in self.comments[addr].strip("\n").splitlines():
                out.append(f"; {text}".rstrip())

    def emit_piece(self, p, out):
        uses_abs = False
        whole = (self.org, self.end, self.data)
        self.org, self.end, self.data = p.run, p.end, p.data
        addr = p.run
        while addr < p.end:
            self.comment(out, addr)
            labelled = addr in self.refs or addr in self.labels
            if addr in self.replacements:
                r = self.replacements[addr]
                if labelled:
                    out.append(f".{self.label_for(addr)}")
                out += r["text"].strip("\n").splitlines()
                addr += r["length"]
                continue
            if addr in self.code:
                if labelled:
                    out.append(f".{self.label_for(addr)}")
                text = self.render_insn(addr)
                uses_abs |= "_ABS" in text
                raw = " ".join(f"{self.byte(a):02X}" for a in range(addr, addr + self.code[addr][3]))
                out.append(self.line(text, addr, raw))
                addr += self.code[addr][3]
                continue
            stop = addr + 1
            while stop < p.end and not self.breaks(stop):
                stop += 1
            if labelled:
                out.append(f".{self.label_for(addr)}")
            for a, text in self.render_data(addr, stop):
                out.append(self.line(text, a))
            addr = stop
        self.org, self.end, self.data = whole
        return uses_abs

    def emit(self):
        out = []
        uses_abs = False
        for p in self.pieces:
            if p.name:
                if p.comment:
                    out.append("")
                    out += [f"; {t}".rstrip() for t in p.comment.strip("\n").splitlines()]
                out.append(f".{p.name}_load")
                out.append(f"SECTION {p.name}, org={hexn(p.run)}")
                if self.labels[p.run] != p.name:
                    out.append(f".{p.name}")
            uses_abs |= self.emit_piece(p, out)
            if p.end_label:
                out.append(f".{p.end_label}")
            if p.name:
                out.append("ENDSECTION")
        return out, uses_abs

    def run(self):
        entries = list(self.hints.get("entries", [])) + self.executed()
        entries += [target for _kind, target in self.table_entries.values() if self.inside(target)]
        self.refs |= {target for _kind, target in self.table_entries.values() if self.inside(target)}
        self.trace(entries)
        self.collect_refs()
        self.refs |= set(self.labels)
        body, uses_abs = self.emit()
        for kind in ("comments", "remarks", "operands"):
            for addr in sorted(getattr(self, kind)):
                if (kind, addr) not in self.used_annotations:
                    print(f"warning: [{kind}] {addr:#06x} isn't the start of a line", file=sys.stderr)
        for addr in sorted(self.labels):
            if not self.inside(addr):
                print(f"warning: [labels] {addr:#06x} is outside the file", file=sys.stderr)
        head = []
        if "header" in self.hints:
            head += [f"; {t}".rstrip() for t in self.hints["header"].strip("\n").splitlines()]
            head.append("")
        used = {insn[2] for insn in self.code.values() if insn[1] not in ("imm", "rel", "imp", "acc")}
        if any(op in self.os and op not in self.local for op in used) or self.hints.get("include_os"):
            head.append('INCLUDE "os.6502inc"')
        if uses_abs:
            head.append('INCLUDE "forceabs.6502inc"')
        for inc in self.hints.get("include", []):
            head.append(f'INCLUDE "{inc}"')
        head.append("")
        head.append(f"SECTION {self.hints['section']}")
        scope = self.hints.get("scope")
        defs = []
        # Every [symbols] name is defined, used or not: some are only used in
        # [operands] expressions, and the rest document the variables.
        groups = {addr_key(k): v for k, v in self.hints.get("symbol_comments", {}).items()}
        for op in sorted(self.local):
            if op in groups:
                if defs:
                    defs.append("")
                defs += [f"; {t}".rstrip() for t in groups[op].strip("\n").splitlines()]
            text = f"{self.local[op]} = {hexn(op)}"
            if self.notes.get(op):
                text = f"{text:<{REMARK_COLUMN}}; {self.notes[op]}"
            defs.append(text)
        consts = self.hints.get("constants", {})
        if consts:
            defs.append("")
        for name, value in consts.items():
            if isinstance(value, dict):
                text = f"{name} = {value['value']}"
                if value.get("note"):
                    text = f"{text:<{REMARK_COLUMN}}; {value['note']}"
            else:
                text = f"{name} = {value}"
            defs.append(text)
        if scope:
            lines = head + [f".{scope}", "{"]
            if "symbols_comment" in self.hints:
                lines += [f"; {t}".rstrip() for t in self.hints["symbols_comment"].strip("\n").splitlines()]
            lines += defs + [""] + body + ["}", "ENDSECTION", ""]
        else:
            lines = head + defs + body + ["ENDSECTION", ""]
        return "\n".join(lines)


def load_hints(path: Path, root: Path) -> dict:
    with open(path, "rb") as f:
        hints = tomllib.load(f)
    for extra in hints.get("annotations", []):
        with open(root / extra, "rb") as f:
            more = tomllib.load(f)
        for key, value in more.items():
            if isinstance(value, dict):
                clash = set(hints.get(key, {})) & set(value)
                if clash:
                    raise SystemExit(f"{extra}: [{key}] {sorted(clash)} already given")
                hints.setdefault(key, {}).update(value)
            elif isinstance(value, list):
                hints.setdefault(key, []).extend(value)
            else:
                raise SystemExit(f"{extra}: {key} belongs in the main hints file")
    return hints


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    root = Path(__file__).resolve().parent.parent
    hints = load_hints(Path(sys.argv[1]), root)
    sys.stdout.write(SegmentedDisassembler(hints, root).run())


if __name__ == "__main__":
    main()
