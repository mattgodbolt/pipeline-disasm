# PIPELINE disassembly

PIPELINE (William Reeve & Ian Holmes, Superior Software 1988), rebuilt from
baron source into a disc byte-identical to `original/pipeline.ssd`. Modelled on
`../frogman`, but assembled with baron (`../baron`), and the disc is rebuilt
whole rather than just the interesting parts. The longer aim: baron's symbol
dump (`build/symbols.json`) feeds jsbeeb as annotation metadata (labels for
the debugger), so label names and scopes matter.

## The invariant

`make verify` must say `identical` at every commit. Replace binaries with
source a piece at a time; never commit a step that changes a byte. If a step
needs the image to differ temporarily, it isn't a step yet: make it smaller.

`make test` = verify + tool tests. CI (`.github/workflows/ci.yml`) runs the same
with baron pinned by commit; bumping the pin is its own commit.

## How the build works

- Each `src/*.6502` assembles independently (baron gives each its own symbol
  table). A `SECTION` with a `filename` is written raw to `build/files/` with a
  `.inf` sidecar. Shared definitions go in `src/*.6502inc` and are INCLUDEd.
- `src/disc.toml` places each piece: catalogue order and start sectors, locked
  flags, the slack bytes past each file's end, and the hidden sector runs
  (`[[raw]]`) the stub loaders read directly.
- `tools/mkssd.py` builds the image; `tools/ssdcmp.py` compares and names the
  file and offset (and load address) of any difference.
- The hidden runs' sectors had deleted data address marks, which an .ssd
  can't hold (`deleted = true` in the layout). `tools/mkhfe.mjs` builds
  `build/pipeline.hfe` with them, and `tools/disccmp.mjs` checks it reads
  the same as the original flux capture `original/E447ED5E.hfe`. Needs
  `npm ci` once.

## Where names live

One definition for each name a piece shares with another piece or with the
machine (`docs/notes/names.md` has the decisions); a name only one program
means stays in that program's source or include. `tests/test_symbols.py`
fails if a scope redefines a name its file already has outside it.

- `src/os.6502inc`: addresses only: MOS entry points, vectors, OS workspace
  (`MOS_ENVELOPES`...) and hardware registers. Add OS addresses there rather
  than locally (one name per address). The disassembler names operands from
  it, except zero page.
- `src/osconst.6502inc`: the machine's other numbers: OSBYTE, OSWORD,
  OSFILE, OSFIND, OSGBPB, OSARGS and FSCV calls and their settings
  (`CURSOR_KEYS_*`...), service calls, SOUND channel flags, buffers, events,
  internal key numbers (`KEY_*`, tested with `INKEY_TEST()`), the codes keys
  give (`KEYCODE_*` after *FX4,1), characters (`CR`, `ESC`, `DEL`,
  `ctrl()`), VDU and PLOT codes, CRTC registers and cursor settings, screen
  memory (`MODE1_SCREEN`, `MODE5_SCREEN`, their row and character sizes,
  `SCREEN_MEMORY_END`: addresses, but kept out of os.6502inc so the
  disassembler doesn't name every &3000 and &5800 after them), 6502 opcodes,
  and the 8271's commands.
- `src/teletext.6502inc`: Mode 7 control codes, `MODE7_SCREEN` and `TT_ROW`;
  `src/mode7_header.6502inc`: rows 0-9 of the Mode 7 pages, which WARNING and
  MENU's screen share.
- `src/sprites.6502inc`: the graphics set's format (sprite sizes, its layout
  `SET_*`, slots and their roles `SLOT_*`, `OBJECT_KINDS`,
  `OBJECT_NAME_LENGTH`, `EXIT_ICON`), then the picture notation
  (`mode5_pictures`, `mode5_byte`).
- `src/leveldata.6502inc`: the level format: field sizes, the setup bytes and
  `ALTERNATE_*`, all 16 `CELL_*`, `DIRECTION_*` with the diagonals,
  `MONSTER_GONE`, `TURN_*` and `PATTERN_*`, positions, objects, `PUZZLE_*`,
  `CONDITION_*`, `COLOUR_*` and `palette_entry()`, and the notation the
  levels are written in.
- `src/io.6502inc` (IO's layout; it includes leveldata.6502inc and
  sprites.6502inc), `src/level.6502inc` (where the Level Designer keeps a
  level; LEVEL1 and PL use it too), `src/basic.6502inc` (BASIC's program
  format and workspace), `src/hidden_loader.6502inc` (the three stubs),
  `src/forceabs.6502inc` (macros for absolute addressing of zero page).
- A program's own: `src/game.6502inc` (INCLUDEd inside the `game` scope, so
  it must not repeat a shared name), `src/levdes.6502inc` (the Level Designer
  and WDATA) and `src/wdata.6502inc`. Where a program numbers something its
  own way (the Level Designer's `MOVE_*`, the game's `DIRECTION_NONE` and
  `TURN_ROW`), the name is its own and its comment says how it differs.

## Tools

- `tools/dis6502.py hints/PIECE.toml > src/PIECE.6502`: first-draft
  disassembly from a hints file (binary, org, SECTION line, entry points,
  optional jsbeeb traces, labels, forced data ranges, local symbols). Run it
  once per piece, then edit the source by hand; don't regenerate over
  annotated work. Its output is guaranteed to reassemble identically
  (`tests/test_dis6502.py` checks this on every built binary).
- `node tools/beeb.mjs [--disc X.ssd] [--boot no] 'script; ...'`: headless
  jsbeeb (run `npm ci` once). `trace FILE` records executed PCs for the
  disassembler's `traces`; `shot`, `dump`, `hex`, `out`, `type`, `key`,
  `prompt`, `until` - see its header.
- `tools/mode7.py` (Mode 7 binary to `TT_ROW` source), `tools/beebscreen.py`
  (MODE 1/5 screen memory to PNG), `tools/plcrypt.py` (PL's encryption).
  Python tools use the standard library only.
- `tools/dis6502seg.py` wraps dis6502 for a binary that moves pieces of
  itself at startup: each moved piece becomes a nested, rephased section;
  also inline-data calls, jump tables and annotation. A drafting tool like
  dis6502: every piece's source is hand-edited once drafted.
- `node tools/play.mjs` plays the game headless (matrix keys, pokes,
  snapshots, random play, traces); `tools/traceranges.py` summarises a trace.
- `tools/beebscreen.py` also draws a CRTC-narrowed screen (`--columns`) from
  part-way into screen memory (`--offset`).
- `tools/graphics.py` draws a graphics set (DEFAULT's format) as a PNG, or
  writes it as picture source; `tools/graphic_tours.mjs` drives the Graphics
  Designer through scripted tours for traces and screenshots.
- `tools/basic.py` lists a tokenised BASIC program as text a baron `BASIC`
  block takes back; `src/basic.6502inc` has `basic_line()` for lines that
  must be EQUB records.
- `src/mission.6502` is NOT valid UTF-8: two REMs hold raw teletext bytes
  (&81-&86). Editors that decode as UTF-8 (including Claude's Edit tool)
  silently replace them and break the build; edit it with byte-safe tools
  (sed, or Python reading and writing bytes).

## The pieces

| Piece | Source | What it is |
|---|---|---|
| `!BOOT` | boot.6502 | `*EXEC` text: credits, `*FX200,3`, CHAIN"MENU" |
| MENU | menu.6502 | BASIC menu (`Originally: GUILDMASTER`) at &1900; its DIM'd heap holds the scroller (C% &2300) and menu screen (S% &3200) |
| MISSION | mission.6502 | BASIC "MISSION GENERATOR": builds IO from DEFAULT/graphics and level files; hides a code scrambler in a REM |
| GAME, GRAPHIC, LEVDES | game/graphic/levdes.6502 | &D9-byte stubs at &0900, one source (hidden_loader.6502inc), reading the hidden runs with OSWORD &7F |
| H.GAME | hidden_game.6502 | the game, all in scope `game`: loaded at &3000, copies itself to &0131, &0400, &0880 and &0900-&23AC, then loads IO |
| H.GRAPH | hidden_graphic.6502 | the Graphics Designer, at &1AB0 entered at &2BAE; edits graphics sets (DEFAULT) and IO directly, exits via /MRUN |
| H.LEVDES | hidden_levdes.6502 | the Level Designer, at &1100 entered at &2E21; moves pieces to &0880, &0400 and zero page; loads WDATA and LDATA, exits via /MRUN |
| TITLE | title.6502 | `*RUN` in MODE 1 before the game: unpacks the title picture over itself |
| MRUN | mrun.6502 | &80 bytes at &0780: restores the editors' vectors, back to the menu via `*E.!BOOT` |
| PL | pl.6502 | "Ian's cheat!": self-decrypting, run by MENU if W and T are held at boot; tools/plcrypt.py |
| WARNING, SCREEN | warning/screen.6502 | Mode 7 warning page (as rows); MODE 5 loading picture |
| WDATA | wdata.6502 (+ wdata.6502inc) | the Level Designer's windows and messages |
| LDATA | ldata.6502 | the Level Designer's title picture (raw MODE 1 screen, narrowed to 64 columns) |
| LEVEL1 | level1.6502 (data in level1.6502inc) | a level in the designer's save format, loaded by MISSION; the game's first level |
| DEFAULT | default.6502 (data in default.6502inc) | the default graphics set: 41 sprites and 15 object names |
| IO | io.6502 (layout in io.6502inc) | the game's data, ending at &5800, built as MISSION builds it from default.6502inc and level1-4.6502inc |

Shared data: `default.6502inc` describes the graphics set once (pictures as
pixel rows) in the format `sprites.6502inc` defines; `level1.6502inc`-
`level4.6502inc` describe the four levels once each (objects, monsters,
triggers, the map as strings) in the format `leveldata.6502inc` defines.
DEFAULT, LEVEL1 and IO are all emitted from these.

## Baron notes

- `&` hex, `.label`, `;` comments, `SECTION name, filename=..., org=..., load=..., exec=...`.
- Load/exec are 32-bit host addresses: `&FFFF1900` for an I/O-processor
  BASIC file, `&FFFFFFFF` for `!BOOT`.
- No syntax forces absolute addressing of a zero-page operand. Where the
  original does that, use a macro emitting `EQUB opcode : EQUW addr`
  (overloads by shape: `MACRO LDA_ABS addr` and `MACRO LDA_ABS addr, "X"`).
- `INCBIN` takes a whole file; to convert part of a binary, split the binary.
- List literals may span lines (`{1, 2,` newline `3}`); no need to build long
  tables in groups with CONCAT.
- Character literals: `'A'` is 65 (`'"'` works; `'` itself can't be written,
  so it's 39). Prefer `'A'` to a FUNCTION: every FUNCTION call leaves a
  frame in the symbol dump.
- `docs/baron-feedback.md` collects baron issues and wishes; check it before
  filing anything (issues are filed as Claude acting for Matt).
- The symbol dump (format 2, baron 0.5) gives each file's sections, with
  their attributes, and each symbol's value, source and line, grouped by
  kind: `labels` (always addresses), `assignments`, `params`, `loop_vars`...
  FUNCTION and macro parameters and FOR variables sit under `@...` scopes;
  anything feeding jsbeeb should drop them (`tests/test_symbols.py`'s
  `load_symbols()` does). Every FUNCTION call leaves a frame of its
  parameters; a MACRO that calls a FUNCTION leaves null frames in every file
  that includes it, even if it's never used, so keep such macros out of
  widely included files. Every file's dump also lists every constant its
  includes define.
- A scope may define a name its file already has outside it, and inside the
  scope the inner one silently wins. Don't rely on it (tests/test_symbols.py
  fails on it).
- A file defining FUNCTIONs can be INCLUDEd only once in a program
  ("Duplicate function arity"); constants may be bound again to the same
  value. So each program reaches each include by one path: io.6502inc brings
  sprites.6502inc, and default.6502inc leaves including it to its includer.
- Named scopes (`.game { ... }`) give dotted symbol paths in the dump; use them
  so labels from overlapping programs (GAME, LEVDES, GRAPHIC and IO overlap in
  memory) stay distinguishable.

## Annotation standards

- Every label meaningful; no `L1234` left in finished code.
- Comments say why, not what; every routine gets a header saying what it's
  for, its inputs, outputs and what it clobbers.
- No hard-coded addresses for anything inside the program: labels and
  expressions (`table_end - table`). OS calls and hardware by name from a
  shared include.
- Data tables documented with their structure.

## Working method

- `docs/journal.md` is append-only and timestamped: discoveries, decisions,
  dead ends. Correct with a later entry, don't rewrite history.
- `docs/overview.md` is the reader's guide to the code: how the programs
  hand over, what's where in memory while each runs, and the routines to
  read first, with addresses. `tests/test_symbols.py` checks those addresses
  against the build, so renaming or moving a routine it lists means
  updating it. The README's "How the code works" stays a paragraph or two
  and points there.
- Use subagents in git worktrees for independent pieces (their own source
  files, so merges don't fight). Each subagent leaves `make test` passing at
  every commit on its branch, and writes what it learns to
  `docs/notes/AREA.md` (its own file, so parallel branches don't collide).
  The journal is appended by whoever merges, summarising the notes.
- Shared files (`src/os.6502inc`, `src/osconst.6502inc`, `src/sprites.6502inc`,
  `src/leveldata.6502inc`, `src/io.6502inc`, `Makefile`, `src/disc.toml`,
  `CLAUDE.md`) change on main, not on piece branches. A piece needing shared
  definitions from another piece (an entry point, a zero-page variable)
  keeps its own `src/PIECE.6502inc` and says so in its notes.
- Running the game: the jsbeeb MCP (`.mcp.json`), or headless jsbeeb from
  node. Check behaviour there, not just bytes, when understanding code.
- Commits: messages end at the `Co-Authored-By:` line. Never put a
  claude.ai session link or `Claude-Session:` trailer in anything that leaves
  the machine (commits, PRs, issues); pass the same rule to subagents.
