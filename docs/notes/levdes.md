# Level Designer notes

The Level Designer (H.LEVDES) and its data: WDATA, LDATA, LEVEL1. Times are
US Central.

## 2026-10-03 18:11 — Loading, memory map, and what the data files are

- The LEVDES stub at &0900 reads sectors &16D-&18B (track &24 sector 5 on,
  &1F sectors) to **&1100** and jumps to **&2E21**, the same addresses the
  STH crack's plain LEVDES file has. It reads track 4's sector ID first and
  double-steps if it reads back a track other than 4 (a 40-track disc in an
  80-track drive). The OSWORD &7F result is loaded and then ignored (`LDA
  result : NOP : JMP next`), so the "Sector read fault!" BRK block in the stub
  is never reached.
- At &2E21 the program moves three pieces of itself before doing anything
  else:
  - &25E1-&2A20 to **&0880-&0CBF**: low code (window drawing, menus, map
    drawing) with a jump table at &0880. The loop is sloppy and actually
    copies &25E1-&2A60 to &0880-&0CFF; the last &40 bytes are the start of
    the font, unused there.
  - &2A21-&2E20 to **&0400-&07FF**: a 64-glyph font, 16 bytes per glyph
    (8x8 pixels in MODE 1, two 4-pixel columns).
  - &25A1-&25E0 to **&00-&3F**: zero page, mostly a table of 17 pointers to
    the menus' jump tables.
  `tools/dis6502seg.py` disassembles a binary like this with each moved piece
  as a nested, rephased baron section.
- Once moved, &25A1-&2FFF is reused as the level being edited (layout in
  `src/level.6502inc`): the startup code at &2E21 and the strings
  "L.WDATA"/"L.LDATA" get overwritten by the map. &2F1F-&2FFF is junk, code
  from something else (it calls &39CA, &34EF, &2186) left in memory when the
  file was saved.
- Screen: MODE 1 with CRTC R1=64 (and R2=&5A to centre it), so 64 character
  columns of 8 bytes: 512 bytes a row, 32 rows, &3000-&6FFF, 256x256
  pixels. The map is drawn a cell to a byte column and four scan lines, so
  the whole 64x64 map fills the screen. OS text still thinks it has 40
  columns of 640 bytes, so the designer picks TAB positions that land where
  it wants (TAB(10,11) and TAB(34,12) are the two lines of its message box).
- **WDATA** (&7000, &C4E bytes): the windows and messages. A table of 2-byte
  pointers at &7000, numbered from 1, then the definitions. A window is
  `x, y, width, height` then height+1 lines, each a length byte (bit 7 set to
  left-justify, else centred) and that many glyph codes; the first line is the
  title, the rest the menu items. x and y bit 7 clear means "relative": the
  window goes on whichever side of the screen the cursor isn't. A message is
  plain VDU text ended by `|`, `&FF` switching to highlighted colours. Glyph
  codes: 0-25 A-Z, 26 `.`, 27 `:`, 28 `?`, 29 `<`, 30 `>`, 31 space, 32-57
  a-z, 58-67 digits 1234567890, 68 a tick, 69 `-`; codes from 64 come from
  &2500 in the program rather than the font.
- **LDATA** (&3400, &3200 bytes): the title screen, a straight copy of screen
  memory &3400-&65FF in the designer's 64-column layout ("PIPELINE Level
  Designer" over a landscape, "Press SPACE"). It is `*LOAD`ed; its exec
  address &3820 is meaningless and none of it is code.
- **LEVEL1** (&25A1, &A5F bytes, exec &8380): a level saved by the
  designer. "Save level" writes &25A1-&2FFF with exactly that load and exec
  (OSFILE block at &1E4E), so LEVEL1 is the designer's file format. It is not
  loaded by the designer at startup (only by "Load level", by name) nor by the
  game: MISSION's "load a level" `*LOAD`s one into its buffer, and MISSION
  packs levels into IO. LEVEL1's palette, start/finish/time block, objects,
  monsters, puzzle types and positions, and its whole map appear verbatim in
  IO (at IO+&163, +&173, +&193, +&213, +&253, +&2D3 and +&5D3), so LEVEL1 is
  the game's first level.
- LEVEL1's editing code is **677636** (decoded from &26E1-&26E3: pairs of
  digits as BCD, bit pairs swapped, rotated right). Load it with F2, Load
  level, Y, `LEVEL1`, `677636`.

## Using the editor (jsbeeb)

- From the menu (about 30 s after boot) `Digit4` then `Enter`; it loads
  WDATA and LDATA, shows the title until Space.
- Then the map, blank. Z X : / move the cursor, Return plots the current
  block, Delete blanks, 0-9 and A-F pick a block directly, S switches the
  simulator (the cursor travels the pipes like the player), Space and Return
  in menus, cursor up/down move the menu bar.
- Function keys: f0 block menu, f1 Options (Start, Finish, Object,
  M.Monster, Puzzle, Collects, Graphics, Time, Clear), f2 Files (Load, Save,
  Edit code, Exit), f3 Help (Find puzzle, Simulate), f4 About. *FX225,128
  makes them return &80-&84. Inside any menu a function key abandons it and
  runs that command instead.
- Escape is an error ("Escape key pressed"); Shift+Escape also offers to
  quit. An error handler shows the message; with keyboard links &CF, typing
  `i` at the error drops into BASIC (a developers' back door).
- Exit (Files) runs `/MRUN`, which goes back to the menu.

## 2026-10-03 18:34 — The STH crack's three bytes

- &1700, &1701 and &179C (file offsets &600, &601, &69C) are all in one
  256-byte sector of the hidden run (&173), and they're ordinary code, not a
  protection check: nothing reads or tests them.
  - &1700 is `STA cursor_x` (85 50) in `edit_marker`, the Options menu's
    Start/Finish "Display" and "Define". The crack has FF FF there: &FF is an
    illegal opcode (ISB abs,X) that swallows the next byte as well, then
    `54 98` runs as a two-byte NOP that swallows the TYA. So the cursor's x
    is never set and its y is computed from garbage.
  - &179C is the low byte of `STA level_objects+1, Y` (99 F1 26) in
    `object_position_define`. The crack's FF makes it `STA &26FF, Y`, so
    setting an object's position writes its y into the next object's
    charges byte (object 4's, for object 1) instead.
- Checked in jsbeeb: with LEVEL1 loaded, Options, Start, Display puts the
  cursor at (62, 35) on the original and at (31, 15) on the STH crack.
- The original's flux capture decodes without a CRC error or odd sector
  (tools/hfe2ssd.mjs refuses otherwise), so there's no unreadable sector
  that would explain them. They look like damage to the crack's copy of that
  sector, which went unnoticed because only those two editors suffer.
- The stub ignores read errors anyway (its result check is NOPped out), so
  the original wouldn't have complained about a bad sector either.

## 2026-10-03 18:34 — The end of the file is the Graphics Designer

- H.LEVDES's own content ends at &2F1E ("L.LDATA", 13). The last &E1 bytes,
  &2F1F-&2FFF (file offsets &1E1F-&1EFF), are byte for byte H.GRAPH's bytes
  at the same file offsets: the level designer was written over a buffer that
  held the Graphics Designer, and the rest of its last sector came along.

## 2026-10-03 18:34 — How the designer is built

- Zero page &00-&21 holds 17 pointers to handler tables (one per menu, plus
  one for the simulator's moves). `jump_to_handler` takes a menu item and a
  table number from 1, and reads the pointer with `LDA &FFFE,Y`, which wraps
  round into zero page.
- Every menu is a WDATA window: `open_window` draws it from its definition
  (positioned out of the cursor's way when it's relative), `window_menu`
  moves an inverted bar with cursor up/down (*FX4,2 and *FX225,128 make them
  &8E/&8F), `close_window` redraws the map underneath. The editing windows
  (object, monster, puzzle, conditions, effects...) loop on their menu until
  their OK item, whose handler (`menu_ok`) pops back out of the loop.
- Ticks and crosses at the ends of window lines show flags (`tick_line`).
- Prompts go in a message box (character rows 14-17) drawn the same way; the
  OS prints into it, at TAB positions chosen to land in the 64-column screen.
  Input is OSWORD 0 with an RDCHV filter (`rdchv_filter`) limiting the
  characters, so numbers only take digits.
- Function keys abandon whatever is going on (`check_function_key` resets the
  stack and dispatches the command), both from `get_key` and from inside
  OSWORD 0 through the RDCHV filter.
- The simulator (S, or Help, Simulate) makes the cursor behave like the
  player: it walks on blanks and collectables, dies on wall 2, barricades
  and the map edge, enters a pipe running its way and travels until it comes
  out, bouncing back off curves, walls, crates and junctions and turning at
  an S.Monster block. Shift moves the cursor anywhere regardless.
- The designer marks positions in the map itself: the start, finish and
  objects with a junction block, monsters with a barricade (`plot_marker`
  blanks the old position if it still holds the marker).
- Errors: a BRKV handler shows the message in the box; Escape (*FX229,0 after
  the title) raises "Escape key pressed". If an error happens during "Load
  level" the half-loaded level is cleared.
- A new level's editing code is 123456; LEVEL1's is 677636. "Load level"
  asks for the code before loading and throws the level away if it doesn't
  match ("Sorry! Wrong code.").

## 2026-10-03 18:34 — The level file format

The whole of &25A1-&2FFF, saved with load &25A1 and exec &8380
(`src/level.6502inc` names every field):

| Address | Size | What |
|---|---|---|
| &25A1 | 32 x 8 | puzzle names, first eight characters |
| &26A1 | 32 x 2 | puzzle names, last two |
| &26E1 | 3 | editing code (BCD digit pairs, odd/even bits swapped, rotated right) |
| &26E4 | 4 | palette: logical colour * 16 + physical, for VDU 19 |
| &26E8 | 2 | start x, y, each less 4 |
| &26EA | 1 | collectables needed |
| &26EB | 1 | time |
| &26EC | 2 | finish x, y |
| &26EE | 1 | monsters: bits 0-3 the block that kills one, bits 4-7 what it leaves |
| &26EF | 1 | sprites for wall one, wall two, collectable, trap (2 bits each, wall one at the top) |
| &26F0 | 8 x 4 | objects: x, y (bit 7: absent), sprite, charges (bits 0-4) + flags (bit 5 no charges, 6 vanishes, 7 can't be thrown) |
| &2710 | 4 x 4 | walking monsters: x*4, y*4, direction (0 W, 1 E, 2 N, 3 S, 8 dead), pattern (four 2-bit choices at junctions, first in bits 0-1: 0 back, 1 forward, 2 right, 3 left) |
| &2720 | 32 | puzzle types: bits 0-3 type, bit 4 re-usable, bit 5 starts off, bit 6 collectables condition, bit 7 needs object 1 |
| &2740 | 32 x 2 | puzzle positions: x, y, bit 7 set to ignore that coordinate |
| &2780 | 32 x 4 | puzzle effects (three bytes, by type) and conditions (bits 0-3 next block, 4-5 direction, bit 6 check next block, bit 7 check direction) |
| &2800 | 64 x 32 | the map: a nibble a cell, 32 bytes per column x, top to bottom, even y in the top nibble |

Puzzle types, in menu order: 0 place block, 1 move block, 2 next block, 3 set
levels, 4 throw object, 5 detonate object, 6 move monster, 7 place monster, 8
teleport, 9 swap next block, 10 turn on puzzle, 11 turn off puzzle, 12 charge
object, 13 push crates, 14 move next block, 15 disorientate. What each keeps
in its three effect bytes is commented at the effect editors in
`src/hidden_levdes.6502` and spelt out per puzzle in `src/level1.6502`.

Map blocks: 0 blank, 1-4 SE/SW/NE/NW curves, 5 wall 1, 6 fatal trap, 7
collectable, 8 crate, 9 marker, A wall 2, B S.monster, C horizontal pipe, D
vertical pipe, E barricade, F junction. The keys 0-9 A-F choose them in a
different order (`tile_menu_map`).

## 2026-10-03 18:34 — What became source

- `src/hidden_levdes.6502`: all code and data named and annotated; the font,
  extra digit glyphs and block patterns are pixel art (GLYPH and TILE macros
  over baron functions encoding MODE 1 bytes).
- `src/wdata.6502`: WDATA as WINDOW/LINE/LEFT macros and message strings;
  window and message numbers in `src/wdata.6502inc`, which the designer uses.
- `src/level1.6502`: LEVEL1 with every field named, puzzles commented with
  what they do, and the map as 64 rows of characters (`MAP` macro transposes
  it into columns). The macros are in `src/level.6502inc`, for MISSION and IO
  to reuse: IO holds the same level data.
- `src/ldata.6502`: still an INCBIN, documented; `tools/screen2png.py` draws
  it.
- The LEVDES stub (`src/levdes.6502`) is untouched (it's the same stub as
  GAME's and GRAPHIC's).

## Baron notes

- `0..2..2` (a stepped range whose end equals its second element) fails with
  "Argument out of domain"; `0..2..3` is fine. `FOR y = 0..2..MAP_SIZE - 1`
  is what the MAP macro uses.
- No character literal: `asc("i")` is a one-line FUNCTION over `CODES`.
- No line continuation, so the level's 32 names and 64 map rows are built as
  groups of eight and joined with CONCAT.
