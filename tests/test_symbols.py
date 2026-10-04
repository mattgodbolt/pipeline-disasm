"""Checks on baron's symbol dump of the build (build/symbols.json, which
`make verify` writes before the tests run)."""

import json
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


if __name__ == "__main__":
    unittest.main()
