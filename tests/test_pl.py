"""PL is stored encrypted; its readable source is a separate, unsaved section.

The disc gets the encrypted bytes from data/pl_encrypted.bin, so nothing in
the build itself stops that file and the decrypted source drifting apart.
This does: encrypting the assembled PLDEC must give the stored bytes.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ROOT / "build" / "files"


@unittest.skipUnless((FILES / "PLDEC").exists(), "needs `make` run first")
class PlTest(unittest.TestCase):
    def test_source_encrypts_to_stored_bytes(self):
        subprocess.run([sys.executable, str(ROOT / "tools" / "plcrypt.py"), "check", str(FILES)], check=True)


if __name__ == "__main__":
    unittest.main()
