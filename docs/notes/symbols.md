# Notes: symbol sets for jsbeeb's debugger

`make jsbeeb-symbols` (part of `make test`) writes one JSON file per set to
`build/jsbeeb-symbols`, in the format of "Symbol sets" in jsbeeb's
`docs/media-registry-proposal.md` (branch `claude/symbol-sets-revision`,
PR #1215): the second slice of jsbeeb's symbol support loads them. The
pieces:

- `tools/jsbeeb_symbols.py` makes the sets; `src/symbols.toml` says which
  programs make a set and where their regions are cut, in the sources' own
  names; `tools/listing.py` reads a baron -vv listing.
- `tests/test_jsbeeb_symbols.py` checks each set by the proposal's per-set
  rules and every anchor against the built files.
- `tools/symbols_corpus.py` is the corpus check (its report is
  `docs/notes/symbols-corpus.md`); `tools/symbols_check.mjs` checks the sets
  against PIPELINE running in the headless jsbeeb.

Times are US Central.

## 2026-10-04 19:40: The sets

| File | Regions (anchors/names) | Anchors | Names | Globals |
|---|---|---|---|---|
| `game.json` | loader &3000-&50FF (1/20), event_handler &0131-&0190 (1/4), sound_data &0880-&08FF (1/3), low_code &0400-&07FF (2/76), main_low &0900-&0CFF (1/85), main_swapped &0D00-&12A2 (2/119), game_start &12A3-&12C2 (1/1), main_swapped_2 &12C3-&1CFF (3/182), main_high &1D00-&23AC (1/123) | 13 | 613 | 155 |
| `graphics-designer.json` | main &1AB0-&3BAF (4/478) | 4 | 478 | 35 |
| `level-designer.json` | main &1100-&25A0 (3/401), startup &25A1-&2FFF (1/20), low_code &0880-&0CBF (2/83), font &0400-&07FF (2/1), wdata &7000-&7C4D (2/77) | 10 | 582 | 78 |
| `game-stub.json` | main &0900-&09D8 (2/24) | 2 | 24 | 3 |
| `graphic-stub.json` | main &0900-&09D8 (2/24) | 2 | 24 | 3 |
| `levdes-stub.json` | main &0900-&09D8 (2/24) | 2 | 24 | 3 |
| `mrun.json` | main &0780-&07FF (1/5) | 1 | 5 | 1 |
| `title.json` | title &6300-&7978 (3/3), unpack &2F18-&2F78 (1/10) | 4 | 13 | 2 |
| `pl.json` | decryptor &0400-&043B (1/4), encrypted &043C-&06FB (1/1), cheat &043B-&06FB (1/38) | 3 | 43 | 15 |
| `menu.json` | program &1900-&22FF (2/1), scroller &2300-&31FF (4/10), menu_screen &3200-&38FF (1/3) | 7 | 14 | 8 |
| `mission.json` | program &1900-&3127 (6/5) | 6 | 5 | 2 |

54 anchors, 1825 region names and 305 globals in all. Every region's
`minAnchors` is its number of anchors.

Each set has `licence: "LicenseRef-TBD"`: the licence is Matt's call and not
made yet. It's the one `licence` setting at the top of `src/symbols.toml`.
`source` is the repository at the commit built (`git rev-parse HEAD`, so a
build from a dirty tree, or CI's merge commit on a pull request, names a
commit that doesn't hold what was built). `madeFrom` is the disc key jsbeeb's
`tools/registry/fingerprint.js` gives `original/pipeline.ssd` and
`build/pipeline.ssd` alike, `dc7201d5fb5bfa137e302dade0b519da`; `make
verify` keeps that true.

### The split, and why

One set per program: the game, each designer, each stub, MRUN, TITLE, PL,
MENU and MISSION.

- Each runs on its own, with its own zero page. A set's globals name only
  its own code's operands, so a set per program is what keeps the game's
  `&70` (`cell_x`) apart from the Graphics Designer's (`sprite_width`) and
  the GRAPHIC stub's (`sectors_this_read`).
- A stub and the program it loads are often in memory together (the GRAPHIC
  stub stays at &0900 all through the Graphics Designer), but not always:
  the stub is there before the program, and the game and the Level Designer
  overwrite theirs. So they're separate sets, as jsbeeb's design notes
  expect.
- The three stubs are one source assembled three times, but three programs:
  each its own set, told apart by its anchor at `read_whole_run` (&0916),
  the one labelled instruction where they differ.
- WDATA is loaded by the Level Designer at its start and stays, so it's a
  region of the Level Designer's set: data the program never writes but for
  one byte (below).
- The data files have no sets of their own. IO, LEVEL1 and DEFAULT are
  loaded and changed by the programs that use them, so their names come in
  as those programs' globals (below). LDATA, SCREEN and WARNING are
  pictures on the screen, which is drawn over; !BOOT is `*EXEC` text.
- MENU and MISSION are BASIC, but each holds labelled machine code (MENU's
  scroller in its DIM'd heap, MISSION's scrambler in a REM), so each has a
  set. Their BASIC lines have no names an address debugger could show
  beyond `program`.

### Regions

A region is a SECTION, or part of one between two names `src/symbols.toml`
gives, cut where memory changes while the program runs:

- **The game.** The loader (the whole of H.GAME as loaded at &3000, which
  IO replaces) and the four pieces it copies, each where it runs:
  `event_handler` &0131, `sound_data` &0880, `low_code` &0400 and
  `main_code` &0900. `main_code` is cut at `SWAP_START` and `SWAP_END`
  (&0D00, &1D00), which `load_mission` swaps into the screen while IO loads,
  and `game_start` (&12A3-&12C2) is a region of its own: `setup_level`
  copies the level's objects over it once it has run.
- **The Level Designer.** `main` (&1100-&25A0); `startup` (&25A1-&2FFF:
  `entry` and the stored zero page, low code and font), which the level
  being edited fills; `low_code` &0880 and `font` &0400 where they run; and
  WDATA.
- **TITLE**: the file as loaded at &6300, which the picture unpacks over,
  and `unpack`, the part of its last page it moves to &2F18 to run.
- **PL**: the decryptor (&0400-&043B), the encrypted bytes (&043C-&06FB)
  and the cheat they decrypt to (`pl_decrypted`, &043B-&06FB). The
  decryptor's last instruction, a BMI at &043B, is also the cheat's first.
- **MENU**: the BASIC program (&1900-&22FF), the scroller and its message
  (C%, &2300), and the menu screen (S%, &3200, with the leftovers past it).

The Level Designer's zero page section (`zero_page_init`, its pointers to
the menus' handler tables, &00-&21) is listed as `globals_sections`: zero
page holds no code, and every program writes it, so a region there couldn't
be anchored. Its labels are globals.

### Names

- **Labels** go to the region of the section they're assembled in, with
  their scopes (`select_sprite.down_not_0f`). A scope that wraps a whole
  program (`game`, the stubs' `*_loader`, `mrun`, `title`) is left off.
  A label at a section's exclusive end (`main_code_end`, `event_handler_end`)
  is in no region and is left out.
- **`=` names** count as addresses when an instruction uses them as a
  memory operand (the operand's first name, not after `#`, not a
  FUNCTION's result), and not when `src/os.6502inc` defines them (jsbeeb's
  MOS set has those). Such a name goes to the region it points into if
  only that region's code uses it (`entry_code_from`, an operand `entry`
  modifies; `saved_rdchv`; PL's `key_bytes`), and is a global otherwise.
  This picks up all of the game's zero page, the trigger flags, the object
  table, `trigger_args` and the 17 fields of IO the game reads; the Level
  Designer's zero page and the level (`level_names`...); the Graphics
  Designer's zero page, buffers and the screen positions it draws at; and
  none of IO's layout in the Graphics Designer, which uses it only for
  offsets.
- Names starting with `@` (baron's internals) never appear: the listing
  shows which labels are inside anonymous scopes, and none of PIPELINE's
  are.
- **One name per address.** In a region, a scope's own name wins over the
  labels inside it (`scroller` over `scroller.start`, `pl` over
  `pl.start`), then the label written last, nearest the bytes (`tune` over
  `sound_data`, `key_order` over `cursor_off_vdu_end`). In the globals, the
  name the most instructions use. `jsbeeb_symbols.py -v` lists every name
  left out and why: 44 of them, mostly end labels.

### Anchors

Candidates are runs of 4 to 8 bytes of the region's own statements: whole
instructions from an instruction's start (aiming for 6 bytes), or data from
any byte. A candidate is out if any of its bytes is:

- reached by a store whose target the instruction gives (an indexed store
  reaches 256 bytes, unless `table_sizes` gives the table's size), except
  that a run-once region (`overwritten`) only minds its own stores, and the
  copies in `moves` (the Level Designer's `entry` putting the low code and
  font in place) don't count;
- in a block the code hands the OS (`LDX #LO(block)`), which OSWORD, OSFILE
  and OSGBPB write results into: from its label to the next one that starts
  code, 18 bytes at most;
- SKIP padding, or under a label the source names as dead or leftover
  (`*unused*`, `leftover`, `junk`, `spare`, `stray`, in any of its scopes);
- in a BASIC program, its first line, any line's CR, number and length,
  or a REM's text (code in a REM, as in MISSION's line 60, stays in);
- in &FC00-&FEFF;

or if the run calls into the MOS (`JSR`/`JMP` to &C000 up: the code every
program shares, `*FX4,1` among it), has two NOPs together, has fewer than
four different bytes, or appears twice in the region.

From those, about one anchor per 2K of region (four at most), spread over
it, preferring a label, then code, then the most different bytes. Then for
every other image of the region's addresses in the build (every section of
every source where it runs, every file where it loads, data files
included): an image holding all the anchors and agreeing with them gets
another anchor where it differs (that never happened); and another
program's image of any part of the region gets an anchor inside that part
where it differs, if there is one. That last rule is what gives each stub
its anchor at `read_whole_run`, MENU's scroller one in the page TITLE
moves its unpacker to, and so on. Two can't be had, which the generator
reports as notes: the Graphics Designer and the Level Designer's `startup`
have no anchor candidate inside &2F18-&2F78, where TITLE's unpacker runs.
They never share memory with it.

Each anchor is checked against the built file at the address it runs at,
by `tests/test_jsbeeb_symbols.py`.

## 2026-10-04 19:45: Checked in jsbeeb

`node tools/symbols_check.mjs` boots `build/pipeline.ssd` in the headless
jsbeeb (beeb.mjs) and, at moments in each scenario, lists the regions whose
anchors all match memory. It fails unless that's exactly the regions
expected, and if regions of two sets over the same addresses both match.
All 128 moments matched as expected, with no such overlap:

- **MENU** (4 moments, in the scroller's vsync handler and on the
  redefine-keys page): exactly `menu/program`, `scroller` and
  `menu_screen`.
- **The game, in play** (`game`, 9 moments, and `play`, 30 moments of
  seeded random play with the direction keys, pick up, drop, throw, use,
  the map and the backpack, checked wherever the PC was): exactly the seven
  regions that stay, `event_handler`, `sound_data`, `low_code`, `main_low`,
  `main_swapped`, `main_swapped_2`, `main_high`. On the way: at the loader's
  entry, the GAME stub, `game/loader`, MENU's BASIC and TITLE's unpacker
  (all still there); at `game_start`, everything the loader has put in
  place, the loader itself and `game_start`; inside `load_mission`, with
  &0D00-&1CFF swapped into the screen, everything but the three regions in
  that range; on the title screen, `game_start` still there until a level
  is set up.
- **The Level Designer** (12 moments): at `main_loop` with a new level,
  with LEVEL1 loaded (checked against the file), after moving, plotting and
  deleting, with the Options menu and a window open, with the simulator on
  and walking, in Help and About: exactly `main`, `low_code`, `font` and
  `wdata`. At its entry, its `main` and `startup` with the LEVDES stub and
  MENU's screen data still above it; at its title, `startup` as well, since
  no level has been set up yet.
- **The Graphics Designer** (3 moments, then 63 in the four tours from
  `tools/graphic_tours.mjs`: painting, OptionsA, OptionsB, files including
  loading DEFAULT and IO, and the CTRL shortcuts): exactly
  `graphics-designer/main` and the GRAPHIC stub, which stays at &0900.
- **TITLE, MRUN and PL** (7 moments): TITLE as loaded and its moved
  unpacker, with MENU's BASIC; MRUN entered from the Graphics Designer, and
  still matching back at the menu, from BASIC's line buffer at &0780; PL
  before and after it decrypts itself, `decryptor` with `encrypted`, then
  with `cheat`.

Regions
that match while their program isn't running are the leftovers the format
expects: the GRAPHIC stub through the Graphics Designer and the menu after
it, MRUN in BASIC's line buffer, TITLE's unpacker until IO loads, MENU's
BASIC until the game's code lands on it.

## 2026-10-04 19:50: What the generator gets wrong, or only roughly

- **Zero page shared by different code in one program** loses names (see
  the first format gap): the game's loader's `copy_return`, `copy_from`
  and `menu_keys` give way to `monster_x`, `monster_direction` and
  `work0`, so the loader's own operands show the main code's names; TITLE's
  `relocate_to` and `clear_ptr` give way to `packed`; PL's decryptor's
  `crypt_ptr` and the cheat's `key_index` and `digit_pair` to `entry_index`;
  MRUN's `typed_index` to `default_vectors`.
- **The operand rule misses** addresses the code reaches only through an
  immediate's `LO()`/`HI()` (the game's `map` at &5800, its screen, IO's
  pictures `io_player` and `io_alternates`), through a FUNCTION (`tile()`
  into IO's pictures, the Level Designer's `screen_address()`, MENU's
  `mode7_address()`), or through a table of addresses. And it takes a name
  whose instruction is dead code as readily as any.
- **Stores it can't see** stay unseen: through a pointer (the Level
  Designer writes RDCHV into `rdchv_filter`'s operand at `saved_rdchv`, and
  the compass window's height into WDATA at &7704), or by the OS into
  blocks it was passed other than with `LDX #LO(...)`. None of today's
  anchors sit on any of those (the jsbeeb check would have shown it), but
  nothing stops a later anchor landing on one. The `LDX #LO(...)` rule also
  over-blocks: it takes OSCLI strings, which the OS only reads.
- **Hand-written knowledge** in `src/symbols.toml`, by name: where to cut
  the regions, the four table sizes that keep the game's tables in zero
  page and the stack page from ruling out `event_handler`, the Level
  Designer's two moving copies, MENU's leftovers. A change to the code that
  moves those needs the config looked at; a misspelt name stops the build.
- **The "another program's image" rule** adds anchors for meetings that
  never happen: MISSION gets one in TITLE's unpacker page and one in the
  game's loader, which no route through the menu puts beside it.
- **Data anchors in text** (the scroller's message, MISSION's BASIC) land
  wherever the spread puts them; they're fine against the corpus, but
  nothing makes them better than any other text.
- **The corpus check** can only compare with files at their load
  addresses (`docs/notes/symbols-corpus.md`).

## 2026-10-04 19:55: Format gaps

Where jsbeeb's format couldn't say what PIPELINE needs, for its design
doc:

1. **Globals scoped to a region's code.** One program's code can use the
   same zero page for different things in different regions: the game's
   loader uses &00-&07 for `copy_block`'s arguments and &50 for MENU's keys,
   where the main code keeps monster 0 and `work0`; TITLE's `start` and
   `unpack` name &70 and &72 differently; PL's decryptor and the cheat it
   decrypts likewise. A set's globals hold one name per address, so one
   region's code shows the other's names. Globals that belong to a region
   (an instruction in it takes them before the set's own) would say it.
2. **Two names for one address.** A table and its first field (`objects`
   and `object_x`), a block and its first byte (`id_buffer` and `id_track`),
   a scope and its entry (`pl` and `pl.start`), a section and its first
   label (`sound_data` and `tune`). The converter keeps one; the other
   can't be shown or used for a breakpoint by name. Aliases, shown once but
   found by either name, would keep them.
3. **Names have no size.** The source says how big each variable is (a
   pointer's two bytes, `backpack`'s four, `input_buffer`'s 16), and the
   code is full of `ptr+1` and `table, X`. Without a size the debugger can
   only show `STA &53` for the Level Designer's `STA ptr+1`.
4. **Code parked where it doesn't run.** H.GAME holds its four pieces at
   &3100-&50AC as loaded, the Level Designer its zero page, low code and
   font at &25A1-&2E20, and the game swaps &0D00-&1CFF into the screen
   while IO loads. Each is the same code as a region elsewhere, but only
   the `*_load` labels name it there. A region with an offset would, which
   the design notes judged not worth a field.
5. **Two regions of one set matching at the same address.** PL's
   decryptor ends with a BMI whose offset is the first byte it decrypts, so
   the cheat's first instruction (`pl_cheat`, &043B) is the decryptor's
   last, and both regions match there once it has run. The format says what
   happens when regions of different sets overlap, not regions of one.
6. **Which bytes are data.** The build knows the inline data after
   `JSR copy_block` and `JSR print_inline`, the jump tables (&1100, &0880,
   &234D in the Level Designer) and the tables inside code. The format can't
   carry it, so a disassembly view decodes them as instructions.
7. **The annotation.** Routine headers and line comments are most of this
   disassembly's value, and the format has no place for them.
8. **Constants.** `CELL_*`, `KEY_*`, `OSBYTE_*` and the like are left out,
   rightly for an address map, but an immediate operand (`LDA #CELL_LAVA`)
   can't be named either.

## 2026-10-04 19:55: Chooser rules

Not the format, but rules for choosing anchors that PIPELINE showed, for
the same design doc:

- **An indexed store's full reach is too much near small tables.** The
  game keeps its trigger flags (32 bytes) and `keys_were_down` (4) at the
  bottom of the stack page, written with `STA table, X`, and its event
  handler 49 bytes on. Counted at 256 bytes, those stores leave the handler
  nothing to anchor on. The chooser's input could take a table's size from
  the build or the listing.
- **Writes through pointers and by the OS.** `LDX #LO(block)` before an OS
  call marks a block the OS can write; a store through a pointer to a
  program's own code (`rdchv_filter`'s operand) needs the listing's
  author to mark it.
- **BASIC.** Beyond the first line, a BASIC program's line headers are much
  alike in every program, and REMs aren't the program at all, so anchors
  belong in its line text, or in machine code it carries.
- **"Tell apart" has two strengths.** No other image holding all of a
  region's anchors is the corpus check's rule; an anchor inside every
  overlap where another program differs is stronger, and is what makes a
  leftover stop matching when part of it is overwritten. The second can't
  always be met (above).
