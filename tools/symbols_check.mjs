#!/usr/bin/env node
// Checks the symbol sets (make jsbeeb-symbols) against PIPELINE running in a
// headless jsbeeb: at a few moments in each program, which regions' anchors
// all match memory, as jsbeeb's debugger would see it each time the machine
// stops, and whether that's exactly the regions expected there. Run `make
// jsbeeb-symbols` first.
//
//   node tools/symbols_check.mjs [--disc build/pipeline.ssd] [--sets build/jsbeeb-symbols] [SCENARIO...]
//
// SCENARIO is one of those below (all of them by default): menu, title, game,
// play (random play), levdes, graphic, tour-NAME (each of
// tools/graphic_tours.mjs's tours of the Graphics Designer), mrun and pl.
// Exits 1 if any moment matches other regions than expected.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { BBC } from "jsbeeb/src/keymap.js";
import { runScript, startBeeb } from "./beeb.mjs";
import { TOURS } from "./graphic_tours.mjs";

const CYCLES_PER_SEC = 2_000_000;
const STEPS_PER_CHECK = 25;
// MENU's screen comes up this long after the boot, after the loading
// picture and the warning page.
const MENU_SECS = 33;

const argv = process.argv.slice(2);
const opts = { disc: "build/pipeline.ssd", sets: "build/jsbeeb-symbols" };
while (argv[0]?.startsWith("--")) opts[argv.shift().slice(2)] = argv.shift();

const sets = Object.fromEntries(
    readdirSync(opts.sets)
        .filter((f) => f.endsWith(".json"))
        .map((f) => [f.replace(/\.json$/, ""), JSON.parse(readFileSync(join(opts.sets, f), "utf8"))]),
);

// A name's address, from the region of a set that holds it.
function address(set, region, name) {
    const found = sets[set].regions[region].symbols[name];
    if (!found) throw new Error(`no ${name} in ${set}/${region}`);
    return parseInt(found, 16);
}

function matching(session) {
    const out = [];
    for (const [set, data] of Object.entries(sets)) {
        for (const [region, { anchors, minAnchors }] of Object.entries(data.regions)) {
            const held = anchors.filter(({ at, bytes }) => {
                const memory = session.readMemory(parseInt(at, 16), bytes.length / 2);
                return Buffer.from(memory).toString("hex") === bytes;
            });
            if (held.length === anchors.length && held.length >= minAnchors) out.push(`${set}/${region}`);
        }
    }
    return out.sort();
}

const hex4 = (n) => n.toString(16).toUpperCase().padStart(4, "0");
let failures = 0;

function check(session, moment, expected) {
    const found = matching(session);
    const want = [...expected].sort();
    const ok = found.length === want.length && found.every((r, i) => r === want[i]);
    const pc = session._machine.processor.pc;
    console.log(`${ok ? "ok  " : "FAIL"} ${moment} (PC &${hex4(pc)}): ${found.join(", ") || "nothing"}`);
    if (!ok) {
        failures++;
        console.log(`     expected: ${want.join(", ")}`);
    }
}

async function bbcKey(session, key, frames = 3) {
    session.keyDownRaw(key);
    await session.runFrames(frames);
    session.keyUpRaw(key);
    await session.runFrames(2);
}

// Presses a key and runs until the PC reaches addr with it still down, then
// lets go: a loop that waits for a key comes round while it's pressed.
async function keyUntil(session, key, addr) {
    session.keyDownRaw(key);
    try {
        await session.runUntilAddress(addr);
    } finally {
        session.keyUpRaw(key);
    }
}

// From the boot to MENU's option N, chosen.
async function menuOption(session, n) {
    await session.runFor(MENU_SECS * CYCLES_PER_SEC);
    await runScript(session, [`key Digit${n}`, "key Enter"]);
}

const GAME = [
    "game/event_handler",
    "game/sound_data",
    "game/low_code",
    "game/main_low",
    "game/main_swapped",
    "game/main_swapped_2",
    "game/main_high",
];
const LEVEL_DESIGNER = ["level-designer/main", "level-designer/low_code", "level-designer/font", "level-designer/wdata"];
const MENU = ["menu/program", "menu/scroller", "menu/menu_screen"];

const scenarios = {
    async menu(session) {
        const vsync = address("menu", "scroller", "scroller.vsync_handler");
        await session.runFor(MENU_SECS * CYCLES_PER_SEC);
        for (const [moment, secs] of [["the menu", 3], ["3 s later", 7], ["10 s later", 0]]) {
            await session.runUntilAddress(vsync);
            check(session, `${moment}, in the scroller's vsync handler`, MENU);
            await session.runFor(secs * CYCLES_PER_SEC);
        }
        await bbcKey(session, BBC.K2);
        await session.runFor(2 * CYCLES_PER_SEC);
        check(session, "redefining the keys", MENU);
    },

    async title(session) {
        await menuOption(session, 1);
        // MENU's MODE 1 has cleared the screen and the end of the scroller with it.
        await session.runUntilAddress(address("title", "title", "start"));
        check(session, "TITLE entered, before it moves", ["menu/program", "title/title"]);
        await session.runUntilAddress(address("title", "unpack", "unpack"));
        check(session, "TITLE's unpacker, moved", ["menu/program", "title/title", "title/unpack"]);
        await session.runUntilAddress(address("title", "unpack", "clear_bottom"));
        check(session, "TITLE's unpacker, the picture unpacked", ["menu/program", "title/unpack"]);
    },

    async game(session) {
        await menuOption(session, 1);
        await session.runUntilAddress(address("game", "loader", "loader"));
        check(session, "H.GAME's loader entered", ["game-stub/main", "game/loader", "menu/program", "title/unpack"]);
        await session.runUntilAddress(address("game", "game_start", "game_start"));
        check(session, "game_start", [...GAME, "game/game_start", "game/loader", "title/unpack"]);
        // load_mission has swapped SWAP_START to SWAP_END into the screen.
        await session.runUntilAddress(address("game", "main_high", "load_mission_block"));
        const swapped = ["game/main_swapped", "game/main_swapped_2"];
        check(session, "loading IO, part of the game swapped out", [
            ...GAME.filter((r) => !swapped.includes(r)),
            "game/loader",
            "title/unpack",
        ]);
        await session.runUntilAddress(address("game", "main_swapped_2", "title_screen"));
        check(session, "the title screen", [...GAME, "game/game_start"]);
        await session.runFor(CYCLES_PER_SEC);
        await bbcKey(session, BBC.SPACE);
        const loop = address("game", "main_swapped_2", "game_loop");
        await session.runUntilAddress(loop);
        check(session, "in play: game_loop, the level just set up", GAME);
        const moves = [BBC.Z, BBC.X, BBC.COLON_STAR, BBC.SLASH];
        for (let i = 0; i < 12; i++) {
            await bbcKey(session, moves[i % moves.length], 20);
            if (i % 4 === 3) {
                await session.runUntilAddress(loop);
                check(session, `in play: game_loop after ${i + 1} moves`, GAME);
            }
        }
        await session.runUntilAddress(address("game", "event_handler", "event_handler"));
        check(session, "in play: the tune's event handler", GAME);
    },

    // Random play: walking, pushing, picking up, dropping and throwing, the
    // map and the backpack, with a check every few seconds wherever the PC is.
    async play(session) {
        await menuOption(session, 1);
        await session.runUntilAddress(address("game", "main_swapped_2", "title_screen"));
        await session.runFor(CYCLES_PER_SEC);
        await keyUntil(session, BBC.SPACE, address("game", "main_swapped_2", "game_loop"));
        const keys = [BBC.Z, BBC.X, BBC.COLON_STAR, BBC.SLASH, BBC.P, BBC.D, BBC.T, BBC.RETURN, BBC.M, BBC.CTRL];
        let seed = 1;
        const random = (n) => Math.floor(((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000) * n);
        for (let moment = 1; moment <= 30; moment++) {
            for (let frames = 0; frames < 200; ) {
                const key = keys[random(keys.length)];
                const hold = 5 + random(40);
                await bbcKey(session, key, hold);
                frames += hold + 2;
            }
            check(session, `random play, moment ${moment}`, GAME);
        }
    },

    async levdes(session) {
        await menuOption(session, 4);
        await session.runUntilAddress(address("level-designer", "startup", "entry"));
        // MENU's screen data is still above it, until MODE 1.
        check(session, "the Level Designer's entry", [
            "level-designer/main",
            "level-designer/startup",
            "levdes-stub/main",
            "menu/menu_screen",
        ]);
        await session.runFor(15 * CYCLES_PER_SEC);
        check(session, "its title, waiting for Space", ["level-designer/startup", ...LEVEL_DESIGNER]);
        const loop = address("level-designer", "main", "main_loop");
        await keyUntil(session, BBC.SPACE, loop);
        check(session, "main_loop, a new level", LEVEL_DESIGNER);
        // Files, Load level, LEVEL1 with its editing code. main_loop comes
        // round again once get_key returns a key it doesn't act on itself,
        // such as a digit choosing the brush.
        await runScript(session, ["key F2", "wait 1", "key Enter", "wait 1", "key KeyY", "wait 1"]);
        await runScript(session, ["type LEVEL1", "wait 1", "type 677636", "wait 4"]);
        const level = parseInt(sets["level-designer"].globals.level_names, 16);
        const loaded = Buffer.from(session.readMemory(level, 0x100)).equals(readFileSync("build/files/LEVEL1").subarray(0, 0x100));
        if (!loaded) throw new Error("LEVEL1 didn't load");
        check(session, "waiting for a key, LEVEL1 loaded", LEVEL_DESIGNER);
        await keyUntil(session, BBC.K1, loop);
        check(session, "main_loop, LEVEL1 loaded, brush 1", LEVEL_DESIGNER);
        for (const key of [BBC.X, BBC.SLASH, BBC.RETURN, BBC.Z, BBC.DELETE]) await bbcKey(session, key, 10);
        await session.runFor(CYCLES_PER_SEC);
        check(session, "after plotting and deleting", LEVEL_DESIGNER);
        await keyUntil(session, BBC.K2, loop);
        check(session, "main_loop, brush 2", LEVEL_DESIGNER);
        await keyUntil(session, BBC.F1, address("level-designer", "low_code", "window_menu"));
        check(session, "the Options menu open", LEVEL_DESIGNER);
        // Into its first item (Start/Finish) and out, then the simulator,
        // Help and About.
        await runScript(session, ["wait 1", "key Enter", "wait 1", "key Space", "wait 1", "key Space", "wait 1"]);
        check(session, "an Options window and out", LEVEL_DESIGNER);
        await runScript(session, ["key KeyS", "wait 1", "key KeyX 20", "key Slash 20", "key KeyZ 20", "key Quote 20", "wait 1"]);
        check(session, "the simulator on, walking", LEVEL_DESIGNER);
        await runScript(session, ["key KeyS", "wait 1", "key F3", "wait 1"]);
        check(session, "Help", LEVEL_DESIGNER);
        await runScript(session, ["key Space", "wait 1", "key F4", "wait 1"]);
        check(session, "About", LEVEL_DESIGNER);
    },

    async graphic(session) {
        await menuOption(session, 3);
        await session.runUntilAddress(address("graphics-designer", "main", "start"));
        check(session, "the Graphics Designer's start", ["graphic-stub/main", "graphics-designer/main"]);
        const loop = address("graphics-designer", "main", "main_loop");
        await session.runUntilAddress(loop);
        // The stub stays where it was, and so does MENU's first page.
        const expected = ["graphic-stub/main", "graphics-designer/main"];
        check(session, "main_loop, DEFAULT loaded", expected);
        for (const key of [BBC.RIGHT, BBC.DOWN, BBC.X, BBC.X, BBC.RETURN, BBC.K1]) await bbcKey(session, key, 10);
        await keyUntil(session, BBC.RETURN, loop);
        check(session, "main_loop, after moving and painting", expected);
    },

    ...Object.fromEntries(
        Object.keys(TOURS)
            .filter((tour) => tour !== "escape")
            .map((tour) => [
                `tour-${tour}`,
                async (session) => {
                    await menuOption(session, 3);
                    await session.runUntilAddress(address("graphics-designer", "main", "start"));
                    await session.runFor(12 * CYCLES_PER_SEC);
                    const steps = TOURS[tour](tour);
                    for (let i = 0; i < steps.length; i += STEPS_PER_CHECK) {
                        await runScript(session, steps.slice(i, i + STEPS_PER_CHECK));
                        check(session, `${tour} tour, step ${Math.min(i + STEPS_PER_CHECK, steps.length)} of ${steps.length}`, [
                            "graphic-stub/main",
                            "graphics-designer/main",
                        ]);
                    }
                },
            ]),
    ),

    async mrun(session) {
        await menuOption(session, 3);
        await session.runUntilAddress(address("graphics-designer", "main", "main_loop"));
        // Escape, then Yes (the second item), then Space for the disc.
        await runScript(session, ["wait 1", "key Escape 3", "wait 1", "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 2"]);
        await keyUntil(session, BBC.SPACE, address("mrun", "main", "start"));
        check(session, "MRUN, leaving the Graphics Designer", ["graphic-stub/main", "graphics-designer/main", "mrun/main"]);
        await session.runFor((MENU_SECS + 5) * CYCLES_PER_SEC);
        await session.runUntilAddress(address("menu", "scroller", "scroller.vsync_handler"));
        // MRUN is in BASIC's line buffer, which MENU hasn't needed yet.
        check(session, "the menu again", [...MENU, "graphic-stub/main", "mrun/main"]);
    },

    async pl(session) {
        // W and T held as MENU starts run PL.
        session.keyDownRaw(BBC.W);
        session.keyDownRaw(BBC.T);
        await session.runUntilAddress(address("pl", "decryptor", "pl"), MENU_SECS);
        session.keyUpRaw(BBC.W);
        session.keyUpRaw(BBC.T);
        check(session, "PL entered, encrypted", ["menu/program", "menu/scroller", "menu/menu_screen", "pl/decryptor", "pl/encrypted"]);
        await session.runUntilAddress(address("pl", "cheat", "pl_cheat.start"));
        check(session, "PL decrypted", ["menu/program", "menu/scroller", "menu/menu_screen", "pl/decryptor", "pl/cheat"]);
    },
};

const wanted = argv.length ? argv : Object.keys(scenarios);
for (const name of wanted) {
    if (!scenarios[name]) throw new Error(`no scenario ${name}`);
    console.log(`-- ${name}`);
    const session = await startBeeb({ disc: opts.disc });
    try {
        await scenarios[name](session);
    } finally {
        session.destroy();
    }
}
process.exit(failures ? 1 : 0);
