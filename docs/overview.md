# A guide to the code

Where to start reading, program by program. The [README](../README.md) says
what's on the disc. This guide says how the pieces hand over to each other,
how each program is laid out in its source and in memory, and which routines
explain the most. The source comments carry the detail; `docs/notes/` has
the evidence behind them.

Addresses are where a routine runs. `build/listing.txt` (after `make`) gives
every label's address, and `build/symbols.json` holds the same names for a
debugger.

## How the programs hand over

```
SHIFT+BREAK
 └ !BOOT          *EXEC'd: credits, *FX200,3, CHAIN "MENU"
    └ MENU        BASIC: SCREEN (loading picture), WARNING, then the menu
       ├ 1 Play       TITLE (MODE 1 picture), then */GAME
       │               └ GAME stub reads H.GAME → the game, which loads IO
       ├ 2 Keys       redefine the game's keys (stays in MENU)
       ├ 3 Graphics   */GRAPHIC → stub reads H.GRAPH → Graphics Designer ┐
       ├ 4 Levels     */LEVDES → stub reads H.LEVDES → Level Designer    ├ */MRUN → *E.!BOOT
       ├ 5 Mission    CHAIN "MISSION" → the mission generator            ┘
       └ 6 Quit       a BREAK that leaves BASIC's prompt
       (W and T held as MENU starts: */PL, "Ian's cheat!")
```

The game and the two designers are *hidden runs*: whole sectors past the
last catalogued file, which no catalogue entry mentions. Each is loaded by a
*stub*, a small catalogued program (GAME, GRAPHIC, LEVDES) that reads the
sectors directly from the disc controller. The designers and MISSION finish
by running MRUN, which puts back the vectors they took and types `*E.!BOOT`,
so the menu comes back as if from a fresh boot.

The game is driven by data. A *mission* (IO is the one on the disc) holds
four levels, a graphics set and the objects' names. The Graphics Designer
edits graphics sets (DEFAULT is one), the Level Designer edits levels
(LEVEL1 is one), and MISSION packs four levels and a graphics set into a
mission.

## Finding your way in the source

| Program | Source | Start at |
|---|---|---|
| the game | `src/hidden_game.6502`, `src/game.6502inc` | the file header, then `loader` and the main loop |
| Graphics Designer | `src/hidden_graphic.6502` | `start` (&2BAE), `main_loop`, `command_table` |
| Level Designer | `src/hidden_levdes.6502`, `levdes.6502inc`, `level.6502inc`, `wdata.6502inc` | `entry` (&2E21), `main` |
| MENU, MISSION | `src/menu.6502`, `src/mission.6502` | the file header's map of the program |
| the stubs | `src/hidden_loader.6502inc` (with `game/graphic/levdes.6502`) | `start` (&0900) |
| IO, LEVEL1, DEFAULT | `src/io.6502`, `src/level1-4.6502inc`, `src/default.6502inc` | `level1.6502inc`'s header on reading a level |

Every file starts with a header saying what the piece is, where it sits in
memory and how it's reached. The long ones also say how the file is laid
out.

**Where the names live.** A name that more than one program uses, or that
belongs to the machine, is defined once in an include:
- `os.6502inc` has the MOS's addresses and the hardware.
- `osconst.6502inc` has the machine's other numbers: OSBYTE and friends, keys, VDU codes, screen sizes, the 8271's commands.
- `leveldata.6502inc` has the level format.
- `sprites.6502inc` has the graphics set's format.
- `io.6502inc` has the mission file's layout.

A name that only one program uses stays in that program's source.

**Routine headers** say what the routine is for, then `In:`, `Out:` and `Clobbers:`, each left out when there's nothing to say. "Clobbers: everything" means the registers and whatever zero page the routines it calls use.

**Conventions:**
- **Sizes:** a number in brackets after a zero-page name, `(2)`, is its size in bytes.
- **Scopes:** each source file assembles with its own symbol table. The game also sits in the scope `game`, and many routines have a scope of their own for their local labels, which then read as `select_sprite.down_not_0f`.
- **Moved code:** code that the program copies elsewhere at startup is a nested section assembled at the address it runs from. For example, the Level Designer's zero page, font and "low code" are assembled at &0000, &0400 and &0880 inside a file loaded at &1100.
- **BASIC programs** are baron `BASIC` blocks, with `;` comments between the lines. A line that can't be written as source text, such as one with raw teletext bytes, is an `EQUB basic_line(...)` record before the block.

**Data as pictures and maps.** The levels and the graphics are written so
they look like what they are: maps as 64 strings of 64 characters, and
sprites as rows of pixels. FUNCTIONs in `leveldata.6502inc` and
`sprites.6502inc` turn them into the bytes the programs read. See [the
data](#the-data-io-the-levels-and-the-graphics) below.

**Seeing it run.** `node tools/beeb.mjs` and `node tools/play.mjs` drive a
headless jsbeeb. They can take screenshots, dump memory, trace which
addresses execute, stop at an address and print the registers. Their
headers list the commands.

## The game (H.GAME)

`src/hidden_game.6502`, all in the scope `game`, with its own names in
`src/game.6502inc`. The GAME stub reads sectors &122-&142 to &3000 and jumps
to `loader`, which copies the rest of the file to where it runs, sets up the
screen and the sound, and starts the game. The game then loads IO over the
loader.

Its words (the file header has more):
- A *map cell* is one of a level's 64 x 64 squares. It's drawn as 4 x 4 of the game's *character cells*, each a byte across (4 pixels) and 8 lines down.
- Things that move a character at a time keep their positions in character cells: the view, the monsters and a thrown object. Everything else uses map cells.
- The *view* is the 8 x 8 map cells round the player. The hardware scrolls it a character at a time.
- A *cycle* is one turn of the main loop, four TV frames long.
- A *step* is the player moving a map cell. A *walk* is the scrolling that goes with it.
- A *trigger* is one of a level's 32 rules. When the player walks on its place, or uses or throws an object there, it changes the map, moves a monster, teleports the player, and so on.

### Memory while it runs

| Address | What |
|---|---|
| &00-&9B | zero page in groups: the monsters (&00), the thrown object (&10), the play state (score, backpack, lives), two SOUND blocks (&30, &38) and the tune, the level's setup (&56), the keys (&66), and the drawing variables (&70) |
| &0100-&0124 | this level's trigger flags, at the bottom of the stack page |
| &0131-&0190 | `event_handler`: feeds the tune to the OS's sound queues |
| &0400-&07FF | `low_code`: picture lookup, drawing the view, scrolling, the walks |
| &0880-&08FF | `sound_data`: the tune, then the envelopes (in the OS's own store at &08C0) |
| &0900-&23AC | `main_code`: the rest. The level's 8 objects are copied over `game_start`, which has run by then |
| &23AD-&242C | `trigger_args` |
| &242D-&57FF | IO, the mission |
| &5800-&5FFF | `map`: the current level's map, as play changes it |
| &6000-&7FFF | the screen: MODE 5 reprogrammed to 32 x 32 characters in 8K, which the hardware scrolls and wraps |

### How it runs

- **`loader`** (&3000) copies MENU's keys into the game's order. It then:
  - copies `event_handler`, `sound_data`, `low_code` and `main_code` into place;
  - sets MODE 5;
  - points EVNTV at `event_handler`;
  - makes the hardware wrap the screen at 8K;
  - jumps to `game_start`.
- **`game_start`** runs once. It sets BRKV and calls `load_mission`. That moves &0D00-&1CFF of the game out of the DFS's way, loads IO and moves it back.
- **The title screen** (`title_screen`): S picks the starting level, L loads another mission, Space plays.
- **A level's start:**
  - `setup_level` copies the level's map to &5800, and its objects, monsters and triggers into place.
  - `reset_level` puts the player at the start.
  - `redraw_view` draws the view.
- **`game_loop`** runs `play_cycle` until the player dies, finishes the level or runs out of time. Each time round:
  1. `player_turn` handles Escape, what's underfoot and walk-on triggers, then the player's action, through `action_table`.
  2. `think` moves a thrown object and decides each monster's way (`monster_think`).
  3. Four frames of `read_keys` and `move_things` move everything a character.
  4. The monsters are marked on the map as fire.
  5. The clock ticks.
- **Dying:** lava or fire underfoot or ahead, a blast, or Escape. `lose_life` restarts the level, or, with no lives left, burns the screen up and goes back to the title.
- **Finishing a level:** collect all the sulphur, then press P facing the exit to light it (`light_exit`), and get clear before the clock runs out. `level_complete` scores 101. `next_level` shows the level's editing code on the backpack screen.
- **After the fourth level,** `mission_done` congratulates the player. A locked mission played from level 1 also shows a competition entry code. Then it's back to the title. The game never returns to MENU.

### Routines to read first

| Label | Address | What it does |
|---|---|---|
| `loader` | &3000 | Entry from the stub: where every piece ends up |
| `game_start` | &12A3 | One-time start-up, then the top of the flow |
| `game_loop` | &12E6 | The main loop: a cycle, the clock, and the ways out of a level |
| `play_cycle` | &15A1 | One cycle: the player, the thinking, four frames of movement |
| `player_turn` | &1611 | Escape, underfoot, walk-on triggers, then the action (`jump_to`) |
| `think` | &15C0 | The thrown object, the frame counter and every monster's decision |
| `move` | &18A9 | The direction keys: turning, stepping, crates, entering pipes |
| `walk_down` | &06E9 | One of four walks: the smooth scroll, drawing the new edge, moving everything |
| `draw_row`, `draw_column` | &058A, &063C | One character row or column of the view, from map cells |
| `redraw_view` | &0AE0 | The whole view |
| `cell_picture` | &0489 | A map cell to its picture: lava off the map, objects' icons; `tile_picture` (&04C4) picks second pictures |
| `draw_sprite` | &0CA2 | A picture at a character position, clipped to the view |
| `draw_player` | &09CE | The player in the middle of the view |
| `move_things` | &0B6C | Moves the thrown object and the monsters a character |
| `cell_at` | &0E36 | The map as the game sees it; `map_address` (&05B1) has the nibble layout |
| `set_cell_and_draw` | &1494 | Writes a map cell and redraws it; every trigger action uses it |
| `read_keys` | &1A8F | Keys to actions |
| `check_underfoot` | &194D | Sulphur, death, pipes |
| `use_trigger`, `throw_trigger` | &1E88, &1E29 | Does a trigger match? `trigger_fires` (&1ECF) runs its action from `trigger_actions` |
| `fire_object_triggers` | &1DA2 | An object's four triggers, and spending a use |
| `monster_think` | &213E | A monster's way, from its turn preferences |
| `step` | &21C6 | One step in a direction |
| `print_inline` | &103E | Prints the text after the JSR |
| `sound_effect` | &1F7A | Sound effects; the tune is `event_handler` (&0131) and `play_tune` (&0900) |
| `load_mission` | &222E | Loads IO round the DFS's workspace; errors go to `error_handler` (&22DB) |

### Before you read

- **Each copied piece is a nested section, assembled where it runs.** `build/listing.txt` shows the addresses it runs at.
- **The screen wraps.** Every screen pointer's high byte is kept in range with `AND #&1F : ORA #&60`.
- **The OS still thinks the screen is MODE 5's at &5800.** So text is placed with `TEXT_AT` (game.6502inc), which can reach only even columns.
- **Between cycles, monsters are fire cells on the map.** That's how they kill the player, and how `monster_think` notices that one has been overwritten.
- **There are two sets of action numbers.** The player's actions are `ACTION_*`, run through `action_table`. Trigger actions are `PUZZLE_*`, run through `trigger_actions`.
- **Some calls carry inline data after the JSR:**
  - `copy_block` takes six bytes.
  - `print_inline` takes text up to a NOP, which then runs.
- **Some routines return from their caller** by dropping its return address. `clip_sprite_out_of_view` and `selected_object` are two.
- **Some data sits over spent code.** The objects table lies over `game_start`.
- **"Monster X / 4":** routines take a monster as its offset in the table, the number times 4.
- **Scores are one more than the number in the code.** `add_points` adds X + 1.
- **Known bugs in the original:**
  - A trigger that sets all four monsters' direction sets only monster 3's properly.
  - Level 2's monster 0 starts with no fire under it. The game takes that for a monster something has overwritten, so it removes the monster at once and scores 26 points.

## The Graphics Designer (H.GRAPH)

`src/hidden_graphic.6502`. The GRAPHIC stub reads sectors &145-&165 to &1AB0
and jumps to `start` (&2BAE). It edits a graphics set in memory at &4000. It
loads and saves whole sets, single sprites, or the graphics inside a mission
file.

Its words:
- A *slot* is a sprite's place in the set.
- The *sheet* is the right half of the screen, showing every sprite.
- A *sprite number* is a place on the sheet, which isn't always the slot.
- A *window* is a box opened over the screen. What it covers is saved, and put back when it closes.

### Memory while it runs

| Address | What |
|---|---|
| &50-&65 | pointers (`screen_ptr`, `data_ptr`, `save_ptr`, `aux_ptr`), scratch and counters |
| &70-&7E | the editor's state: `sprite` (the selection), `cursor_x`/`cursor_y`, `colour`, `by_slot`, `escape_latch`... |
| &1AB0-&2053 | data: the PIPELINE logo, `slot_of_position`, the 4x8 font (at &1D00), the windows' places |
| &2054-&3ADB | the code. Many variables are bytes inside it (`stack_pointer`, `disc_fs`, `osfile_block`...) |
| &3E00, &3E80 | `frame_a`, `frame_b`: Animate's two frames |
| &3F80 | `undo_buffer`: the sprite as it was when selected |
| &4000-&4F33 | the graphics set (large slots &00-&0F, small &10-&1F at &4800, large &20-&28 at &4A00, names at &4E80) |
| &5000-&537F | `window_store`: what the open window covers |
| &5800-&7FFF | the MODE 5 screen: the editing grid top left, the sheet top right, the logo at the bottom |

BRKV points to `error_handler` and EVNTV to `escape_event`. The OS's
values are kept in the spare vectors IND1V and IND2V until the designer
leaves.

### How it runs

- **Start.** The first time through, `start` takes BRKV and EVNTV. It then:
  - sets MODE 5, unless the screen is already MODE 5, so an error restart keeps the palette;
  - draws the boxes and the logo;
  - on disc, loads DEFAULT.
  
  `start.redraw` draws the sheet and the grid, then falls into `main_loop`.
- **Each pass of `main_loop`:**
  - It resets the stack and closes any open window.
  - `select_sprite` moves the selection with the cursor keys. It also paces the loop.
  - `edit_pixels` handles painting: Z, X, colon and slash move the pixel cursor, 0-4 pick a colour, and Return and Delete plot.
  - `read_command` turns a CTRL shortcut, or an item picked from the f0-f3 menus, into a command number. `command_table` maps that number to a routine, which the loop calls by writing its address into a `JSR` (`main_loop.dispatch`).
- **Commands that work on two sprites** (OptionsB) go through `pick_second_sprite`, which asks for the second sprite and checks the two are the same size.
- **Files.** `ask_load_name` and `ask_save_name` read a file's catalogue entry and decide from its load address and length what it is:
  - **A graphics set** moves whole, with OSFILE.
  - **A mission file** is never held whole. The set's three pieces are read or written in place with OSGBPB (`io_segments`).
  - **A single sprite** moves on its own, with OSGBPB.
- **Errors.** An OS error reaches `error_handler`, which shows it and restarts through `start`; the work survives. The designer's own complaints go through `show_error`.
- **Leaving.** Escape then Yes puts the vectors back and runs `*/MRUN`. On tape it resets the machine instead.

### Routines to read first

| Label | Address | What it does |
|---|---|---|
| `start` | &2BAE | Entry and error restart: vectors, screen, first-time load, first draw |
| `main_loop` | &2D06 | One pass: selection, painting, command dispatch, Escape |
| `command_table` | &2DCC | Every command, by its menu or shortcut number |
| `read_command` | &3A4D | CTRL shortcuts and f0-f3 menu picks to a command number |
| `menu` | &21E6 | A pop-up menu; returns the line picked |
| `open_window`, `close_window` | &2079, &215E | Save what a window covers, draw it; put it back |
| `print_char` | &21A9 | All text: a font character in one cell, stored or EORed |
| `key_pressed` | &2186 | Tests one key with OSBYTE &81 |
| `select_sprite` | &3366 | Moves the selection over the sheet, and paces the loop |
| `sprite_address` | &22D2 | Sprite number to its bytes and width: the key to the numbering |
| `sheet_address` | &252F | Sprite number to its place on the sheet |
| `draw_grid` | &234A | The magnified editing grid; bit 7 of A takes the undo copy |
| `draw_sheet_sprite` | &24D4 | Copies a sprite to its place on the sheet |
| `show_selection` | &2A60 | The selection box, and the object's number and name |
| `edit_pixels` | &387F | Painting: the pixel cursor, colours, plotting |
| `pixel_address` | &39E6 | Sprite and x, y to a byte and mask; `plot_pixel` and `read_pixel` build on it |
| `pick_second_sprite` | &307E | The front end of every two-sprite command |
| `combine_sprites` | &2F52 | Overlay, Underlay and Backing, pixel by pixel |
| `cmd_animate` | &326E | Animate: two frames flipped in turn |
| `error_handler` | &2B62 | Shows an OS error, then restarts |
| `ask_load_name` | &36DA | A file name to a set or a mission file (`check_io_file`) |
| `io_segments` | &377B | Where a set's three pieces sit in a mission file |
| `input_line` | &380F | The line editor for file and object names |

### Before you read

- **Sprite numbers are sheet positions, not slots.**
  - &00-&0F and &20-&28 are the large places in reading order. `slot_of_position` maps them to slots.
  - &10-&1F are the small sprites, whose slots are the same as their places.
  - &57 and &58 are Animate's frames.
  - While `by_slot` has bit 7 set (only in Animate), the numbers are slots.
- **`main_loop` resets the stack on every pass.** So a command can give up from any depth with a plain `JMP main_loop`.
- **Routines often fall into the next one or share another's tail.** For example, `error_handler` runs into `start`, and `start` runs into `main_loop`. `open_file` and `read_block` have second entry points behind a `BITABS`: a BIT opcode that swallows the instruction after it.
- **Text, the input echo and the pixel cursor are EORed on.** Drawing them again erases them.
- **Undo is a swap.** Pressing Undo again redoes.
- **Slot 0, the floor, is kept as one 4x8 cell repeated** (`repeat_background`), because the game fills floor from that cell alone.
- **Slot &1F is the exit's icon.** It has no name. The name box shows "Finish Block" for it, a name `start` writes just past the real names.
- **Dead code** is kept as entry points in `hints/hidden_graphic.toml` (`unused_*`, `stray_rts`).

## The Level Designer (H.LEVDES)

`src/hidden_levdes.6502`, with `levdes.6502inc` (its screen and keys),
`level.6502inc` (where the level lives), `wdata.6502` (its windows and
messages) and `ldata.6502` (its title picture). The LEVDES stub reads
sectors &16D-&18B to &1100 and jumps to `entry` (&2E21).

Its words:
- A *block* is a map cell's contents, one of the game's cell types.
- A *puzzle* is the game's *trigger*.
- The *brush* is the block that Return plots.
- A *marker* (block F) marks the start, the finish and the objects.
- An *S.Monster* (block E) marks a monster.
- The *simulator* makes the cursor move by the player's rules.
- A *window* is a box with a title and a menu, defined in WDATA.
- The *low code* is the drawing code that `entry` moves to &0880.

### Memory while it runs

| Address | What |
|---|---|
| &00-&21 | pointers to the menus' handler tables (`menu_tables`), by number from 1 |
| &40-&4F | `input_buffer`, for OSWORD 0 |
| &50-&89 | the editor's variables (cursor, brush, simulator...), then the low code's (window pointers, menu state) |
| &0400-&07FF | the font (moved there by `entry`) |
| &0880-&0CBF | the low code: map, windows, menus, the message box; a jump table at &0880 |
| &1100-&25A0 | the rest of the program; jump tables at &1100 and &234D |
| &25A1-&2FFF | the level being edited, as a level file: puzzle names, fields, the map at &2800 |
| &3000-&6FFF | the screen: MODE 1 narrowed to 64 columns (256 x 256 pixels) |
| &7000-&7C4D | WDATA |

`entry` and the originals of the moved pieces sat where the level now goes,
so `entry` runs only once. LDATA is loaded straight onto the screen for the
title.

### How it runs

- **`entry`** moves zero page, the font and the low code to where they run. It then:
  - sets MODE 1 and narrows it to 64 columns;
  - makes the cursor keys soft keys and makes the function keys give &80-&89;
  - hooks RDCHV through `rdchv_filter`;
  - loads WDATA and LDATA.
  
  The title waits for Space.
- **`main`** sets up a new level with `new_level`, then loops:
  - `get_key` moves the cursor and plots by itself while the keys are held. It returns any other key.
  - `hex_key` turns 0-9 and A-F into the brush.
  - `do_command` runs f0-f4's menus.
- **A function key abandons whatever is going on.** `check_function_key` is called from `get_key` and from `rdchv_filter`, so it works even inside OSWORD 0. It resets the stack, redraws the map and jumps to the dispatcher.
- **Windows:**
  - `open_window` places a WDATA window on the side of the screen away from the cursor.
  - `window_menu` runs its menu bar, and `jump_to_handler` turns the item picked into a handler through the window's table.
  - `close_window` doesn't save what was under the window. It redraws the map there, so the editors reopen their windows each time round their loops.
- **The message box** (`open_message_box`, `print_line1`, `print_line2`) prints WDATA's messages through the OS. `os_tab` picks OS TAB positions that land in the right place on the 64-column screen.
- **Loading and saving** go through `ask_filename` and `level_file`, which save or load &25A1-&2FFF with OSFILE. Loading asks for the level's editing code, then loads the file over the level being edited before it compares the codes. So a wrong code loses both levels: the one being edited is overwritten, and the one loaded is thrown away.
- **There's no test play.** The simulator (S) makes the cursor obey the player's rules (`move_cursor`, `simulate_travel`): walking, losing a life, and travelling through pipes.
- **Leaving.** Files > Exit, or SHIFT+Escape, asks for the PIPELINE disc and runs `*/MRUN`.

### Routines to read first

| Label | Address | What it does |
|---|---|---|
| `entry` | &2E21 | Startup: moves the pieces, sets up the screen and the OS, loads WDATA and LDATA |
| `main`, `main_loop` | &15D0, &15E0 | The command loop: how keys flow |
| `get_key` | &13BD | Waits for a key, acting on held movement and plotting keys; drives the simulator |
| `hex_key` | &15F9 | 0-9 and A-F to the brush |
| `do_command` | &1638 | Dispatches f0-f4 |
| `check_function_key` | &1269 | A function key abandons anything |
| `rdchv_filter` | &124A | RDCHV: limits what can be typed, catches function keys |
| `jump_to_handler` | &166B | A menu item to its handler, through the tables in zero page |
| `choose_from_window` | &1126 | Open, run and close a menu in one call |
| `window_menu` | &0BEE | The menu bar: cursor keys, Return, Space |
| `draw_window`, `close_window` | &0A27, &0B47 | Draw a WDATA window; close it by redrawing the map |
| `window_address` | &249E | Window or message number to its address in WDATA |
| `print_message` | &245A | A WDATA message through the OS |
| `input_line`, `ask_number` | &1342, &1A4F | Line input, and asking for a number in range |
| `read_map`, `write_map` | &24CF, &24A9 | The map's nibbles |
| `draw_map` | &089B | Redraws the whole map |
| `move_cursor`, `simulate_travel` | &14C9, &154F | Cursor movement and the simulator |
| `brk_handler` | &1196 | Errors: the message box, and wiping a half-loaded level |
| `level_file`, `ask_filename` | &1DF2, &1E0A | Loading and saving |
| `new_level` | &2368 | What a blank level holds |
| `option_object`, `edit_puzzle`, `effect_editor` | &1756, &1B04, &1EA1 | The editing windows' pattern: menu, handler, round again until OK |

### Before you read

- **Calls between the parts mostly go through jump tables** (&1100, &0880, &234D), as if the parts were assembled separately. Read a `vector_*` as the routine it jumps to.
- **The keys choose block-menu items, not block numbers.** Key 6 is Wall 2, block 8. `block_menu_map` holds the mapping both ways.
- **The cursor's directions aren't a level's.** The cursor's `MOVE_*` go clockwise from left, so EOR 2 reverses one. A level's `DIRECTION_*` are left, right, up, down.
- **Some positions are stored offset.** The start and a teleport's target are kept 4 less in each direction: the top left of the game's view, not the player's cell. Monsters' x and y are kept times 4.
- **The OS thinks the screen is MODE 1's 40 columns**, hence `os_tab`.
- **At an error, a lower-case "i" drops into BASIC,** with the keyboard links set to &CF. It's a back door for the developers.
- **Ian Holmes's own labels survive** from a fragment of his source left in MENU's file (sel0, sure, wind and others). They're noted at their routines.

## MENU, MISSION and PL

### MENU (`src/menu.6502`)

A BASIC program at &1900 (Ian Holmes, "Originally: GUILDMASTER"), and,
past its end in the same file, what its DIMs hold. `LOMEM=PAGE+&A00` starts
the heap exactly where the program ends, and DIM doesn't clear memory, so
`DIM C% &EFF, S% &700` lands on bytes the file brought with it:

| Address | What |
|---|---|
| &1900-&22FF | the program |
| &2300 | C%: the scroller, a vsync event handler (`scroller.start`, `scroller.vsync_handler`), and its message |
| &3200 | S%: the menu screen's top 16 Mode 7 rows (`menu_screen`), then leftovers |

**Lines to read first:**
- 50: the DIMs.
- 60-80: an error handler that is itself an error, so any error hangs the machine.
- 250-300: SCREEN, WARNING, then `CALL C%` to start the scroller.
- 290: `*/PL`, hidden from LIST by VDU 21 and VDU 6.
- 310-400: the menu loop.
- 690: redefining keys, by scanning every INKEY number.
- 910-990: the options that leave MENU.

MENU leaves the game's ten keys in &50-&59. The file also carries a tune
program that nothing runs.

### MISSION (`src/mission.6502`)

The mission generator, a BASIC program at &1900. It builds a mission (IO is
one) from a graphics set and four level files, and edits the mission's name
and features. The file header maps the program by line. These are the
places to start:
- **PROCinit (440):** every size, and the buffers.
- **PROCloadlev (1590):** how a mission keeps each field of all four levels together, then the four maps.
- **PROClock (1390):** the secret i and h keys that lock a mission.
- **FNn (1160) and the machine code hidden in line 60:** the editing codes.
- **PROCsavemss (2000):** the save, which goes to whatever disc is in the drive. On the PIPELINE disc it lands on the hidden runs, which DFS thinks are free space.

The file isn't valid UTF-8 (two REMs hold raw teletext bytes), so edit it
as bytes.

### PL (`src/pl.6502`)

"Ian's cheat!", run by MENU when W and T are held at boot. It loads at
&0400 (pages 4-6, BASIC's workspace, so it never goes back to BASIC). It
decrypts itself in place:
- **The cipher:** each plain byte is a key byte, EORed with the previous plain byte and the stored byte.
- **The key:** the key bytes are the decryptor's own code, so patching the decryptor breaks it.

The decrypted program is the `pl_cheat` section. It works through these steps:
1. It reads a level file's name and editing code without a prompt, and lists the level's puzzles.
2. It fakes a "Bad program" error until I, N, O and S are held.
3. It loads GAME and pokes extra lives and every level into it. On this disc, though, GAME is only a stub, so the machine resets.

`tools/plcrypt.py` does the encryption. To start reading, see `pl.start`, `key_bytes`, `pl_cheat.start` and `check_code_byte`.

## The small pieces

- **!BOOT** (`src/boot.6502`): the `*OPT 4,3` boot file, typed in by `*EXEC`. Credits as `*|` comments, `*FX200,3` (Escape off, memory cleared on BREAK), a line that unhooks an Econet filing system from NETV, then `CHAIN"MENU"`.
- **TITLE** (`src/title.6502`): loaded at &6300 and run at &7900 by MENU before the game. A picture packed as runs of zeros, which unpacks over its own file from &3000 up. Its code first copies itself out of the way, to &2F00.
- **MRUN** (`src/mrun.6502`): &80 bytes at &0780, in BASIC's keyboard buffer. It puts back RDCHV and EVNTV and turns off the Escape event, then types `*E.!BOOT` into the keyboard buffer and enters BASIC.
- **WARNING** and **SCREEN** (`src/warning.6502`, `src/screen.6502`): a Mode 7 page and a MODE 5 picture, loaded straight to the screen by MENU. `TT_ROW` writes a Mode 7 row with its control codes by name. Rows 0-9 of WARNING and of MENU's screen are the same, and are written once, in `mode7_header.6502inc`.

## The loader stubs

GAME, GRAPHIC and LEVDES are one program, `src/hidden_loader.6502inc`. Each
of `game.6502`, `graphic.6502` and `levdes.6502` includes it in its own
scope, with four numbers: the run's first sector and length, and where the
program loads and starts. Each stub is &D9 bytes, loaded and run at &0900.

| Stub | Run | Sectors | Loads at | Enters at |
|---|---|---|---|---|
| GAME | H.GAME | &122-&142 | &3000 | &3000, `game.loader` |
| GRAPHIC | H.GRAPH | &145-&165 | &1AB0 | &2BAE, `start` |
| LEVDES | H.LEVDES | &16D-&18B | &1100 | &2E21, `entry` |

`start` (&0900) seeks to track 0. It then reads a sector ID off track 4: an
ID from any other track means a 40-track disc in an 80-track drive, and the
stub double-steps.
`read_whole_run` (&0916) and `read_next_track` (&0924) read a track's worth
of sectors at a time with the 8271's "read data and deleted data" command,
through OSWORD &7F (`disc_command`).

The hidden sectors were written with deleted data address marks, which
stop a DFS `*BACKUP`. The result byte that would report them is fetched and
then skipped over.

## The data: IO, the levels and the graphics

**IO**, the mission file, is built by `src/io.6502` from the four levels and
the default graphics. Its layout is in `src/io.6502inc`, which the game
reads it by. MISSION saves it so that it ends at &5800, where the game
keeps the map of the level being played:

| Address | What | Labels |
|---|---|---|
| &242D | the no-object picture (slot &28) and the 15 object names | `io_no_object_picture`, `io_object_names` |
| &2561 | the mission's name, two halves of 15 bytes | `io_mission_text` |
| &257F | five settings: clock rate, map levels, backpack size, throw distance, lock | `io_attrs`... |
| &2584 | the levels' fields, each field of all four levels together | `io_level_setup`, `io_level_objects`... |
| &2A00 | the four maps, &800 bytes each | `io_maps` |
| &4A00-&57FF | the graphics: slots &00-&27 | `io_tiles`, `io_object_icons`, `io_player`, `io_alternates` |

**A level** is written once, in `src/level1.6502inc` to `level4.6502inc`, as one list:
- the editing code;
- the palette;
- the setup (the start, things to collect, the clock, the exit, what monsters eat);
- 8 objects;
- 4 monsters;
- 32 triggers, each with a comment saying what it does in the game;
- the map, as 64 strings of 64 characters.

`level1.6502inc`'s header explains how to read one. The notation and
the FUNCTIONs that turn it into bytes are in `leveldata.6502inc`, and both
`level1.6502` (the LEVEL1 file) and `io.6502` use them.

**The graphics set** is written once, in `src/default.6502inc`, as
pictures: one string per pixel row, two characters per pixel (`.` `1` `2`
`3`), since a MODE 5 pixel is twice as wide as it is tall.
`sprites.6502inc` has the notation and `mode5_pictures`, which turns the
pictures into bytes. `default.6502` (DEFAULT) and `io.6502` both use them.

Before you read:
- **Triggers are numbered 0-31,** as the game counts them; the Level Designer shows them one higher.
- **Object n can fire only triggers n, n+8, n+16 and n+24.**
- **In the game, a "character cell" is its own:** a byte across (4 pixels) and 8 lines down. That's half a MODE 5 character. The game's screen is MODE 5, reprogrammed.
- **Slack:** some files' last sectors hold bytes past the file's end. `src/disc.toml` keeps them.
- **`forceabs.6502inc`'s macros are for the disassembler's drafts.** Nothing in `src/` uses them.
