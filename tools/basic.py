#!/usr/bin/env python3
"""List a tokenised BBC BASIC program, as text baron's BASIC block can take back.

usage: basic.py [--offsets] [--page ADDR] FILE

Each line prints as `NUMBERtext` (LISTO 0: no padding, the spaces after the
number are the program's own), which is what goes between `BASIC` and
`ENDBASIC`. Keywords are expanded; REM, DATA and `*` commands, and strings,
are copied as stored, since the tokeniser passes them through untouched.
A byte with no plain-text form (a control code, or a top-bit-set byte where
no keyword would be) prints as `{&XX}`, and that line is flagged with `!`
after its number in --offsets mode: baron can't take it as text.

--offsets prefixes each line with its record's address (PAGE + offset; PAGE
defaults to &1900), and the end shows where the program's `0D FF` ends,
which is where anything carried past the program in the file begins.
"""

import argparse
import sys
from pathlib import Path

# BBC BASIC 2 tokens; &CF-&D3 are the statement forms (PTR=, PAGE= ...) of
# the pseudo-variables at &8F-&93, which the tokeniser picks by adding &40.
TOKENS = {
    0x80: "AND", 0x81: "DIV", 0x82: "EOR", 0x83: "MOD", 0x84: "OR", 0x85: "ERROR",
    0x86: "LINE", 0x87: "OFF", 0x88: "STEP", 0x89: "SPC", 0x8A: "TAB(", 0x8B: "ELSE",
    0x8C: "THEN", 0x8E: "OPENIN", 0x8F: "PTR", 0x90: "PAGE", 0x91: "TIME",
    0x92: "LOMEM", 0x93: "HIMEM", 0x94: "ABS", 0x95: "ACS", 0x96: "ADVAL", 0x97: "ASC",
    0x98: "ASN", 0x99: "ATN", 0x9A: "BGET", 0x9B: "COS", 0x9C: "COUNT", 0x9D: "DEG",
    0x9E: "ERL", 0x9F: "ERR", 0xA0: "EVAL", 0xA1: "EXP", 0xA2: "EXT", 0xA3: "FALSE",
    0xA4: "FN", 0xA5: "GET", 0xA6: "INKEY", 0xA7: "INSTR(", 0xA8: "INT", 0xA9: "LEN",
    0xAA: "LN", 0xAB: "LOG", 0xAC: "NOT", 0xAD: "OPENUP", 0xAE: "OPENOUT", 0xAF: "PI",
    0xB0: "POINT(", 0xB1: "POS", 0xB2: "RAD", 0xB3: "RND", 0xB4: "SGN", 0xB5: "SIN",
    0xB6: "SQR", 0xB7: "TAN", 0xB8: "TO", 0xB9: "TRUE", 0xBA: "USR", 0xBB: "VAL",
    0xBC: "VPOS", 0xBD: "CHR$", 0xBE: "GET$", 0xBF: "INKEY$", 0xC0: "LEFT$(",
    0xC1: "MID$(", 0xC2: "RIGHT$(", 0xC3: "STR$", 0xC4: "STRING$(", 0xC5: "EOF",
    0xC6: "AUTO", 0xC7: "DELETE", 0xC8: "LOAD", 0xC9: "LIST", 0xCA: "NEW", 0xCB: "OLD",
    0xCC: "RENUMBER", 0xCD: "SAVE", 0xCF: "PTR", 0xD0: "PAGE", 0xD1: "TIME",
    0xD2: "LOMEM", 0xD3: "HIMEM", 0xD4: "SOUND", 0xD5: "BPUT", 0xD6: "CALL",
    0xD7: "CHAIN", 0xD8: "CLEAR", 0xD9: "CLOSE", 0xDA: "CLG", 0xDB: "CLS", 0xDC: "DATA",
    0xDD: "DEF", 0xDE: "DIM", 0xDF: "DRAW", 0xE0: "END", 0xE1: "ENDPROC",
    0xE2: "ENVELOPE", 0xE3: "FOR", 0xE4: "GOSUB", 0xE5: "GOTO", 0xE6: "GCOL", 0xE7: "IF",
    0xE8: "INPUT", 0xE9: "LET", 0xEA: "LOCAL", 0xEB: "MODE", 0xEC: "MOVE", 0xED: "NEXT",
    0xEE: "ON", 0xEF: "VDU", 0xF0: "PLOT", 0xF1: "PRINT", 0xF2: "PROC", 0xF3: "READ",
    0xF4: "REM", 0xF5: "REPEAT", 0xF6: "REPORT", 0xF7: "RESTORE", 0xF8: "RETURN",
    0xF9: "RUN", 0xFA: "STOP", 0xFB: "COLOUR", 0xFC: "TRACE", 0xFD: "UNTIL",
    0xFE: "WIDTH", 0xFF: "OSCLI",
}
LINE_NUMBER = 0x8D
REST_RAW = {0xF4, 0xDC}  # REM, DATA


def records(data: bytes):
    """Yield (offset, line number, text bytes) up to the 0D FF end marker;
    finally yield (offset just past the marker, None, None)."""
    pos = 0
    while True:
        if data[pos] != 0x0D:
            sys.exit(f"no line record at offset &{pos:X}")
        if data[pos + 1] & 0x80:
            yield pos + 2, None, None
            return
        number = data[pos + 1] << 8 | data[pos + 2]
        length = data[pos + 3]
        yield pos, number, data[pos + 4:pos + length]
        pos += length


def decode_line_number(b1: int, b2: int, b3: int) -> int:
    x = b1 ^ 0x54
    return ((b3 & 0x3F) | (x & 0x0C) << 4) << 8 | (b2 & 0x3F) | (x << 2 & 0xC0)


def plain(c: int) -> str | None:
    return chr(c) if 0x20 <= c < 0x7F else None


def detokenise(text: bytes) -> tuple[str, bool]:
    """The line's text, and whether it is all plain (re-enterable) text."""
    out = []
    clean = True

    def raw(c):
        nonlocal clean
        ch = plain(c)
        if ch is None:
            clean = False
            ch = f"{{&{c:02X}}}"
        out.append(ch)

    i = 0
    quoted = False
    statement_start = True
    while i < len(text):
        c = text[i]
        if quoted:
            raw(c)
            quoted = c != 0x22
            i += 1
            continue
        if c == 0x22:
            out.append('"')
            quoted = True
        elif c == ord("*") and statement_start:
            for c in text[i:]:
                raw(c)
            break
        elif c == LINE_NUMBER and i + 4 <= len(text):
            out.append(str(decode_line_number(*text[i + 1:i + 4])))
            i += 4
            statement_start = False
            continue
        elif c in TOKENS:
            out.append(TOKENS[c])
            if c in REST_RAW:
                for c in text[i + 1:]:
                    raw(c)
                break
        else:
            raw(c)
        if c == ord(":") or c in (0x8B, 0x8C):  # ':', ELSE, THEN
            statement_start = True
        elif c != 0x20:
            statement_start = False
        i += 1
    return "".join(out), clean


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--offsets", action="store_true")
    parser.add_argument("--page", type=lambda s: int(s.replace("&", "0x"), 0), default=0x1900)
    args = parser.parse_args()
    data = args.file.read_bytes()
    for offset, number, text in records(data):
        if number is None:
            if args.offsets:
                print(f"&{args.page + offset:04X} end of program "
                      f"(&{len(data) - offset:X} bytes follow in the file)")
            break
        line, clean = detokenise(text)
        if args.offsets:
            print(f"&{args.page + offset:04X}{' ' if clean else '!'} {number}{line}")
        else:
            print(f"{number}{line}")


if __name__ == "__main__":
    main()
