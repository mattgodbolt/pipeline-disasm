"""Checks on baron's symbol dump of the build (build/symbols.json, which
`make verify` writes before the tests run)."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYMBOLS = ROOT / "build" / "symbols.json"


@unittest.skipUnless(SYMBOLS.exists(), "no build/symbols.json: run make first")
class ShadowingTest(unittest.TestCase):
    def test_no_scope_shadows_a_file_level_name(self):
        # Baron lets a scope define a name the file already has outside it,
        # and inside the scope the inner one silently wins. The shared names
        # (os.6502inc, osconst.6502inc, io.6502inc...) are defined once each,
        # so a scoped name that repeats one is a stale copy or a label that
        # hides one: either way, a different name is wanted.
        dump = json.loads(SYMBOLS.read_text())
        found = []
        for source, symbols in dump.items():
            names = [name for name in symbols if "@" not in name]
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
        for symbols in json.loads(SYMBOLS.read_text()).values():
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
