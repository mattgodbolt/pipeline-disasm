# Notes: the game (H.GAME) and its data (IO)

Times are US Central.

## 2026-10-03 18:16 — How H.GAME starts, and where it lives

- The GAME stub reads the hidden run to &3000 and jumps there. The code at
  &3000 is a loader: it copies the ten key codes MENU left at &50-&59 into
  &29-&32 (as they are) and &66-&6F (reordered), then copies itself into
  place with a block-copy routine that reads its source, destination and
  length from the six bytes after each `JSR` (an inline-data call):
  - &0D9F-&0DFF (the OS's extended vector table) to &037F, saved because
    the game is about to overwrite page &0D;
  - &3100-&315F to &0131: an event handler, in the stack page;
  - &3160-&31DF to &0880: two tunes and four sound envelopes;
  - &3200-&35FF to &0400: map-view patterns and the scrolling code;
  - &3600-&50AC to &0900-&23AC: the game.
  It then does MODE 5, turns the cursor off, points EVNTV at &0131, sets
  the screen wrap-around to 8K with the addressable latch, and jumps to
  &12A3. The game proper never returns to &3000, which IO then overwrites.
- &3000-&30FF's last bytes and &31E0-&31FF are zeros; &50AD-&50FF is
  leftover (it looks like the tail of some graphics) and is never copied.
- The game screen is an 8K hardware-scrolled MODE 5 screen at &6000-&7FFF:
  32 character cells across and down (the CRTC is reprogrammed from a table
  at &0978), 128 x 256 pixels. The code wraps every screen address with
  `AND #&1F : ORA #&60` on the high byte.
- &12A3-&12C2 is one-time initialisation (BRKV, scores, loading IO) that
  is then overwritten: it doubles as the table of the level's 8 objects, 4
  bytes each, copied there at the start of each level. The loader jumps to
  &12A3, whose `EOR #&48` is just the first table bytes' original contents.
- Loading IO (&222E): the game swaps &0D00-&1CFF with &6000-&6FFF (the
  screen) so that the DFS gets its workspace back, puts an RTI at &0D00
  (the NMI handler), restores the extended vectors from &037F, re-claims
  the DFS's workspace with service calls (OSBYTE &8F 1 and 2), does `*DISK`,
  loads `:0.$.IO` with OSFILE (VDU 21 around it), then swaps back. The title
  screen's `L` key does the same for another file name, so a player can
  load their own mission.

## 2026-10-03 18:16 — Keys

MENU's defaults, as negative INKEY numbers, and what the game does with them
(MENU's redefine screen still has GUILDMASTER's action names, and they fit):

| &50+ | INKEY | key | GUILDMASTER | PIPELINE |
|---|---|---|---|---|
| 0 | -98 | Z | move west | left |
| 1 | -67 | X | move east | right |
| 2 | -73 | : | move north | up |
| 3 | -105 | / | move south | down |
| 4 | -56 | P | pick up | pick up the object in front |
| 5 | -51 | D | drop | drop the selected object |
| 6 | -74 | Return | use | use the selected object |
| 7 | -36 | T | throw | throw the selected object |
| 8 | -2 | CTRL | view backpack | backpack/status screen |
| 9 | -102 | M | view map | map (only on early levels) |

- Each level copies the four direction keys from &29-&2C to &6C-&6F, because
  a trigger action can swap them (left/right and up/down) for the rest of
  the level.
- The action keys are tested in the order Return, T, CTRL, M, D, P and the
  directions after, through a jump table at &2351 indexed by action number.
- Title screen: `S` steps the starting level (up to the furthest level
  reached without losing a life), Space starts, `L` asks for a mission file
  name. In the game, Escape loses a life and SHIFT+Escape ends the game.
- Backpack screen (CTRL): Z and X move the backpack selection, S toggles
  sound effects, T toggles the tune, M opens the map, Space returns.
- Map screen (M): Z and X scroll it, Space returns.

## 2026-10-03 18:16 — IO, the mission file

IO is exactly what MISSION's PROCsavemss writes: `names` (&134), `miss`
(30), `attrs` (5), `numlev` (4) levels of `size` (&91F), and `grfs`
(&E00), loaded at &5800 minus the total, &242D. src/io.6502inc gives the
addresses from those sizes.

- Names block (&242D): a 128-byte picture (a red barrel, drawn for a map
  cell that says "object here" when no object is there), then 15 object
  names of 12 characters. The Graphics Designer keeps this block with the
  graphics: DEFAULT is IO's graphics followed by this block, byte for byte.
- Mission text (&2561): two halves, each a VDU 31 TAB and 12 characters with
  spaces as 9 (cursor right) so the backpack screen's background shows.
- Attributes (&257F): the clock's rate, the number of levels the map works
  on, the backpack's size less one, the throwing distance, and a lock flag
  (negative: finishing the mission shows a competition entry code; MISSION
  sets it with a secret key, `h` or `i` at its menu).
- Level fields (&2584): eleven fields of 1, 1, 1, 4, 8, 32, 16, 32, 64, 64
  and 64 bytes per level, each stored as four consecutive copies (so a
  field's level n is at field + n * size): the level's edit code (3 bytes,
  printed when a level is finished), its palette, its setup (start x and
  y, things to collect, time, exit x and y, the cell monsters eat and what
  they leave, which cells animate), 8 objects (x, y, icon, uses and flags),
  4 monsters (x, y in quarter cells, direction, turning preferences), and
  32 triggers (a flags byte whose low nibble is the action, a place, and 4
  bytes of arguments, split over the last two fields).
- Maps (&2A00): 64 x 64 cells of 4 bits, a column at a time (column x is
  32 bytes at x * 32; even rows in the high nibble). The game copies the
  current level's to &5800 and plays on that copy.
- Graphics (&4A00): 28 pictures of 128 bytes, each 4 x 4 MODE 5 character
  cells stored a column at a time: one per map cell type (0-15), then 16
  object icons of 32 bytes (2 x 2 cells; icon 15 is the exit), the player
  facing left, right, up and down, and second animation frames for cells 5,
  7, 8 and A. Outside the map is drawn as cell A's second frame, lava.
- Cell types seen so far: 0 floor, 7 the "sulphur" to collect, A lava
  (deadly, also what's off the map), E deadly, F an object (looked up in
  the object table by position); monsters are drawn with pictures E and F.

## 2026-10-03 18:44 — How the game plays (from the code)

Corrections first: the "second animation frames" above are really second
pictures, chosen once per level on a checkerboard (`alternate_cells`, the
level's last setup byte: two bits per cell type 5, 7, 8 and A, for even and
odd squares); nothing animates over time except the monsters (pictures E and
F alternate) and the player (flipped upside down every other step; walking up
or down also alternates the third and fourth player pictures). The player
pictures are left, right, then two for up/down.

- The view is 8 x 8 map cells; a map cell is 4 x 4 character cells. The
  player sits in the middle and the view scrolls a character at a time, four
  per step, with the hardware (CRTC start address) and the newly exposed
  row or column drawn from the map. Everything else that moves (monsters, a
  thrown object) moves a character at a time too, as clipped sprites.
- Goal: step on every cell 7 ("Collect the Sulphur!": the level's setup says
  how many), then press P facing the exit (an object cell showing icon 15):
  the exit turns to fire (cell E), the time left is scored, and the player
  has 4 clock ticks to get 5 or more cells away across or down. Caught, they
  lose a life but the level still counts. WELL DONE! and 100 points, then
  the finished level's edit code (MISSION asks for it before saving an
  edited level).
- Cells: 0 floor; 1-5, 8, 9 walls (8 is also what the exit counts as); 6 a
  crate, pushable while the player has pushes (a trigger gives them); 7 the
  thing to collect; A lava and E fire kill; B, C, D pipes: stepping into a
  C (moving across) or D (moving up/down) carries the player along, hidden,
  turning at junctions (B) and reversing at dead ends, until they come out
  onto the floor. F holds an object; off the map is lava.
- Monsters (4 a level) are flames that wander by a turning preference (four
  2-bit choices: back, straight, clockwise, anticlockwise), marking their
  cell as fire. Each has a food cell type (the level's setup): a monster that
  reaches it turns it into another type and goes out, for 25 points; so does
  one whose fire cell is changed under it.
- Objects (8 a level, 15 kinds named in IO): pick up (P), drop (D), throw (T,
  up to the mission's distance) and use (Return); the backpack holds the
  mission's backpack size. Each object has a number of uses (bits 0-5; 32
  and up never run out), bit 6 (vanishes when used up) and bit 7 (does
  nothing thrown). Using or landing a thrown object tries its four triggers:
  n, n + 8, n + 16 and n + 24.
- Triggers (32 a level): a flags byte (bits 0-3 the action; bit 4 can fire
  again, bit 5 fired already, bit 6 only once everything's collected, bit 7
  needs an object rather than being walked onto), a place (x, y; negative
  for anywhere on that axis) and four arguments: three for the action and a
  condition (bit 7: facing direction bits 4-5; bit 6: facing cell type bits
  0-3). Actions: 0 set a cell, 1 move a cell, 2 set the cell in front, 3 set
  the clock and the number to collect, 4 throw an object, 5 blow an object
  up (in the backpack it kills), 6 set a monster's direction (8 removes it),
  7 move a monster, 8 teleport, 9 toggle the cell in front between two
  types, 10 enable and 11 disable triggers, 12 recharge an object, 13 give
  pushes, 14 push the cell in front, 15 swap the direction keys (left/right,
  up/down) for the rest of the level.
- Scoring: a point per cell 7 and per clock tick left when the exit is lit,
  25 per monster gone, 100 a level. The score is BCD.
- Codes: after each level, its edit code (the three io_edit_code bytes,
  scrambled); after the last level of a locked mission played from level 1,
  an entry code made from the score and a checksum of all the mission's level
  data, printed in a base-32 alphabet (1-9, A-W): the competition entry.
- Escape loses a life, SHIFT+Escape the game. Losing all lives: the player
  burns up in spreading flames.
- The title tune is played by the sound event handler: each time channel 1
  or 2's queue empties, the next note of its voice is queued (two voices of
  32 notes in the printer buffer; the envelopes are poked straight into the
  OS's envelope store at &08C0). Each time round it transposes or swaps the
  voices.

## 2026-10-03 18:44 — Memory while playing

| Address | What |
|---|---|
| &00-&9B | zero page: monsters &00-&0F, thrown object &10-&14, player and game state, sound blocks &30-&3F, tune &40-&44, scratch &50-&55, level setup copy &56-&5D, keys &66-&6F, drawing &70-&9B (see the game's symbols) |
| &0100-&011F | trigger flags (this level's, copied from IO) |
| &0120-&0124 | direction keys held last time; a scratch byte |
| &0131-&0190 | the sound event handler |
| &037F-&03DF | the OS's extended vectors, saved while the game uses page &0D |
| &0400-&07FF | map view patterns; drawing and scrolling code |
| &0880-&08BF | the tune (in the printer buffer) |
| &08C0-&08FF | the four envelopes (the OS's envelope store) |
| &0900-&236C | the game (&0D00-&1CFF is swapped with &6000 while IO loads) |
| &12A3-&12C2 | this level's 8 objects, over run-once start-up code |
| &236D-&242C | trigger places and arguments (over the end of the game) |
| &242D-&57FF | IO, the mission |
| &5800-&5FFF | the current level's map, copied from IO, changed by play |
| &6000-&7FFF | the screen: MODE 5, 32 x 32 characters, 8K with wrap-around |

The OS's DFS workspace (&0E00-&10FF), NMI area and extended vectors are
overwritten by the game; load_mission puts things right for long enough to
load IO and swaps the game back. TITLE (&6300-&7979) is long gone by then.

## 2026-10-03 18:44 — For the other pieces

- `src/io.6502inc` has IO's layout from MISSION's formulas, the meaning of
  each field, and names for the cell types (CELL_*). LEVEL1 (a Level
  Designer file, 320 bytes of puzzle names then one level's &91F bytes: the
  same eleven fields un-interleaved, then the map) and DEFAULT (the Graphics
  Designer's file: IO's graphics block then its names block) share these
  formats; io.6502's PICTURE and MAP macros would turn them into readable
  source too.
- OS names H.GAME defines locally that belong in os.6502inc: EXTENDED_VECTORS
  (&0D9F), NMI_HANDLER (&0D00), VSYNC_COUNTER (&0240), ESCAPE_FLAG (&FF),
  ERROR_POINTER (&FD).

## 2026-10-03 18:50 — How H.GAME's source is made, and tools

- `src/hidden_game.6502` is generated: `python3 tools/dis6502seg.py
  hints/hidden_game.toml > src/hidden_game.6502` (after `make`, since it
  reads the binary the build makes; data/hidden_game.bin is gone). The
  hints carry everything: the relocated segments, the inline-data calls,
  jump tables, names (labels, zero page, IO addresses), routine comments,
  end-of-line remarks, operand expressions and hand-written source for
  data tables, split by area under hints/hidden_game/. Edit those and
  regenerate; annotations at addresses that aren't the start of a line are
  reported. This departs from "run the disassembler once, then edit by
  hand": the alternative is to freeze the generated file and edit it from
  now on, which also works.
- The static trace finds all the code; gameplay traces (title, start-level
  select, backpack and map screens, deaths, lighting the exit, using an
  object at a trigger) found nothing more. Entry points it can't see: the
  event handler (EVNTV), the error handler (BRKV), restore_floor_picture
  (an RTS to a pushed address), throw_trigger (a self-modified JMP), and
  three bits of code nothing uses (&0C60, &113B, the JMP at &1C88).
- Quirks worth knowing: the print routine takes its text inline after the
  JSR up to a NOP, which then runs; the loader's copy routine takes six
  bytes inline; `BIT bit4_mask` / `BIT bit6_mask` test bits against the
  operand bytes of other instructions (&10 and &40); the objects table is
  laid over run-once code; trigger places and arguments overwrite the end of
  the game's own code; the trigger action and the object-trigger checker are
  reached through self-modified JSR/JMPs.
- `tools/play.mjs` plays the game headless: `game` gets from boot to &3000
  (menu option 1, Return), `bkey NAME` presses BBC keys by matrix position
  (Z, X, COLON_STAR, SLASH, P, D, RETURN, T, CTRL, M, SPACE, S...),
  `random SECS` wanders, `poke`/`peek`, `save`/`restore` snapshots, `shots`.
  On the title screen wait about 6 seconds before pressing keys (the
  keyboard buffer is flushed late), and after Space about 8 for the level
  to draw. `tools/traceranges.py` summarises a trace's executed ranges.
- Handy pokes: the level's setup is at io_level_setup (&25A0 for level 1):
  poking the start position there before Space puts the player anywhere;
  &58 is the number left to collect, &59 the clock, &24-&27 the backpack.
