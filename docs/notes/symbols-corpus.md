# Notes: the symbol sets against the Stairway To Hell discs

The corpus check jsbeeb's proposal asks a set's pull request to carry
("Symbol sets" in its docs/media-registry-proposal.md): for every region,
every title on the Stairway To Hell discs whose files hold all of its
anchors at the same addresses, with how much of the region that title's
files hold and how much of that is identical. Made by
`tools/symbols_corpus.py` from jsbeeb's `.registry-corpus/sth-disc` (read
only) and the sets `make jsbeeb-symbols` writes:

```
python3 tools/symbols_corpus.py ../jsbeeb/.registry-corpus/sth-disc
```

Times are US Central.

## 2026-10-04 19:30: summary

- Every region that any other title matches is matched by one title only,
  Superior/Pipeline.zip, Stairway To Hell's crack of PIPELINE, and there it's
  the same code: 100% identical for every region its files hold, but for
  the Level Designer's main region at 99.9% (the crack's three changed bytes,
  which no anchor sits on). Nothing else holds all of any region's anchors,
  so there is no collision to fix.
- No other title holds even one of the 54 anchors. Cut to its first four
  bytes, one anchor turns up in one other title: MISSION's `DD F2 6C 6F`
  at &2519 (`DEFPROClo...`, a BASIC procedure's start) is also in
  SoftwareInvasion/BlackJack-SoftwareInvasion.zip. The whole six bytes
  aren't.
- The crack holds the game's loader region (its GAME is H.GAME as loaded),
  the Graphics Designer (its GRAPHIC loads at &1A80, &30 bytes before
  H.GRAPH's start, and holds all of it), the Level Designer's main and
  startup regions, WDATA, TITLE, PL as stored (the decryptor and the
  encrypted bytes), MENU and MISSION. It has no stubs and no MRUN.
- What the corpus can't test: files sit at their load addresses, so the
  pieces the game and the Level Designer move to where they run (the game's
  event handler, tune, low code and main code; the Level Designer's low
  code and font), TITLE's moved unpacker and PL's decrypted cheat are only
  ever compared with other titles' files that load at those addresses, not
  with other programs' code as it runs there. "none" says only that no
  catalogued file holds those anchors there.
- The other half of the check, every set already in jsbeeb's index run over
  PIPELINE's bytes, has nothing to run yet: the only set on the way, MOS
  1.20's (jsbeeb#1219), anchors in ROM from &C000, where no PIPELINE
  program sits.

## The report

1602 titles, 9214 distinct files placed at their load addresses. "Holding one" counts the titles holding any of a region's anchors; "Held" is how many of the region's bytes that title's files hold, and "Identical" how many of those are the same.

### game

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| loader &3000-&50FF | 1 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.GAME | 8448 of 8448 | 8448 (100.0%) |
| event_handler &0131-&0190 | 1 | 0 | none | | | |
| sound_data &0880-&08FF | 1 | 0 | none | | | |
| low_code &0400-&07FF | 2 | 0 | none | | | |
| main_low &0900-&0CFF | 1 | 0 | none | | | |
| main_swapped &0D00-&12A2 | 2 | 0 | none | | | |
| game_start &12A3-&12C2 | 1 | 0 | none | | | |
| main_swapped_2 &12C3-&1CFF | 3 | 0 | none | | | |
| main_high &1D00-&23AC | 1 | 0 | none | | | |

### graphics-designer

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &1AB0-&3BAF | 4 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.GRAPHIC | 8448 of 8448 | 8448 (100.0%) |

### level-designer

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &1100-&25A0 | 3 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.LEVDES | 5281 of 5281 | 5278 (99.9%) |
| startup &25A1-&2FFF | 1 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.LEVDES | 2655 of 2655 | 2655 (100.0%) |
| low_code &0880-&0CBF | 2 | 0 | none | | | |
| font &0400-&07FF | 2 | 0 | none | | | |
| wdata &7000-&7C4D | 2 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.WDATA | 3150 of 3150 | 3150 (100.0%) |

### game-stub

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &0900-&09D8 | 2 | 0 | none | | | |

### graphic-stub

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &0900-&09D8 | 2 | 0 | none | | | |

### levdes-stub

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &0900-&09D8 | 2 | 0 | none | | | |

### mrun

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| main &0780-&07FF | 1 | 0 | none | | | |

### title

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| title &6300-&7978 | 3 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.TITLE | 5753 of 5753 | 5753 (100.0%) |
| unpack &2F18-&2F78 | 1 | 0 | none | | | |

### pl

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| decryptor &0400-&043B | 1 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.PL | 60 of 60 | 60 (100.0%) |
| encrypted &043C-&06FB | 1 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.PL | 704 of 704 | 704 (100.0%) |
| cheat &043B-&06FB | 1 | 0 | none | | | |

### menu

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| program &1900-&22FF | 2 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.MENU | 2560 of 2560 | 2560 (100.0%) |
| scroller &2300-&31FF | 4 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.MENU | 3840 of 3840 | 3840 (100.0%) |
| menu_screen &3200-&38FF | 1 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.MENU | 1792 of 1792 | 1792 (100.0%) |

### mission

| Region | Anchors | Holding one | Title holding all | Files | Held | Identical |
|---|---|---|---|---|---|---|
| program &1900-&3127 | 6 | 1 | Superior/Pipeline.zip | Pipeline.ssd:$.MISSION | 6184 of 6184 | 6184 (100.0%) |

