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

## 2026-10-03 19:05 — Merged: the boot chain and loaders (agent branch)

Details in `docs/notes/loaders.md`. The headlines:

- The three stubs are one program (`src/hidden_loader.6502inc`), each stub
  setting four numbers (first hidden sector, length, load, entry). Hidden
  runs: H.GAME &3000 (entry &3000), H.GRAPH &1AB0 (entry &2BAE), H.LEVDES
  &1100 (entry &2E21) - the STH crack's addresses were right.
- Correction to 17:30's "none of it is encrypted, the protection is just
  hiding": every hidden sector, and only those, carries a deleted data
  address mark, on every capture (checked again here with jsbeeb's decoder:
  97 sectors, exactly the three runs). The 8271 returns &20 for them, DFS
  calls that a fault, so `*BACKUP` stops at track 29. The stubs use OSWORD
  &7F "read data and deleted data" and ignore the result. An .ssd can't
  hold the marks, so ours (and jsbeeb's HFE-to-SSD conversion) silently lose
  them; jsbeeb's `ssdOrDsdShortfalls` doesn't count deleted marks.
- The stubs probe track 4's sector ID to spot an 80-track drive
  double-stepping, and then seek to twice each track and fix up the 8271's
  track register. jsbeeb never takes that path.
- The "Sector read fault!" BRK block is unreachable: a `NOP : JMP` sits
  where a 7-byte result check fits exactly, presumably patched out once the
  deleted marks made every read return &20.
- PL is "Ian's cheat!", run by MENU if W and T are held at boot. It decrypts
  itself (`plain = key ^ previous plain ^ stored`, keys from its own
  decryptor's bytes), silently reads a level filename and six-digit code
  (LEVEL1's is 677636), lists the level file's 32 puzzles, fakes "Bad
  program" until I, N, O and S are held, then `*L.GAME`s and pokes cheats
  into the game at &3FC7, &4875 and &4F31. On this disc GAME is a stub, so it
  resets: PL predates the hidden sectors. Kept as decrypted source plus the
  stored bytes; `tests/test_pl.py` checks they agree.
- MRUN restores RDCHV (hooked by the Level Designer) and EVNTV (Graphics
  Designer), then types `*E.!BOOT` into the keyboard buffer and enters BASIC.
- TITLE is a zero-run-packed MODE 1 picture ("PIPELINE by IAN HOLMES and
  WILLIAM REEVE") that copies its unpacker to &2F00 and unpacks over itself.
- Shared names reorganised on main: addresses in `src/os.6502inc` (now with
  the CPU vectors and MOS default-vector pointer), constants in the new
  `src/osconst.6502inc` (OSBYTE/OSWORD numbers, key numbers, 8271 commands,
  `ascii()`). The disassembler no longer names zero-page operands from the
  OS file, since a game that owns the machine reuses those bytes.
- Baron wishes from this piece: a way to transform or read back a section's
  bytes (so PL's encrypted image could be generated from its source inside
  the build), and character literals. Neither blocks anything; noted, not
  filed.

## 2026-10-03 19:40 — Built a flux image; merged MENU and MISSION (agent branch)

- The build now also writes `build/pipeline.hfe`: the .ssd's sectors laid
  out with jsbeeb's track builder, with deleted data marks on the sectors
  `src/disc.toml` flags (the three hidden runs). `tools/disccmp.mjs` reads it
  and the original capture (now committed as `original/E447ED5E.hfe`) the
  way a controller would and compares every sector's ID, data and mark: 40
  tracks, 400 sectors, 97 deleted, identical. The game boots from it in
  jsbeeb. A test that it notices a missing mark: it does.
- MENU and MISSION are source (details in `docs/notes/basic.md`). Baron's
  BASIC tokeniser matched the originals on every line; the only trouble is
  raw bytes. `ENDBASIC` always writes the `&0D &FF` end, so an EQUB'd line
  can only come before the BASIC block, and lines with raw control codes
  stay inside it as raw bytes. MISSION's two REMs with teletext bytes
  &81-&86 make `src/mission.6502` invalid UTF-8; the Edit tool mangles it.
- MENU's heap: `LOMEM=PAGE+&A00` is exactly TOP (&2300), so C% is &2300
  and S% &3200, and DIM leaves the file's contents in place. C% is a vsync
  event handler scrolling a message as 16x8 blocks of sixels, reading
  character shapes with OSWORD &0A. Its EVNTV entry is 4 bytes early, landing
  mid-instruction on `04 4C` and `F4 FF`: undocumented NMOS NOPs, run every
  frame (on a 65C02, &04 would be TSB).
- The PL trigger is hidden from LIST by VDU 21 inside a string and VDU 6
  after `*/PL "`. The second-processor check can't fire on BASIC 2
  (`?&FFFF7C00` is `?&7C00`). The game's keys, Guildmaster's names
  notwithstanding, default to Z X * ? P D RETURN T CTRL M.
- The tail of MENU's S% holds a three-voice tune as a BASIC program at
  PAGE+&1C00 (line 1020 runs it, nothing reaches line 1020), and a fragment
  of BASIC assembler that assembles to the Level Designer at &168A-&16A6,
  giving some original label names: sel0 &1126, canc &1637, sure &1323,
  wind &14A8, table &166B, key3 &169E, help &16AD, t2 &54.
- MISSION hides an unscrambler in line 60's REM. Missions can be saved
  locked; the shipped IO is. Level codes (six hex digits, unscrambled by
  swapping adjacent bits and rotating) are 677636, 878702, 218652, 114226
  for levels 1-4; 677636 matches PL's.
- IO's layout as MISSION writes it: &242D-&57FF; +&0000 names (&134: the
  tail of a graphics file, 15 object names of 12 characters), +&0134 the
  mission name (two VDU 31 halves), +&0152 five feature bytes (time,
  mapping, backpack, throw distance, lock), +&0157 four levels' fields
  interleaved field by field (11 fields, &11F per level) then four &800
  maps, +&25D3 graphics (&E00). LEVEL1 is one level (320 bytes of puzzle
  names, the fields, the map); DEFAULT is graphics plus names.
- Shared: `OSWORD_READ_CHAR_DEFINITION` and `EVENT_VSYNC` into
  `osconst.6502inc`; `MODE7_SCREEN`, `mode7_address()` and `SOLID_BLOCK`
  into `teletext.6502inc`.

## 2026-10-03 20:05 — Baron issues, and notes on symbols

- Filed baron#12 (as Claude, for Matt): a way to put a byte by value into a
  BASIC line, or to interleave EQUB'd records with a BASIC block, so MENU
  and MISSION can be valid UTF-8 with their control codes named.
- baron#10 (filed earlier from another session) is about FUNCTION call frames
  colliding when the same function is called at the same byte offset in two
  files of one assembly. We call FUNCTIONs from several includes; `make
  verify` would catch any wrong byte it caused. Bump the pin when it's fixed.
- `docs/symbols-feedback.md` collects what this disc shows a symbol consumer
  (jsbeeb) needs from baron's dump: label vs constant, which section a label
  is in, and a way to tell which of several overlapping programs is loaded.
  Both ends are works in progress, so it's feedback, not a plan.

## 2026-10-03 20:35 — Merged: the Level Designer, WDATA, LEVEL1 (agent branch)

Details in `docs/notes/levdes.md`.

- H.LEVDES is fully source: loaded at &1100, entered at &2E21, which moves
  three pieces of itself (low code to &0880, a 64-glyph font to &0400, and
  17 pointers to menu handler tables into zero page, read by a `LDA &FFFE,Y`
  that wraps), then reuses &25A1-&2FFF as the level being edited. Its font,
  digit glyphs and map-block patterns are pixel-art macros.
- The screen is MODE 1 narrowed to 64 columns (CRTC R1=64, 512 bytes a
  row), so the 64x64 map is one byte (4x4 pixels) per cell. LDATA is its
  title picture (`docs/img/levdes-title.png`), not code; its exec address
  &3820 means nothing.
- The three bytes the STH crack changes (&600, &601, &69C) aren't
  protection: they're two ordinary stores, broken in the crack (a `FF FF`
  that runs as an illegal opcode, and a store to the wrong object's byte).
  Shown in jsbeeb: Options, Start, Display puts the cursor at (62, 35) on
  the original and (31, 15) on the crack. Probably a bad sector in whatever
  the crack was made from.
- Its last &E1 bytes are H.GRAPH's bytes at the same offsets: the file was
  saved from a buffer that had held the Graphics Designer.
- A back door: with the keyboard links at &CF, typing `i` at an error drops
  to BASIC.
- LEVEL1 is the designer's save format (and the game's first level, verbatim
  in IO); WDATA its windows and messages, both now readable source with
  their layouts in `src/level.6502inc` and `src/wdata.6502inc` for MISSION
  and IO to reuse.
- On main: `screen2png.py` (needed Pillow) folded into `beebscreen.py`
  (`--columns`, `--offset`); `MOS_STARTUP_OPTIONS` into `os.6502inc`.
- Baron: list literals can span lines already (the agent built long tables
  eight at a time with CONCAT; simplify later). A stepped range whose limit
  equals its second element fails (`0..2..2`, `1..3..3`, `10..8..8` all give
  "Argument out of domain"); reported upstream. Character literals are now
  asked for by two pieces; `CODES("c")[0]` works.
