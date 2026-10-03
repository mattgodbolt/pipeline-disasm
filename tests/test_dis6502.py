"""The disassembler's output must reassemble to the bytes it came from.

Every binary the build produced (build/files) is disassembled as if it were
all code from its load address, which exercises every opcode, operand form and
data fallback the disc has to offer, then reassembled with baron and compared.
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

from dfs import parse_inf  # noqa: E402
from dis6502 import Disassembler  # noqa: E402

FILES = ROOT / "build" / "files"
BARON = os.environ.get("BARON") or shutil.which("baron")


@unittest.skipUnless(FILES.is_dir() and BARON, "needs `make` run first and baron")
class RoundTripTest(unittest.TestCase):
    def test_every_built_binary_round_trips(self):
        binaries = sorted(p for p in FILES.iterdir() if p.suffix != ".inf")
        self.assertTrue(binaries)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copy(ROOT / "src" / "os.6502inc", tmp)
            shutil.copy(ROOT / "src" / "forceabs.6502inc", tmp)
            for path in binaries:
                with self.subTest(binary=path.name):
                    load = parse_inf((FILES / f"{path.name}.inf").read_text())[2] & 0xFFFF
                    # Somewhere the whole binary fits without wrapping.
                    org = load if load + path.stat().st_size <= 0x10000 else 0x1000
                    shutil.copy(path, tmp / "in.bin")
                    hints = {
                        "binary": str(tmp / "in.bin"),
                        "org": org,
                        "section": f'rt, filename="OUT", org=&{org:04X}',
                        "entries": [org],
                    }
                    (tmp / "rt.6502").write_text(Disassembler(hints, Path("/")).run())
                    out = tmp / "out"
                    shutil.rmtree(out, ignore_errors=True)
                    out.mkdir()
                    subprocess.run([BARON, "-p", str(out), str(tmp / "rt.6502")], check=True,
                                   capture_output=True)
                    self.assertEqual((out / "OUT").read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
