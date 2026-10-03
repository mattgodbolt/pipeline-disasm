#!/usr/bin/env python3
"""Summarise a jsbeeb execution trace (tools/beeb.mjs `trace`) as address runs.

Prints each contiguous-ish run of executed PCs (gaps under GAP bytes merged)
with its instruction count and total executions, so it's quick to see which
parts of memory ran: the OS, relocated code, code inside a data file...

usage: traceranges.py TRACE.json [TRACE.json...] [--gap N] [--below ADDR]
"""

import argparse
import json


def load(paths):
    pcs = {}
    for path in paths:
        with open(path) as f:
            for name, (opcode, count) in json.load(f)["executed"].items():
                pc = int(name[1:].split("/")[0], 16)
                pcs[pc] = pcs.get(pc, 0) + count
    return pcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--gap", type=lambda s: int(s, 0), default=16)
    ap.add_argument("--below", type=lambda s: int(s, 0), default=0x8000,
                    help="ignore PCs at or above this (default &8000: skip ROMs)")
    args = ap.parse_args()
    pcs = load(args.traces)
    run = None
    for pc in sorted(p for p in pcs if p < args.below):
        if run and pc - run[1] <= args.gap:
            run[1] = pc
            run[2] += 1
            run[3] += pcs[pc]
        else:
            if run:
                print(f"&{run[0]:04X}-&{run[1]:04X}  {run[2]:5d} insns  {run[3]:10d} runs")
            run = [pc, pc, 1, pcs[pc]]
    if run:
        print(f"&{run[0]:04X}-&{run[1]:04X}  {run[2]:5d} insns  {run[3]:10d} runs")


if __name__ == "__main__":
    main()
