"""tools/basic.py must list a program as text baron's BASIC block takes back.

The round trip lists each BASIC program the build produced and tokenises
every line again with baron (bytes with no text form as splices), which
must give the same program.
Needs `make` to have run first, and baron (BARON=path, as make passes it).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import basic  # noqa: E402

FILES = ROOT / "build" / "files"
BARON = os.environ.get("BARON") or shutil.which("baron")
PROGRAMS = ["MENU", "MISSION"]


class DetokeniseTest(unittest.TestCase):
    def test_line_numbers(self):
        # Encodings from baron's own tokeniser tests.
        self.assertEqual(basic.decode_line_number(0x54, 0x4A, 0x40), 10)
        self.assertEqual(basic.decode_line_number(0x44, 0x4D, 0x41), 333)
        self.assertEqual(basic.decode_line_number(0x54, 0x79, 0x70), 12345)
        self.assertEqual(basic.decode_line_number(0x74, 0x4B, 0x40), 139)

    def test_raw_regions(self):
        # REM keeps its bytes even when they look like tokens; a * command
        # at a statement start does too; strings aren't expanded.
        self.assertEqual(basic.detokenise(bytes([0xF4]) + b" \xf1"), ("REM {\n    EQUB &F1 }", False))
        self.assertEqual(basic.detokenise(b"*FX15,1"), ("*FX15,1", True))
        self.assertEqual(basic.detokenise(bytes([0xF1]) + b'"AND"'), ('PRINT"AND"', True))
        self.assertEqual(basic.detokenise(bytes([0xE5, 0x8D, 0x54, 0x4A, 0x40])), ("GOTO10", True))

    def test_splices(self):
        # Runs of bytes with no text form become one splice each, the text
        # carrying on after the `}`; a brace ending the line is spliced too,
        # as baron would read it as opening one.
        self.assertEqual(basic.detokenise(bytes([0xF4]) + b'"\x7f\x82Hi,\x83So'),
                         ('REM"{\n    EQUB &7F, &82 }Hi,{\n    EQUB &83 }So', False))
        self.assertEqual(basic.detokenise(bytes([0xF4]) + b" a{"), ("REM a{\n    EQUB &7B }", False))


@unittest.skipUnless(FILES.is_dir() and BARON, "needs `make` run first and baron")
class RoundTripTest(unittest.TestCase):
    def test_listing_retokenises(self):
        for name in PROGRAMS:
            with self.subTest(program=name):
                data = (FILES / name).read_bytes()
                lines = []
                for end, number, text in basic.records(data):
                    if number is None:
                        break
                    line, clean = basic.detokenise(text)
                    lines.append(f"{number}{line}")
                self.assertGreater(len(lines), 90)
                with tempfile.TemporaryDirectory() as tmp:
                    tmp = Path(tmp)
                    src = "SECTION t, filename=\"OUT\", org=&1900\nBASIC\n"
                    src += "\n".join(lines) + "\nENDBASIC\nENDSECTION\n"
                    (tmp / "t.6502").write_text(src)
                    subprocess.run([BARON, "-p", str(tmp), str(tmp / "t.6502")], check=True,
                                   capture_output=True)
                    self.assertEqual((tmp / "OUT").read_bytes(), data[:end])


if __name__ == "__main__":
    unittest.main()
