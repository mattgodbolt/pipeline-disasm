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

## 2026-10-03 19:52 — Reviewing H.GAME's source: corrections and findings

A reviewer's pass over every routine of `src/hidden_game.6502`, checking
the comments against the code, with the emulator where reading wasn't
enough (play.mjs pokes, peeks and screenshots; each check is noted).

Corrections to earlier claims (here and in the source's comments):

- The player is drawn upside down every four cells walked, not every other
  step: player_frame goes up &20 a cell (peeked: 00, 20, 40, 60, 80...) and
  bit 7 flips the picture. Facing up or down, a flipped player uses the
  other up/down picture.
- Scores are one more than they looked: add_points runs into add_point
  after its loop, so it adds X + 1. A monster put out or eaten scores 26
  (checked: removing one monster scored 26), a level 101 (checked: a poked
  1234 became 1335), and the time bonus is the time left plus one (257 if
  the clock reached 0 in the cycle the exit was lit). score_25 is now
  score_monster.
- The entry code is, in order: a digit of the checksum's running sum, the
  score's low byte (scrambled, EOR &AA, two characters), four of the
  checksum, one of the score mixed, then the high byte (EOR &55, two). The
  comments had the score's bytes swapped. Checked: score 1335 gives
  PW8CKNJGDA, and "W8" decodes from &35, "DA" from &13. It's shown in a box
  of background colour 2, rows of spaces above and below.
- The tune is not the title's: start_tune runs as a level starts (peeked:
  silent on the title screen). Each voice plays 30 of its 32 notes, and the
  variations go voice 1 alone, both, voice 1 alone a fourth up, both a
  fourth up, then the same with voice 2 alone. The sound effects use all
  four envelopes, not just 3 and 4.
- WELL DONE: each set bit is a speckled block in colours 2 and 3, and two
  pixels of colour 1 go in the cell to its right, so a shadow shows on the
  right of each run (screenshot). Not "the bottom half: a shadow".
- Caught by the blaze (time up, under 5 cells from the lit exit), the view
  is wiped to bare floor, not flashed (screenshot); then colour 0 flashes
  red and cyan as for any lost life.
- redraw_view fills with a diagonal hatch (&7F, &BF, &DF...), not stripes
  (screenshot).
- The map view draws each byte's low nibble, the odd row, first, in the
  lower four lines; the comments had the rows swapped.
- After a level, the edit code shown is the level just finished's
  (screenshot: 677636 after level 1), not the next one's.
- draw_title_screen is the title screen, also behind the filename prompt
  and error messages; the backpack screen uses draw_screen_frame alone.
- random mixes in the user VIA's timer 2 high byte, not two low bytes.
- The OSFILE block's top zeros don't mean "the I/O processor"; it's the
  execution address's low byte of 0 that makes OSFILE load at io_start.
- The CRTC values don't overlap alternate_pictures; setup_crtc reads
  exactly crtc_values.
- trigger_places is leftover data in the file, overwritten per level; four
  of its bytes had been drafted as the string "pp00".

Newly understood:

- Text goes through the OS, which still believes MODE 5 (peeked &350:
  `00 58 40 01`, screen at &5800, 320-byte rows), while the game shows
  256-byte rows from &6000. So TAB(x, y) lands at &5800 + 320y + 16x on the
  game's screen, and the game's odd-looking TABs are chosen for where that
  falls: TAB(7,15) and TAB(19,16) are columns 6 of rows 11 and 13, say.
  The source now writes `TEXT_AT column, row` (game.6502inc), which
  computes the TAB. The filename prompt's box is twelve DELETEs walked
  backwards from "<" at the right edge, wrapping from one OS row to the
  previous, which on the game's screen is one straight run (screenshot).
- A teleport moves where the level restarts: place_player stores its
  target as start_x and start_y. Checked: after a poked teleport and an
  Escape, the player came back at the teleport's destination.
- Action 6 with X = &10 ("all four monsters") is broken: only monster 3
  gets the direction asked for; set_monster_direction changes A, and the
  loop then passes each monster the previous X, so monsters 2 and 1 get 12
  and 8 (gone, 26 points each) and monster 0 gets 4, stuck going left,
  which it soon moves out of. Checked with a poked trigger. The shipped
  mission never asks for all four (its only action 6 is level 2's trigger
  6, for monster 0).
- action_explode reads the object's place with Y straight from the
  trigger's third argument: the Level Designer stores the object * 4 there
  ("+2 the same times 4"), and every shipped detonate trigger has it.
- action_recharge works on any object except the one landing, and
  re-enables trigger A, the object's own first trigger.
- An OBJECT_NO_THROW object can still be thrown; its triggers just aren't
  tried when it lands (the designer's "Throw:" flag).
- thrown_object is the object while it flies, + &80 only while its landing
  triggers run, then &FF; so "in flight" in find_carried (explode,
  recharge, launch) means "landing".
- A one-shot trigger is marked fired before its action runs, so one whose
  action can't happen (a blocked cell in front, say) is spent anyway.
- When something landing during a step's think stops the step
  (ACTION_STOP), move_done drops the pushed cell rather than play_cycle's
  return address, and the cycle goes on to think a second time.
- The on-foot check underfoot runs twice a turn, before the triggers
  (check_pipe_end) and after (check_underfoot); anything underfoot but
  floor or sulphur kills.
- The last sulphur's spin is four turns to a falling run of four notes,
  each run a semitone higher (pitch - &3F, wrapping).
- Never used, beside the known three: thing_picture's player-picture
  branch (nothing passes it &20 and up), and walk_up's last screen_high
  sum, which is overwritten before it's read.
- OSWORD returns with Z clear, which the backpack's tune toggle leans on
  (checked: T off and on again restarts the tune).
- The Level Designer's block names in `src/level.6502inc` (TILE_*) are
  mislabelled for 6, 8, 9, A, B, E and F. choose_from_window reads
  tile_menu_map both ways: the high nibble of entry n is block n's menu
  item, the low nibble is menu item n's block. Read so, menu item "Crate"
  is block 6, "Wall 2" 8, "Barricade" 9, "Fatal trap" A, "Junction" B,
  "S.Monster" E and "Marker" F, which is what the game does with them (it
  pushes 6, A kills, B is a pipe junction, E is a monster's fire), and the
  designer's graphics window order (wall one, wall two, collectable, fatal
  trap) is alternate_cells' 5, 8, 7, A. leveldata.6502inc's MAP_KEY note
  calls 9 the designer's marker; it's the barricade.

Source changes: `src/game.6502inc` holds the game's own names (screen
geometry, pictures, actions, MENU's key order, monster, object and trigger
masks, stages, sound, OS numbers not yet shared), INCLUDEd inside the
`.game` scope; leveldata.6502inc supplies the shared level names. Routine
headers are purpose, In:, Out:, Clobbers:. Renamed: player_steps to
steps_since_drawn, return_0AD0 to draw_player_at_done, unused_1260 to
burn_up_unused, the object_icon routine to object_icon_picture (object_icon
is now the field), map_key to map_screen, trigger_move_monster to
action_move_monster, score_25 to score_monster, return_from_caller to
drop_two_and_return, envelope_1 to envelopes. The WELL DONE bitmap is
drawn as rows of blocks, and ASSERTs pin what the code relies on (the
objects over game_start's 32 bytes, trigger data running up to io_start,
the swap's range, the BIT masks' operands).

## 2026-10-03 23:41 — Clipping sprites at the map's edges (&E2 and &F1)

clip_sprite_x and clip_sprite_y compared view_x and view_y with bare &E2
and &F1. They're now `VIEW_PAST_END` and `VIEW_BEFORE_START` in
game.6502inc, with `MAP_CHARS`, `VIEW_FIRST` and `VIEW_LAST`, and ASSERTs
that hold them inside the ranges below. Both values are exact for everything
on the map; the only thing that shows is in the game-over flames.

The views the game makes:

- Standing still, place_player puts the view half a cell into a map cell
  (`view_cell * 4 + 2`) with the player PLAYER_CHAR (14) characters in, so
  view_x = 4 * player_x - 14. Walking scrolls a character at a time through
  every value between.
- The player never leaves the map: `move` doesn't step into lava or fire (it
  kills where the player stands), and in a pipe `pipe_check_ahead` kills
  with lava ahead. Off the map reads as lava, so view_x runs from &F2 (the
  player in column 0) round through 0 to &EE (column 63), and &EF-&F1 never
  happen. The same goes for view_y. Level 1 starts at the right edge
  (view_x &EA).

What the three cases do (positions are bytes, 256 to the map):

- view_x below &E2: compared plainly, right edge view_x + 28 (+ 3). Right
  while view_x + 28 doesn't carry (to &E3) for anything at &FC or less.
- &E2 up to &F0: running off the right edge. Anything right of view_x is
  taken to be wholly in view, the right edge not checked; right once the
  view reaches the map's last column (from &E0). Anything left of view_x is
  clipped or dropped as usual, so the map's first columns don't show in the
  lava past its end.
- &F1 up: hanging off the left edge (view_x negative). No left check at all;
  the right edge is view_x + 31 - 256.

So &E2 could be anything from &E0 to &E4 (it's the middle, and the first
standing view whose last half cell is off the map: view cell 56), and &F1
anything from &EF to &F2 (it's one short of the leftmost view). Neither is
off by one.

How it was checked:

- A small 6502 interpreter (Python, not in the repo) ran draw_sprite from
  build/files/H.GAME, copied to its run-time address as the loader does, for
  every view_x the game makes and every X from 0 to &FC (Y in the middle),
  and the same down, comparing the screen bytes written with an exact clip
  of the view: all 64009 cases each way match. Patching the two CMP
  operands, the matches hold for &E0-&E4 and &EF-&F2 and fail outside: at
  &DF a sprite at &FC with view_x &DF puts a column at the view's left edge
  a row down; at &E5 a view_x of &E4 loses sprites from &E5 up; at &EE the
  view at &EE draws X 0-&D in the lava and loses &EB-&FC; at &F3 the view at
  &F2 loses X 0-&11 and draws &EF-&FC in the lava.
- The same in the game, with play.mjs (screenshots in build/shots/, not
  committed). A monster put at (0, 35) with level 1's start view at the
  right edge, its cell made fire and the monsters' food made 9 so it doesn't
  eat the lava off the map:

      node tools/play.mjs --disc build/pipeline.ssd 'game; wait 7; poke 2640 00 8C 01 39; poke 25A6 79; poke 2A11 8E; bkey SPACE; wait 9; shot build/shots/phantom-shipped.png'

  shows nothing past the map's edge; with `poke D1C EA` after `wait 7`
  (VIEW_BEFORE_START lowered to &EA) the monster from the left edge is drawn
  in the lava at the right (phantom-patched-F1-to-EA.png). With the player
  at column 59 (view_x &DE), a floor patch and a monster going up and down
  column 63:

      node tools/play.mjs --disc build/pipeline.ssd 'game; wait 7; poke 25A0 37 10; poke 25A6 79; poke 2640 FC 50 02 00; poke 3108 0 0 0 0; poke 3128 0 0 0 0; poke 3148 0 0 0 0; poke 3168 0 0 0 0; poke 3188 0 0 0 0; poke 31A8 0 0 0 0; poke 31C8 0 0 0 0; poke 31E8 0 0 E0 0; bkey SPACE; wait 9; shot build/shots/overhang-shipped.png'

  draws it cut to two columns at the right edge; with `poke CD3 DC`
  (VIEW_PAST_END lowered to &DC) its other two columns appear at the left
  edge a row down (overhang-patched-E2-to-DC.png).

What shows: only burn_up draws off the map. Its flames fill a square round
the player regardless of the map (X from view_x to view_x + 29, Y from
view_y - 1 to view_y + 28), and a flame whose top left is past the map's
edge counts as out of view. So at the left and top edges the lava stays as
it was, and at the right and bottom the flames reach 3 characters past the
edge (a flame at &FF drawn whole):

    node tools/play.mjs --disc build/pipeline.ssd 'game; wait 7; bkey SPACE; wait 8; bdown SHIFT; bkey ESCAPE; bup SHIFT; until 125F; shot build/shots/burn-right-edge.png'
    node tools/play.mjs --disc build/pipeline.ssd 'game; wait 7; poke 25A0 FD FE; bkey SPACE; wait 8; bdown SHIFT; bkey ESCAPE; bup SHIFT; until 125F; shot build/shots/burn-top-left.png'

(SHIFT+Escape ends the game; &125F is burn_up's RTS. Matching each view cell
against the pictures after the first: flames to column 24, lava from 25,
with the map's last column at 21.) One slip: with view_x exactly &E2 (the
player in column 60) a flame at X = &FF is view column 29, and with the
right edge unchecked its fourth column lands in view column 0 a row down.
Watched in jsbeeb (start at column 60, a hook on draw_sprite diffing screen
memory round each flame at &FF): a flame at (&FF, &96) changed view cells
rows 24-27 columns 29-31 and rows 25-28 column 0. It happens in most game
overs there (about 3 of the last ring's 100 flames) but is lost among the
flames. Rows can't do it: flames go down only to view_y + 28.

## 2026-10-03 23:43 — H.GAME's leftover is a strip of LDATA's picture

Correcting the first section ("it looks like the tail of some graphics"):
H.GAME's last &93 bytes, &506D-&50FF (file offsets &206D-&20FF: the 64
bytes the loader copies as trigger_places, then the uncopied &50AD-&50FF),
are LDATA's bytes at the same file offsets. LDATA is screen memory from
&3400 in the Level Designer's 64-column MODE 1, so they're character row 18,
columns 13 (from its sixth line) to 31: a band through the tops of "esig" in
"Designer", continuous with the picture round it.

- Searching every built file and the whole .ssd for runs of these bytes
  (10 or more) finds the whole &93 in LDATA and H.GRAPH, both at offset
  &206D, and nothing longer than 18 elsewhere. `cmp -l build/files/H.GAME
  build/files/LDATA | tail -1` says the last difference is byte 8301 (offset
  &206C); they agree from &206D to H.GAME's end.
- `cmp -l build/files/H.GRAPH build/files/H.GAME | tail -1`: byte 8236, so
  H.GRAPH's last &D4 bytes (its leftover, &3ADC-&3BAF, from offset &202C)
  are H.GAME's at the same offsets: the end of the game's code
  (error_handler_done's last bytes, trigger_actions, action_table,
  reverse_moves; &232C-&236C as it runs) and then the same strip of LDATA.
  docs/notes/levdes.md already has H.LEVDES's last &E1 bytes as H.GRAPH's.
- So the three hidden files went onto the disc, a whole number of sectors
  each, from one buffer, which had held LDATA: H.GAME (own bytes to offset
  &206C), then H.GRAPH (to &202B), then H.LEVDES (to &1E1E), each carrying
  what the one before left in its last sector. The match is by file offset,
  not address (LDATA loads at &3400, H.GAME at &3000, H.GRAPH at &1AB0).
- Drawing it: `tools/beebscreen.py 1 build/files/LDATA OUT.png --columns 64
  --offset 400 --palette 0,4,3,1` draws the picture; inverting LDATA's
  &206D-&20FF first shows where the strip is.
