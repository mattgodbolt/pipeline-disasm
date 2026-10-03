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
