# PIPELINE disassembly

[![CI](https://github.com/mattgodbolt/pipeline-disasm/actions/workflows/ci.yml/badge.svg)](https://github.com/mattgodbolt/pipeline-disasm/actions/workflows/ci.yml)

A rebuild-from-source of **PIPELINE** for the BBC Micro, by William Reeve and
Ian Holmes, published by Superior Software in 1988. The sources assemble with
[baron](https://github.com/waitingforvsync/baron) into a disc image that is
byte-for-byte identical to the original release, hidden sectors and all.

It starts as every file included as an opaque binary, and becomes a commented
disassembly one piece at a time; at every step `make verify` must still
produce the original disc exactly.

## Building

```
make verify
```

needs baron (looked for at `../baron/build/src/baron`, else on the `PATH`;
override with `BARON=...`), Python 3.11 or later, and node with `npm ci` run
once (for jsbeeb's disc code). It writes `build/pipeline.ssd` and compares
it with `original/pipeline.ssd`, and `build/pipeline.hfe`, a flux image with
the original's deleted data marks on its hidden sectors, which it compares
with the original flux capture. Baron's
symbol dump lands in `build/symbols.json`, and a listing in
`build/listing.txt`.

## Layout

```
original/      the original disc, and where it came from
src/*.6502     baron source, one file per piece of the disc
src/disc.toml  where each piece goes on the disc
data/          binaries not (yet) turned into source
tools/         disc building, comparison and analysis tools
tests/         tests of the tools
docs/          the journal and notes
```

See [docs/journal.md](docs/journal.md) for how it's going.
