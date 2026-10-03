#!/usr/bin/env python3
"""Draw a piece of MODE 1 screen memory as a PNG, to see what a binary shows.

usage: screen2png.py FILE LOAD OUT.png [--columns 64] [--palette 0,4,3,1]

FILE is loaded at LOAD (hex) in a screen starting at &3000 with COLUMNS
character columns of 8 bytes (64 for the Level Designer, which narrows the
screen; 80 for a standard MODE 1) and 32 rows. PALETTE gives the physical
colour (0-7) of logical colours 0-3; the default is the designer's title
palette. Needs Pillow.
"""

import argparse

from PIL import Image

PHYSICAL = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 0),
            (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
SCREEN = 0x3000
ROWS = 32


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file")
    parser.add_argument("load", type=lambda s: int(s.lstrip("&$"), 16))
    parser.add_argument("out")
    parser.add_argument("--columns", type=int, default=64)
    parser.add_argument("--palette", default="0,4,3,1")
    parser.add_argument("--scale", type=int, default=3)
    args = parser.parse_args()

    palette = [PHYSICAL[int(c)] for c in args.palette.split(",")]
    data = open(args.file, "rb").read()
    row_bytes = args.columns * 8
    img = Image.new("RGB", (args.columns * 4, ROWS * 8))
    for offset, byte in enumerate(data):
        row, rest = divmod(args.load - SCREEN + offset, row_bytes)
        column, line = divmod(rest, 8)
        if not 0 <= row < ROWS:
            continue
        for pixel in range(4):
            colour = (byte >> (7 - pixel) & 1) * 2 + (byte >> (3 - pixel) & 1)
            img.putpixel((column * 4 + pixel, row * 8 + line), palette[colour])
    # MODE 1's 320x256 fills a 4:3 screen, so its pixels are near enough square.
    img = img.resize((img.width * args.scale, img.height * args.scale), Image.NEAREST)
    img.save(args.out)


if __name__ == "__main__":
    main()
