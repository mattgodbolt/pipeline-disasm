# Journal

Discoveries and decisions, as they happen. Append-only: later entries correct
earlier ones rather than rewriting them. Times are US Central.

## 2026-10-03 17:20 — Finding the disc

- jsbeeb can reach two archives: Stairway to Hell (`sth:Superior/Pipeline.zip`,
  one SSD) and the bbcdiscs flux captures (HFE; nine for Pipeline across the
  Superior release, the *Play It Again Sam 11* compilation and an
  FSD reconstruction).
- The STH image is a crack. Its `!BOOT` is `*EXEC`'d into an STH-bannered
  BASIC `LOAD`, and GAME (&2100 at &3000), GRAPHIC (&2130 at &1A80) and LEVDES
  (&1F00 at &1100) are plain files.
- On every original capture GAME, GRAPHIC and LEVDES are &D9-byte locked stubs
  loading at &0900. Decoded with jsbeeb's own `loadHfe` + `toSsdOrDsd`, the
  scarybeasts capture (E447ED5E) and the FSD reconstruction are byte-identical,
  so that's the target. Matt picked the Superior original over STH and PIAS.

## 2026-10-03 17:30 — What's on the disc

- Credits in `!BOOT`: `*| PIPELINE/B 1.01`, `Copyright (c) 1988`,
  `William Reeve & Ian Holmes`, `For Superior Software`. It does `*BASIC`,
  `*FX200,3` (Escape disabled, memory cleared on BREAK),
  `?&224=?(&24+!&FFB7)` and `CHAIN"MENU"`. &FFB7 points at the OS's default
  vector table, so that restores the low byte of vector &224 from the ROM's
  copy; worth understanding why later.
- 16 catalogued files, all locked; the catalogue claims 800 sectors although
  the disc is 40 tracks.
- Three uncatalogued runs past the last file, at sectors &122-&142,
  &145-&165 and &16D-&18B; everything else past &113 is &E5 format filler.
  Matched against the STH crack:
  - &122: GAME, &2100 bytes, identical.
  - &145: GRAPHIC, &2100 bytes, identical to the STH file minus its first &30
    bytes (STH's are zeros, so it really loads at &1AB0).
  - &16D: LEVDES, &1F00 bytes, three bytes different from STH's (&600, &601,
    &69C) - presumably where it was patched for the crack.
  None of it is encrypted on disc. The protection so far is just hiding.
- Slack past the end of several files is junk rather than padding (e.g.
  DEFAULT's starts "Finish Block"), so it's recorded in the layout.

## 2026-10-03 17:35 — Build pipeline and INCBIN baseline

- Baron can't write this disc itself: its SSD writer picks file positions and
  has no locked flag, hidden sectors or slack; and a section can't exceed 64K,
  so the whole image can't be one baron section either. So: baron saves each
  piece raw with a `.inf` sidecar (`-p build/files --inf`), and
  `tools/mkssd.py` places them using `src/disc.toml` (catalogue order and
  positions, locked flags, slack, hidden runs).
- `tools/split.py` made the baseline: every piece in `data/`, a one-line
  INCBIN source per piece in `src/`, and the layout. `make verify` rebuilt an
  identical image first time; a deliberately corrupted byte in a hidden run
  and one in slack were both caught and attributed by `tools/ssdcmp.py`.
- `!BOOT` loads at &FFFFFFFF; the generated `org=&FFFF` would wrap, and an
  `*EXEC` file has no org that matters, so it's `org=0`.
- Baron is pinned in CI at 016a764 (0.4.2.0).
- The jsbeeb MCP wasn't registered for this directory; `.mcp.json` adds it
  for the next session.
