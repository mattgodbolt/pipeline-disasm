# BASIC pieces: MENU and MISSION

Notes from converting the two BASIC programs to baron source. Times are US
Central.

## 2026-10-03 18:10 — Tokenising, and what baron can't take

- `tools/basic.py FILE` lists a tokenised program as text a BASIC block
  takes back; `--offsets` adds each record's address and flags (`!`) lines
  holding bytes with no plain-text form, shown as `{&XX}`. Fed back through
  baron, every line of both programs (and MENU's hidden tune) tokenises to
  the original bytes: no spacing or keyword quirks at all.
- The only trouble is bytes. A BASIC line is copied byte for byte from the
  source, so control codes and top-bit-set bytes inside REMs and strings
  must be raw in the source file. Plain ASCII control codes are tolerable
  (they survive editing); top-bit-set bytes make the file invalid UTF-8,
  and Claude's Edit tool silently turns them into U+FFFD (tested); a
  newline (MISSION line 60 has &0A in its machine code) can't be in a line
  at all.
- `ENDBASIC` always writes the &0D &FF end marker, so a block can't be
  split around a line written as EQUB: anything EQUB'd has to come before
  the one BASIC block. Both programs open with their awkward lines, so:
  - MENU: lines 10-40 are EQUB records (`basic_line()` in
    `src/basic.6502inc`), lines 50-1020 a BASIC block. Line 290 carries two
    raw bytes, VDU 21 and VDU 6 (ASCII, so the file stays UTF-8).
  - MISSION: lines 10-60 are EQUB (line 60 holds machine code, now
    disassembled in place), 70-2890 a BASIC block. Lines 1430 and 2780 are
    REMs with raw teletext colour codes (&81-&86), so `src/mission.6502` is
    NOT valid UTF-8; its header warns. Edit it with sed or Python bytes.
- FUNCTION and macro parameters appear in baron's symbol dump under
  anonymous scopes (`@5:6257.column`); anything reading `build/symbols.json`
  for jsbeeb should drop names starting `@`.

## 2026-10-03 18:10 — Listing tricks

- LIST copies a string's bytes straight to the screen, and inside a REM it
  still expands tokens unless a quote has started a "string". So the REMs
  start `REM"` and then VDU 127 to erase the quote, and what follows is
  teletext control codes: MENU line 40 and MISSION line 60 print a double
  height "Hello, all my friends!" band, MISSION 10-50 the title and
  credits in colour, 1430 "Hello, Soni", 2780 "This subroutine was
  written by William Reeve (mainly)".
- MENU line 290 hides the cheat: the second-processor message ends with
  VDU 21 (output off) inside its string, and `*/PL "` + VDU 6 turns it
  back on, so LIST shows `...re-load this program.":IFGET` and nothing of
  `ELSE IF INKEY-36 AND INKEY-34 THEN */PL` (T and W held down at that
  moment run PL). The `":IFGET` is part of the `*` command, so DFS ignores it.
- MISSION line 60 does the same with machine code: after the Hello band,
  VDU 21, then 28 bytes of code, then VDU 6. FNn CALLs it at PAGE+198.

## 2026-10-03 18:10 — MENU (by Ian Holmes, "Originally: GUILDMASTER")

Load &1900, exec &8023, &2000 bytes. Every byte:

| Address | What |
|---|---|
| &1900-&22FF | the program (TOP = &2300) |
| &2300-&23C8 | C%: the scroller's code (CALL C%, vsync handler) |
| &23C9-&31FF | C%: the scroll message, zero-terminated (exactly fills `DIM C% &EFF`) |
| &3200-&347F | S%: the menu screen's top 16 Mode 7 rows, copied to HIMEM by PROCmenu |
| &3480-&34FF | unused: a blank row holding a stray zero, and a 0-terminated message "What colour is acidified KMnO4 ? ..." |
| &3500-&3883 | a separate BASIC program (a three-voice tune), at PAGE+&1C00; line 1020 `PAGE=PAGE+&1C00:RUN` runs it, but no line leads there |
| &3884-&38FF | the tail of the Level Designer's BASIC assembler source (lines 3890-3950, cut off by the end of the file): `CMP#4:BEQcanc:STAt2`, `.key3:LDA#62`... |

- `LOMEM=PAGE+&A00` puts the heap exactly at TOP, so `DIM C% &EFF` gives
  C% = &2300 and `DIM S% &700` gives S% = &3200 (checked in jsbeeb:
  &040C = &2300, &044C = &3200). DIM doesn't clear memory, so the file's
  bytes are the DIMs' contents.
- Line 300, `!&75=(C%+&49)*65536+C%+&C9`, passes the message address in
  &75/&76 and the handler address in &77/&78. C%+&49 is four bytes short of
  the handler (&234D): it lands on the operand of the init's `LDX #4`, and
  the bytes from there run as `04 4C` / `F4 FF`, undocumented NMOS NOPs, so
  it works on a BBC B (traced in jsbeeb: &2349 and &234B execute every
  frame). On a 65C02 &04 is TSB &4C.
- The scroller: OSBYTE &0E,4 enables the vsync event; each frame the
  handler moves rows 17-24, columns 2-37, one cell left, reads the current
  character's definition with OSWORD &0A and fills column 37 with a solid
  block per lit pixel of one column of it. The column advances every other
  frame (&60 flips between &49 and 0), so each character is 16x8 cells.
  Columns 0-1 of each row get separated-graphics cyan.
- Zero page: &60 (frame toggle), &70/&71 (temp), &72/&73 (message
  pointer), &74 (pixel mask), &75/&76, &77/&78 (from BASIC), &79-&8A (row
  pointers; &7B-&8A used), &8B-&93 (OSWORD &0A block; spills past &8F).
- The game's keys: line 280 reads ten negative INKEY numbers into &50-&59,
  as their low bytes (-98 is &9E, the form OSBYTE &81 takes in X): defaults -98 Z, -67 X, -73 * (:), -105 ?, -56 P, -51 D, -74
  RETURN, -36 T, -2 CTRL, -102 M; option 2 redefines them, storing `-P%`.
  The names shown are Guildmaster's (MOVE WEST ... VIEW MAP). H.GAME
  presumably reads &50-&59.
- Setup before the menu: restores every vector in page 2 to the MOS
  defaults from the table at !&FFB7 (length ?&FFB6) but keeps BRKV
  (BASIC's); `*FX255 8 247` sets start-up option bit 3 so plain BREAK
  boots the disc; `*FX200 2` clears memory on BREAK; `*FX229 1` makes
  Escape a key; `*FX4 1` cursor keys give 136-139; `*FX9 1`/`*FX10 1`
  flash colours every frame; `*TV255 1`; MODE 5 and `*L.SCREEN` (the
  loading picture), 10 s; then the second-processor check, `*L.WARNING`,
  10 s, and the menu.
- Line 60-80: `ON ERROR GOTO 80` around `*SHADOW 1` (a B+/Master keeps the
  screen in main memory; a B gives "Bad command"), then
  `ON ERROR AWopBabaLuMopALopBamBoom` (Little Richard): the handler is
  itself an error, so any error hangs the machine (checked in jsbeeb).
- The second-processor check (`?&FFFF7C00=128:?&7C00=0`, then
  `IF ?&FFFF7C00>0`) can never fire: BASIC 2's indirection only uses the
  low 16 bits, so both are &7C00 (checked in jsbeeb). If it did, it would
  print the message, OSBYTE 151 writes &7F to the system VIA's IER (all its
  interrupts off) and it loops forever.
- Options: 1 `*FX230 1`, `*FX11`, MODE 1 with the palette black, `*RUN
  TITLE`, palette 0,1,4,7 (DATA 1000), 3 s, MODE 7, `*/GAME`; 2 redefine
  keys (Escape restarts the list; keys 3-16 and nameless ones refused; a
  repeat refused); 3 `*/GRAPHIC`; 4 `*/LEVDES`; 5 `CHAIN"MISSION"`;
  6 "Are you sure?" then `CALL !-4`, which jumps through the reset vector.
  Before 1, 3, 4, 5 it stops the scroller (`*FX13 4`) and sets
  `LOMEM=TOP`.
- PL is self-decrypting (EORs pages &04-&06 with its own bytes) - for
  whoever does PL.

## 2026-10-03 18:10 — MISSION (Ian Holmes) and the IO format

Load &1900, &1828 bytes; the file ends with the program. On tape
(`OSARGS 0,0` returning 1 or 2) T% is TRUE: no catalogue option, DEFAULT
isn't loaded, and quitting resets the machine instead of `*/MRUN`.

Sizes, from PROCinit:

```
numlev = 4        levels in a mission
size   = &91F     one level: data + &800 map
data   = &11F     one level's fields (size - &800)
grfs   = &E00     graphics
attrs  = 5        mission features
miss   = 30       mission text
names  = &134     what a graphics file carries after its graphics
puznms = 320      a level file's puzzle names (32 x 10)
```

### Mission file (IO is one)

Saved by PROCsavemss: `SAVE F% +&33D3, exec 0, reload addr`, where
`addr = &5800-numlev*size-grfs-attrs-miss-names` = &242D, so the file
always ends at &5800. IO matches: load &242D, &33D3 bytes.

| Offset | Size | What |
|---|---|---|
| &0000 | &134 | `names`: copied from the graphics file's tail. In IO (and DEFAULT): &00-&7F look like graphics, &80-&133 are 15 object names of 12 characters: Remote C.D.1-3, Blueprints, Mallet, Spanner, Screwdriver, Magnet, Space Burger, Jovian Wine, Fire Blanket, Laser Gun, Extinguisher, Detonator, Explosives |
| &0134 | 30 | the mission's name ("change name"; the game prints it): two 15-byte halves, each VDU 31,x,y then 12 characters, spaces stored as 9 (cursor right, so the background shows). MISSION writes 31,18,16 and 31,14,17. IO: "Collect the" / "Sulphur!" |
| &0152 | 5 | features: time consumption (stored as shown + 6; shown 1-16), mapping ability (0-4), backpack size (stored as shown - 1; shown 1-4), throwing distance (0-63), lock (0; 1 or &FF when saved with the secret keys, below). Defaults 15, 2, 2, 6, 0. IO: 15, 4, 2, 6, &FF (locked) |
| &0157 | &247C | four levels (L%): first the fields, then the maps |
| &25D3 | &E00 | graphics (G%), as in a graphics file |

The levels block keeps each field for all four levels together: field f
of level s is at `L% + numlev*pnt(f) + s*ext(f)`, with the field sizes
from DATA 2090 (`pnt` is the running total):

| Field | ext | pnt | Offset in L% (levels 0-3) |
|---|---|---|---|
| 0 | 1 | 0 | &000-&003 |
| 1 | 1 | 1 | &004-&007 |
| 2 | 1 | 2 | &008-&00B |
| 3 | 4 | 3 | &00C-&01B |
| 4 | 8 | 7 | &01C-&03B |
| 5 | 32 | 15 | &03C-&0BB |
| 6 | 16 | 47 | &0BC-&0FB |
| 7 | 32 | 63 | &0FC-&17B |
| 8 | 64 | 95 | &17C-&27B |
| 9 | 64 | 159 | &27C-&37B |
| 10 | 64 | 223 | &37C-&47B |

then level s's &800-byte map at `L% + &47C + s*&800`. MISSION doesn't
interpret the fields beyond: fields 0-2 are each level's scrambled editing
code (below). PROCinit leaves fields 0-2 alone (bar L%+0), sets field 3
of every level to 31 22 14 00 (`1319473`), fills fields 4-10 with &FF and
the maps with 0.

### Level file (LEVEL1 is one)

Saved by PROCsavelev: `SAVE B% +&A5F, exec &8380, reload &25A1` (so it
ends at &3000): 320 bytes of puzzle names (32 names of 8 characters at
+0, then 32 two-character suffixes at +256 - MISSION overwrites them all
with "Puzzle N" when it saves), the level's &11F bytes of fields in order,
then its &800 map. LEVEL1 is identical to IO's level 0.

### Graphics file (DEFAULT is one)

Saved by PROCsavegrf: `SAVE G% +&F34, exec 0, reload &4000`: &E00 of
graphics then the &134 `names`. DEFAULT's graphics and names are
identical to IO's.

Run in jsbeeb, MISSION starts with features 9, 2, 3, 6 (DEFAULT loaded),
and loading IO shows its name as "Collect the" / "Sulphur!".

### What MISSION loads and saves

- Loads: DEFAULT at start (disc only), any graphics file (option 3), a
  level into level slot 1-4 (option 5), a whole mission (option 7, with
  no checks). Shows `*CAT` of a chosen drive (option 9).
- Saves: graphics (4), a level (6), a mission (8). Quitting (Escape, Y)
  asks for the PIPELINE disc and does `*/MRUN`.

### The lock and the editing code

- In the option menu, `i` or `h` jumps straight to "save a mission" with
  the lock byte set to 1 or &FF (PROClock: `I%=A%*2-209`).
- A mission whose lock byte is non-zero can't be saved again, and saving
  one of its levels (option 6) asks for the "editing code": six digits,
  read as hex (`EVAL("&0"+...)`) into E%, then CALL PAGE+198 unscrambles
  each of E%'s low three bytes (swap adjacent bits, then rotate right one).
  It must equal level s's fields 0, 1, 2 (high to low). For IO the codes
  are level 1: 677636, 2: 878702, 3: 218652, 4: 114226 (checked in jsbeeb:
  `E%=&677636:CALL PAGE+198` leaves &CDDC9C).
- Loading a locked mission (option 7) isn't checked at all.

## For the other pieces

- H.GAME: IO's layout above; the keys in &50-&59. IO's load address
  (&242D-&57FF) overlaps H.GAME's &3000-&50FF, so the game must load it
  elsewhere or before itself.
- LEVDES/GRAPHIC: the level and graphics file formats above; where the
  fields and `names` come from.
- H.LEVDES: the source fragment at the end of MENU assembles to its
  &168A-&16A6 (`LDA#37:JSRsel0`, `CMP#4:BEQcanc:STAt2`, `JSRsure:LDAt2`,
  `LDY#7:BNEtable`, `.key3:LDA#62`, `JSRwind:LDA#0`, `BEQhelp:.simt...`),
  so the original names: sel0 &1126, canc &1637, t2 &54, sure &1323,
  table &166B, key3 &169E, wind &14A8, help &16AD, simt... &16A7 (taking
  H.LEVDES to run at &1100).
- `src/teletext.6502inc` (Mode 7 control codes, `mode7_address()`) is
  general; WARNING may want it. `src/basic.6502inc` has the BASIC record
  format and VDU 6/21/127 names.
- OS call numbers defined locally in `src/menu.6502` (OSBYTE &0E, OSWORD
  &0A, event 4) belong in `src/os.6502inc` when someone adds call numbers
  there.
