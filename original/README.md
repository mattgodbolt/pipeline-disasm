# The original disc

`pipeline.ssd` is the original 1988 Superior Software release of PIPELINE
(`*| PIPELINE/B 1.01`, "William Reeve & Ian Holmes"), side 1, 40 tracks.

It was decoded from a flux capture in the bbcdiscs archive that jsbeeb uses:

| | |
|---|---|
| Capture | `E447ED5E.hfe`, submitted by scarybeasts, <https://bbc.xania.org/archive/bbcdiscs/hfe/E447ED5E.hfe> |
| Decoded with | `node tools/hfe2ssd.mjs E447ED5E.hfe pipeline.ssd` (jsbeeb's own HFE and SSD code) |
| Size | 102400 bytes (40 tracks x 10 sectors) |
| CRC32 | `8C94E3FE` |
| SHA-256 | `e77711f674083c873b96543a7af8e28968261e8a90f00ff1340fa9508535825c` |

The capture decodes cleanly: no CRC errors and no odd sectors. But one thing
on it can't be held by a sector image: every sector of the three hidden runs
(&122-&142, &145-&165, &16D-&18B), and only those, was written with a
*deleted* data address mark. It's the same on every capture in the archive.
That's half the copy protection: the 8271 reports result &20 for a deleted
sector, which DFS treats as a disc fault, so `*BACKUP` stops at track 29. The
stub loaders read with "read data and deleted data" through OSWORD &7F and
ignore the result, so the game runs from this .ssd regardless; the marks
themselves are lost from it. See `src/hidden_loader.6502inc`.

So the capture itself is here too, as `E447ED5E.hfe`. The build makes
`build/pipeline.hfe` with the marks put back (`src/disc.toml` says which
sectors), and `tools/disccmp.mjs` checks that it reads the same as this
capture, sector by sector: IDs, data, and data marks.

## Other copies considered

- The FSD-reconstructed image in the same archive (`8b8a721db2359be9.hfe`,
  FSD0381) decodes to the same bytes, which is good evidence this is what the
  disc held.
- sbadger's capture `D3CF930B.hfe` (dated 88/09/13) has identical files; only
  the catalogue cycle number differs (&22 rather than &20), and it has an
  extra unreadable sector on track 40.
- The *Play It Again Sam 11* compilation (`45D0B1C4.hfe`, `E5FFF173.hfe`) has a
  different MENU and different stub loaders.
- The Stairway to Hell image (`sth:Superior/Pipeline.zip`) is a cracked copy:
  GAME, GRAPHIC and LEVDES are ordinary files there rather than stub loaders
  for hidden sectors, LEVDES has three bytes patched, and `!BOOT` runs an STH
  banner (`LOAD`).
