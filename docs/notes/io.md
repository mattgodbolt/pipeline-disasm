# IO, DEFAULT and the levels: one description each

Notes from making the disc's repeated data come from one description. Times
are US Central.

## 2026-10-03 19:30 — What's shared now

The disc holds the same data more than once: DEFAULT is IO's graphics and
names, and LEVEL1 is IO's first level. The sources described each copy
separately, in different notations. Now:

| Description | What | Made into |
|---|---|---|
| `src/default.6502inc` | the default graphics set: 41 pictures (two characters a pixel) and 15 object names, as data | DEFAULT (`default_graphics()` then `default_names()`), IO (the names first, the graphics last) |
| `src/level1.6502inc` | level 1, with its trigger names | LEVEL1 (`level_names_bytes`, `level_fields`, `level_map_bytes`), IO's level 1 |
| `src/level2.6502inc`-`level4.6502inc` | IO's other three levels, written the same way | IO's levels 2-4 |
| `src/leveldata.6502inc` | the level format: MISSION's 11 field sizes, the names for values (CELL_*, LEVEL_*, OBJECT_*, PUZZLE_*, PATTERN_*, DIRECTION_*, COLOUR_*), the map key, and the FUNCTIONs that turn a level into bytes | included by `level.6502inc` and `io.6502inc` |

`src/io.6502` now holds nothing of its own but the attributes and the
mission's name, and reads as MISSION builds it (PROCsavemss): the graphics
file's names, the mission name, the attributes, the four levels' fields
interleaved (`FLATTEN(ZIP(level_fields(level_1), ...))`, MISSION's
`L% + numlev*pnt + S%*ext`), the four maps, then the graphics.
`io.6502inc` and `level.6502inc` work out IO's and the designer's field
addresses from `LEVEL_FIELD_SIZES` (MISSION's DATA 2090) and its running
totals (`LEVEL_FIELD_OFFSETS`, MISSION's `pnt`) rather than listing them.

## 2026-10-03 19:30 — The notations chosen

- Pictures: two characters a pixel, IO's notation, so a picture looks in the
  source as it does on the screen (a MODE 5 pixel is twice as wide as tall).
  Each picture's comment gives its slot (the Graphics Designer's number), its
  part in the game and what it looks like, merging the two sets of comments.
  `sprites.6502inc`'s `SPRITE_COLUMNS` and `SCREEN_PICTURE` (the Graphics
  Designer's own pictures) still take one character a pixel.
- A level is one list of its parts: the editing code as six digits, the
  palette as `COLOUR_*` names, the setup (the player's own start cell, not
  the view's), a row per object, monster (in cells, `DIRECTION_*`,
  `PATTERN_*`) and trigger, and the map as 64 strings. A trigger row is
  `{name, PUZZLE_* action + flags, x, y, A, X, Y, condition}`, so everything
  about a trigger is together, with a comment saying what it does in the
  game's terms. Triggers are numbered 0-31, as the game counts them (object
  n fires n, n + 8, n + 16 and n + 24); the designer shows them one more.
- The map key says what the game makes of each cell, not what the Level
  Designer calls it (its names are TILE_* and don't fit: its "fatal trap" is
  a crate, "crate" a wall, "wall 2" lava, "S.monster" a pipe junction,
  "barricade" fire and "junction" an object): `.` floor, `r 7 L J` walls
  filling a corner, `#` and `=` walls, `@` the marker wall triggers look for,
  `c` crate, `o` sulphur, `~` lava, `+ - |` pipes, `*` fire, `$` an object.
- Levels 2-4 have no trigger names: a mission doesn't keep them (MISSION
  names them "Puzzle 1" on when it saves a level file), so their names are
  "" and `level_names_bytes` refuses them.
- The mission's name is written as its text, `mission_name_half(18, 16,
  "Collect the ")`, spaces becoming 9 (cursor right) as MISSION stores them.

## 2026-10-03 19:30 — Other copies on the disc

- IO's slack (the rest of its last sector, in `src/disc.toml`) is the first
  45 bytes of slot &28's picture, DEFAULT's &E00-&E2C: MISSION loads the
  graphics file at G%, the mission's last &E00 bytes, so the file's names
  run on past the mission's end and are still in memory when it saves.
  `disc.toml` holds them as hex; they could come from `default.6502inc` if
  mkssd took slack from a built file.
- Otherwise nothing of IO, DEFAULT or LEVEL1 appears anywhere else on the
  disc (searched 12- and 16-byte runs): the mission text is only in IO, and
  H.GAME's leftover graphics at &3000 aren't these.

## 2026-10-03 19:30 — Levels, read in the game's terms

Writing the levels' comments from the game's code (`trigger_action`) turned
up:

- Action 14 (push the cell in front) takes A as a row of the game's `turns`
  table plus the way the player faces: 0 back, 4 on, 8 clockwise, 12
  anticlockwise, which is what the designer stores (its choice times 4).
  Level 1's trigger 15 has &02, which the designer would show as backwards
  but the game turns anticlockwise (2 + facing happens to land on the
  anticlockwise entries for every facing).
- Action 1 (move a cell) takes the designer's eight compass directions, and
  the game's `direction_dx`/`direction_dy` do go diagonally (4-7).
- Unused argument bytes keep whatever the designer left there (level 3's
  trigger 1 teleports with A = &FF; conditions keep direction or cell bits
  whose check bit is clear), so the arguments stay hex.
- The setup's last byte is two bits a cell type for 5, 8, 7 and A (5 at the
  top): bit 1 shows its second picture on even squares, bit 0 on odd.

## 2026-10-03 19:30 — Baron and the symbol dump

| File | Before | After |
|---|---|---|
| default.6502 | 11,411 entries, 416 KB | 109, 139 KB |
| io.6502 | 522, 341 KB | 316, 236 KB |
| level1.6502 | 6,508, 192 KB | 145, 34 KB |
| build/symbols.json | 1.44 MB | 0.83 MB |

- `mode5_pictures` converts a whole list of same-sized pictures with list
  operations (gather the four pixels of every byte from the rows run
  together as one string), so a picture group is one FUNCTION frame rather
  than a FOR iteration per byte. What's left in the dump is mostly the data
  itself, once as the named symbol and again as frame parameters and locals:
  baron keeps every FUNCTION frame's parameters and locals, so large locals
  cost as much as the data.
- A FUNCTION called inside a MACRO appears in the dump twice (under two
  scope numbers), so the emitters are FUNCTIONs called at the top level
  (`EQUB default_graphics()`) rather than macros.
- A MACRO whose body calls a FUNCTION leaves null-valued `@` entries in the
  dump of every file that includes it, even if the macro is never used. So
  `EDITING_CODE` stays in `level.6502inc` (the designer's) rather than the
  format the game includes.
- Expressions can only span lines inside braces, not parentheses; long
  expressions are wrapped in a list (`FLATTEN({...})`, `SUM({...}, 0)`) or
  given named steps.
- `1..2..` is every element from 1, not every other one (the second element
  sets the step): every other from 1 is `1..3..`.

## For other pieces (a later pass)

- `tools/graphics.py asm` still writes DEFAULT's old notation
  (`LARGE_SPRITE`/`SMALL_SPRITE`/`OBJECT_NAME`, one character a pixel),
  which `sprites.6502inc` no longer has; it should write
  `default.6502inc`'s.
- `hidden_graphic.6502`'s pictures (`SPRITE_COLUMNS`, `SCREEN_PICTURE`) are
  one character a pixel; `mode5_pictures` would take them two a pixel with
  far fewer dump entries.
- `hidden_levdes.6502`'s `default_header` could be written with the level
  notation's names (COLOUR_*, CELL_*), and its TILE_* comparisons sit
  alongside CELL_* now that both are visible.
- `src/disc.toml`'s IO slack is DEFAULT's &E00-&E2C (above).
- CLAUDE.md's pieces table should point DEFAULT, LEVEL1 and IO at
  `default.6502inc`, `leveldata.6502inc` and `level1.6502inc`-`level4.6502inc`.
