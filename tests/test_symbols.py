"""Checks on baron's symbol dump of the build (build/symbols.json, which
`make verify` writes before the tests run)."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYMBOLS = ROOT / "build" / "symbols.json"

# The kinds of symbol that name something in the program. FUNCTION and
# macro parameters and FOR variables are left out: every call or iteration
# leaves its own frame of them, under `@...` scopes.
NAMING_GROUPS = ("labels", "assignments", "za_autos", "defines")


def load_symbols():
    """Each source file's symbols as {file: {dotted name: value}}, from
    either baron's format-2 dump (sections, grouped by kind) or the older
    flat one."""
    dump = json.loads(SYMBOLS.read_text())
    if "format" not in dump:
        return {source: {name: value for name, value in symbols.items()
                         if "@" not in name}
                for source, symbols in dump.items()}
    files = {}
    for assembly in dump["assemblies"]:
        names = files.setdefault(assembly["sources"][0], {})
        for section in assembly["sections"]:
            for group in NAMING_GROUPS:
                for name, symbol in section.get(group, {}).items():
                    if "@" not in name:
                        names[name] = symbol["value"]
    return files


@unittest.skipUnless(SYMBOLS.exists(), "no build/symbols.json: run make first")
class ShadowingTest(unittest.TestCase):
    def test_no_scope_shadows_a_file_level_name(self):
        # Baron lets a scope define a name the file already has outside it,
        # and inside the scope the inner one silently wins. The shared names
        # (os.6502inc, osconst.6502inc, io.6502inc...) are defined once each,
        # so a scoped name that repeats one is a stale copy or a label that
        # hides one: either way, a different name is wanted.
        found = []
        for source, symbols in load_symbols().items():
            names = list(symbols)
            top = {name for name in names if "." not in name}
            found += [f"{source}: {name}" for name in names
                      if "." in name and name.rsplit(".", 1)[1] in top]
        self.assertEqual(found, [])


OVERVIEW = ROOT / "docs" / "overview.md"


@unittest.skipUnless(SYMBOLS.exists(), "no build/symbols.json: run make first")
class OverviewTest(unittest.TestCase):
    def test_overview_addresses_match_the_build(self):
        # docs/overview.md gives routines' addresses for reading alongside
        # jsbeeb; a rename or a moved routine would leave them stale. Each
        # name may be given with any of the scopes it's nested in left off.
        addresses = {}
        for symbols in load_symbols().values():
            for name, value in symbols.items():
                if isinstance(value, int):
                    parts = name.split(".")
                    for i in range(len(parts)):
                        addresses.setdefault(".".join(parts[i:]), set()).add(value)
        claims = []
        for line in OVERVIEW.read_text().splitlines():
            # Table rows: names in the first column, addresses in the second.
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if line.startswith("| `") and len(cells) > 1:
                claims += zip(re.findall(r"`([\w.]+)`", cells[0]),
                              re.findall(r"&([0-9A-F]+)", cells[1]))
            # In the text: `name` (&ADDR).
            claims += re.findall(r"`([\w.]+)` \(&([0-9A-F]+)\)", line)
        self.assertGreater(len(claims), 50)
        wrong = [f"{name} &{address}" for name, address in claims
                 if int(address, 16) not in addresses.get(name, ())]
        self.assertEqual(wrong, [])


if __name__ == "__main__":
    unittest.main()
