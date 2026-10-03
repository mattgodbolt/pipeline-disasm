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

## 2026-10-03 17:50 — Running it headless

- `tools/beeb.mjs` drives the published `jsbeeb` package (MachineSession)
  from a tiny script language: wait, frames, key, type, until, shot, dump,
  hex, regs, and `trace FILE`, which records every executed PC with the
  opcode found there (so code at an address shared by several programs can
  be told apart). `reads FILE` records every address read and written.
- jsbeeb notes the disc "loaded as 80 track: its catalogue claims 800
  sectors" - harmless, it only reads tracks 0-39.
- Boot sequence seen: SCREEN is the Superior/Acornsoft loading picture
  (MODE 5 at &5800, `docs/img/loading-screen.png`); then WARNING, a Mode 7
  page saying "Unauthorised commercial exploitation of screens or graphics
  data produced by the PIPELINE Level Designer or the PIPELINE Graphics
  Designer is strictly prohibited". So GRAPHIC and LEVDES are the Graphics
  and Level Designers, not data.
- Then the MENU (`docs/img/menu.png`): 1 Start the game, 2 Redefine keys,
  3 Edit graphics, 4 Edit levels, 5 Edit missions, 6 Quit PIPELINE, over a
  Mode 7 double-height scroller. "Edit missions" will be MISSION (BASIC).

## 2026-10-03 18:20 — MENU, and who loads what

- Listed MENU in jsbeeb (`--boot no`, `PAGE=&1900`, `LOAD "MENU"`, `LIST`).
  "PIPELINE menu prog / By Ian Holmes / Originally: GUILDMASTER", and the
  redefine-keys option still names Guildmaster's actions (MOVE NORTH, PICK
  UP OBJECT, VIEW BACKPACK...) though only the key codes are used. Line 40
  is a REM full of VDU codes that prints "Hello, all my friends!" over the
  listing; line 80 is `ON ERROR AWopBabaLuMopALopBamBoom`.
- `LOMEM=PAGE+&A00:DIM C% &EFF, S% &700`: the 8K MENU file carries
  pre-initialised data for those DIMs: C% is machine code (`CALL C%` after
  `!&75=(C%+&49)*65536+C%+&C9`, presumably the Mode 7 scroller) and S% is the
  menu's Mode 7 screen, copied to HIMEM by PROCmenu.
- It restores the OS's default BRKV low half from the ROM's vector table
  (`!&FFB7`), refuses to run with a second processor, and sets up keys in
  &50-&59 (INKEY codes, defaults in DATA).
- `IF INKEY-36 AND INKEY-34 THEN */PL`: PL only runs with two keys held
  at boot.
- Options: 1 `*FX230 1`, MODE 1, `*RUN TITLE`, palette, MODE 7, `*/GAME`;
  2 redefine keys in BASIC; 3 `*/GRAPHIC`; 4 `*/LEVDES`; 5 `CHAIN"MISSION"`;
  6 `CALL !-4` (a reset).
- Strings in the binaries say who uses the data files: H.GAME names
  `:0.$.IO`; H.GRAPH names DEFAULT and `/MRUN`; H.LEVDES names `/MRUN`,
  `L.WDATA` and `L.LDATA`; MRUN is `*E.!BOOT` and `*BASIC` (back to the
  menu). MISSION is the "MISSION GENERATOR", and its
  `l0addr=&5800-numlev*size-grfs-attrs-miss-names` says IO is the game's
  data packed to end at &5800.
- The GAME stub (disassembled as a tool test) reads the hidden run track by
  track with OSWORD &7F into &3000 and jumps there; it carries a BRK error
  block, "Sector read fault!".
- `tools/dis6502.py` (tracing disassembler to baron source) round-trips every
  piece on the disc, even data disassembled as code. Nothing on the disc
  uses absolute addressing for zero page, so no baron feature is needed for
  that.
