#!/usr/bin/env python3
"""PL's self-decryption, run offline: to read PL, and to rebuild it from source.

PL (&0400) decrypts itself in place before running. Each page from the start
of the encrypted part is XORed with a key byte taken from PL's own code, and
each byte with the plain byte before it:

    plain[a] = key(page) ^ plain[a-1] ^ stored[a]

starting at &043C on page 4 and at offset 1 on pages 5 and 6 (so &0500 and
&0600 are stored as they are). The keys are the bytes at &0404, &0403 and
&0402 for pages 4, 5 and 6: the operands and opcode of the decryptor's first
instructions, so patching those breaks the decryption.

src/pl.6502 holds the decryptor as code, the stored (encrypted) bytes as
data/pl_encrypted.bin, and the decrypted program as source in a section of
its own, saved as build/files/PLDEC but not put on the disc.

usage:
  plcrypt.py decrypt PL OUT          decrypt a whole PL file (as on the disc)
  plcrypt.py encrypt PL PLDEC OUT    encrypt PLDEC with PL's keys: OUT is the
                                     stored bytes from &043C on
  plcrypt.py check BUILD_DIR         PL's stored bytes are PLDEC encrypted
"""

import sys
from pathlib import Path

ORG = 0x0400
START = 0x043C  # first byte decrypted: the offset of the branch into the plain code
END_PAGE = 0x07


def keys(pl: bytes) -> dict:
    """Page -> key byte, read from the decryptor (LDA key_bytes,X with X = 2, 1, 0)."""
    return {4: pl[0x0404 - ORG], 5: pl[0x0403 - ORG], 6: pl[0x0402 - ORG]}


def crypted_addresses(end: int):
    """The addresses the decryptor rewrites, in the order it does them."""
    for page in range(4, END_PAGE):
        first = START if page == 4 else page << 8 | 1
        for a in range(first, min(page + 1 << 8, end)):
            yield a


def decrypt(pl: bytes) -> bytes:
    out = bytearray(pl)
    k = keys(pl)
    for a in crypted_addresses(ORG + len(pl)):
        out[a - ORG] = k[a >> 8] ^ out[a - 1 - ORG] ^ out[a - ORG]
    return bytes(out)


def encrypt(plain: bytes, k: dict) -> bytes:
    """`plain` is the whole image from ORG, decrypted; returns it as stored."""
    out = bytearray(plain)
    for a in crypted_addresses(ORG + len(plain)):
        out[a - ORG] = k[a >> 8] ^ plain[a - 1 - ORG] ^ plain[a - ORG]
    return bytes(out)


def stored_from_source(pl: bytes, pldec: bytes) -> bytes:
    """The stored bytes from START on, given PL as built and PLDEC (plain from START-1)."""
    plain = pl[: START - 1 - ORG] + pldec
    return encrypt(plain, keys(pl))[START - ORG :]


def main():
    args = sys.argv[1:]
    if args[:1] == ["decrypt"] and len(args) == 3:
        Path(args[2]).write_bytes(decrypt(Path(args[1]).read_bytes()))
    elif args[:1] == ["encrypt"] and len(args) == 4:
        pl, pldec = (Path(p).read_bytes() for p in args[1:3])
        Path(args[3]).write_bytes(stored_from_source(pl, pldec))
    elif args[:1] == ["check"] and len(args) == 2:
        build = Path(args[1])
        pl, pldec = (build / "PL").read_bytes(), (build / "PLDEC").read_bytes()
        if pl[START - ORG :] != stored_from_source(pl, pldec):
            raise SystemExit("PL's encrypted bytes don't match its decrypted source (PLDEC)")
        print("PL decrypts to PLDEC")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
