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

## 2026-10-03 20:55 — Merged: the Graphics Designer and DEFAULT (agent branch)

Details in `docs/notes/graphic.md`.

- H.GRAPH is fully source (loaded at &1AB0, entered at &2BAE), each routine
  a named scope; its logo and font are pixel pictures. DEFAULT is the
  graphics set drawn as pictures (`src/sprites.6502inc` turns them back into
  bytes): 16 large sprites (16x32), 16 small (8x16), 9 more large, then 15
  twelve-character object names; small sprite &1F, the man, has none. Stored
  a column at a time like a MODE 5 character cell, logical colours (black,
  blue, yellow, red), no masks. `docs/img/graphics-default.png` shows it.
- The designer edits IO directly as well as graphics sets, telling them
  apart by length. In IO the set is in three pieces (large slot &28 at +0,
  the names at +&80, slots &00-&27 at +&25D3), so in the game the sprites
  sit at &4A00-&57FF. The shipped IO holds DEFAULT's sprites and names byte
  for byte.
- "Finish Block", the start of DEFAULT's slack on the disc, is 12 bytes the
  designer writes straight after the set at &4F34.
- Errors restart the designer without losing work (it takes BRKV and EVNTV
  once, keeping the old values in IND1V/IND2V); Undo swaps, so it's also
  Redo; sheet position 0 is the background tile.
- &3ADC-&3BAF isn't program, just memory at save time. Like H.LEVDES's tail,
  the files were saved from wherever the build happened to leave things.
- On main: `MOS_ERROR_PTR` and `MOS_ESCAPE_FLAG` into `os.6502inc`; the
  piece's own `RESET_VECTOR` was `CPU_RESET_VECTOR`.
- Symbol dump: the picture macros' FOR loops add about 15,000 `@` entries to
  `build/symbols.json`, and constants like `CELL = 8` look like addresses.
  Both already in `docs/symbols-feedback.md`'s list.

## 2026-10-03 21:20 — Merged: the game and IO (agent branch); everything is source

Details in `docs/notes/game.md`. With this, every catalogued file and hidden
run is source; the binaries left are pictures (SCREEN, TITLE's packed
picture, LDATA) and PL's encrypted bytes, which a test ties to its source.

- H.GAME's loader at &3000 copies the game into place with an
  inline-parameter block copier (saved extended vectors to &037F, a sound
  event handler into the stack page at &0131, the tune to &0880 and its
  envelopes straight into the OS's envelope store, scrolling code to &0400,
  the game to &0900-&23AC), sets MODE 5 with latch bit 5 clear for an 8K
  wrapping screen at &6000, and jumps to &12A3. It also holds "GET YOUR
  GRUBBY LITTLE HANDS OFF THIS PROGRAM!".
- IO is loaded at the start and again on the title screen's `L` (another
  mission): the game swaps &0D00-&1CFF out to the screen, puts an RTI at the
  NMI routine, restores the extended vectors, re-claims filing system
  workspace, `*DISK`, OSFILE `:0.$.IO`, and swaps back.
- The game: step on every cell 7 ("Collect the Sulphur!"), press P facing
  the exit, then get 5+ cells away within 4 clock ticks as it turns to
  fire. Crates push; lava and fire kill; pipes carry you hidden to their
  other end. Up to 4 flame monsters with 2-bit turning preferences; 8
  objects a level, each owning 4 of the 32 triggers (teleport, move a
  cell, swap the keys...). Keys default to Z X : / P D M CTRL T RETURN -
  Guildmaster's actions fit this game after all. A locked mission played
  from level 1 ends with a competition code made from the score and a
  checksum of the level data.
- Tricks: the object table overlays run-once startup code; trigger data
  overwrites the end of the game's code; operand bytes double as BIT masks;
  `throw_trigger` is reached only through a self-modified JMP; text is
  printed inline after a JSR up to a NOP. Traces (title, play, deaths, the
  exit, objects, pipes) saw about 78% of instructions and no code the static
  trace had missed.
- IO is source in `src/io.6502` with its layout in `src/io.6502inc`, computed
  from MISSION's own size formulas; pictures, icons and the four 64x64 maps
  are drawn in the source.
- Decided on merge: the agent had made `src/hidden_game.6502` generated, from
  hint files holding all the names and comments plus the binary the build
  makes from that same source - circular, and two places to edit. Frozen
  instead: the source is hand-edited from now on like every other piece,
  the annotation hints are gone (history has them, 435d925), and
  `hints/hidden_game.toml` stays as a record that still drafts the
  structure.
- Both the game and Level Designer agents wrote a `tools/dis6502seg.py`; the
  game's is the superset and now also takes the Level Designer's `org` for a
  segment's run address, so both hints files still draft code that
  reassembles identically.
- On main: `MOS_VSYNC_COUNTER`, `MOS_NMI_ROUTINE`, `MOS_EXTENDED_VECTORS`
  into `os.6502inc`; the game's own names for the error pointer and Escape
  flag now use the shared ones. `docs/baron-feedback.md` collects every
  baron issue and wish so far.

## 2026-10-03 21:40 — Phase 2: one description per thing, and reviews

Everything is source; now it gets better rather than bigger. Four agents in
parallel worktrees, partitioned by file so they can't collide:

- IO built as MISSION builds it: the default graphics set and each level
  described once (DEFAULT and IO share the pictures; LEVEL1 and IO's level 0
  share a level description), instead of the same data drawn twice in two
  notations. It may add names to io/level/sprites includes but not rename
  any that code uses.
- A critical review of each big program (the game, the Level Designer, the
  Graphics Designer): check every comment against the code (and the
  emulator where unsure), name the magic numbers (directions, cell types,
  flags, geometry, characters via `ascii()`), tidy structure, and record
  corrections. A sample of the game's source showed why: sound annotation,
  but comparisons like `CMP #&01` for a direction.

## 2026-10-03 22:40 — Merged: IO, DEFAULT and LEVEL1 from one description each

Details in `docs/notes/io.md`.

- The default graphics set is described once (`src/default.6502inc`: 41
  pictures as pixel rows, 15 names) and DEFAULT and IO's three pieces are
  emitted from it. Each of the four levels is described once
  (`src/level1.6502inc` to `level4.6502inc`: code, palette, setup, a row per
  object, monster and trigger, the map as 64 strings), in a format defined
  once (`src/leveldata.6502inc`, from MISSION's field sizes); LEVEL1 and IO
  are both built from them, IO interleaving the four levels' fields as
  MISSION does. `default.6502` and `level1.6502` are a few lines each now.
- IO's slack on the disc is DEFAULT's bytes &E00-&E2C: MISSION loads the
  graphics file at the mission's graphics offset, so its names run past the
  mission's end and the save picks up what follows. The mission text
  appears nowhere else.
- Level 1's trigger 15 stores &02 for "push the cell in front": the designer
  would show that as backwards, but the game turns it anticlockwise.
- The symbol dump shrank from 1.44 MB to 0.83 MB by making data emitters
  top-level FUNCTION calls and vectorising per-element loops. Confirmed here:
  every FUNCTION leaves a null `@` frame in each file including it, and a
  call inside a MACRO adds another (`docs/symbols-feedback.md`).
- Left for later: `tools/graphics.py asm` still writes the old picture
  notation; the Graphics Designer's pictures could use `mode5_pictures`;
  `disc.toml`'s IO slack could come from DEFAULT; `TILE_*` (designer) and
  `CELL_*` (game) name the same values differently. The three reviewers were
  told to merge main and use the shared names.

## 2026-10-03 23:20 — Merged: the Level Designer review

Details in `docs/notes/levdes.md`.

- The first pass had the designer's block numbers wrong: its block menu
  table holds two tables, a nibble each (indexed by block, its menu item;
  indexed by item, its block), and was read as key-to-block. Read right, the
  designer's names agree with the game's meanings (6 Crate, 7 Collectable,
  8 Wall 2, 9 Barricade, A Fatal trap = lava, B Junction, E S.Monster =
  fire, F Marker = object). Confirmed key by key in jsbeeb, and by the
  simulator dying on A and E and turning at B. On main the TILE_* names
  (which had the old reading) are gone, `level.6502inc` lists the menu names
  against CELL_*, and comments calling cell 9 a marker now say barricade.
- Other corrections: WDATA's units are screen columns and character rows;
  its messages' TABs were misread constants (now `os_tab(column, row)`); the
  back door needs Caps Lock off then I; a puzzle's status digit is its
  object (puzzle mod 8 + 1); the simulator's directions number 0 left,
  1 up, 2 right, 3 down, unlike the level's, so they keep their own names.
- Found: a 12-character filename doesn't save (its Return is overwritten by
  the file control block) - silently; loading a level with the wrong code
  loses the one being edited.
- Ian's labels from the MENU fragment are noted at their routines (sel0
  `choose_from_window`, sure `confirm`, wind `open_window`, table
  `jump_to_handler`, key3 `help_menu`, help `help_menu_show`, canc the RTS at
  `hex_key_done`, t2 `work`).
- Every OS call, key, character, VDU code, CRTC register, menu item, flag and
  direction in the designer is named, in `src/levdes.6502inc` for now; many
  belong in shared includes, which waits for the other reviews so it's done
  once.

## 2026-10-03 23:45 — Merged: the Graphics Designer review

Details in `docs/notes/graphic.md`.

- Corrections: small slot &1F isn't "the man" but object icon 15, which the
  game draws as the exit; "Finish Block" sits exactly where its name would
  be (&E80 + 15 * 12 = &F34), so it's the designer's name for the exit, not
  just an end marker. Slots &20-&23 are the player facing left, right, up
  and down (not a machine), and &0E/&0F the flame monster's two pictures;
  Animate previews the game's own animations (side views alternate with
  themselves upside down). `default.6502inc` on main corrected to match.
- Also: on tape nothing loads at startup; the pixel cursor never blinks; a
  window covers at most &5000-&537F; three loop labels were swapped or
  misnamed; the "unused" `SKIP 39` was an `ALIGN &100` the font relies on;
  MOS 1.20 only sets the Escape flag itself when the Escape event is
  disabled, which is why the designer's event handler sets it.
- The designer now uses `osconst.6502inc`, `io.6502inc` addresses (asserted
  against its own layout) and `mode5_pictures`; its dump entries fell from
  5,119 to 1,064 and `build/symbols.json` to 719 KB.
- Many names it defines (OSBYTE/OSWORD/OSFILE numbers, internal key numbers,
  VDU and PLOT codes, the graphics set's layout and slot roles) belong in
  shared includes; that consolidation waits for the game review, so it's
  done once across all three programs.

## 2026-10-04 00:05 — Merged: the game review; phase 2's reviews are in

Details in `docs/notes/game.md` (section 2026-10-03 19:52).

- Corrections, checked in jsbeeb: `add_points` falls into `add_point`, so it
  adds one more than asked: a monster scores 26, a level 101, the time bonus
  is the time left plus one. The competition entry code prints the score's
  low byte first. The player picture flips every four cells walked, not
  every other step. The tune plays during levels, not on the title screen.
  WELL DONE has a shadow; the map view's odd and even rows were the wrong
  way round in the comments.
- The game prints through the OS, which still believes it's in MODE 5
  (&350 holds &5800 and a 320-byte row), so TAB(x, y) lands at &5800 + 320y
  + 16x on the game's 256-byte rows from &6000: every TAB is now
  `TEXT_AT column, row`, matching screenshots.
- New: a teleport moves the restart point (lose a life and you come back at
  the destination). Action 6's "all four monsters" is an original bug: only
  monster 3 gets the direction, 2 and 1 are sent off the map (gone) and
  monster 0 carries on; the shipped mission never uses it. A one-shot
  trigger is used up before its action runs, so it's spent even if the
  action fails. An OBJECT_NO_THROW object can still be thrown; only its
  landing triggers are skipped.
- `src/game.6502inc` holds the game's own names, included inside the `game`
  scope. ASSERTs now pin the layout tricks: the objects over run-once code,
  trigger data running exactly up to IO, the BIT-mask operands.
- Next: one pass moving the names all three programs define locally (OSBYTE
  and OSWORD numbers, internal key numbers, VDU and CRTC codes, the graphics
  set's layout) into the shared includes.

## 2026-10-04 00:40 — Merged: one definition per shared name

Details in `docs/notes/names.md`; CLAUDE.md's new "Where names live" says
which include holds what.

- OS call numbers, settings, keys, characters, VDU/PLOT codes, CRTC
  registers, screen memory and opcodes are all in `osconst.6502inc` now
  (screen memory too, though they're addresses, so the disassembler doesn't
  name every &3000 or &5800 after them); `os.6502inc` keeps addresses only.
  The graphics set's format heads `sprites.6502inc`; the level format's
  shared names (all 16 cell types, diagonal directions, turns, conditions,
  alternates) are in `leveldata.6502inc`; PL reads the level file through
  `level.6502inc` instead of its own addresses.
- Where programs disagreed, one name won (e.g. `MONSTER_GONE`,
  `PUZZLE_ACTION`, `TURN_*` as 0-3 with the game multiplying by its own
  `TURN_ROW`); where they number something differently on purpose (the
  Level Designer's `MOVE_*`, each designer's own function-key base) the
  names stay separate with a comment.
- Baron: a scope may silently shadow a name from outside it (now a test,
  `tests/test_symbols.py`, which caught one case); a file of FUNCTIONs can be
  included only once per program. Both in `docs/baron-feedback.md`.
- The symbol dump grew from 744 KB to 797 KB: each file's dump lists every
  constant its includes define, and osconst is in 15 of the 19 sources. The
  `@` entries didn't grow.

## 2026-10-04 01:30 — Merged: the second review of the smaller pieces

Details in the newest sections of `docs/notes/loaders.md` and
`docs/notes/basic.md`. Corrections, mostly seen in jsbeeb:

- MENU's `*FX255 8 247` sets start-up option bit 3, which stops plain BREAK
  booting the disc (the notes had it the other way round); why isn't clear.
  Quit's `CALL !-4` is a BREAK that, with `*FX200 2`, clears memory and stops
  at BASIC's prompt. `LOMEM=TOP` before starting something matters: with C%
  and S% still DIM'd, option 1's MODE 1 would be "Bad MODE", and line 80's
  error trap would hang the machine.
- MISSION's REM routine scrambles the typed editing code the way levels
  store theirs, to compare them; it never unscrambles (correcting 19:40's
  entry). Backpack sizes are 2-4. The lock keys work lower case only, i
  storing 1 and h &FF; only h's negative value makes the game show the
  competition entry code.
- PL's cheat, mapped onto the game's source: 31 lives (`new_game`'s
  `LDX #START_LIVES`), every level offered (`load_mission`'s store of
  `furthest_level` NOPped and &61 set to 3) - and the competition entry code
  never shown, so a cheat can't win the prize. Another anti-tamper check: X
  from `*FX200` doubles as the last code byte's index.
- TITLE's unpacker overwrites the packed data's last 41 bytes with zeros
  before reading them, which then read as runs of 256 zeros and carry the
  writes to &8DB1 (jsbeeb's write record agrees); the final clear changes
  nothing.
- The stubs' 80-track path, untested until now: jsbeeb can put a 40-track
  disc in an 80-track drive, and each stub then sets `double_step` and reads
  its run correctly - but DFS 1.2 doesn't double-step its own reads, so the
  game then fails to load IO ("Disk fault 18"). The stubs' care only pays off
  with a DFS that does.
- On main: WARNING's rows 0-9 and MENU's menu screen rows 0-9 are now one
  include (`src/mode7_header.6502inc`).

## 2026-10-03 23:15 — The journal's clock; jsbeeb's registry proposal

- Correction: from 18:20 on, this journal's headings ran ahead of the clock,
  by up to four and a half hours. The commits that went with them, by
  `git log`: "MENU, and who loads what" 17:46; the merges of the boot chain
  18:20, MENU and MISSION 18:24, the Level Designer 18:37, the Graphics
  Designer 18:43, the game and IO 18:52; IO, DEFAULT and LEVEL1 from one
  description 19:32; the reviews of the Level Designer 19:38, the Graphics
  Designer 19:41 and the game 19:53; one definition per shared name 20:23;
  the smaller pieces' second review 20:58 (headed 2026-10-04 01:30). Times
  from here on come from `date`, and the agents' briefs say so too. The
  notes files' headings drifted the same way; git has the real times.
- Read jsbeeb's media registry proposal: the fingerprint matches all our
  images, and the symbol sets need more for a disc of overlapping programs.
  Details in `docs/symbols-feedback.md`; Matt has passed the comments on.
- Three open questions are out to agents, one per program: why MENU forces
  start-up option bit 3 (and why !BOOT puts NETV back), why a 12-character
  filename fails to save without a word in the Level Designer, and what the
  game's clipping thresholds &E2 and &F1 are (and the leftover at
  &50AD-&50FF).
