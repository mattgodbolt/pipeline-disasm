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
- `src/os.6502inc`: MOS entry points, vectors and hardware registers -
  addresses only. INCLUDE it; add OS names there rather than locally (one
  name per address). The disassembler names operands from it, except zero
  page.
- `src/osconst.6502inc`: OSBYTE/OSWORD numbers, buffers, events, internal
  key numbers, the 8271's commands, `ascii()`.
- `src/teletext.6502inc`: Mode 7 control codes and `TT_ROW`.
- `tools/mode7.py` (Mode 7 binary to `TT_ROW` source), `tools/beebscreen.py`
  (MODE 1/5 screen memory to PNG), `tools/plcrypt.py` (PL's encryption).
  Python tools use the standard library only.
- `tools/dis6502seg.py` wraps dis6502 for a binary that moves pieces of
  itself at startup: each moved piece becomes a nested, rephased section.
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
- `src/forceabs.6502inc`: macros for absolute addressing of zero page.

## The pieces

| Piece | Source | What it is |
|---|---|---|
| `!BOOT` | boot.6502 | `*EXEC` text: credits, `*FX200,3`, CHAIN"MENU" |
| MENU | menu.6502 | BASIC menu (`Originally: GUILDMASTER`) at &1900; its DIM'd heap holds the scroller (C% &2300) and menu screen (S% &3200) |
| MISSION | mission.6502 | BASIC "MISSION GENERATOR": builds IO from DEFAULT/graphics and level files; hides an unscrambler in a REM |
| GAME, GRAPHIC, LEVDES | game/graphic/levdes.6502 | &D9-byte stubs at &0900, one source (hidden_loader.6502inc), reading the hidden runs with OSWORD &7F |
| H.GAME | hidden_game.6502 | the game, run at &3000; loads IO |
| H.GRAPH | hidden_graphic.6502 | the Graphics Designer, at &1AB0 entered at &2BAE; edits graphics sets (DEFAULT) and IO directly, exits via /MRUN |
| H.LEVDES | hidden_levdes.6502 | the Level Designer, at &1100 entered at &2E21; moves pieces to &0880, &0400 and zero page; loads WDATA and LDATA, exits via /MRUN |
| TITLE | title.6502 | `*RUN` in MODE 1 before the game: unpacks the title picture over itself |
| MRUN | mrun.6502 | &80 bytes at &0780: restores the editors' vectors, back to the menu via `*E.!BOOT` |
| PL | pl.6502 | "Ian's cheat!": self-decrypting, run by MENU if W and T are held at boot; tools/plcrypt.py |
| WARNING, SCREEN | warning/screen.6502 | Mode 7 warning page (as rows); MODE 5 loading picture |
| WDATA | wdata.6502 (+ wdata.6502inc) | the Level Designer's windows and messages |
| LDATA | ldata.6502 | the Level Designer's title picture (raw MODE 1 screen, narrowed to 64 columns) |
| LEVEL1 | level1.6502 (+ level.6502inc) | a level in the designer's save format, loaded by MISSION; the game's first level |
| DEFAULT | default.6502 (+ sprites.6502inc) | the default graphics set as pixel pictures: 41 sprites and 15 object names |
| IO | io.6502 | the game's data (ends at &5800: names, mission, levels, graphics) |

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
- Stepped ranges whose limit equals their second element fail
  (`0..2..2`: "Argument out of domain"); write `0..2..3` or a list.
- The symbol dump also holds FUNCTION and macro parameters under `@...`
  scopes; anything feeding jsbeeb should drop names starting with `@`.
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
- Use subagents in git worktrees for independent pieces (their own source
  files, so merges don't fight). Each subagent leaves `make test` passing at
  every commit on its branch, and writes what it learns to
  `docs/notes/AREA.md` (its own file, so parallel branches don't collide).
  The journal is appended by whoever merges, summarising the notes.
- Shared files (`src/os.6502inc`, `Makefile`, `src/disc.toml`, `CLAUDE.md`)
  change on main, not on piece branches. A piece needing shared
  definitions from another piece (an entry point, a zero-page variable)
  keeps its own `src/PIECE.6502inc` and says so in its notes.
- Running the game: the jsbeeb MCP (`.mcp.json`), or headless jsbeeb from
  node. Check behaviour there, not just bytes, when understanding code.
- Commits: messages end at the `Co-Authored-By:` line. Never put a
  claude.ai session link or `Claude-Session:` trailer in anything that leaves
  the machine (commits, PRs, issues); pass the same rule to subagents.
