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
