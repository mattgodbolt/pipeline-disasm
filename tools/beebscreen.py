#!/usr/bin/env python3
"""Render BBC Micro screen memory (MODE 1 or MODE 5) to a PNG, for docs/img.

    beebscreen.py MODE IN.bin OUT.png [--palette 0,1,4,7] [--title]

IN.bin is screen memory from its start (&3000 for MODE 1, &5800 for MODE 5),
as *SAVEd or as a loading picture is stored. --title unpacks it as TITLE
does (see src/title.6502) first: a nonzero byte stands for itself, a zero is
followed by a count of zeros (0 meaning 256), and the screen's last 2K is
cleared afterwards. --palette
gives the physical colour (0-7) for each logical colour, as VDU 19 would;
the default is the mode's own.

The picture is scaled to 640x512 so pixels have the shape they have on a
television.
"""

import argparse
import struct
import zlib
from pathlib import Path

# Physical colours 0-7: black, red, green, yellow, blue, magenta, cyan, white.
RGB = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 0),
       (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]

# mode -> (bytes per character row of 8 lines, screen size, default palette)
MODES = {
    1: (640, 0x5000, [0, 1, 3, 7]),
    5: (320, 0x2800, [0, 1, 3, 7]),
}


def unpack_zero_runs(packed: bytes, size: int) -> bytes:
    out = bytearray()
    i = 0
    while i < len(packed) and len(out) < size:
        if packed[i]:
            out.append(packed[i])
            i += 1
        else:
            if i + 1 >= len(packed):
                break
            out += bytes(packed[i + 1] or 256)
            i += 2
    return bytes(out[:size])


def unpack_title(packed: bytes) -> bytes:
    """TITLE's picture as it leaves MODE 1 screen memory: unpacked from &3000,
    then &7800-&7FFF cleared, which hides the stream's overrun."""
    screen = bytearray(unpack_zero_runs(packed, 0x5000))
    screen[0x4800:] = bytes(0x800)
    return bytes(screen)


def pixels(mode: int, screen: bytes):
    """Rows of logical colours. Both modes have 4 colours: pixel p of a byte
    takes bit 7-p as its high bit and bit 3-p as its low."""
    row_bytes, size, _ = MODES[mode]
    screen = screen.ljust(size, b"\0")
    width = row_bytes // 8 * 4
    rows = []
    for y in range(256):
        base = (y // 8) * row_bytes + (y % 8)
        row = []
        for col in range(row_bytes // 8):
            b = screen[base + col * 8]
            for p in range(4):
                row.append((b >> (7 - p) & 1) << 1 | (b >> (3 - p) & 1))
        assert len(row) == width
        rows.append(row)
    return rows


def write_png(path: Path, rgb_rows):
    height, width = len(rgb_rows), len(rgb_rows[0])
    raw = b"".join(b"\0" + bytes(c for px in row for c in px) for row in rgb_rows)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", type=int, choices=sorted(MODES))
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--palette", help="physical colours for logical 0-3, e.g. 0,1,4,7")
    ap.add_argument("--title", action="store_true", help="unpack IN.bin as TITLE does first")
    args = ap.parse_args()

    _, size, palette = MODES[args.mode]
    if args.palette:
        palette = [int(c) for c in args.palette.split(",")]
    data = args.input.read_bytes()
    if args.title:
        data = unpack_title(data)
    xscale = 640 // (MODES[args.mode][0] // 8 * 4)
    out = []
    for row in pixels(args.mode, data):
        line = [RGB[palette[c]] for c in row for _ in range(xscale)]
        out += [line, line]
    write_png(args.output, out)


if __name__ == "__main__":
    main()
