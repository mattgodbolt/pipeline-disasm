# Notes: one definition per shared name

Times are US Central.

## 2026-10-03 20:21 — Where the shared names went, and why

Each program had grown its own copies of the machine's names and of the
data formats' (KEY_SHIFT, VDU_MODE, OSFILE_LOAD and CRTC_CURSOR_START three
times each; the 12-character object name under three names). Each now has
one home; CLAUDE.md's "Where names live" lists them.

- **os.6502inc** (addresses, which tools/dis6502.py names operands from):
  gained `MOS_ENVELOPES` (&08C0) from the game.
- **osconst.6502inc** (the machine's other numbers): every OSBYTE, OSWORD,
  OSFILE, OSFIND, OSGBPB, OSARGS and FSCV number the game and both designers
  used; *FX settings (`CURSOR_KEYS_EDIT`/`CODES`/`SOFT`,
  `FUNCTION_KEYS_STRINGS`); service calls; SOUND channel flags
  (`SOUND_FLUSH`, `SOUND_SYNC_1`, `CHANNEL_NOISE`); buffers and events; one
  sorted table of internal key numbers; `KEYCODE_LEFT`... (*FX4,1's cursor
  codes); `BEL`, `CR`, `ESC`, `DEL`, `ctrl()` (printable characters are `'A'`
  literals); the VDU and PLOT
  codes (including basic.6502inc's three); CRTC registers and cursor
  settings; the screen latch value `SCREEN_WRAP_8K`; screen memory
  (`MODE1_SCREEN`, `MODE5_SCREEN`, their row and character sizes,
  `SCREEN_MEMORY_END`); 6502 opcodes. !BOOT, MISSION, WDATA, SCREEN and IO
  now include it.
- **sprites.6502inc**: the graphics set's format, from the Graphics
  Designer's own include (deleted): sizes, `SET_*`, `SET_LOAD_ADDRESS`,
  slots, `SLOT_*`, `OBJECT_KINDS`, `OBJECT_NAME_LENGTH`, `EXIT_ICON`.
  io.6502inc includes it, and puts IO's graphics offsets in its terms.
- **leveldata.6502inc**: the level format: the cell types only the designer
  named (`CELL_SE_CURVE`... `CELL_WALL_1`, `CELL_BARRICADE`), the diagonal
  directions, `MONSTER_GONE`, `TURN_*`, positions (`COORDINATE_BITS`,
  `POSITION_FLAGS`), `OBJECT_CHARGES`, `OBJECT_BYTES`, `MONSTER_BYTES`,
  `LEVEL_SETUP_BYTES`, `PUZZLE_ACTION`, `PUZZLE_NAME_LENGTH`/`HEAD`,
  `CONDITION_*`, `SET_LEVELS_KEEP_*`, `ALTERNATE_*`, `palette_entry()`.
  PL now reads its level file through level.6502inc rather than its own
  addresses.

Naming decisions, where programs disagreed:

- `CONDITION_DIRECTION` was the flag (&80) to the game and the field (&30)
  to the Level Designer. Now the flags are `CONDITION_CHECK_DIRECTION` and
  `CONDITION_CHECK_CELL`, the fields `CONDITION_DIRECTION` and
  `CONDITION_CELL` ("cell", the shared CELL_* word, not the designer's
  "block").
- `TURN_*`: the game had 0/4/8/12 (offsets into its turns table), the
  designer 0-3 (`TURN_FORWARDS`, `TURN_RIGHT`, `TURN_LEFT`, unused). The
  format's values are 0-3, with the game's clearer names (`TURN_AHEAD`,
  `TURN_CLOCKWISE`, `TURN_ANTICLOCKWISE`); the game multiplies by its own
  `TURN_ROW`. The monster `PATTERN_*` are now written in `TURN_*`s.
- `MONSTER_GONE` (the game's) over the designer's `MONSTER_DEAD`.
- `PUZZLE_ACTION` over the game's `TRIGGER_ACTION` and the designer's
  `PUZZLE_TYPE` (PL already said `PUZZLE_ACTION`).
- `OBJECT_NAME_LENGTH` over `IO_NAME_LENGTH` and `DEFAULT_NAME_LENGTH`;
  `OBJECT_KINDS` over the Graphics Designer's `OBJECT_NAMES`. The level's
  `NAME_LENGTH`, ambiguous next to it, became `PUZZLE_NAME_LENGTH`.
- `ALTERNATE_NONE`/`ODD`/`EVEN`/`ALL` for the designer's `SPRITES_A`/`ODD`/
  `EVEN`/`B`: the game calls second pictures alternates, and "Sprite A"
  means something only in the designer's menu.
- The game's CRTC names (`CRTC_HORIZONTAL_DISPLAYED`, `CRTC_HSYNC_POSITION`)
  over the designer's abbreviations; `CRTC_CURSOR_OFF` over `CURSOR_NONE`.
- `KEYCODE_*` (the Level Designer's prefix) for the codes keys give, so the
  Graphics Designer's `CODE_LEFT` and `CODE_F0` became `KEYCODE_LEFT` and
  `KEYCODE_F0`; `OSBYTE_FUNCTION_KEY_BASE` over `OSBYTE_SOFT_KEY_BASE`.
- Screen memory is in osconst.6502inc though it's addresses: in
  os.6502inc the disassembler would name every &3000 and &5800 operand as
  the screen. Mode 7's stays in teletext.6502inc with the rest of Mode 7.

Kept apart on purpose:

- The Level Designer's `MOVE_*` (clockwise from left, so EOR 2 turns
  about) aren't `DIRECTION_*` (left, right, up, down); its comment says so.
- The game's `DIRECTION_NONE` is 8 like `MONSTER_GONE` but indexes its
  step tables; `MONSTER_STUCK` and `OBJECT_USES` (charges plus
  OBJECT_NO_CHARGES, as the game reads them) are the game's readings.
- `KEYCODE_F0` is &80 in the Level Designer and &E0 in the Graphics
  Designer, and the Level Designer's `KEYCODE_CURSOR_UP`/`DOWN` are *FX4,2's
  function keys: each program sets *FX225 and *FX4 its own way.
- Each program's own screen (`SCREEN`, `SCREEN_COLUMNS`, `SCREEN_END`...)
  stays its own; only the modes' facts are shared.
- The game's load address appears as the GAME stub's `hidden_load`, PL's
  `GAME_START` and H.GAME's org: an inter-piece entry point, not part of
  these families, left as it was. MENU's key order (`MENU_KEY_*`) is the
  game's only, since MENU is BASIC text.

Found on the way:

- Baron lets a scope define a name the file has outside it, and the inner
  one silently wins; game.6502inc (inside `game`) could have kept stale
  copies forever. tests/test_symbols.py now fails on any scoped name that
  repeats a file-level one. The only case was the Graphics Designer's
  `sprite_file_offset.io_graphics` label, hiding io.6502inc's
  `io_graphics` (now `in_io_graphics`).
- A file defining FUNCTIONs can be INCLUDEd only once per program
  ("Duplicate function arity"); constants may repeat with the same value.
  So default.6502inc no longer includes sprites.6502inc (io.6502 gets it
  from io.6502inc; default.6502 includes it itself).
- A MACRO calling a FUNCTION leaves null frames in every includer's dump.
  sprites.6502inc's unused `SPRITE_COLUMNS` and `SCREEN_PICTURE` went, and
  level.6502inc's `EDITING_CODE` and `MONSTER` moved into the Level
  Designer, their only user, before PL included level.6502inc.
- `build/symbols.json` went from 744,274 to 796,510 bytes (11,049 to
  13,124 entries): every file's dump lists every constant its includes
  define, and osconst.6502inc is in 15 of the 19. The `@` frames didn't grow
  (fewer in LEVEL1, DEFAULT and H.GRAPH).
