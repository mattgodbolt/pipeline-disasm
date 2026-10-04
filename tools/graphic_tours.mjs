#!/usr/bin/env node
// Drive the Graphics Designer (H.GRAPH) through every feature in headless
// jsbeeb, recording an execution trace per tour for tools/dis6502.py
// (hints/hidden_graphic.toml lists them) and screenshots to look at.
//
//   node tools/graphic_tours.mjs [TOUR...]     default: every tour, in parallel
//
// Writes build/trace/graphic_TOUR.json and build/trace/shots/TOUR_*.png.
// Each tour boots the disc, picks "3 Edit graphics" from the menu and starts
// tracing once the designer is running (at its entry point, &2BAE), so code
// from MENU that ran earlier at the same addresses isn't mistaken for it.
//
// The designer's keys (from its key tables): Z X : / move the pixel cursor;
// the cursor keys pick a sprite; 0-4 pick a colour (4 is 0 again); Return
// plots, Delete clears; f0-f3 open the OptionsA, OptionsB, Environment and
// credits menus (cursor up/down, Return to pick, Space to leave), and CTRL
// with a letter is a shortcut for a menu item. jsbeeb's physical layout puts
// ':' on the apostrophe key, f0 on F10 and COPY on End.
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { startBeeb, runScript } from "./beeb.mjs";

const SHOTS = "build/trace/shots";

// Press the keys that type TEXT (capitals, digits and '.').
const typed = (text) =>
    [...text].flatMap((c) => {
        if (/[A-Z]/.test(c)) return [`key Key${c} 3`, "wait 0.1"];
        if (/[0-9]/.test(c)) return [`key Digit${c} 3`, "wait 0.1"];
        if (c === ".") return ["key Period 3", "wait 0.1"];
        throw new Error(`can't type ${c}`);
    });

const MENU_KEYS = ["F10", "F1", "F2", "F3"];
// Open menu N (0-3) and pick item ITEM (1-based) from it. Keys pressed in
// quick succession get lost (the menus read the keyboard buffer), hence the
// pauses between them.
const menu = (n, item) => [
    `key ${MENU_KEYS[n]} 5`,
    "wait 0.5",
    ...Array(item - 1).fill(["key ArrowDown 3", "wait 0.2"]).flat(),
    "key Enter 5",
    "wait 1",
];
const ctrl = (code) => ["down ControlLeft", `key ${code} 4`, "up ControlLeft", "wait 1"];
const hold = (code, secs) => [`down ${code}`, `wait ${secs}`, `up ${code}`];
const shot = (tour, name) => `shot ${SHOTS}/${tour}_${name}.png`;
// Pick a sprite by moving the selection: home to the top left first.
const home = [...hold("ArrowUp", 4), ...hold("ArrowLeft", 4)];
const step = (code, n) => Array(n).fill(`key ${code} 8`).flatMap((k) => [k, "wait 0.3"]);
// Load or save a file by name through an Environment menu item.
const file = (item, name, secs = 5) => [...menu(2, item), ...typed(name), "key Enter 3", `wait ${secs}`];

const TOURS = {
    // Painting: the pixel cursor, colours, plotting and clearing; every
    // sprite in the sheet, large and small; sprite edges.
    edit: (t) => [
        ...step("KeyX", 2), ...step("Slash", 2),
        "key Digit1 3", "key Enter 3", "key KeyX 3", "key Digit2 3", "key Enter 3",
        "key KeyX 3", "key Digit3 3", "key Enter 3", "key Slash 3", "key Digit0 3", "key Enter 3",
        "key Digit4 3", "key Enter 3", "key Delete 3", "key Quote 3", "key KeyZ 3", "key Delete 3",
        ...hold("KeyX", 3), ...hold("Slash", 4), ...hold("KeyZ", 3), ...hold("Quote", 4),
        ...hold("KeyZ", 1), ...hold("Quote", 1),
        shot(t, "painted"),
        // Walk the whole 5x5 sheet of large sprites, then the small ones.
        ...[0, 1, 2, 3, 4].flatMap(() => [...step("ArrowRight", 5), "key ArrowDown 3", "wait 0.2"]),
        ...step("ArrowLeft", 6), ...step("ArrowUp", 6), ...step("ArrowDown", 9),
        ...[0, 1, 2, 3].flatMap(() => [...step("ArrowRight", 4), "key ArrowDown 3", "wait 0.2"]),
        ...step("ArrowLeft", 5), ...step("ArrowUp", 4),
        shot(t, "small"),
        "key Digit2 3", ...step("KeyX", 3), "key Enter 3", ...hold("KeyX", 2), ...hold("Slash", 3),
        "key Enter 3", "key Digit3 3", ...hold("KeyZ", 2), "key Enter 3",
        ...hold("Quote", 3),
        shot(t, "small_painted"),
        ...hold("ArrowUp", 4), ...hold("ArrowRight", 4), ...hold("ArrowDown", 4), ...hold("ArrowLeft", 4),
        // The background tile (top left) repeats every pixel plotted into it.
        ...home, "key Digit3 3", "key Enter 3", ...step("KeyX", 3), "key Enter 3",
        shot(t, "background"),
    ],
    // OptionsA: Flip X, Flip Y, Delete, Undo, Animate, Obj name.
    optionsA: (t) => [
        "key ArrowRight 3", "wait 0.3", "key ArrowDown 3", "wait 0.3",
        ...menu(0, 1), shot(t, "flipx"), ...menu(0, 2), shot(t, "flipy"),
        ...menu(0, 4), shot(t, "undo"), ...menu(0, 3), shot(t, "delete"), ...menu(0, 4), shot(t, "undone"),
        // Animate only does anything on the two-frame pairs: sheet positions 9
        // and 14 (right column, rows 1 and 2) and 37-40 (bottom row, columns 1-4).
        ...menu(0, 5), shot(t, "animate_none"),
        ...home, ...step("ArrowRight", 4), ...step("ArrowDown", 1),
        ...menu(0, 5), "wait 1", shot(t, "animate1"), "wait 0.3", shot(t, "animate2"), "key Space 3", "wait 1",
        ...step("ArrowDown", 1), ...menu(0, 5), "wait 2", "key Escape 3", "wait 1", "key Enter 3", "wait 1",
        ...home, ...step("ArrowDown", 4), ...step("ArrowRight", 1),
        ...[0, 1, 2, 3].flatMap(() => [...menu(0, 5), "wait 2", "key Space 3", "wait 1", ...step("ArrowRight", 1)]),
        // Small sprites (below the sheet): names, and the operations at half size.
        ...home, ...hold("ArrowDown", 4), ...step("ArrowRight", 1),
        ...menu(0, 6), shot(t, "name"), ...typed("BOMB"), "key Delete 3", "wait 0.1", "key KeyX 3", "wait 0.1",
        "key Enter 3", "wait 1", shot(t, "named"),
        ...menu(0, 6), "key Escape 3", "wait 1", "key Enter 3", "wait 1",
        ...menu(0, 6), ...typed("ABCDEFGHIJKLMN"), "key Enter 3", "wait 1",
        ...menu(0, 1), ...menu(0, 2), ...menu(0, 3), ...menu(0, 4), ...menu(0, 5), "wait 1", "key Space 3",
        // The last small sprite (the exit's icon) has no name.
        ...hold("ArrowRight", 4), ...hold("ArrowDown", 4), ...menu(0, 6), shot(t, "man"),
        ...menu(0, 3), ...menu(0, 4),
        // Leave a menu by Space, by another menu's key, and step over its ends.
        "key F10 5", "wait 0.5", "key ArrowUp 3", "wait 0.3", ...step("ArrowDown", 8), ...step("ArrowUp", 2), "key Space 3", "wait 0.5",
        "key F10 5", "wait 0.5", "key F1 3", "wait 0.5", "key F10 5", "wait 0.5", "key Escape 3", "wait 1",
        "key Enter 3", "wait 1",
    ],
    // OptionsB: each two-sprite operation, confirmed and cancelled.
    optionsB: (t) => [
        "key ArrowRight 3", "wait 0.3", "key ArrowDown 3", "wait 0.3",
        ...menu(1, 1), shot(t, "swap"), "key ArrowRight 3", "wait 0.5", "key Enter 3", "wait 1",
        ...menu(1, 2), shot(t, "copy"), "key ArrowDown 3", "wait 0.5", "key Enter 3", "wait 1",
        ...menu(1, 3), "key ArrowLeft 3", "wait 0.5", "key Enter 3", "wait 1", shot(t, "overlay"),
        ...menu(1, 4), "key ArrowUp 3", "wait 0.5", "key Enter 3", "wait 1", shot(t, "underlay"),
        ...menu(1, 5), "key ArrowRight 3", "wait 0.5", "key Enter 3", "wait 1", shot(t, "remove"),
        ...menu(1, 6), "key ArrowRight 3", "wait 0.5", "key Enter 3", "wait 1", shot(t, "backing"),
        ...menu(1, 1), "key Space 3", "wait 1", ...menu(1, 2), "key Escape 3", "wait 1", "key Enter 3", "wait 1",
        // Large onto small and back, which it refuses or scales.
        ...menu(1, 2), ...hold("ArrowDown", 4), "key Enter 3", "wait 1", shot(t, "copy_small"),
        ...menu(1, 1), ...hold("ArrowUp", 4), "key Enter 3", "wait 1",
        ...menu(1, 3), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...menu(1, 4), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...menu(1, 5), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...menu(1, 6), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...menu(0, 4), "wait 1",
    ],
    // Environment: whole files and single sprites, to and from disc, and the
    // errors; then the default colour and the credits.
    files: (t) => [
        "key ArrowRight 3", "wait 0.3",
        ...file(4, "GFX1", 8), shot(t, "savefile"),
        ...file(4, "GFX1", 3), shot(t, "exists"), "key Enter 3", "wait 1",
        ...file(4, "GFX1", 3), "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 8",
        ...menu(0, 3),
        // Saving a sprite writes it into a graphics file that's already there.
        ...file(2, "GFX1", 2), shot(t, "savesprite"), "key ArrowDown 3", "wait 0.3", "key Enter 3", "wait 5",
        ...menu(0, 3), ...file(1, "GFX1", 5), shot(t, "loadsprite"),
        ...hold("ArrowDown", 4), ...file(2, "GFX1", 2), "key ArrowDown 3", "wait 0.3", "key Enter 3", "wait 5",
        ...menu(0, 3), ...file(1, "GFX1", 5),
        ...file(2, "GFX1", 2), "key Enter 3", "wait 1",
        ...file(2, "NEW", 5),
        ...file(1, "NOSUCH", 4), shot(t, "nosuch"), "key Space 3", "wait 1",
        ...file(1, "MENU", 4), shot(t, "wrongtype"), "key Space 3", "wait 1",
        ...file(3, "MENU", 4), "key Space 3", "wait 1",
        ...file(3, "NOSUCH", 4), "key Space 3", "wait 1",
        ...file(3, "DEFAULT", 8), shot(t, "loaddefault"),
        ...file(3, "IO", 8), shot(t, "loadio"),
        ...file(1, "IO", 5), ...file(2, "IO", 2), "key ArrowDown 3", "wait 0.3", "key Enter 3", "wait 5",
        ...hold("ArrowUp", 4), ...file(1, "IO", 5), ...file(2, "IO", 2), "key ArrowDown 3", "wait 0.3", "key Enter 3", "wait 5",
        ...menu(2, 2), "key Delete 3", "key Enter 3", "wait 2", "key Space 3", "wait 1",
        ...menu(2, 2), "key Escape 3", "wait 1", "key Enter 3", "wait 1",
        ...file(4, "IO", 8), "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 8",
        ...file(3, "GFX1", 8), shot(t, "loadfile"),
        ...menu(2, 5), shot(t, "colour"), "key Enter 3", "wait 1",
        ...menu(2, 5), "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 1",
        ...menu(2, 5), "key ArrowDown 3", "wait 0.2", "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 1",
        ...menu(2, 5), "key ArrowDown 3", "wait 0.2", "key ArrowDown 3", "wait 0.2", "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 1",
        ...menu(2, 5), "key Space 3", "wait 1",
        "key F3 5", "wait 1", shot(t, "credits"), "key Space 3", "wait 1",
        "key F3 5", "wait 1", "key Enter 3", "wait 1", "key F3 5", "wait 1", "key F2 5", "wait 1", "key Space 3",
    ],
    // CTRL shortcuts for menu items.
    shortcuts: (t) => [
        "key ArrowRight 3", "wait 0.3", "key ArrowDown 3", "wait 0.3",
        ...ctrl("KeyX"), ...ctrl("KeyY"), ...ctrl("KeyU"), ...ctrl("Delete"), ...ctrl("KeyU"),
        ...ctrl("KeyA"), "key Space 3", ...ctrl("KeyS"), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...ctrl("End"), "key ArrowRight 3", "key Enter 3", "wait 1",
        ...ctrl("KeyO"), "key ArrowLeft 3", "key Enter 3", "wait 1",
        ...ctrl("KeyR"), "key ArrowLeft 3", "key Enter 3", "wait 1",
        ...ctrl("KeyB"), "key ArrowLeft 3", "key Enter 3", "wait 1",
        ...ctrl("KeyC"), shot(t, "colour"), "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 1",
        ...ctrl("F8"), shot(t, "f8"), "key Space 3", "wait 1",
        ...ctrl("F9"), shot(t, "f9"), "key Space 3", "wait 1",
        ...ctrl("F6"), shot(t, "f6"), "key Space 3", "wait 1",
        ...ctrl("F7"), shot(t, "f7"), "key Space 3", "wait 1",
        ...hold("ArrowDown", 4), ...ctrl("KeyN"), "key Space 3", "wait 1",
        // Holding CTRL steps the pixel cursor without the sprite selection.
        "down ControlLeft", ...hold("KeyX", 1), ...hold("Slash", 1), "up ControlLeft",
    ],
    // Escape: stay, then leave for the menu through /MRUN.
    escape: (t) => [
        "key Escape 3", "wait 1", shot(t, "asked"), "key Enter 3", "wait 1",
        "key Escape 3", "wait 1", "key ArrowDown 3", "wait 0.2", "key Enter 3", "wait 2", shot(t, "insert"),
        "key Space 3", "wait 12", shot(t, "left"),
    ],
};

async function runTour(name) {
    mkdirSync(SHOTS, { recursive: true });
    const session = await startBeeb();
    await runScript(session, ["wait 30", "key Digit3 10", "wait 2", "key Enter 10", "until 2BAE"]);
    await runScript(session, [`trace build/trace/graphic_${name}.json`, "wait 12", ...TOURS[name](name)]);
    session.destroy();
}

async function main() {
    const names = process.argv.slice(2);
    if (names.length === 1) return runTour(names[0]);
    const all = names.length ? names : Object.keys(TOURS);
    const self = fileURLToPath(import.meta.url);
    await Promise.all(
        all.map(
            (name) =>
                new Promise((resolve, reject) =>
                    spawn(process.execPath, [self, name], { stdio: "inherit" }).on("exit", (code) =>
                        code === 0 ? resolve() : reject(new Error(`tour ${name} failed`)),
                    ),
                ),
        ),
    );
}

if (import.meta.url === `file://${process.argv[1]}`) await main();
