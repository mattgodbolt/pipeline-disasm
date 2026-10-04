# Notes: the boot chain and small loaders

GAME, GRAPHIC, LEVDES (stub loaders), !BOOT, MRUN, PL, TITLE, WARNING,
SCREEN. Times are US Central.

## 2026-10-03 17:54 — The stub loaders and the protection

GAME, GRAPHIC and LEVDES are one program assembled three times
(`src/hidden_loader.6502inc`, INCLUDEd by `src/game.6502`, `graphic.6502`,
`levdes.6502` inside a named scope each: `game_loader`, `graphic_loader`,
`levdes_loader`). The three differ in exactly six bytes, all from four
numbers per stub:

| Stub | Hidden run | Sectors | Track/sector | Load | Entry |
|---|---|---|---|---|---|
| GAME | H.GAME | &122, &21 of them | 29/0 - 32/2 | &3000 | &3000 |
| GRAPHIC | H.GRAPH | &145, &21 | 32/5 - 35/7 | &1AB0 | &2BAE |
| LEVDES | H.LEVDES | &16D, &1F | 36/5 - 39/5 | &1100 | &2E21 |

The differing bytes: the first sector within the track (`LDA #`), first track
(`LDX #`), sector count (`LDY #`), the low byte and page of the buffer address
in the read block, and the `JMP` to the entry. Ends: H.GAME &3000-&50FF,
H.GRAPH &1AB0-&3BAF, H.LEVDES &1100-&2FFF. These confirm the STH crack's
addresses.

How it loads (all OSWORD &7F, i.e. raw 8271 commands via DFS, drive 0 only):

1. Seek to track 0 (the seek block's track byte starts at 0): a recalibrate.
2. Read ID (&5B) on track 4, one ID into `id_buffer` (the last four bytes of
   the file). This is the `CMP #&04`: if the ID's track number isn't 4, the
   drive is an 80-track drive with this 40-track disc, it landed on the
   disc's track 2, and `double_step` is set to &FF.
3. Per track: read (&57, read data *and deleted data*) from the current
   sector to the end of the track or of the run, whichever comes first
   (`min(10 - sector, left)`, count | &20 for 256-byte sectors), step the
   buffer page by the count, sector back to 0, track + 1.
   With double stepping: before the read, seek to 2*track (the 8271 counting
   physical tracks), then write special register &12 (drive 0's current
   track) := track so the read's track matches the sector IDs; after it,
   write &12 := 2*track again so later seeks start from the right place.
4. `JMP` to the entry.

The protection, seen on the flux captures (E447ED5E, the target, and
`Pipeline_FSD0391_1.hfe` in the local HFE archive cache; read with
jsbeeb's `loadHfe`, whose sectors carry `isDeleted`): every sector of the
three hidden runs, and only
those, is written with a **deleted data address mark**. The .ssd can't
represent that, which is why original/README.md's "the capture decodes
cleanly ... any protection is in the software" is only half right. So the
scheme is two layers:

- the runs are past the last catalogued file and no catalogue entry names
  them, so `*COPY` copies only the stubs;
- the deleted marks make the 8271 end every read of them with result &20.
  DFS reports any nonzero result as a disc fault, so a `*BACKUP` of the disc
  should stop at track 29. The stub uses command &57, which transfers deleted
  sectors, and doesn't look at the result.

Checked in jsbeeb against the HFE capture: after `*/GAME` the read block's
result byte is &20; from BASIC, OSWORD &7F reads of track 29 return &20 with
both &53 (read data) and &57, and 0 on track 28. On the .ssd every read
returns 0.

The result check is dead code. After each read, `LDA read_result` is followed
by `NOP : JMP next_track_or_run`, which jumps over a BRK error block
(`BRK`, &FF, "Sector read fault!", 0). Those seven bytes are exactly the room
for `LDA result / two-byte test / BEQ next`, falling into the BRK on failure.
Since every read of the real disc returns &20, a test for zero could never
pass, so it looks like a check patched out after the protection was added.
The error block is unreachable.

Double stepping (step 2's other branch) isn't exercised by jsbeeb: it loads
an .ssd as a 40- or 80-track disc to match its catalogue, and either way
track 4's ID says 4. Untested beyond reading the code.

Zero page used: &70 (`sectors_this_read`), &72 (`sectors_left`). Nothing else
outside the stub's own &0900-&09D8 is written, apart from what the 8271 reads
into the load area.

## 2026-10-03 18:05 — !BOOT and MRUN

- `!BOOT` is now one `EQUS "...", CR` per line. `?&224=?(&24+!&FFB7)` puts
  back the low byte of NETV from the MOS's default vector table (&FFB7 holds
  that table's address; &24 is NETV's offset). Nothing on the disc touches
  NETV (searched every binary for &0224), so it's presumably undoing a ROM or
  an earlier program; MENU later restores every vector except BRKV the same
  way.
- MRUN (&0780) is how the editors get back to the menu: it restores RDCHV
  (which the Level Designer hooks, at &15D4 in H.LEVDES) and EVNTV (the
  Graphics Designer's, &2BC3 in H.GRAPH) from the default table, disables the
  Escape event (the Graphics Designer enables it), then pushes
  `*E.!BOOT`, CTRL-V CTRL-G, two spaces, CR into the keyboard buffer with
  OSBYTE &8A and does `*BASIC`. BASIC's line input echoes the control codes
  (so MODE 7 happens as it's "typed") and runs `*E.!BOOT`, so the whole boot
  file runs again. Checked in jsbeeb: `*/MRUN` from BASIC lands back on the
  loading picture and menu. The first instruction is `LDX #6` twice, harmless.
  The file's last 29 bytes are 13 zeros then 16 bytes of stale memory, kept
  as data; the slack past it is in disc.toml.
- Shared constants for these pieces are in `src/loaders.6502inc` (OSBYTE and
  event numbers, the default-vector-table pointer); they belong in
  `src/os.6502inc` once that can change on main.

## 2026-10-03 18:11 — WARNING, and PL is "Ian's cheat!"

- WARNING is *LOADed by MENU (line 295) straight into Mode 7 screen memory
  at &7C00 and shown for up to ten seconds (`docs/img/warning.png`). Rows
  0-15 are the same picture the menu uses (PIPELINE logo, credits, pipe
  frame) with a flashing "WARNING" and "All Rights Reserved" inside the
  frame; rows 18-22 the text. The file ends 16 bytes into row 22. Now source
  as one checked `TT_ROW` of 40 per line (`src/teletext.6502inc` names the
  control codes; `tools/mode7.py` writes that form from any Mode 7 binary,
  which MENU's own screen may want).
- MENU line 290 runs `*/PL` when W and T (INKEY-34, INKEY-36) are held as it
  starts; confirmed in jsbeeb by booting with both held. The rest of the line
  (`"<VDU 6>":IFGET`) is passed to PL as a command tail it never reads.
- PL decrypts itself: from &043C (the offset byte of its own BMI into the
  plain code) to &06FB, `plain = key ^ previous plain ^ stored`, keys taken
  from its own decryptor bytes (&0404, &0403, &0402 for pages 4-6); &0500
  and &0600 are stored plain. `tools/plcrypt.py` does it offline.
- Decrypted, it's "Ian's cheat!": MODE 7 with nothing shown, reads a
  filename and a six-digit code with no prompt, *LOADs the file (a Level
  Designer level file, loaded at &25A1 like LEVEL1), checks the code against
  three bytes at &26E1 (each BCD byte of the code, bit pairs swapped and
  rotated right one, must match), and lists the file's 32 puzzles: name (8
  chars at &25A1+8n, 2 at &26A1+2n), action (low nibble of &2720+n, one of
  16: Place block, Move block, ... Disorientate), and On/Off (bit 5 set =
  Off). LEVEL1's code is 677636; seen working in jsbeeb.
- After a key it floods the screen with a fake BASIC "Bad program" error
  until I, N, O and S are held together; then beeps, sets &61 to 3, does
  `*FX229,0` and `*FX230,1`, `*L.GAME`, and pokes the game: &3FC7 (operand
  of `LDX #3 : STX &2E` in H.GAME) := 31; &4875 (offset of a `BEQ +3` over
  `JMP &1C13`) := 0; &4F31-&4F32 (`STA &61`) := NOP NOP; then `JMP &3000`.
  On this disc GAME is the stub, so &3000 holds no game and the machine
  resets (seen in jsbeeb). PL predates the hidden sectors: it expects GAME to
  be the game at &3000, as in the STH crack. **For the hidden_game agent:**
  those four places in H.GAME are what Ian's cheat changed; &2E starts at 3
  and &61 is set from `JSR &0D7E` at &4F2E.
- Anti-tamper in PL: BRKV is pointed at the reset entry (any error resets);
  `*FX200,2` (BREAK clears memory) every listed line; a wrong code resets; a
  counter checks all three code compares ran; a test of pushed flags that
  can never fail (B and I always set) dressed as a check; format characters
  stored inverted; patch addresses formed with index registers.
- Source: `src/pl.6502` has the decryptor as code, the stored bytes as
  `data/pl_encrypted.bin`, and the decrypted program as annotated source in
  a second section saved as `build/files/PLDEC` (not on the disc). Baron
  can't transform a section's bytes, so the two are tied by
  `tools/plcrypt.py check build/files` rather than by the build.

## 2026-10-03 18:25 — TITLE

- MENU option 1 (lines 910-960): `*FX230 1`, `*FX11`, MODE 1 with all four
  colours black and the cursor off, `*RUN TITLE`, then palette 0,1,4,7
  (black, red, blue, white), `INKEY(300)`, MODE 7, `*/GAME`. The menu is
  driven by digits to choose and RETURN to go (`key Digit1; key Enter` in
  beeb.mjs), which is why a bare digit didn't start anything.
- TITLE is a packed MODE 1 picture at &6300-&78FF and &79 bytes of code at
  &7900: "PIPELINE by IAN HOLMES and WILLIAM REEVE" (`docs/img/title.png`).
  The code copies its own page to &2F00 (just below the screen; the copy
  starts at the Y *RUN leaves, 5 under DFS 1.2) and unpacks there into
  &3000 upward, over the file itself. Packing: nonzero bytes are literal; 0,
  n is n zeros (0 = 256). The stream overruns: it writes past &8000 (paged
  ROM space; harmless on a B, would hit sideways RAM) and catches up with
  its own unread tail only at &78D6, below the picture, and the code clears
  &7800-&7FFF afterwards, then `*FX15,1` and back to BASIC. Checked the
  unpacked screen against jsbeeb's memory after `*RUN TITLE`: identical
  apart from BASIC's prompt.
- Source: the code is source, with the unpacker as a nested rephased
  section (org &2F18) so its labels are where it runs; the packed picture is
  `data/title_picture.bin`.
- `tools/beebscreen.py` renders MODE 1/5 screen memory to PNG (with
  `--title` to unpack TITLE's format first). The SCREEN render with palette
  0,1,3,5 matches the jsbeeb screenshot in `docs/img/loading-screen.png`.

## 2026-10-03 18:35 — SCREEN, and what's left for main

- SCREEN is the whole of MODE 5 screen memory (&5800-&7FFF) saved as it
  stood; MENU line 250 *LOADs it after `MODE 5`, cursor off and
  `VDU 19,3,5` (palette black, red, yellow, magenta), for `INKEY(1000)`. The
  picture fills the top 27 character rows; the last five are zero, now a
  `SKIPTO` rather than part of `data/screen.bin`.
- Still binary, on purpose: `data/screen.bin` (a picture),
  `data/title_picture.bin` (a packed picture), `data/pl_encrypted.bin`
  (PL's stored bytes, regenerable from source with tools/plcrypt.py).
- For main:
  - `src/loaders.6502inc` (OSBYTE/OSWORD numbers, CPU vectors, INKEY key
    numbers, `ascii()`) and the OSWORD &7F / 8271 names at the top of
    `src/hidden_loader.6502inc` belong in `src/os.6502inc`;
    `src/teletext.6502inc` could be shared as it is (MENU's Mode 7 screen).
  - `make test` should run `python3 tools/plcrypt.py check build/files`, so
    PL's encrypted bytes and its decrypted source can't drift apart.
  - `original/README.md` says any protection is in the software; the hidden
    runs' deleted data marks say otherwise.
  - CLAUDE.md's table: PL is "Ian's cheat" (W+T at boot), not just "&400".

## 2026-10-03 20:54 — Second review: corrections and checks

Every claim in the small pieces' comments was read against the code, and
the behavioural ones run in jsbeeb (headless, `tools/beeb.mjs` and small
scripts using its `startBeeb`). Corrections first, then what was confirmed.

### Corrections

- **TITLE's overrun** was described as catching up with "its own unread
  tail only at &78D6". Precisely: simulating the unpacker, and recording
  what it writes in jsbeeb, the unpacking passes the read pointer there and
  zeros the packed data's last 41 bytes (&78D7-&78FF) before reading them.
  They read as `0, 0` pairs, runs of 256 zeros, which carry the writing to
  **&8DB1** (jsbeeb's write record: &8000-&8DB1, 3506 bytes into paged ROM
  space). The output from those stale bytes all lands at &79B2 and above,
  under the picture. So the final clear of &7800-&7FFF changes nothing: the
  overrun has already left it zero.
- **PL's cheat**, mapped onto hidden_game.6502 (H.GAME as loaded at &3000;
  the game runs the code copied down to &0900 on):
  - &3FC6 is `new_game`'s `LDX #START_LIVES : STX lives`: the cheat gives
    **31 lives**.
  - &4874 is `mission_done_screen`'s `BEQ show_entry_code` over `JMP
    wait_for_space`: made BEQ +0, so **the competition entry code is never
    shown** - a cheat can't win one.
  - &4F31 is `load_mission`'s `STA furthest_level` (&61): made NOPs, with
    &61 set to 3, so **the title screen's S offers all four levels**, even
    after loading another mission.
  PL's names are now `game_set_lives`, `game_entry_code_test`,
  `game_clear_furthest_level`, `game_furthest_level`, `CHEAT_LIVES`,
  `CHEAT_FURTHEST_LEVEL` instead of names after the instructions.
- **PL's code check** takes X from OSBYTE, not from its own code: `*FX200`
  hands back the old setting, 2 (as set at the start), which is also the
  last code byte's index. So changing the *FX200 setting breaks the check -
  one more anti-tamper the notes missed. (Seen: X = 2 at
  `check_code_byte`.) The "decoy" test can't fail because PHP always pushes
  B set; the comment had leaned on I as well.
- **LDATA's header** named `tools/screen2png.py`, which doesn't exist; it's
  `tools/beebscreen.py 1 data/ldata.bin OUT.png --columns 64 --offset 400
  --palette 0,4,3,1`. Its address is now `screen_address(0, 2)` from
  levdes.6502inc, with its 25 rows asserted.
- **WARNING**: MENU clears rows 18-24 after it, but the scroller is on rows
  17-24 (row 17 is blank already).
- **MRUN**'s doubled `LDX #6`, overwritten before use, is EVENT_ESCAPE's
  number; "exactly as at power-on" was too strong (nothing's cleared; the
  boot file just runs again).
- Stale from the 18:35 list: `src/loaders.6502inc` is gone (its names are
  in os.6502inc and osconst.6502inc); `make test` does run the PL check
  (tests/test_pl.py); original/README.md and CLAUDE.md are updated.

### Confirmed in jsbeeb

- **The stubs on an 80-track drive** (previously untested): jsbeeb models
  the 96 tpi surface, so a 40-track disc can be put in a drive stepping one
  surface track per step (`fdc.loadDisc(0, disc, 1)` with the disc loaded
  as `DiscLayout.expanded40`). Each stub reads ID track 2 off the probe,
  sets double_step to &FF, and reads its run correctly; with the drive
  stepping two (a 40-track drive) double_step stays 0. Logging writes to
  the 8271's registers shows the stub's commands arrive unchanged: seek
  &3A (2 * 29), write special &12 := &1D, read &57 track &1D, &12 := &3A,
  seek &3C... so DFS 1.2 passes OSWORD &7F straight through. But DFS 1.2
  doesn't double-step its own reads, so the game, once loaded, fails to
  load IO ("Disk fault 18 at 08/08" on its error screen). The stub's care
  only pays with a DFS that double-steps its own reads.
- The recalibrate: a seek to track 0 steps out until the drive signals
  track 0 (jsbeeb's 8271 model, from beebjit, treats it so).
- On the HFE (deleted marks) every read returns &20 once; DFS doesn't
  retry it.
- TITLE is entered with Y = 5 and copies &2F05-&2FFF (251 bytes).
- MRUN: stopped at BASIC's OSCLI after `*/MRUN`, &0700 holds `*E.!BOOT  `
  and the mode is 7 (it was 4 before).
- PL: Y = 0 going into its first `*FX200` (left so by `*FX4`), so it sets
  2 whatever was there; the listing of LEVEL1 with 677636 works; what's
  typed is echoed (there's just no prompt).
- !BOOT's NETV claim: the only &24 &02 byte pairs on the disc are in IO
  and LEVEL1's level data, not code.
