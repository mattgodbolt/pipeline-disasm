"""Checks on the symbol sets `make jsbeeb-symbols` writes for jsbeeb's
debugger: each set on its own, by the rules in jsbeeb's
docs/media-registry-proposal.md ("Symbol sets"), and every anchor against
the built files. jsbeeb's own validator will do the first part once the
sets live in its registry; the second needs the build."""

import json
import re
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from jsbeeb_symbols import operand_base  # noqa: E402
from listing import parse  # noqa: E402

SETS = ROOT / "build" / "jsbeeb-symbols"
LISTINGS = ROOT / "build" / "listings"
FILES = ROOT / "build" / "files"
CONFIG = ROOT / "src" / "symbols.toml"

HEX_ADDRESS = re.compile(r"0x[0-9a-f]{1,5}")
HEX_BYTES = re.compile(r"(?:[0-9a-f]{2})+")
NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
LICENCE = re.compile(r"(?:LicenseRef-[A-Za-z0-9.-]+|[A-Za-z0-9.+-]+)")
DISC_KEY = re.compile(r"[0-9a-f]{32}")
TOP_KEYS = {"format", "title", "licence", "source", "notice", "madeFrom", "regions", "globals"}
REGION_KEYS = {"start", "end", "anchors", "minAnchors", "symbols"}
ANCHOR_LENGTHS = range(4, 9)
IO_PAGES = range(0xFC00, 0xFF00)


def address(text):
    assert HEX_ADDRESS.fullmatch(text), text
    return int(text, 16)


def load_sets():
    return {path.stem: json.loads(path.read_text()) for path in sorted(SETS.glob("*.json"))}


@unittest.skipUnless(SETS.is_dir(), "no build/jsbeeb-symbols: run make jsbeeb-symbols first")
class SetRulesTest(unittest.TestCase):
    """What jsbeeb's build checks of each set."""

    def setUp(self):
        self.sets = load_sets()

    def test_one_file_per_configured_set(self):
        with open(CONFIG, "rb") as f:
            config = tomllib.load(f)
        self.assertEqual(sorted(self.sets), sorted(spec["id"] for spec in config["set"]))

    def test_schema(self):
        for name, data in self.sets.items():
            with self.subTest(set=name):
                self.assertLessEqual(set(data), TOP_KEYS)
                self.assertEqual(data["format"], 1)
                self.assertTrue(data["title"].strip())
                self.assertRegex(data["licence"], LICENCE)
                self.assertTrue(data["source"].startswith("https://"))
                for key in data.get("madeFrom", []):
                    self.assertRegex(key, DISC_KEY)
                self.assertTrue(data["regions"])
                for region_name, region in data["regions"].items():
                    self.assertRegex(region_name, NAME)
                    self.assertEqual(set(region), REGION_KEYS)
                    self.assertLess(address(region["start"]), address(region["end"]))
                    self.assertLessEqual(address(region["end"]), 0x10000)
                    for symbol, where in region["symbols"].items():
                        self.assertRegex(symbol, NAME)
                        self.assertTrue(address(region["start"]) <= address(where) < address(region["end"]),
                                        f"{region_name}: {symbol} {where} is outside the region")
                for symbol, where in data["globals"].items():
                    self.assertRegex(symbol, NAME)
                    self.assertLess(address(where), 0x10000)

    def test_anchors(self):
        for name, data in self.sets.items():
            for region_name, region in data["regions"].items():
                with self.subTest(region=f"{name}/{region_name}"):
                    anchors = region["anchors"]
                    self.assertTrue(anchors, "a region without anchors never shows")
                    # Every anchor has to match, so asking for fewer is only
                    # ever a mistake here.
                    self.assertEqual(region["minAnchors"], len(anchors))
                    start, end = address(region["start"]), address(region["end"])
                    covered = set()
                    for anchor in anchors:
                        self.assertEqual(set(anchor), {"at", "bytes"})
                        self.assertRegex(anchor["bytes"], HEX_BYTES)
                        length = len(anchor["bytes"]) // 2
                        self.assertIn(length, ANCHOR_LENGTHS)
                        at = address(anchor["at"])
                        span = set(range(at, at + length))
                        self.assertTrue(start <= at and at + length <= end, f"{anchor} is outside the region")
                        self.assertFalse(span & set(IO_PAGES), f"{anchor} is in &FC00-&FEFF")
                        self.assertFalse(span & covered, f"{anchor} overlaps another anchor")
                        covered |= span

    def test_names_unique_in_a_set(self):
        for name, data in self.sets.items():
            with self.subTest(set=name):
                names = [n for r in data["regions"].values() for n in r["symbols"]] + list(data["globals"])
                self.assertEqual(sorted(n for n in set(names) if names.count(n) > 1), [])

    def test_one_name_per_address(self):
        for name, data in self.sets.items():
            for where, symbols in [(f"{name}/{r}", region["symbols"]) for r, region in data["regions"].items()] \
                    + [(f"{name} globals", data["globals"])]:
                with self.subTest(names=where):
                    addresses = [address(a) for a in symbols.values()]
                    self.assertEqual(sorted({a for a in addresses if addresses.count(a) > 1}), [])


@unittest.skipUnless(SETS.is_dir() and LISTINGS.is_dir(), "no build/jsbeeb-symbols: run make jsbeeb-symbols first")
class AnchorsMatchTheBuildTest(unittest.TestCase):
    """Each anchor's bytes are the built file's, at the address the byte
    runs at (a section assembled to run elsewhere is stored in its parent's
    file)."""

    def test_anchors_match_the_built_files(self):
        with open(CONFIG, "rb") as f:
            config = tomllib.load(f)
        sets = load_sets()
        listings = {}
        checked = 0
        for spec in config["set"]:
            for region in spec["region"]:
                source = region.get("source", spec["sources"][0])
                if source not in listings:
                    listings[source] = parse(LISTINGS / f"{source}.txt")
                section = listings[source].section(region["section"])
                top = section.top()
                data = (FILES / top.filename).read_bytes()
                for anchor in sets[spec["id"]]["regions"][region["name"]]["anchors"]:
                    at = address(anchor["at"])
                    expected = bytes.fromhex(anchor["bytes"])
                    built = bytes(data[section.load_address(at + i) - top.org] for i in range(len(expected)))
                    self.assertEqual(built.hex(), anchor["bytes"], f"{spec['id']}/{region['name']} {anchor['at']}")
                    checked += 1
        self.assertGreater(checked, 0)


class OperandTest(unittest.TestCase):
    """Which name in an operand is the address it uses."""

    def test_operand_base(self):
        self.assertEqual(operand_base("menu_keys, X"), "menu_keys")
        self.assertEqual(operand_base("copy_from - 1, Y"), "copy_from")
        self.assertEqual(operand_base("(copy_return), Y"), "copy_return")
        self.assertEqual(operand_base("select_sprite.down_not_0f"), "select_sprite.down_not_0f")
        self.assertEqual(operand_base("&0D00 + work0"), "work0")
        self.assertIsNone(operand_base("#LO(event_handler)"))
        self.assertIsNone(operand_base("tile(CELL_FLOOR), X"))
        self.assertIsNone(operand_base("A"))
        self.assertIsNone(operand_base(""))


if __name__ == "__main__":
    unittest.main()
