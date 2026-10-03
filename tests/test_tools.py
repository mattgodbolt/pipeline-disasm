"""Tests for the disc tooling, independent of the disassembly itself."""

import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from dfs import SECTOR, Catalogue, Entry, dfs_address, read_catalogue, write_catalogue  # noqa: E402
from mkssd import Image, parse_bytes  # noqa: E402

ORIGINAL = (ROOT / "original" / "pipeline.ssd").read_bytes()


class CatalogueTest(unittest.TestCase):
    def test_original_round_trips(self):
        cat = read_catalogue(ORIGINAL)
        self.assertEqual(write_catalogue(cat), ORIGINAL[: 2 * SECTOR])

    def test_original_catalogue(self):
        cat = read_catalogue(ORIGINAL)
        self.assertEqual(cat.title, "PIPELINE")
        self.assertEqual(len(cat.entries), 16)
        boot = cat.entries[-1]
        self.assertEqual((boot.full_name, boot.load, boot.length), ("$.!BOOT", 0x3FFFF, 0x94))
        self.assertTrue(all(e.locked for e in cat.entries))

    def test_high_address_bits(self):
        e = Entry("X", "$", False, 0x31900, 0x38023, 0x21234, 0x3FF)
        cat = Catalogue("T", 0, 0, 800, [e])
        self.assertEqual(read_catalogue(write_catalogue(cat) + bytes(SECTOR)).entries[0], e)


class AddressTest(unittest.TestCase):
    def test_io_processor_addresses(self):
        self.assertEqual(dfs_address(0xFFFF1900), 0x31900)
        self.assertEqual(dfs_address(0xFFFFFFFF), 0x3FFFF)
        self.assertEqual(dfs_address(0x0900), 0x0900)


class LayoutTest(unittest.TestCase):
    def test_parse_bytes(self):
        self.assertEqual(parse_bytes("00*3 A1b2 10"), bytes([0, 0, 0, 0xA1, 0xB2, 0x10]))
        self.assertEqual(parse_bytes(""), b"")

    def test_overlap_refused(self):
        image = Image(4, 0xE5)
        image.place("a", 1, bytes(300))
        with self.assertRaises(SystemExit):
            image.place("b", 2, bytes(1))

    def test_layout_covers_every_catalogued_file(self):
        with open(ROOT / "src" / "disc.toml", "rb") as f:
            layout = tomllib.load(f)
        names = [f["name"] for f in layout["file"]]
        self.assertEqual(names, [e.name for e in read_catalogue(ORIGINAL).entries])


if __name__ == "__main__":
    unittest.main()
