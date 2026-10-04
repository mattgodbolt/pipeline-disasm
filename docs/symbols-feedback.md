# Symbols for jsbeeb: what this disc needs

Baron's `--symbols` dump and jsbeeb's use of it are both works in progress.
This collects what PIPELINE shows a consumer will need, as feedback for both;
nothing here is built yet.

## What the disc is like

- Several programs share memory at different times. H.LEVDES (&1100-&2FFF),
  H.GRAPH (&1AB0-&3BAF), MENU (&1900-&38FF), H.GAME (&3000-&50FF), IO
  (&242D-&57FF), and the stubs at &0900 (three programs, the same addresses).
  A name is right for an address only while that program is the one loaded.
- Some code runs somewhere other than where it's stored (TITLE's unpacker is a
  rephased section at &2F18; PL decrypts itself in place). Baron already puts
  labels at their run address, which is what a debugger wants.

## What the dump gives today, and what's missing

- One object per top-level source file, every symbol under its dotted path.
  Good: the file is a natural unit.
- No difference between a label and a constant. `CR = 13`, `ADC_HIGH =
  &FEC1` and `loading_screen = &5800` all look alike, so a consumer can't
  tell which numbers name addresses in this program and which are just
  numbers (or OS addresses defined by an include).
- No record of which section a label is in, so no load/run range or output
  file to tie it to. With overlapping programs that's the key to knowing
  when a name applies.
- Baron's internals are included under `@` keys: FUNCTION and macro
  parameters, FOR iterations, anonymous scopes, and the BASIC block's
  per-line records (`@0:2210.number`, `@0:2210.text`). Easy to filter, but
  they swamp the rest: the picture macros in DEFAULT add about 15,000 of
  them, IO's macros once made 628 KB of them, and the whole dump is still
  about 370 KB. An option to
  leave them out would help.

- Every FUNCTION leaves a `null` parameter frame (`"@0:46.n": null`) in the
  dump of every file that includes its definition, used or not; a call made
  inside a MACRO adds a second frame. Moving data emitters out of macros and
  into top-level FUNCTION calls, and vectorising per-element loops into list
  expressions, took this project's dump from 1.44 MB to 0.83 MB.

## What a consumer would want, at minimum

For each saved section: its filename, run address range (org to end), and
the labels defined inside it (name and address), separately from constants.
Optionally the section's bytes or a hash, so the consumer can check that the
program is actually in memory before using its names: compare RAM against
the assembled bytes over the section's range, tolerating some differences
(self-modifying code and variables in the code change bytes at run time).

## Nice to have later

- Routine header comments and line comments, keyed by address: the
  annotation is most of the value of this disassembly, and the `-v` listing
  is the only place it survives today.
- The listing is currently not valid text: MENU's and MISSION's BASIC lines
  carry raw control and teletext bytes into it (see baron#12).

## Until then

The listing (`build/listing.txt`) has what's needed: SECTION lines with
their attributes, then `ADDR  .label` for each label, with `{`/`}` for named
scopes. A small parser could build the per-section label tables from it, at
the cost of depending on a human-oriented format.
