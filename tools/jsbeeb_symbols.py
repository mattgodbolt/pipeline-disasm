#!/usr/bin/env python3
"""Writes jsbeeb's debugger symbol sets for PIPELINE's programs, one JSON
file per set, from the build: baron's symbol dump, each source's -vv listing
and the built files.

    jsbeeb_symbols.py CONFIG LISTINGS SYMBOLS FILES OUT --commit SHA

CONFIG is src/symbols.toml, which says which programs make a set and how
each is cut into regions; LISTINGS holds one -vv listing per source
(NAME.txt), SYMBOLS is build/symbols.json and FILES build/files. The format
is jsbeeb's ("Symbol sets" in its docs/media-registry-proposal.md);
docs/notes/symbols.md says how the names and anchors are chosen. Exits 1 if
a region can't be anchored or its anchors match another of the build's
images.
"""

import argparse
import json
import math
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from listing import parse

FORMAT = 1
ANCHOR_MIN, ANCHOR_TARGET, ANCHOR_MAX = 4, 6, 8
MIN_DISTINCT_BYTES = 4
IO_PAGES = range(0xFC00, 0xFF00)
MOS_START = 0xC000
OPCODE_JSR, OPCODE_JMP, OPCODE_NOP = 0x20, 0x4C, 0xEA
INDEXED_REACH = 0x100
OS_BLOCK_MOST = 18          # an OSFILE block, the longest the OS writes back
BASIC_EXEC = 0x8023         # BASIC II's entry: a saved BASIC program's exec address
BASIC_LINE_LENGTH = 3       # where a line's length byte is, after CR and its number
BASIC_LINE_TEXT = 4         # where its text starts
CR, QUOTE, TOKEN_REM = 0x0D, 0x22, 0xF4

# Stores and read-modify-writes whose target the instruction names, by
# opcode. An indexed one in zero page wraps round it.
ZP, ZP_INDEXED, ABS, ABS_INDEXED = "zp", "zp,i", "abs", "abs,i"
STORES = {0x85: ZP, 0x95: ZP_INDEXED, 0x8D: ABS, 0x9D: ABS_INDEXED, 0x99: ABS_INDEXED,     # STA
          0x86: ZP, 0x96: ZP_INDEXED, 0x8E: ABS,                                         # STX
          0x84: ZP, 0x94: ZP_INDEXED, 0x8C: ABS}                                         # STY
for opcode in (0x06, 0x26, 0x46, 0x66, 0xC6, 0xE6):                 # ASL ROL LSR ROR DEC INC
    STORES |= {opcode: ZP, opcode + 0x10: ZP_INDEXED, opcode + 0x08: ABS, opcode + 0x18: ABS_INDEXED}

# The source names dead code and the bytes a file was saved with like this.
NOT_THE_PROGRAM = re.compile(r"(^|_)(unused|leftover|junk|spare|stray)(_|$)")

NAME = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*"
OPERAND_TOKEN = re.compile(
    rf"\s*(?:&[0-9A-Fa-f]+|%[01]+|\d+|'(?:[^']|'')'|\"(?:[^\"]|\"\")*\"|(?P<name>{NAME})|.)")


def hexaddr(address):
    return f"0x{address:04x}"


def evaluate(expression, lookup):
    """A config expression: names, &hex, decimal, + - * / and brackets."""
    def value(match):
        found = lookup(match.group(0))
        if found is None:
            raise SystemExit(f"symbols.toml: no symbol {match.group(0)!r} in {expression!r}")
        return str(found)
    text = re.sub(r"&([0-9A-Fa-f]+)", lambda m: str(int(m.group(1), 16)), str(expression))
    text = re.sub(NAME, value, text)
    if not re.fullmatch(r"[\d\s+\-*/()]*", text):
        raise SystemExit(f"symbols.toml: can't evaluate {expression!r}")
    return int(eval(text))      # only digits and arithmetic are left, checked above


def operand_base(operand):
    """The name an operand's address is built on, its first name; None for
    an immediate operand, one with no name, or one built on a FUNCTION."""
    if not operand or operand.startswith("#"):
        return None
    for match in OPERAND_TOKEN.finditer(operand):
        name = match.group("name")
        if name:
            if name.upper() in ("A", "X", "Y") or operand[match.end():].lstrip().startswith("("):
                return None
            return name
    return None


@dataclass(eq=False)
class Source:
    """One source file's listing and symbols."""
    name: str
    listing: object
    symbols: dict

    def __post_init__(self):
        self.labels = {label.name for label in self.listing.labels}

    def resolve(self, scope, name):
        """The qualified name `name` means when written inside `scope`."""
        for depth in range(len(scope), -1, -1):
            if None in scope[:depth]:
                continue
            candidate = ".".join([*scope[:depth], name])
            if candidate in self.symbols:
                return candidate
        return None

    def lookup(self, name):
        value = self.symbols.get(name)
        return value if isinstance(value, int) and not isinstance(value, bool) else None


@dataclass(eq=False)
class Region:
    name: str
    full_name: str          # set/region, for messages
    source: Source
    section: object
    start: int
    end: int
    overwritten: bool
    avoid: list
    memory: dict = field(default_factory=dict)
    image: bytes = b""
    symbols: dict = field(default_factory=dict)
    anchors: list = field(default_factory=list)

    def holds(self, address):
        return self.start <= address < self.end

    def runs(self, statement):
        return statement.section is self.section and self.holds(statement.address)


@dataclass
class Candidate:
    at: int
    data: bytes
    labelled: bool
    code: bool

    def score(self):
        # A routine's entry first, then code, then the most distinct bytes.
        return (self.labelled, self.code, min(len(set(self.data)), ANCHOR_TARGET),
                len(self.data) >= ANCHOR_TARGET)

    def covers(self, other):
        return self.at < other.at + len(other.data) and other.at < self.at + len(self.data)

    def fails_on(self, memory):
        """Whether memory holding another image fails this anchor."""
        return any((self.at + i) in memory and memory[self.at + i] != b for i, b in enumerate(self.data))

    def held_by(self, memory):
        return all((self.at + i) in memory for i in range(len(self.data)))


@dataclass
class Store:
    statement: object
    first: int
    last: int


class Builder:
    def __init__(self, config, listings, symbols, files, commit):
        self.config = config
        self.listings = Path(listings)
        self.dump = json.loads(Path(symbols).read_text())
        self.files = Path(files)
        self.commit = commit
        self.sources = {}
        self.errors = []
        self.notes = []
        self.reasons = []
        self.os_names = set(re.findall(r"^([A-Za-z_]\w*)\s*=", Path(config["os_names"]).read_text(), re.M))
        self.program_sources = {name for spec in config["set"] for name in spec["sources"]} | \
            {r["source"] for spec in config["set"] for r in spec["region"] if "source" in r}
        self.images = self.load_images()

    def source(self, name):
        if name not in self.sources:
            source = Source(name, parse(self.listings / f"{name}.txt"), self.dump[f"src/{name}.6502"])
            for label in source.listing.labels:
                if source.symbols.get(label.name) != label.address:
                    raise SystemExit(f"{name}: the listing has {label.name} at &{label.address:04X}, "
                                     f"the symbol dump {source.symbols.get(label.name)!r}")
            self.sources[name] = source
        return self.sources[name]

    def load_images(self):
        """Everything the build puts in memory, at the addresses it occupies:
        each section where it runs, and each file where it loads. (name,
        {address: byte}, program) with program true for a section of a
        source that makes a set."""
        out = []
        for path in sorted(self.listings.glob("*.txt")):
            source = self.source(path.stem)
            for section in source.listing.sections:
                memory = section.image()
                if memory:
                    out.append((f"{source.name}:{section.name}", memory, source.name in self.program_sources))
        for inf in sorted(self.files.glob("*.inf")):
            name = inf.name[: -len(".inf")]
            load = int(inf.read_text().split()[1], 16) & 0xFFFF
            data = (self.files / name).read_bytes()
            out.append((f"file {name}", {load + i: b for i, b in enumerate(data)}, False))
        return out

    # ------------------------------------------------------------------ a set

    def build(self, spec):
        sources = [self.source(name) for name in spec["sources"]]
        strip = spec.get("strip_scope")

        def shown(name):
            return name[len(strip) + 1:] if strip and name.startswith(strip + ".") else name

        regions = []
        for r in spec["region"]:
            source = self.source(r.get("source", spec["sources"][0]))
            section = source.listing.section(r["section"])
            find = finder(source, strip)
            start = evaluate(r["from"], find) if "from" in r else section.org
            end = evaluate(r["to"], find) if "to" in r else section.end
            region = Region(r["name"], f"{spec['id']}/{r['name']}", source, section, start, end,
                            r.get("overwritten", False),
                            [(evaluate(a, find), evaluate(b, find)) for a, b in r.get("avoid", [])])
            region.memory = {a: b for a, b in section.image().items() if start <= a < end}
            region.image = bytes(region.memory.get(a, 0) for a in range(start, end))
            regions.append(region)

        named = {id(r): {} for r in regions}       # address -> [(name, rank)]
        globals_named = {}
        dropped = []

        # Labels belong to the region of the section they're assembled in.
        for source in sources + [r.source for r in regions if r.source not in sources]:
            for label in source.listing.labels:
                if label.name == strip:
                    continue
                section = label.section
                if section is not None and section.name in spec.get("globals_sections", []):
                    if section.org <= label.address < section.end:
                        globals_named.setdefault(label.address, []).append((shown(label.name), (0, label.order)))
                    else:
                        dropped.append((shown(label.name), label.address, "past its section's end"))
                    continue
                homes = [r for r in regions if r.source is source and r.section is section
                         and r.holds(label.address)]
                if len(homes) != 1:
                    dropped.append((shown(label.name), label.address, "in no region"))
                    continue
                named[id(homes[0])].setdefault(label.address, []).append(
                    (shown(label.name), (-len(label.scope), label.order)))

        # A `=` name an instruction uses as a memory operand is an address:
        # its region's, if only that region's code uses it, else a global.
        for source in sources:
            uses = {}
            for s in source.listing.statements:
                base = operand_base(s.operand) if s.mnemonic else None
                name = source.resolve(s.scope, base) if base else None
                if name in source.listing.assigns and name not in source.labels and name not in self.os_names:
                    uses.setdefault(name, []).append(s)
            order = {name: i for i, name in enumerate(source.listing.assigns)}
            for name, statements in uses.items():
                address = source.lookup(name)
                if address is None or not 0 <= address <= 0xFFFF:
                    continue
                inside = [r for r in regions if r.source is source and r.holds(address)]
                if len(inside) == 1 and all(inside[0].runs(s) for s in statements):
                    named[id(inside[0])].setdefault(address, []).append(
                        (shown(name), (-len(source.listing.assigns[name]) - 1, order[name])))
                else:
                    globals_named.setdefault(address, []).append((shown(name), (len(statements), order[name])))

        # One name per address: in a region, a scope's own name over the
        # labels inside it, then the label nearest the bytes (the last
        # written); in the globals, the name most instructions use.
        for region in regions:
            for address, names in named[id(region)].items():
                names.sort(key=lambda n: n[1], reverse=True)
                region.symbols[names[0][0]] = address
                dropped += [(n, address, f"{region.name} calls it {names[0][0]}") for n, _ in names[1:]]
        globals_chosen = {}
        for address, names in globals_named.items():
            names.sort(key=lambda n: n[1], reverse=True)
            globals_chosen[names[0][0]] = address
            dropped += [(n, address, f"the globals call it {names[0][0]}") for n, _ in names[1:]]

        every = [n for r in regions for n in r.symbols] + list(globals_chosen)
        twice = sorted({n for n in every if every.count(n) > 1})
        if twice:
            raise SystemExit(f"{spec['id']}: names given twice: {twice}")

        stores = [store for source in sources for store in self.stores(spec, source)]
        for region in regions:
            self.choose_anchors(region, stores)

        out = {"format": FORMAT, "title": spec["title"], "licence": self.config["licence"],
               "source": f"{self.config['repository']}/tree/{self.commit}"}
        for key in ("notice", "madeFrom"):
            if key in self.config:
                out[key] = self.config[key]
        out["regions"] = {
            r.name: {
                "start": hexaddr(r.start),
                "end": hexaddr(r.end),
                "minAnchors": len(r.anchors),
                "anchors": [{"at": hexaddr(c.at), "bytes": c.data.hex()} for c in r.anchors],
                "symbols": by_address(r.symbols),
            }
            for r in regions
        }
        out["globals"] = by_address(globals_chosen)
        return out, regions, dropped

    # ------------------------------------------------------------------ stores

    def stores(self, spec, source):
        """Every store whose target the code gives, with how far it reaches:
        256 bytes for an indexed one, unless symbols.toml gives its table's
        size, and none for a copy that puts the program in place."""
        strip = spec.get("strip_scope")
        find = finder(source, strip)
        sizes = {find(name): evaluate(size, find) for name, size in spec.get("table_sizes", {}).items()}
        moves = {find(name) for name in spec.get("moves", [])}
        if None in sizes or None in moves:
            raise SystemExit(f"symbols.toml: {spec['id']}: a table or a move names no symbol")
        out, used = [], set()
        for s in source.listing.statements:
            if not s.mnemonic or s.data[0] not in STORES:
                continue
            if s.address in moves:
                used.add(s.address)
                continue
            mode = STORES[s.data[0]]
            target = s.data[1] if len(s.data) == 2 else s.data[1] | s.data[2] << 8
            base = operand_base(s.operand)
            table = source.lookup(source.resolve(s.scope, base) or "") if base else None
            if mode in (ZP, ABS):
                out.append(Store(s, target, target))
            elif table in sizes:
                used.add(table)
                out.append(Store(s, target, target + sizes[table] - 1))
            elif mode == ZP_INDEXED:
                out.append(Store(s, 0, 0xFF))
            else:
                out.append(Store(s, target, target + INDEXED_REACH - 1))
        if (set(sizes) | moves) - used:
            raise SystemExit(f"symbols.toml: {spec['id']}: a table or a move matches no store")
        return out

    # ------------------------------------------------------------------ anchors

    def blocked(self, region, stores):
        """Addresses in the region no anchor may cover."""
        out = set()
        for store in stores:
            if region.overwritten and not region.runs(store.statement):
                continue    # what overwrites run-once code is why its anchors are there
            out.update(range(max(store.first, region.start), min(store.last + 1, region.end)))
        for first, end in region.avoid:
            out.update(range(first, end))
        out.update(a for a in range(region.start, region.end) if a in IO_PAGES)
        for s in region.section.statements:
            if s.is_skip:
                out.update(range(s.address, s.address + len(s.data)))
        out.update(self.basic_line_starts(region))
        out.update(self.os_blocks(region))
        labels = sorted((l.address, l.name) for l in region.source.listing.labels
                        if l.section is region.section and region.holds(l.address))
        for i, (address, name) in enumerate(labels):
            if any(NOT_THE_PROGRAM.search(part) for part in name.split(".")):
                following = [a for a, _ in labels[i + 1:] if a > address]
                out.update(range(address, following[0] if following else region.end))
        return out

    @staticmethod
    def os_blocks(region):
        """Blocks the code hands to the OS (LDX #LO(block)), which OSWORD,
        OSFILE and OSGBPB write results back into: from the block's label to
        the next that starts code or another block, OS_BLOCK_MOST at most."""
        source, section = region.source, region.section
        targets = set()
        for s in source.listing.statements:
            match = re.fullmatch(rf"#\s*LO\(\s*({NAME})\s*\)", s.operand) if s.mnemonic == "LDX" else None
            name = source.resolve(s.scope, match.group(1)) if match else None
            if name in source.labels:
                targets.add(source.lookup(name))
        code = {s.address for s in section.statements if s.mnemonic}
        stops = sorted({l.address for l in source.listing.labels if l.section is section
                        and (l.address in code or l.address in targets)} | {section.end})
        out = set()
        for first in sorted(t for t in targets if region.holds(t)):
            end = min(next(a for a in stops if a > first), first + OS_BLOCK_MOST)
            out.update(range(first, end))
        return out

    @staticmethod
    def basic_line_starts(region):
        """In a BASIC program, what's much the same in every program or
        isn't the program at all: the first line, often only a REM; each
        line's CR, number and length; and REMs, but for any code in them."""
        exec_address = re.search(r"exec=&([0-9A-Fa-f]+)", region.section.header)
        if not exec_address or int(exec_address.group(1), 16) & 0xFFFF != BASIC_EXEC:
            return set()
        code = {a for s in region.section.statements if s.mnemonic for a in range(s.address, s.address + len(s.data))}
        memory, out, line = region.memory, set(), region.section.org
        while memory.get(line) == CR and memory.get(line + 1, 0xFF) < 0x80:
            end = line + memory[line + BASIC_LINE_LENGTH]
            out.update(range(line, end if line == region.section.org else line + BASIC_LINE_TEXT))
            quoted = False
            for a in range(line + BASIC_LINE_TEXT, end):
                quoted ^= memory[a] == QUOTE
                if memory[a] == TOKEN_REM and not quoted:
                    out.update(set(range(a, end)) - code)
                    break
            line = end
        return out

    def candidates(self, region, blocked):
        """Every run of 4 to 8 bytes that could be an anchor: whole
        instructions from an instruction's start, or data from any byte."""
        statements = sorted((s for s in region.section.statements if region.holds(s.address)),
                            key=lambda s: s.address)
        labelled = {l.address for l in region.source.listing.labels if l.section is region.section}
        starts = []
        for i, s in enumerate(statements):
            starts += [(s.address, i, 0)] if s.mnemonic else [(s.address + k, i, k) for k in range(len(s.data))]
        out = []
        for at, i, k in starts:
            data, has_code = bytearray(), False
            while len(data) < ANCHOR_TARGET and i < len(statements):
                s = statements[i]
                if s.address + k != at + len(data) or s.is_skip:
                    break
                if s.mnemonic:
                    if len(data) + len(s.data) > ANCHOR_MAX:
                        break
                    data += s.data
                    has_code = True
                    if self.calls_os(s):
                        data = bytearray()
                        break
                else:
                    data += s.data[k:k + ANCHOR_TARGET - len(data)]
                i, k = i + 1, 0
            data = bytes(data)
            if len(data) < ANCHOR_MIN or len(set(data)) < MIN_DISTINCT_BYTES:
                continue
            if any(a in blocked or not region.holds(a) for a in range(at, at + len(data))):
                continue
            if has_code and bytes([OPCODE_NOP, OPCODE_NOP]) in data:
                continue    # where cheats poke
            if occurrences(region, data) > 1:
                continue
            out.append(Candidate(at, data, at in labelled, has_code))
        return out

    @staticmethod
    def calls_os(statement):
        """A JSR or JMP into the MOS: the code every program shares."""
        return statement.data[0] in (OPCODE_JSR, OPCODE_JMP) and len(statement.data) == 3 \
            and (statement.data[1] | statement.data[2] << 8) >= MOS_START

    def choose_anchors(self, region, stores):
        pool = self.candidates(region, self.blocked(region, stores))
        if not pool:
            self.errors.append(f"{region.full_name}: nothing to anchor on")
            return
        chosen = []

        def take(options):
            best = max(c.score() for c in options)
            chosen.append(next(c for c in options if c.score() == best))

        # About one per bytes_per_anchor, spread over the region.
        count = max(1, min(self.config["spread_anchors"],
                           math.ceil((region.end - region.start) / self.config["bytes_per_anchor"])))
        width = (region.end - region.start) / count
        for slot in range(count):
            here = [c for c in pool if region.start + slot * width <= c.at < region.start + (slot + 1) * width
                    and not any(c.covers(o) for o in chosen)]
            if here:
                take(here)

        # Another image holding every anchor has to fail one of them; another
        # program's image of the same addresses should fail one inside it.
        own = f"{region.source.name}:{region.section.name}"
        for name, memory, program in self.images:
            if name == own:
                continue
            overlap = [a for a in region.memory if a in memory]
            if not overlap or all(memory[a] == region.memory[a] for a in overlap):
                continue
            collides = all(c.held_by(memory) and not c.fails_on(memory) for c in chosen)
            covered = any(c.fails_on(memory) for c in chosen)
            if covered or not (collides or program):
                continue
            telling = [c for c in pool if c.fails_on(memory) and not any(c.covers(o) for o in chosen)]
            if telling:
                take(telling)
                self.reasons.append(f"{region.full_name}: an anchor at &{chosen[-1].at:04X} for {name}")
            elif collides:
                self.errors.append(f"{region.full_name}: its anchors all match {name}")
            else:
                self.notes.append(f"{region.full_name}: no anchor where {name} differs")
        region.anchors = sorted(chosen, key=lambda c: c.at)


def finder(source, strip):
    """Looks up a name as symbols.toml writes it: in the source's own
    terms, or inside the scope the set leaves off its names."""
    def find(name):
        value = source.lookup(name)
        return source.lookup(f"{strip}.{name}") if value is None and strip else value
    return find


def occurrences(region, data):
    count, start = 0, 0
    while (start := region.image.find(data, start)) >= 0:
        count, start = count + 1, start + 1
    return count


def by_address(names):
    return {n: hexaddr(a) for n, a in sorted(names.items(), key=lambda x: (x[1], x[0]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for arg in ("config", "listings", "symbols", "files", "out"):
        parser.add_argument(arg)
    parser.add_argument("--commit", required=True)
    parser.add_argument("-v", "--verbose", action="store_true", help="list the names left out, and why")
    args = parser.parse_args()
    with open(args.config, "rb") as f:
        config = tomllib.load(f)
    builder = Builder(config, args.listings, args.symbols, args.files, args.commit)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    for spec in config["set"]:
        data, regions, dropped = builder.build(spec)
        (out / f"{spec['id']}.json").write_text(json.dumps(data, indent=2) + "\n")
        print(f"{spec['id']}: " + ", ".join(f"{r.name} {len(r.anchors)}/{len(r.symbols)}" for r in regions)
              + f"; {len(data['globals'])} globals ({len(dropped)} names left out)")
        if args.verbose:
            for name, address, why in dropped:
                print(f"    left out {name} &{address:04X}: {why}")
    if args.verbose:
        for reason in builder.reasons:
            print(f"    {reason}")
    for note in builder.notes:
        print(f"note: {note}")
    for error in builder.errors:
        print(f"error: {error}", file=sys.stderr)
    return 1 if builder.errors else 0


if __name__ == "__main__":
    sys.exit(main())
