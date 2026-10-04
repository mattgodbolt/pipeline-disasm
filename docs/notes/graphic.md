# The Graphics Designer (H.GRAPH) and DEFAULT

Notes from disassembling the Graphics Designer and its default graphics set.
Times are US Central.

## 2026-10-03 18:12 — Where it lives, and how to drive it

- The GRAPHIC stub reads H.GRAPH (&2100 bytes, sectors &145-&165) to &1AB0
  and jumps to &2BAE, as the STH crack's &1A80 load with &30 zero bytes and
  exec &2BAE suggested. So H.GRAPH occupies &1AB0-&3BAF.
- It runs in MODE 5 (screen &5800-&7FFF) with the palette set to black,
  blue, yellow and red (logical 0-3), redefined from a four-byte table.
- Memory it uses beyond itself: the graphics set at &4000-&4F33 (DEFAULT's
  load address; it clears &4000-&4FFF on first entry and writes the 12
  bytes "Finish Block" at &4F34), and scratch sprite buffers at &3E00 and
  &3E80.
- Driving it in jsbeeb: `tools/graphic_tours.mjs` runs scripted tours
  (painting, each menu, files, CTRL shortcuts, Escape) and writes a trace
  per tour for the disassembler, plus screenshots. Keys pressed in quick
  succession are lost (menus read the keyboard buffer; the sprite selection
  polls with a repeat delay), so the tours hold keys for several frames and
  pause between them.
- The UI, as seen and from its key tables:
  - Z X : / move the pixel cursor (CTRL held: moves without the sprite
    selection reacting); 0-3 pick the colour (4 also gives 0); Return plots,
    Delete clears.
  - The cursor keys move the selection over the sprite sheet on the right:
    a 5x5 grid of large sprites (16x32 MODE 5 pixels), and below it a 4x4
    grid of small ones (8x16). The large editing grid on the left shows the
    selected sprite magnified; under it, the current colour and (for small
    sprites) the object's name, e.g. "13:Extinguisher".
  - f0 OptionsA: Flip X, Flip Y, Delete, Undo, Animate, Obj name.
    f1 OptionsB: Swap, Copy, Overlay, Underlay, Remove, Backing (each asks
    "Select sprite to ... this onto/with/from/under" and takes a second
    sprite from the sheet). f2 Environment: Load Sprite, Save Sprite, Load
    File, Save File, Def. Colour. f3: the credits ("Written by & (c)
    WILLIAM REEVE and IAN HOLMES").
  - CTRL shortcuts: X Flip X, Y Flip Y, Delete, U Undo, A Animate, N Obj
    name, S Swap, COPY Copy, O Overlay, R Remove, B Backing, f8 Load Sprite,
    f9 Save Sprite, f6 Load File, f7 Save File, C Def. Colour. (Underlay has
    none.)
  - Escape asks "Escape? No/Yes"; Yes says "Return to menu: Please insert
    Pipeline disc and press SPACE", then `*/MRUN` (on DFS; on another
    filing system it resets with `*FX200,3` and `JMP (&FFFC)`).
  - Animate alternates two frames (one possibly mirrored) every six vsyncs
    until Space or Escape; it only applies to the animated pairs.

## 2026-10-03 18:23 — The graphics set format (DEFAULT)

- A graphics set is what the designer keeps at &4000-&4F33 and saves with
  OSFILE (load &4000, length &F34); DEFAULT is the shipped one.
  - &000: 16 large sprites, slots &00-&0F, &80 bytes each.
  - &800: 16 small sprites, slots &10-&1F, &20 bytes each.
  - &A00: 9 large sprites, slots &20-&28.
  - &E80: 15 names, 12 characters each (space padded), for small sprites
    &10-&1E; small &1F (the man) has none, and the designer refuses to name
    it. In memory the designer puts the 12 bytes "Finish Block" right
    after, at &4F34, which is why DEFAULT's slack on the disc starts with
    them: DFS wrote the rest of the last sector from memory.
- Large sprites are 16x32 MODE 5 pixels, small ones 8x16. Both are stored a
  column of bytes at a time (as MODE 5 lays out a character cell): the
  first byte is the top four pixels of the leftmost column, then the four
  pixels below, down to the bottom; then the next column. Pixel n of a byte
  (n=0 leftmost) is bits 7-n (high bit of its colour) and 3-n (low bit).
  There are no masks: colour 0 is just a colour (the designer's Overlay and
  Underlay treat it as transparent).
- Colours are logical; the designer's palette is 0 black, 1 blue, 2 yellow,
  3 red (from the table at disc_fs+1), changeable with Def. Colour.
- The designer's sheet shows the 25 large slots in a 5x5 grid in its own
  order (slot_of_position: 00 01 02 03 04 / 05 08 07 0A 0E / 24 26 25 27 0F
  / 06 28 0C 0D 0B / 09 20 21 22 23), and the small ones below in slot
  order, four to a row. Its "sprite number" (zero page `sprite`) is a sheet
  position: &00-&0F and &20-&28 for the large grid in reading order, &10-&1F
  for the small one.
- Animated pairs (its Animate command): &0E/&0F (flames) and &20/&21,
  &22/&23 (a yellow and red machine), alternated, some frames mirrored.
- src/default.6502 is now the set as pictures (`.123` per pixel), made by
  `tools/graphics.py asm`; src/sprites.6502inc turns them back into bytes
  with a baron FUNCTION and FOR loops. `tools/graphics.py png` renders a set
  (docs/img/graphics-default.png as the designer's sheet,
  graphics-default-slots.png in slot order).

## 2026-10-03 18:23 — What the designer reads and writes

- Load File / Save File: a whole graphics set by OSFILE. Save asks
  "Exists / Cancel / Replace" when the name is taken (OSFILE 5 first).
- Load File also accepts an IO file (the game's data, which MISSION
  writes): it checks the catalogue entry, accepting load &40xx with length
  &0Fxx as a graphics set and length &33xx as IO; anything else is "Bad
  File". From IO it reads three pieces with OSGBPB at set pointers
  (io_segments in H.GRAPH):
  - IO offset &0000, &80 bytes: large sprite slot &28 (&4E00 in the set);
  - IO offset &0080, &B4 bytes: the 15 object names;
  - IO offset &25D3, &E00 bytes: slots &00-&27 (&4000-&4DFF in the set).
  So in the shipped IO (&33D3 bytes, loaded at &242D) the sprites sit at
  &4A00-&57FF, ending where IO ends, at &5800, slot &28 at &242D and the
  names at &24AD. Save File into an IO file writes the same three pieces
  back (OPENUP). This is for whoever documents IO and MISSION.
- Load Sprite / Save Sprite move one sprite (and a small one's name) to or
  from the same place in a graphics set or IO file on disc, with OSGBPB at
  the sprite's offset; the file must exist already.
- On tape (filing system below 4, from OSARGS 0) it loads DEFAULT as the
  next file (name ""), and the sprite operations say "Not available with
  this filing system".

## 2026-10-03 18:41 — How H.GRAPH works (for the journal)

- Confirmed: the shipped IO carries DEFAULT's sprites and names byte for
  byte (IO+&25D3 = DEFAULT &000-&DFF, IO+0 = DEFAULT &E00-&E7F, IO+&80 =
  the names). So IO's graphics could be written with src/sprites.6502inc's
  LARGE_SPRITE / SMALL_SPRITE / OBJECT_NAME pictures too.
- Start-up (`start`, &2BAE): on first entry (BRKV still pointing into ROM)
  it takes BRKV and EVNTV, saving the old values in IND1V/IND2V to restore
  on exit, and enables the Escape event; then MODE 5, the palette, cursor
  off, `*OPT 1,0` on disc, the screen furniture from a VDU list, the logo,
  and (first time only, flag `graphics_loaded`) clears &4000-&4FFF and
  loads DEFAULT. Errors go to `error_handler`, which shows the message in a
  window and re-enters `start`, so work survives an error.
- `main_loop` resets the stack from `stack_pointer` each pass, which is why
  commands can bail out with a plain JMP. Pacing: `select_sprite` waits for
  the interval timer to reach 2 cs each pass. Commands dispatch through a
  self-modified JSR from `command_table` (number = menu * 8 + item, or a
  CTRL shortcut's place + 1).
- Pop-up windows: eight fixed windows (`window_address`, `window_size`),
  each saving what it covers at &5000; opening one closes the others.
  Window text is a flag byte (&FF = menu: the lines after the title are
  picked with the cursor keys), lines ending CR, and &FF. The font is 4x8
  pixels, exclusive-ORed on, so the menu highlight is an EOR with &0F.
- Escape: the event handler sets the Escape flag, and a latch when SHIFT is
  held; Escape -> "Escape? No/Yes"; Yes -> "Please insert Pipeline disc and
  press SPACE", restore vectors, `*/MRUN`. On a non-disc filing system it
  does `*FX200,3` and `JMP (&FFFC)` instead. While picking a second sprite
  or animating, f0-f3 raise an Escape (OSBYTE &7D) to cancel.
- Sprite numbers in the code are sheet positions, mapped to storage slots
  through `slot_of_position`, except while `by_slot` bit 7 is set (Animate
  works in slots). Numbers &57/&58 are two frame buffers at &3E00/&3E80;
  &3F80 is the undo copy taken whenever a sprite is selected (Undo swaps
  with it, so it is also redo).
- Sheet position 0 is the background tile: plotting in it copies the 4x8
  pixel cell changed through the whole sprite (`repeat_background`).
- Odd bits: `clear_rows` has no RTS and returns through `divide_by_5`;
  `sheet_row`'s `LDA #&80 : RTS` doubles as select_sprite's exit;
  `SBC row_down_step-1,X` reads the table from an RTS byte (`column_rewind`
  likewise); `open_file.update` and `read_block.write` are BIT-skip entry
  points; the Escape menu's flag byte is also the end of the error message
  buffer. Dead code: copies of three helpers at &2B18-&2B3F, an orphan RTS
  at &2594, a "read PTR" stub at &3610, a "Not implemented" error at &3633,
  and unused texts ("E S C A P E" error, "ActiCol"). &3ADC-&3BAF is
  leftover memory, not program.
- Zero page used: &50-&65 (pointers and loop counters), &70-&7E (editor
  state), plus the OS's &FD (error pointer) and &FF (Escape flag).

## 2026-10-03 18:55 — Corrections

- Animate's second frame is turned upside down (flip_vertically), not
  mirrored, where it isn't the partner sprite: &20 and &21 each alternate
  with themselves upside down, &22/&23 with each other upside down, and the
  flames &0E/&0F simply alternate.
- The Escape latch is set by SHIFT-Escape (INKEY -1), not CTRL.
- Baron's symbol dump lists every FOR iteration and FUNCTION frame under
  `@` keys; the picture macros in sprites.6502inc add thousands of them, so
  anything reading build/symbols.json for jsbeeb should drop keys with `@`
  (as baron's guide advises).

## 2026-10-03 19:40 — Review: corrections, and what's newly understood

A reviewer's pass over src/hidden_graphic.6502, checking every header and
comment against the code, and the doubtful ones in jsbeeb (scratch driver
around tools/beeb.mjs, logging registers at chosen PCs).

Corrections to the earlier notes and comments:

- Small slot &1F isn't "the man": it's object icon 15, which the game
  draws as the exit (H.GAME's `exit_picture` is `io_object_icons + 15 *
  32`). "Finish Block" sits exactly where its name would be (&E80 + 15 *
  12 = &F34), so selecting it shows "16:Finish Block": it's the
  designer's label for the exit, not only an end marker. Seen in jsbeeb.
- Slots &20-&23 aren't "a yellow and red machine": they're the player
  facing left, right, up and down (io_player; the figure in the game's
  screenshots), and &0E/&0F the flame monster's two pictures. Animate
  previews the game's own animations: the monster alternates its
  pictures; the player facing left or right alternates with itself upside
  down; facing up, &22 alternates with &23 upside down, and facing down
  &23 with &22 upside down. (default.6502inc on main says Animate shows
  "&20 with &21": it shows &20 with itself upside down.)
- On tape nothing is loaded at the start: the set stays empty. The name is
  changed to `""` first, but nothing reads it afterwards. (jsbeeb: `*LOAD
  GRAPHIC`, `*TAPE`, `CALL &900`; &4000 stays zero, disc_fs 0, and the
  sprite commands say "Not available".) The earlier note had it loading
  the next file.
- The pixel cursor doesn't blink. main_loop toggles it only when the
  selection has moved, to put it back on the grid draw_grid just redrew
  (screenshots 0.4 s apart are identical).
- After a two-sprite command the selection stays on the sprite picked,
  not the first (redraw_pair): a Copy of 1 onto 2 leaves 2 selected.
- The pick window's picture of the first sprite sits to the right of the
  "to/copy/this/onto" lines (rows 2-5), not on the empty title line.
- Leaving does OSBYTE 4,1, not 4,0: X is 0 from the OSBYTE &7E before it,
  since no Escape is pending (a trace of the exit shows X=1 at the call).
  Harmless: MENU does `*FX4 1` itself.
- The 39 bytes after slot_of_position aren't unused: they put the font on
  a page boundary (&1D00), which print_char needs, as it adds only a high
  byte to find a glyph. Now `ALIGN &100` and `HI(font)`.
- A character row is 40 cells of 8 bytes (each 4 pixels by 8 lines; a
  MODE 5 text character is two), not 20. ROW is &140.
- A pop-up window covers at most &380 bytes: &5000-&537F, not up to &57FF.
- invert_menu_row exclusive-ORs colour 1 into every pixel (red and yellow,
  black and blue swap), not "colours 1 and 2".
- `SBC row_down_step-1,X` and `SBC column_rewind-1,X` never read the RTS
  before their tables: X is always 1 or more there. Only the expression's
  base is the RTS.
- Labels that said the wrong thing: show_selection's `.left` and `.right`
  were swapped; sheet_column's `.small` and sheet_row's `.large` were the
  paths for positions &20-&28 (now `.high`); escape_event's `.not_ctrl` is
  `.not_shift`; `flip_x`/`flip_y` (Flip X's scratch pixel) are
  `mirror_x`/`mirror_y`.
- check_filing_system had text_not_available's address hard-coded (`LDX
  #&78 : LDY #&29`). ask_load_name's tail made `io` and `not_graphics`
  global symbols; it's `check_io_file` now.

Newly understood:

- Why escape_event sets the Escape flag itself: MOS 1.20's key handler
  (&E4F0) calls OSEVEN for event 6 and sets the flag (`JSR &E674`, a ROR
  &FF with carry set) only if OSEVEN returns carry set, which it does
  (&E494) when the event is disabled. With the event enabled, the
  handler has to. MENU's line 380 does `*FX229` (0) before running the
  designer, undoing its earlier `*FX229 1`, so Escape is a real Escape
  here; `*FX200` is 2.
- What the SHIFT-Escape latch is for: plain Escape in a menu only cancels
  it (the menu acknowledges the Escape); SHIFT-Escape cancels and then
  asks "Escape?", because the latch outlives the acknowledgement. Seen in
  jsbeeb.
- Sheet position 0 is slot 0, the floor. The game fills the floor round
  an object's icon from that picture's first cell alone (`io_tiles, Y` in
  H.GAME's draw_row_floor_cell), which is why the designer keeps it one
  4x8 cell repeated.
- Plotting a pixel, and Delete, draw the sheet's copy of the sprite over
  its selection box, which stays off until the selection moves (jsbeeb).
- A palette changed with Def. Colour survives an error, because start
  leaves the mode and palette alone when the screen is already MODE 5.
- The VDU list narrows the text window to the top 18 rows so the CLS done
  on tape (for the filing system's messages) leaves the boxes and logo.
- `JSR &1234` at main_loop.dispatch is the original's own placeholder
  operand. Spare bytes: the one after row_step, key_held's second, the
  three after the OSGBPB block (cleared with it), two after the OSFILE
  block.

How the source is now:

- Keys use osconst.6502inc's convention, `INKEY_TEST(KEY_X)` with
  internal key numbers. Names no shared include has yet are in
  src/graphics_designer.6502inc, by where they should go: OS call
  numbers, cursor-key codes, `DEL`, `ctrl()`, key numbers, VDU and PLOT
  codes, CRTC register 10 (osconst.6502inc); the graphics set's layout
  `SET_*`, sprite sizes and what each slot is, `SLOT_*`
  (sprites.6502inc). IO's offsets come from io.6502inc's addresses.
- The logo and font are drawn two characters a pixel and built with
  sprites.6502inc's `mode5_pictures` (the logo as its three 8-row bands,
  the screen's own layout). H.GRAPH's symbol-dump entries went from 5,119
  (4,214 of them `@`) to 1,064 (159), and build/symbols.json from 837,247
  to 718,726 bytes. sprites.6502inc's SPRITE_COLUMNS and SCREEN_PICTURE
  now have no users.

## 2026-10-03 23:45 — The leftover at the end of H.GRAPH

Correction: `leftover` (&3ADC-&3BAF, file offsets &202C-&20FF) isn't a
pointer table and graphics. It's H.GAME's bytes at the same offsets: the
last &41 bytes of the game's code, then the strip of LDATA's picture H.GAME
ends with (docs/notes/game.md). The hidden files were written whole sectors
at a time from one buffer, H.GAME, H.GRAPH, then H.LEVDES, each ending with
what the one before left there. Checked by comparing the files' tails:
H.GRAPH equals H.GAME from &202C, and both equal LDATA from &206D.

## 2026-10-04 12:54 - Readability pass

A pass over src/hidden_graphic.6502 for a reader who hasn't read these
notes: the header now says how the designer is reached and left, defines
the words the comments use (slot, sheet, sprite number, object, floor,
window, frame, on tape), maps zero page with the rest of memory, and lists
the file's parts in order with their addresses.

Comments the code contradicted:

- `key_held` said it held the INKEY number of the cursor key held. It holds
  key_pressed's result, &FF, so it's only a "held this pass" flag (jsbeeb:
  &FF while a cursor key is down, 0 after).
- `sheet_address` said it returns A = Y = the sprite number. Y always is,
  but for a small sprite A is left as the screen address's high byte. No
  caller uses A.
- `sheet_row` said its last two bytes double as select_sprite's exit. The
  shared exit is `return_negative` (LDA #&80 : RTS, three bytes), in the
  middle of the routine.

Renames: select_sprite's `.not_a` (reached when the selection isn't &0F)
is `.down_not_0f`, and its upward twin `.not_f` is `.up_not_0f`.

Correction to the 19:40 entry: src/graphics_designer.6502inc no longer
exists. The names it held went to the shared includes (osconst.6502inc for
the OS's, sprites.6502inc for the set's layout and slots).
