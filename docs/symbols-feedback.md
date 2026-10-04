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

## jsbeeb's media registry proposal (read 2026-10-03)

jsbeeb's `docs/media-registry-proposal.md` (with its design notes and
findings, PR #1179) is where the symbols would plug in. A disc is
recognised by a fingerprint, the record found for it names symbol sets, and
a set's labels show only while its regions' anchors (a few bytes at known
addresses) match memory. Matt passed these comments on to its author.

- The fingerprint works for this disc. jsbeeb's `tools/registry/fingerprint.js`
  gives one disc key, `dc7201d5fb5bfa137e302dade0b519da`, to the capture
  `E447ED5E.hfe`, `original/pipeline.ssd`, and our rebuilt SSD and HFE (the
  deleted marks don't count). The Stairway To Hell crack gets
  `42e2a68ee9c4efd1e19093f7fe15de3b` and needs an alias. A disc the
  designers have saved to gets a new key of its own.
- Anchors can tell the programs apart: six bytes at each labelled
  instruction give 570 candidates in H.GAME, 441 in H.LEVDES and 381 in
  H.GRAPH, and none matches another program's bytes at the same address.
  The three stubs differ in 6 bytes, and 8 of each one's 10 candidates are
  shared by all three.
- What the schema needed for this disc:
  - a selector from a region into the dump (one JSON holds all 19 files);
  - labels told apart from constants (in H.GAME's dump &80 has ten names,
    one of them the variable `view_screen`);
  - per-program names shown whenever the program is in (zero page, IO's
    layout), which `globals` can be if each program is its own set;
  - a matching region's labels winning over those at the same addresses
    (start-up code that becomes data: &12A3 in the game, &25A1-&2FFF in the
    Level Designer);
  - regions cut where memory changes mid-run (the game swaps &0D00-&1CFF
    out while IO loads), found from recorded writes, since the DFS and
    `(zp),Y` copies are invisible to static analysis;
  - a rule for when two regions both match;
  - the same check for lookups from name to address (breakpoints by name);
  - anchors chosen from a build's own output, not only a py8dis listing.

## jsbeeb PR #1215, the revised symbol sets (read 2026-10-04)

The revision answers the list above: sets in the registry's own format, one
per program, regions with their own `symbols`, globals the converter picks,
regions winning over globals, cuts at known copies and swaps, a build check
that overlapping regions' anchors disagree, and an index of anchors for
discs without a record. Commented on the PR:

- The check can be met for every overlapping pair here, but the three stubs
  differ at only one labelled instruction, `read_whole_run` (&0916), so each
  stub's set must anchor there.
- Globals leak from leftovers: the GRAPHIC stub stays at &0900 through the
  Graphics Designer's run and back to the menu, so its region keeps
  matching and its zero page (&70, &72) would show beside the designer's own
  names for those addresses. Suggested: globals follow the program the PC
  is in (or, in ROM, the nearest return address on the stack).
- A disc with levels saved to it keeps H.GAME intact for one save only (the
  second lands on its first eight sectors).
- Followed up (2026-10-04): MISSION's saves land on the same disc with no
  prompt, and one mission (all of H.GAME) or one graphics set (H.GAME's
  loader) stops the game, so the example should drop "hasn't changed"
  rather than say "one level saved".
- Answered the jsbeeb side's three questions (2026-10-04):
  - No other title on the STH discs, Superior's included, holds PIPELINE's
    code at the same address, and no other image holds the stub loader.
    Only `start` in H.GRAPH (`*FX4,1`) and the BASIC programs' first line
    make anchors that collide.
  - Splitting linked names by range misplaces the Level Designer's level
    (it sits over its start-up code), IO's names in H.GAME (over the
    loader as loaded) and IO's layout in H.GRAPH, which uses it only for
    offsets. Neither baron's dump nor its listing says which `=` names are
    addresses; using a name as a memory operand is a good test.
  - The game's variables reach &9B, its envelopes sit on the MOS's own,
    and its code covers &0900-&0DFF. A system global shouldn't name an
    address inside another set's matching region.
