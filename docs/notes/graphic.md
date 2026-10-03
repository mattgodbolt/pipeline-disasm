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
