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

## 2026-10-03 19:37 — Review: corrections, and what's newly understood

A second pass over `src/hidden_levdes.6502` and WDATA, checking each claim
against the code and, where it mattered, in jsbeeb.

### The block numbers were wrong

The designer's block table (`block_menu_map`, at &21BF; it was
`tile_menu_map`) is two tables in one, a nibble each:

- indexed by block, the top nibble is that block's item in the block menu;
- indexed by menu item, the bottom nibble is that item's block.

The keys 0-9 and A-F pick menu items by number (`hex_key` reads the bottom
nibble at the key's value). The first pass read the table as key-to-block,
which named blocks 6, 8, 9, A, B, E and F wrongly; `level.6502inc`'s
`TILE_*`, its comment on them, leveldata's `MAP_KEY` note on 9 and
`level1.6502`'s comments carry the mistake. Correctly:

| Block | Menu item | Designer's name | Game's name (CELL_*) |
|---|---|---|---|
| 0 | 0 | Blank | CELL_FLOOR |
| 1 | 1 | SE curve | (a wall shape) |
| 2 | 2 | SW curve | (a wall shape) |
| 3 | 3 | NE curve | (a wall shape) |
| 4 | 4 | NW curve | (a wall shape) |
| 5 | 5 | Wall 1 | (a wall) |
| 6 | 10 | Crate | CELL_CRATE |
| 7 | 7 | Collectable | CELL_SULPHUR |
| 8 | 6 | Wall 2 | CELL_WALL |
| 9 | 15 | Barricade | (a wall) |
| A | 8 | Fatal trap | CELL_LAVA |
| B | 14 | Junction | CELL_JUNCTION |
| C | 12 | Horz.Pipe | CELL_PIPE_ACROSS |
| D | 13 | Vert.Pipe | CELL_PIPE_DOWN |
| E | 9 | S.Monster | CELL_FIRE |
| F | 11 | Marker | CELL_OBJECT |

The table's bytes are `00 11 22 33 44 55 A8 77 6A FE 86 EF CC DD 9B B9`; the
source now builds them from the menu's list of blocks with `FIND`. So the
designer's names agree with the game's meanings; there's no mismatch to
explain. Confirmed in jsbeeb: key 6 sets the brush (&59) to 8 and f0's menu
highlights "Wall 2"; choosing "Crate" from the menu sets 6; key 9 gives E
with "S.Monster" highlighted; keys B and F give F and 9; and with the
simulator on, key 8 (a fatal trap, block A) plotted next to the cursor and
walked into gives "You have lost one life." The code agrees throughout:

- The simulator loses a life on A and E (fatal trap, S.Monster) and off the
  map; walks onto blanks and collectables; bounces off curves, walls,
  crates, barricades and markers; and at a junction (B), not an S.Monster,
  turns into the first pipe running its way, trying left, right, then
  straight on, else back.
- The start, finish and objects are marked in the map with a marker (F),
  monsters with an S.Monster (E), not a junction and a barricade.
- The Graphics window's four sprites are for wall one, wall two,
  collectable and fatal trap: cells 5, 8, 7 and A, the game's cells with
  second pictures.
- A new level's monster rule is A, A: monsters die in fatal traps and leave
  one.

### Other corrections

- WDATA's x and width are screen columns (of the 64; a glyph is two), y and
  height character rows; not glyph columns and half rows.
- WDATA's messages wrote their VDU 31 positions with whatever name or
  character had the right value (`TAB, TAB, 2` is TAB(31,2); `TAB, "#",
  VDU_CLS` is TAB(35,12), no CLS in it). They're `os_tab(column, row)` in our
  64 columns now; e.g. "Press any key..." is at column 8, row 17.
- The back door at an error needs a lower-case "i", and `get_key` forces
  Caps Lock on with OSBYTE &CA (Y=&4F, X=&20), which also clears bit 7, so
  Shift doesn't reverse it. With &028F = &CF: Caps Lock then I reaches
  BASIC (seen in jsbeeb, `PRINT 6*7` works); Shift+I goes back to the map.
- The puzzle status window's digit is the puzzle's object, puzzle mod 8
  plus 1, printed over the 1 of "Use object 1:" (puzzle 13 shows "Use object
  5:" in jsbeeb). The game tries object n's puzzles n, n + 8, n + 16 and
  n + 24, so the type byte's bit 7 is "fired by using or throwing its
  object", not "needs object 1".
- A swap next block puzzle shows Check next ticked in the Conditions window
  while its flag is kept clear (the Type editor clears it); Next block and
  Check next do nothing for it. The game's swap compares the cell in front
  itself.
- The Time option, like `ask_number`, allows 0-255, not 1-255.
- `rdchv_filter` is RDCHV from `main` on (out while an error shows), not
  only during line input; it lets everything through unless `input_line`
  has narrowed the range, and turns function keys into commands everywhere.
- OBJECT_NO_CHARGES (bit 5) means the uses never run out (the game treats
  32 and up as unlimited); the object window's "Charges:" is ticked when
  it's clear, and setting a number of charges clears it.
- The sprites byte's two bits per block say which squares of a checkerboard
  show the block's second picture (the game's `alternate_cells`): Sprite A
  is 0 (none), Sprite B 3 (all), Patterned 1 (odd squares); 2 isn't offered.
- The start is kept 4 less than the cursor because the game keeps the top
  left of its 8x8 view, the player 4 cells in (as Teleport's arguments).
- `unused_read_key` isn't "INKEY with a long time limit": it's OSBYTE &81
  with Y = &81.
- Baron: list literals may span lines, so nothing needs building eight at a
  time with CONCAT; and `ascii()` is in `osconst.6502inc` (the local `asc()`
  is gone).

### Newly understood

- An Escape from a menu (`menu_select`) restarts the main loop without
  resetting the stack, so each leaves a few bytes on it; the stack wraps in
  its page, so it's harmless. BRKs and function keys reset it.
- Loading a level loads it over the one being edited before checking the
  code, so a wrong code loses both (a new level replaces it).
- A 12-character filename doesn't save: its Return lands on the first byte
  of `osfile_block`, which `ask_filename` then fills from the template, so
  OSFILE sees the name followed by "0" and &1E (`filename`'s address). In
  jsbeeb, Save level to ":0.$.ABCDEFG" left the catalogue unchanged;
  ":0.$.ABCDEF" saved.
- The program calls between its parts mostly through three jump tables (at
  &1100, the low code's &0880 and before `new_level`), as if they were
  assembled separately.
- Ian's labels from MENU's fragment, now noted at their routines: sel0
  `choose_from_window`, sure `confirm`, wind `open_window`, table
  `jump_to_handler`, key3 `help_menu` (f3), help `help_menu_show`, simt...
  `help_simulate`, canc the RTS at `hex_key_done` that `files_menu` uses to
  cancel, t2 `work` (&54). The fragment is `files_menu` and the start of
  `help_menu`.
- Confirmed in jsbeeb: *FX229 is 1 during the title and 0 after, so entry's
  "X is still 1" after *OPT holds.

### Names, and where they should live

`src/levdes.6502inc` is new: the designer's (and WDATA's) names that no
shared include has. To move when the shared includes can take them:

- leveldata.6502inc: CELL_SE_CURVE, CELL_SW_CURVE, CELL_NE_CURVE,
  CELL_NW_CURVE, CELL_WALL_1, CELL_BARRICADE (cells the game doesn't name);
  DIRECTION_UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT (4-7, Move block's
  diagonals); MONSTER_DEAD (8); TURN_BACK, FORWARDS, RIGHT, LEFT (pattern
  fields); COORDINATE_BITS, POSITION_FLAGS; OBJECT_CHARGES (&1F),
  OBJECT_KINDS (15); PUZZLE_TYPE (&0F); NAME_HEAD (8); CONDITION_BLOCK,
  CONDITION_DIRECTION, CONDITION_CHECK_BLOCK, CONDITION_CHECK_DIRECTION;
  SET_LEVELS_KEEP_TIME, SET_LEVELS_KEEP_COLLECTS; SPRITES_A, SPRITES_ODD,
  SPRITES_EVEN, SPRITES_B; palette_entry().
- osconst.6502inc: OSBYTE_AUTO_REPEAT_PERIOD (&0C), OSBYTE_WAIT_VSYNC
  (&13), OSBYTE_ACKNOWLEDGE_ESCAPE (&7E), OSBYTE_OPT (&8B),
  OSBYTE_KEYBOARD_STATUS (&CA), OSBYTE_BELL_DURATION (&D6),
  OSBYTE_SOFT_KEY_BASE (&E1), OSFILE_SAVE, OSFILE_LOAD, CURSOR_KEYS_EDIT and
  CURSOR_KEYS_SOFT (*FX4 0 and 2), ESC, DEL, the VDU codes (VDU_COLOUR,
  VDU_PALETTE, VDU_MODE, VDU_TAB, VDU_CLS, VDU_RESET_WINDOWS,
  VDU_TEXT_WINDOW, VDU_RIGHT, VDU_NOTHING), CRTC register numbers
  (CRTC_HORIZ_DISPLAYED, CRTC_HORIZ_SYNC, CRTC_CURSOR_START), and internal
  key numbers KEY_SHIFT, KEY_X, KEY_COLON, KEY_RETURN, KEY_DELETE, KEY_Z,
  KEY_SLASH (the Graphics Designer defines some of these locally as INKEY
  values instead).
- Designer-only, staying in levdes.6502inc: the screen geometry and
  `os_tab()`, the message box, `mode1_byte()`, the soft key codes,
  CURSOR_NONE/CURSOR_BLINK, DEVELOPERS_LINKS, ERROR_ESCAPE_KEY.
- In wdata.6502inc: WINDOW_HEIGHT, MESSAGE_END, HIGHLIGHT, and the menu
  items the designer acts on (I_*, with `item_line()`).
- In hidden_levdes.6502: MOVE_LEFT/UP/RIGHT/DOWN, the cursor's own
  directions (0 left, 1 up, 2 right, 3 down: clockwise, so EOR 2 reverses),
  deliberately not DIRECTION_*, whose order differs.

## 2026-10-03 23:25 — A 12-character filename: DFS says "Bad name", not nothing

- The failure isn't silent. Save level to ":0.$.ABCDEFG" puts "Error 204
  has occurred !", "Bad name" and "Press any key..." in the message box,
  and nothing is written: the disc jsbeeb holds afterwards is byte for byte
  the original (catalogue cycle still &20). The earlier note saw only the
  catalogue, and the journal's "silently" followed it. Probably that run
  typed the name with beeb.mjs's `type`, which presses Return itself, and
  then `key Enter`: the second Return dismisses the error at once, leaving
  the map (tried; the screen after is just the map).
- Why: OSFILE gets ":0.$.ABCDEFG0", &1E, &A1, &25... (`hex 1E30 16` after
  the save: `3a 30 2e 24 2e 41 .. 47 30 1e a1 25`). DFS 1.2 parses the name
  from &A070, each character read through GSREAD by &A0C9. After the drive
  and directory, the loop at &A0BA keeps up to seven characters of the
  leaf; the eighth, the "0", goes from &A0C7 (`CPX #7`, `BEQ`) to &A0A5,
  `JSR &9FAE`, DFS's "Bad " errors, here &CC "name". A trace of the save
  runs &A0C7 and &A0A5 once each, then the BRK in page 1 (where DFS builds
  its errors), then `brk_handler` (&1196) once. The &1E is never reached.
- So the outcome goes where every error goes: `brk_handler` undoes
  `level_file`'s text window and SEI (`level_file_done`) and shows the number
  and DFS's text until a key (`wait_for_key` flushes typed-ahead keys
  first). Output isn't off around OSFILE; `level_file` only opens the
  one-line text window M_FILING_WINDOW for the filing system's messages.
- 13 characters: OSWORD 0 (`input_max_length` 12) refuses the 13th, so
  ":0.$.ABCDEFGH" leaves ":0.$.ABCDEFG" and a Return at &40-&4C and fails
  the same way.
- 11 characters, and shorter names with prefixes, save where they say:
  ":0.$.ABCDEF", "$.ABCDEFG" and ":0.B.XYZ" were all catalogued with load
  &25A1, exec &8380, length &A5F. A 12-character line whose name ends early
  works too: "AB CDEFGHIJK" saved $.AB, since GSREAD stops at the space.
- Every legal 12-character name fails: 12 is the most a drive, a directory
  and a seven-character leaf make, so the leaf always gains the "0". (DFS
  1.2 does take a directory prefix twice: in ":0.$.$.ABCDE" the leaf can
  take the "0", and then the MOS's GSREAD refuses the &1E as "Bad string",
  error 253. Tried from BASIC with the same bytes, not in the designer.)
- Load level overruns the same way (it uses `ask_filename` too), but only
  after asking for the code, by when `loading` is set, so `brk_handler`
  replaces the level being edited with a new one, as for any failed load.
  With LEVEL1 loaded (code 677636), Load ":0.$.ABCDEFG" showed Bad name and
  then a blank map; LEVEL1's code bytes at &26E1 (CD DC 9C) were gone.
- Nothing else overruns: `input_number` (3 digits) and `input_editing_code`
  (6) read into `input_buffer` (16 bytes at &40) and use it there; only
  `ask_filename` copies the line, into the 12-byte `filename`.
- Correction to the first section: the OSFILE control block is
  `osfile_block`, &1E3C; &1E4E is `osfile_template`, copied into it before
  each call.
- Saving onto the PIPELINE disc itself: DFS puts a new file after the last
  catalogued one, the LEVDES stub at &113, so the first level saved lands
  at &114-&11E, just short of H.GAME (&122), and the second at &11F-&129,
  over H.GAME's first eight sectors (the four saves above changed sectors
  &114-&13F). The designer asks for the PIPELINE disc back when it exits,
  so levels were meant for a disc of their own.

How, from the repository root. `<AGAIN>` stands for the steps from the map
to the Save level filename prompt, `key F2; wait 1; key ArrowDown 10; wait
1; key Enter; wait 1; key KeyY; wait 1`, and `<SAVE>` for booting into the
designer first, `wait 33; key Digit4; key Enter; wait 15; key Space; wait
2; <AGAIN>`. `type` presses Return after its text. The `ssd` command (new
in beeb.mjs) writes the disc as it stands.

```
node tools/beeb.mjs '<SAVE>; trace t12.json; type :0.$.ABCDEFG; shot err12.png; hex 1E30 16; ssd save12.ssd'
node tools/beeb.mjs '<SAVE>; type :0.$.ABCDEFG; key Enter; wait 1; shot dismissed.png'
node tools/beeb.mjs '<SAVE>; type :0.$.ABCDEFGH; wait 1; hex 40 16; shot err13.png'
node tools/beeb.mjs '<SAVE>; type :0.$.ABCDEF; wait 3; <AGAIN>; type $.ABCDEFG; wait 3; <AGAIN>; type :0.B.XYZ; wait 3; <AGAIN>; type AB CDEFGHIJK; wait 3; ssd saves.ssd'
node tools/beeb.mjs 'wait 33; key Digit4; key Enter; wait 15; key Space; wait 2; key F2; wait 1; key Enter; wait 1; key KeyY; wait 1; type LEVEL1; wait 1; type 677636; wait 4; hex 26E0 8; key F2; wait 1; key Enter; wait 1; key KeyY; wait 1; type :0.$.ABCDEFG; wait 1; type 677636; wait 2; shot loaderr.png; key Space; wait 2; shot blank.png; hex 26E0 8'
node tools/beeb.mjs --boot no 'type DIM B% 40, N% 40:!B%=N%:B%!2=&25A1:B%!6=&8380:B%!10=&25A1:B%!14=&3000; type $N%=":0.$.ABCDEFG0":N%?13=&1E:N%?14=&A1:A%=0:X%=B%:Y%=B% DIV 256:CALL &FFDD; type PRINT ERR; type $N%=":0.$.$.ABCDE0":N%?13=&1E:N%?14=&A1:A%=0:X%=B%:Y%=B% DIV 256:CALL &FFDD; type PRINT ERR; out'
python3 -c 'import sys; sys.path.insert(0, "tools"); from dfs import read_catalogue; c = read_catalogue(open("save12.ssd", "rb").read()); print(c.cycle, [(e.full_name, hex(e.start)) for e in c.entries])'
```

The DFS addresses come from a linear disassembly of
`node_modules/jsbeeb/public/roms/b/DFS-1.2.rom` (mapped at &8000), checked
against the save's trace.
