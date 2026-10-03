#!/usr/bin/env python3
"""PIPELINE graphics sets (DEFAULT, or a file saved by the Graphics Designer).

    graphics.py png FILE OUT.png [--sheet]   draw the set: every sprite by slot,
                                             or (--sheet) laid out as the designer shows it
    graphics.py asm FILE SECTION             baron source for the set, pictures as text,
                                             SECTION being the SECTION line to use

A graphics set is &F34 bytes, loaded at &4000:

    &000  16 large sprites, slots &00-&0F, &80 bytes each
    &800  16 small sprites, slots &10-&1F, &20 bytes each
    &A00   9 large sprites, slots &20-&28, &80 bytes each
    &E80  15 object names, 12 characters each, for small sprites &10-&1E

A large sprite is 16x32 MODE 5 pixels, a small one 8x16. Both are stored a
column of bytes at a time, the way MODE 5 screen memory runs down a character
cell: the first byte is the top four pixels of the leftmost column, the next
byte the four pixels below it, and so on to the bottom before the next column
starts. Each byte holds four pixels: pixel n (n=0 leftmost) is bits 7-n (the
high bit of its colour) and 3-n (the low bit). Colours are logical, 0-3; the
designer shows them as black, blue, yellow and red.
"""

import struct
import sys
import zlib
from pathlib import Path

LARGE = (16, 32)
SMALL = (8, 16)
# (first slot, count, offset in the file, size)
BLOCKS = [(0x00, 16, 0x000, LARGE), (0x10, 16, 0x800, SMALL), (0x20, 9, 0xA00, LARGE)]
NAMES_OFFSET = 0xE80
NAME_LENGTH = 12
NAME_COUNT = 15
FILE_LENGTH = 0xF34
PIXELS = ".123"
# The designer's palette (its Def. Colour can change it): black, blue, yellow, red.
PALETTE = [(0, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 0)]

# The designer's sprite sheet: a 5x5 grid of large sprites, each position
# showing the slot listed here, and below it a 4x4 grid of the small ones in
# slot order (copied from the table at slot_of_position in H.GRAPH).
SHEET_SLOTS = [0x00, 0x01, 0x02, 0x03, 0x04,
               0x05, 0x08, 0x07, 0x0A, 0x0E,
               0x24, 0x26, 0x25, 0x27, 0x0F,
               0x06, 0x28, 0x0C, 0x0D, 0x0B,
               0x09, 0x20, 0x21, 0x22, 0x23]


def sprites(data):
    """slot -> (width, height, rows of pixel values)"""
    out = {}
    for first, count, offset, (w, h) in BLOCKS:
        size = w * h // 4
        for i in range(count):
            raw = data[offset + i * size: offset + (i + 1) * size]
            rows = [[0] * w for _ in range(h)]
            for col in range(w // 4):
                for y in range(h):
                    b = raw[col * h + y]
                    for n in range(4):
                        rows[y][col * 4 + n] = (b >> (7 - n) & 1) << 1 | (b >> (3 - n) & 1)
            out[first + i] = (w, h, rows)
    return out


def names(data):
    return [data[NAMES_OFFSET + i * NAME_LENGTH: NAMES_OFFSET + (i + 1) * NAME_LENGTH].decode("latin1")
            for i in range(NAME_COUNT)]


def write_png(path, pixels):
    """pixels: rows of (r, g, b)"""
    h, w = len(pixels), len(pixels[0])
    raw = b"".join(b"\0" + bytes(c for px in row for c in px) for row in pixels)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render(data, sheet):
    """MODE 5 pixels are twice as wide as tall: draw each 2x1, then scale up."""
    spr = sprites(data)
    gap = 2
    if sheet:
        places = [(slot, (i % 5) * 16, (i // 5) * 32) for i, slot in enumerate(SHEET_SLOTS)]
        places += [(0x10 + i, (i % 4) * 16 + 4, 160 + (i // 4) * 16) for i in range(16)]
        width, height = 80, 224
    else:
        places = [(slot, (i % 8) * (16 + gap), (i // 8) * (32 + gap)) for i, slot in enumerate(
            [s for s in sorted(spr) if spr[s][0] == 16])]
        top = 4 * (32 + gap) + gap
        places += [(0x10 + i, (i % 8) * (16 + gap), top + (i // 8) * (16 + gap)) for i in range(16)]
        width, height = 8 * (16 + gap), top + 2 * (16 + gap)
    canvas = [[(48, 48, 48)] * width for _ in range(height)]
    for slot, x0, y0 in places:
        w, h, rows = spr[slot]
        for y in range(h):
            for x in range(w):
                canvas[y0 + y][x0 + x] = PALETTE[rows[y][x]]
    scale = 3
    return [[px for px in row for _ in range(2 * scale)] for row in canvas for _ in range(scale)]


# What each large sprite in DEFAULT shows, for the comments in its source.
DESCRIPTIONS = {
    0x00: "the background tile, also repeated behind everything",
    0x01: "left half of a chequered peak",
    0x02: "right half of the peak",
    0x03: "left half of a chequered funnel",
    0x04: "right half of the funnel",
    0x05: "chequered wall",
    0x06: "red crate",
    0x07: "blue drum",
    0x08: "chequered frame round a dark red panel",
    0x09: "yellow disc",
    0x0A: "red and blue wreckage",
    0x0B: "yellow pipe with a red valve",
    0x0C: "yellow pipe, across",
    0x0D: "yellow pipe, down",
    0x0E: "flames, first frame (animates with &0F)",
    0x0F: "flames, second frame",
    0x20: "yellow and red machine, first frame (animates with &21)",
    0x21: "the machine, second frame",
    0x22: "the machine, third frame (animates with &23)",
    0x23: "the machine, fourth frame",
    0x24: "chequered block with a black star",
    0x25: "yellow drum",
    0x26: "red and yellow rubble",
    0x27: "red and yellow strata",
    0x28: "red drum in a yellow pool",
    0x1F: "the man (the only small sprite without a name)",
}


def source(data, path, section):
    spr = sprites(data)
    nm = names(data)
    name = Path(path).stem.upper()
    out = [f"; {name}: a PIPELINE graphics set, written out by tools/graphics.py. The",
           "; Graphics Designer loads it at &4000 and saves &4000-&4F33 back; MISSION",
           "; packs the sprites and names into the game's IO file.",
           ";",
           ";   &000  large sprites, slots &00-&0F (16x32 pixels, &80 bytes each)",
           ";   &800  small sprites, slots &10-&1F (8x16, &20 bytes each)",
           ";   &A00  large sprites, slots &20-&28",
           ";   &E80  the names of small sprites &10-&1E, 12 characters each",
           ";",
           "; Each picture is rows of logical colours . 1 2 3 (the designer shows",
           "; black, blue, yellow, red); sprites.6502inc stores them a column at a",
           "; time, as the designer and the game expect. The designer's sheet shows",
           "; the large slots in its own order (slot_of_position in H.GRAPH).",
           'INCLUDE "sprites.6502inc"', "", section]
    for first, count, offset, (w, h) in BLOCKS:
        kind = "large" if w == 16 else "small"
        out.append("")
        out.append(f"; Slots &{first:02X}-&{first + count - 1:02X}: {kind} sprites, {w}x{h} pixels.")
        for slot in range(first, first + count):
            w, h, rows = spr[slot]
            note = DESCRIPTIONS.get(slot)
            if 0x10 <= slot < 0x10 + NAME_COUNT:
                note = f'object {slot - 0x0F}, "{nm[slot - 0x10].strip()}"'
            out.append("")
            out.append(f".slot_{slot:02X}" + (f"                      ; {note}" if note else ""))
            out.append(f"    {kind.upper()}_SPRITE {{")
            out += [f'        "{"".join(PIXELS[p] for p in row)}",' for row in rows]
            out.append("    }")
    out.append("")
    out.append("; The small sprites' names, 12 characters each, for slots &10-&1E.")
    out.append(".object_names")
    out += [f'    OBJECT_NAME "{n}"' for n in nm]
    out.append("ENDSECTION")
    return "\n".join(out) + "\n"


def main():
    args = sys.argv[1:]
    if len(args) >= 3 and args[0] == "png":
        data = Path(args[1]).read_bytes()
        write_png(args[2], render(data, "--sheet" in args))
    elif len(args) == 3 and args[0] == "asm":
        sys.stdout.write(source(Path(args[1]).read_bytes(), args[1], args[2]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
