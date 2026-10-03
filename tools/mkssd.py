#!/usr/bin/env python3
"""Build a DFS disc image from baron's raw outputs and a layout manifest.

Baron's own .ssd writer chooses where files go and can't express what a
commercial disc needs to be reproduced exactly: locked files, a catalogue
whose order and sector positions are fixed, the junk left past the end of
each file in its last sector, and data hidden in sectors no catalogue entry
mentions. So baron saves each piece as a raw binary with a .inf sidecar
(`-p DIR --inf`) and the layout (src/disc.toml) says where each one goes.

usage: mkssd.py LAYOUT.toml BUILD_DIR OUT.ssd
"""

import sys
import tomllib
from pathlib import Path

from dfs import SECTOR, Catalogue, Entry, dfs_address, parse_inf, write_catalogue


def parse_bytes(spec: str) -> bytes:
    """Hex bytes, whitespace-separated, where `XX*N` repeats XX N times."""
    out = bytearray()
    for token in spec.split():
        if "*" in token:
            byte, count = token.split("*")
            out += bytes([int(byte, 16)]) * int(count)
        else:
            out += bytes.fromhex(token)
    return bytes(out)


class Image:
    def __init__(self, sectors: int, fill: int):
        self.data = bytearray([fill]) * (sectors * SECTOR)
        self.owner = {}

    def place(self, name: str, start: int, data: bytes):
        sectors = (len(data) + SECTOR - 1) // SECTOR
        for s in range(start, start + sectors):
            if s in self.owner:
                raise SystemExit(f"{name} overlaps {self.owner[s]} at sector &{s:03X}")
            self.owner[s] = name
        end = start * SECTOR + len(data)
        if end > len(self.data):
            raise SystemExit(f"{name} runs off the end of the image at &{end:X}")
        self.data[start * SECTOR : end] = data


def load_piece(build_dir: Path, spec: dict):
    name = spec["name"]
    path = build_dir / name
    if not path.exists():
        raise SystemExit(f"{path}: not built (is there a baron SECTION saving {name!r}?)")
    data = path.read_bytes()
    directory, bare, load, exec_, length = parse_inf((build_dir / f"{name}.inf").read_text())
    if length != len(data):
        raise SystemExit(f"{name}: .inf says {length} bytes, file has {len(data)}")
    slack = parse_bytes(spec.get("slack", ""))
    if (len(data) + len(slack)) % SECTOR and slack:
        raise SystemExit(
            f"{name}: {len(data)} bytes + {len(slack)} slack doesn't end on a sector boundary"
        )
    return directory, bare, load, exec_, data, slack


def build(layout: dict, build_dir: Path) -> bytes:
    image = Image(layout["image_sectors"], layout.get("fill", 0xE5))
    image.place("catalogue", 0, bytes(2 * SECTOR))
    entries = []
    for spec in layout.get("file", []):
        directory, bare, load, exec_, data, slack = load_piece(build_dir, spec)
        entries.append(
            Entry(
                name=bare,
                directory=directory,
                locked=spec.get("locked", False),
                load=dfs_address(load),
                exec=dfs_address(exec_),
                length=len(data),
                start=spec["start"],
            )
        )
        image.place(spec["name"], spec["start"], data + slack)
    for spec in layout.get("raw", []):
        _, _, _, _, data, slack = load_piece(build_dir, spec)
        image.place(spec["name"], spec["start"], data + slack)
    image.data[0 : 2 * SECTOR] = write_catalogue(
        Catalogue(
            title=layout["title"],
            cycle=layout["cycle"],
            opt=layout["opt"],
            disc_sectors=layout["disc_sectors"],
            entries=entries,
        )
    )
    return bytes(image.data)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    layout_path, build_dir, out = sys.argv[1:]
    with open(layout_path, "rb") as f:
        layout = tomllib.load(f)
    Path(out).write_bytes(build(layout, Path(build_dir)))


if __name__ == "__main__":
    main()
