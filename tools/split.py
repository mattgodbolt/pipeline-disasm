#!/usr/bin/env python3
"""One-off: split the original disc into the INCBIN baseline.

Writes every catalogued file and every hidden run of sectors to data/, a baron
source per piece that does nothing but INCBIN it, and the layout manifest that
puts them back. It's the starting point the disassembly then replaces piece by
piece; it's kept to show where the baseline came from, not to be run again
(it would overwrite the sources).

usage: split.py ORIGINAL.ssd REPO_ROOT
"""

import sys
from pathlib import Path

from dfs import SECTOR, read_catalogue, file_data

# Uncatalogued runs of sectors that the stub loaders read directly. Found by
# looking for non-&E5 sectors past the last catalogued file; the names come
# from matching their contents against the cracked Stairway to Hell copy.
HIDDEN = [
    ("H.GAME", 0x122, 0x143, "game", "the game proper"),
    ("H.GRAPH", 0x145, 0x166, "graphic", "the graphics"),
    ("H.LEVDES", 0x16D, 0x18C, "levdes", "the level designer"),
]


def host_address(dfs: int) -> int:
    """Undo DFS's 18-bit truncation: the top pair set means the I/O processor."""
    return dfs | 0xFFFF0000 if dfs >> 16 == 3 else dfs


def slack_spec(slack: bytes) -> str:
    if not slack:
        return ""
    if len(set(slack)) == 1:
        return f"{slack[0]:02X}*{len(slack)}"
    return " ".join(slack[i : i + 32].hex().upper() for i in range(0, len(slack), 32))


def source_name(name: str) -> str:
    return name.lstrip("!").lower()


def main():
    image = open(sys.argv[1], "rb").read()
    root = Path(sys.argv[2])
    (root / "data").mkdir(exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    cat = read_catalogue(image)

    layout = [
        "# Where everything goes on the disc. tools/mkssd.py reads this together with",
        "# baron's raw outputs (build/files/NAME + NAME.inf) to make the image.",
        "",
        f'title = "{cat.title}"',
        f"cycle = 0x{cat.cycle:02X}",
        f"opt = {cat.opt}",
        "# The catalogue claims an 80 track disc although only 40 tracks were",
        "# formatted; it's reproduced as found.",
        f"disc_sectors = {cat.disc_sectors}",
        f"image_sectors = {len(image) // SECTOR}",
        "fill = 0xE5",
        "",
        "# Catalogue order, which is descending start sector as DFS keeps it.",
        "# `slack` is what's left in each file's last sector past its end.",
    ]
    for e in cat.entries:
        src = source_name(e.name)
        data = file_data(image, e)
        (root / "data" / f"{src}.bin").write_bytes(data)
        end = e.start * SECTOR + e.length
        slack = image[end : (e.start + e.sectors) * SECTOR]
        layout += [
            "",
            "[[file]]",
            f'name = "{e.name}"',
            f"start = 0x{e.start:03X}",
            f"locked = {'true' if e.locked else 'false'}",
        ]
        if slack:
            layout.append(f'slack = "{slack_spec(slack)}"')
        load, exec_ = host_address(e.load), host_address(e.exec)
        (root / "src" / f"{src}.6502").write_text(
            f"; {e.full_name}: &{e.length:X} bytes at sector &{e.start:03X}.\n"
            f'SECTION {src}, filename="{e.name}", org=&{load & 0xFFFF:04X}, '
            f"load=&{load:X}, exec=&{exec_:X}\n"
            f'    INCBIN "../data/{src}.bin"\n'
            "ENDSECTION\n"
        )

    layout += [
        "",
        "# Runs of sectors no catalogue entry mentions, read directly by the stub",
        "# loaders catalogued as GAME, GRAPHIC and LEVDES.",
    ]
    for name, start, end, src, what in HIDDEN:
        data = image[start * SECTOR : end * SECTOR]
        (root / "data" / f"hidden_{src}.bin").write_bytes(data)
        layout += ["", "[[raw]]", f'name = "{name}"', f"start = 0x{start:03X}", f"length = 0x{len(data):X}"]
        (root / "src" / f"hidden_{src}.6502").write_text(
            f"; {what.capitalize()}, hidden in sectors &{start:03X}-&{end - 1:03X}.\n"
            f'SECTION hidden_{src}, filename="{name}"\n'
            f'    INCBIN "../data/hidden_{src}.bin"\n'
            "ENDSECTION\n"
        )
    (root / "src" / "disc.toml").write_text("\n".join(layout) + "\n")


if __name__ == "__main__":
    main()
