#!/usr/bin/env python3
"""The corpus check for the symbol sets: every title on the Stairway To Hell
discs whose files hold all of a region's anchors at the same addresses, with
how much of the region that title's files hold and how much of it is
identical. A region that's all or nearly all identical there is the same
code (a crack, a compilation); anchors that agree over a region whose other
bytes differ are a collision, and the region needs another anchor.

    symbols_corpus.py CORPUS [--config src/symbols.toml] [--build build]

CORPUS is the directory of Stairway To Hell disc zips (jsbeeb's
.registry-corpus/sth-disc), each zip one title. Every complete DFS file is
placed at its load address, as jsbeeb's tools/registry/anchor-collisions.js
does, but BASIC programs stay in: a BASIC program's lines can collide too.
Files of one repeated byte, and files catalogued to load in page zero (a
placeholder, usually, for data a program puts elsewhere), are left out.
Prints the report as Markdown.
"""

import argparse
import sys
import tomllib
import zipfile
from pathlib import Path

from jsbeeb_symbols import Builder

SECTOR = 256
TRACK = 10 * SECTOR
PAGE = 0x100
MAX_ENTRIES = 31
SAME_CODE = 0.9     # the share identical above which the report calls it the same code


def sides(name, data):
    """A sector image's sides: an .ssd is one, a .dsd two, track by track."""
    if name.lower().endswith(".ssd"):
        return [data]
    if name.lower().endswith(".dsd"):
        tracks = [data[i:i + TRACK] for i in range(0, len(data), TRACK)]
        return [b"".join(tracks[0::2]), b"".join(tracks[1::2])]
    return []


def catalogue(side):
    """(name, load, data) for each complete file in a DFS catalogue, or
    nothing if the side doesn't hold one."""
    if len(side) < 2 * SECTOR:
        return []
    s0, s1 = side[:SECTOR], side[SECTOR:2 * SECTOR]
    entries, total = s1[5], (s1[6] & 3) << 8 | s1[7]
    if entries % 8 or entries > MAX_ENTRIES * 8 or not 2 <= total <= 800:
        return []
    out = []
    for offset in range(8, entries + 1, 8):
        name = s0[offset:offset + 7]
        if any((b & 0x7F) < 0x20 for b in name):
            return []
        mixed = s1[offset + 6]
        load = s1[offset] | s1[offset + 1] << 8
        length = s1[offset + 4] | s1[offset + 5] << 8 | (mixed >> 4 & 3) << 16
        start = s1[offset + 7] | (mixed & 3) << 8
        if not 2 <= start <= total:
            return []
        data = side[start * SECTOR:start * SECTOR + length]
        if len(data) == length:
            directory = chr(s0[offset + 7] & 0x7F)
            out.append((f"{directory}.{bytes(b & 0x7F for b in name).decode('latin-1').rstrip()}", load, data))
    return out


def titles(corpus):
    """{title: [(file, load, data)]}, each file placed once per content and address."""
    out = {}
    for path in sorted(Path(corpus).rglob("*.zip")):
        title = str(path.relative_to(corpus))
        files, seen = [], set()
        with zipfile.ZipFile(path) as z:
            for member in sorted(z.namelist()):
                for side in sides(member, z.read(member)):
                    for name, load, data in catalogue(side):
                        if not data or load < PAGE or load + len(data) > 0x10000 or len(set(data)) == 1:
                            continue
                        if (load, data) in seen:
                            continue
                        seen.add((load, data))
                        files.append((f"{Path(member).name}:{name}", load, data))
        if files:
            out[title] = files
    return out


def holds(load, data, at, expected):
    offset = at - load
    return 0 <= offset and data[offset:offset + len(expected)] == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("corpus")
    parser.add_argument("--config", default="src/symbols.toml")
    parser.add_argument("--build", default="build")
    args = parser.parse_args()
    with open(args.config, "rb") as f:
        config = tomllib.load(f)
    build = Path(args.build)
    builder = Builder(config, build / "listings", build / "symbols.json", build / "files", "corpus")

    corpus = titles(args.corpus)
    by_page = {}
    for title, files in corpus.items():
        for file in files:
            _, load, data = file
            for page in range(load >> 8, (load + len(data) - 1 >> 8) + 1):
                by_page.setdefault(page, []).append((title, file))
    print(f"{len(corpus)} titles, {sum(len(f) for f in corpus.values())} distinct files placed at their "
          f"load addresses. \"Holding one\" counts the titles holding any of a region's anchors; \"Held\" is "
          f"how many of the region's bytes that title's files hold, and \"Identical\" how many of those "
          f"are the same.\n")

    collisions = 0
    for spec in config["set"]:
        _, regions, _ = builder.build(spec)
        print(f"## {spec['id']}\n")
        print("| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |")
        print("|---|---|---|---|---|---|---|")
        for region in regions:
            anchors = [(c.at, c.data) for c in region.anchors]
            # Titles whose files, together, hold every anchor.
            holders = {}
            for at, expected in anchors:
                for title, file in by_page.get(at >> 8, []):
                    if holds(file[1], file[2], at, expected):
                        holders.setdefault(title, {}).setdefault(at, []).append(file)
            matches = [t for t, found in holders.items() if len(found) == len(anchors)]
            where = f"{region.name} &{region.start:04X}-&{region.end - 1:04X} | {len(anchors)} | {len(holders)}"
            if not matches:
                print(f"| {where} | none | | | |")
                continue
            for title in sorted(matches):
                files = {f[0]: f for found in holders[title].values() for f in found}
                held = same = 0
                for address, byte in region.memory.items():
                    here = [data[address - load] for _, load, data in files.values()
                            if 0 <= address - load < len(data)]
                    held += bool(here)
                    same += byte in here
                share = same / held if held else 0
                verdict = "" if share >= SAME_CODE else " (collision)"
                collisions += share < SAME_CODE
                print(f"| {where} | {title} | {', '.join(sorted(files))} | "
                      f"{held} of {len(region.memory)} | {same} ({100 * share:.1f}%){verdict} |")
        print()
    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
