#!/usr/bin/env python3
"""Compare a rebuilt disc image against the original, byte for byte.

Differences are reported against what lives there on the original disc - the
catalogue, a file (with the offset into it and the address it loads to), a
file's slack, or a hidden run named by the layout - so a mismatch points
straight at the source that produced it.

usage: ssdcmp.py ORIGINAL.ssd REBUILT.ssd [LAYOUT.toml]
Exits 0 only when the two are identical.
"""

import sys
import tomllib
from collections import Counter

from dfs import SECTOR, read_catalogue

MAX_RUNS = 20


def regions(image: bytes, layout: dict):
    """(first byte, end byte, name, base address) for everything we can name."""
    out = [(0, 2 * SECTOR, "catalogue", None)]
    for e in read_catalogue(image).entries:
        start = e.start * SECTOR
        out.append((start, start + e.length, e.full_name, e.load & 0xFFFF))
        end_sector = (e.start + e.sectors) * SECTOR
        out.append((start + e.length, end_sector, f"{e.full_name} slack", None))
    for raw in layout.get("raw", []):
        start = raw["start"] * SECTOR
        out.append((start, start + raw.get("length", SECTOR), raw["name"], raw.get("org")))
    return out


def describe(offset: int, named) -> str:
    for start, end, name, base in named:
        if start <= offset < end:
            where = f"{name}+&{offset - start:04X}"
            if base is not None:
                where += f" (&{base + offset - start:04X})"
            return where
    return f"sector &{offset // SECTOR:03X}"


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    original = open(sys.argv[1], "rb").read()
    rebuilt = open(sys.argv[2], "rb").read()
    layout = {}
    if len(sys.argv) == 4:
        with open(sys.argv[3], "rb") as f:
            layout = tomllib.load(f)

    if original == rebuilt:
        print(f"identical: {len(rebuilt)} bytes")
        return
    if len(original) != len(rebuilt):
        print(f"lengths differ: original {len(original)}, rebuilt {len(rebuilt)}")

    named = regions(original, layout)
    diffs = [i for i in range(min(len(original), len(rebuilt))) if original[i] != rebuilt[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    for start, end in runs[:MAX_RUNS]:
        print(
            f"&{start:05X}: {describe(start, named)}: {end - start} byte(s) differ: "
            f"original {original[start:min(end, start + 8)].hex(' ')}"
            f" rebuilt {rebuilt[start:min(end, start + 8)].hex(' ')}"
        )
    if len(runs) > MAX_RUNS:
        print(f"... and {len(runs) - MAX_RUNS} more runs")
    per_region = Counter(describe(i, named).split("+")[0] for i in diffs)
    print(f"{len(diffs)} byte(s) differ:", ", ".join(f"{k} {v}" for k, v in per_region.most_common()))
    sys.exit(1)


if __name__ == "__main__":
    main()
