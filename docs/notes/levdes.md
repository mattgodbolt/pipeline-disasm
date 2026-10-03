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
