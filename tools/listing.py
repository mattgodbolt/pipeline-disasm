"""Reads a baron -vv listing of one source file: its sections, where each sits
in memory and in its file, the bytes of every statement, its labels and its
`=` names, each with the scope it was written in.

A -vv listing (baron -vv -log0 FILE SOURCE) has a line for each label
(`  3000  .loader`), each statement that emits bytes (address, up to eight
bytes, then the statement; longer runs go on in lines of bytes alone), each
statement that emits none (`INCLUDE`, a macro's call), each `NAME = value
[expression]` assignment, `SECTION ...` and `ENDSECTION`, and `{` and `}`
for scopes, a label just before a `{` naming it. Comments don't appear.

A SECTION inside another (a "rephased" section, assembled for where it runs
but stored in its parent's file) emits its bytes into the parent's stream at
the parent's address when the SECTION starts.
"""

import re
from dataclasses import dataclass, field

# The documented 6502 instruction set, which is all the sources use as
# instructions (anything else is data, a macro's call or a directive).
MNEMONICS = set(
    "ADC AND ASL BCC BCS BEQ BIT BMI BNE BPL BRK BVC BVS CLC CLD CLI CLV CMP CPX CPY "
    "DEC DEX DEY EOR INC INX INY JMP JSR LDA LDX LDY LSR NOP ORA PHA PHP PLA PLP ROL "
    "ROR RTI RTS SBC SEC SED SEI STA STX STY TAX TAY TSX TXA TXS TYA".split()
)

ADDRESS = re.compile(r"^  ([0-9A-F]{4})  ")
LABEL = re.compile(r"^  ([0-9A-F]{4})  \.([A-Za-z_][\w]*)\s*$")
ASSIGN = re.compile(r"^([A-Za-z_][\w]*) = ")
HEX_BYTE = re.compile(r"^[0-9A-F]{2}$")
SOURCE_COLUMN = 36


@dataclass
class Statement:
    address: int            # where it runs
    data: bytearray
    text: str               # the statement as the listing gives it
    section: "Section"
    scope: tuple            # the named scopes it's in, outermost first; None
                            # for one that's anonymous

    @property
    def mnemonic(self):
        word = self.text.split(None, 1)[0] if self.text.strip() else ""
        return word.upper() if word.upper() in MNEMONICS else None

    @property
    def operand(self):
        parts = self.text.split(None, 1)
        return parts[1].strip() if len(parts) > 1 else ""

    @property
    def is_skip(self):
        return self.text.split(None, 1)[0:1] == ["SKIP"]


@dataclass
class Label:
    name: str               # qualified with its scopes
    address: int
    section: "Section"
    scope: tuple
    order: int              # position in the listing


@dataclass
class Section:
    name: str
    header: str             # the SECTION line
    parent: "Section | None"
    stored_at: int | None = None    # parent's address where its bytes are stored
    org: int | None = None
    end: int | None = None
    statements: list = field(default_factory=list)

    @property
    def filename(self):
        match = re.search(r'filename="([^"]*)"', self.header)
        return match.group(1) if match else None

    def top(self):
        section = self
        while section.parent:
            section = section.parent
        return section

    def load_address(self, address):
        """Where the byte that runs at `address` sits as its file is loaded."""
        if self.parent is None:
            return address
        return self.parent.load_address(self.stored_at + address - self.org)

    def memory(self):
        """{run address: byte} for everything this section emits itself."""
        out = {}
        for s in self.statements:
            for i, byte in enumerate(s.data):
                out[s.address + i] = byte
        return out


@dataclass
class Listing:
    sections: list
    statements: list
    labels: list
    assigns: dict           # qualified `=` name -> scope it was written in
    internal_labels: list   # labels in an anonymous scope (baron's @ names)

    def section(self, name):
        found = [s for s in self.sections if s.name == name]
        if len(found) != 1:
            raise KeyError(f"no single section {name!r}")
        return found[0]


def qualify(scope, name):
    return ".".join([*scope, name])


def parse(path):
    sections, statements, labels, internal = [], [], [], []
    assigns = {}
    stack = []              # open sections, innermost last
    scope = []              # named scopes (None for anonymous)
    position = {}           # section -> its current address
    last_label = None       # the label line just before, for `{`
    current = None          # statement collecting continuation lines

    def advance(section, address, length):
        if section.org is None:
            section.org = address
        position[id(section)] = address + length

    with open(path, encoding="latin-1") as f:
        for number, raw in enumerate(f):
            line = raw.rstrip("\n")
            follows_label, last_label = last_label, None
            if line.startswith("SECTION "):
                name = line[len("SECTION "):].split(",")[0].strip()
                parent = stack[-1] if stack else None
                section = Section(name, line, parent)
                if parent is not None:
                    section.stored_at = position.get(id(parent), parent.org)
                sections.append(section)
                stack.append(section)
                current = None
                continue
            if line == "ENDSECTION":
                section = stack.pop()
                section.end = position.get(id(section), section.org)
                if stack:
                    parent = stack[-1]
                    advance(parent, section.stored_at, section.end - section.org)
                current = None
                continue
            if line == "{":
                scope.append(follows_label.name.rsplit(".", 1)[-1] if follows_label else None)
                current = None
                continue
            if line == "}":
                scope.pop()
                current = None
                continue
            match = ASSIGN.match(line)
            if match:
                if None not in scope:
                    assigns[qualify(scope, match.group(1))] = tuple(scope)
                current = None
                continue
            match = LABEL.match(line)
            if match:
                address = int(match.group(1), 16)
                section = stack[-1] if stack else None
                label = Label(qualify([s or "@" for s in scope], match.group(2)), address,
                              section, tuple(scope), number)
                (internal if None in scope else labels).append(label)
                if section is not None:
                    advance(section, address, 0)
                last_label = label
                current = None
                continue
            match = ADDRESS.match(line)
            if not match:
                current = None
                continue
            address = int(match.group(1), 16)
            field_text = line[8:SOURCE_COLUMN].split()
            text = line[SOURCE_COLUMN:].strip()
            data = bytearray(int(b, 16) for b in field_text if HEX_BYTE.match(b))
            section = stack[-1] if stack else None
            if data and not text and current is not None \
                    and current.address + len(current.data) == address:
                current.data += data
            elif data:
                current = Statement(address, data, text, section, tuple(scope))
                if section is not None:
                    section.statements.append(current)
                statements.append(current)
            else:
                current = None
            if section is not None:
                advance(section, address, len(data))
    return Listing(sections, statements, labels, assigns, internal)
