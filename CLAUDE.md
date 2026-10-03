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

## Baron notes

- `&` hex, `.label`, `;` comments, `SECTION name, filename=..., org=..., load=..., exec=...`.
- Load/exec are 32-bit host addresses: `&FFFF1900` for an I/O-processor
  BASIC file, `&FFFFFFFF` for `!BOOT`.
- No syntax forces absolute addressing of a zero-page operand. Where the
  original does that, use a macro emitting `EQUB opcode : EQUW addr`
  (overloads by shape: `MACRO LDA_ABS addr` and `MACRO LDA_ABS addr, "X"`).
- `INCBIN` takes a whole file; to convert part of a binary, split the binary.
- `BASIC`...`ENDBASIC` tokenises BBC BASIC inline; worth trying for MENU and
  MISSION, checking the tokenisation matches byte for byte.
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
- Use subagents in git worktrees for independent pieces (one source file
  each, so merges don't fight). Each subagent must leave `make verify`
  identical and add its findings to the journal (append, under its own
  timestamped heading) before its branch is merged.
- Running the game: the jsbeeb MCP (`.mcp.json`), or headless jsbeeb from
  node. Check behaviour there, not just bytes, when understanding code.
- Commits: messages end at the `Co-Authored-By:` line. Never put a
  claude.ai session link or `Claude-Session:` trailer in anything that leaves
  the machine (commits, PRs, issues); pass the same rule to subagents.
