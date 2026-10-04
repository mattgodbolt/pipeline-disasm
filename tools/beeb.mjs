#!/usr/bin/env node
// Drive a headless jsbeeb from a little script, for seeing what the game does:
// screenshots, memory dumps, and a record of every address executed (which is
// what separates code from data when disassembling).
//
//   node tools/beeb.mjs [--disc original/pipeline.ssd] [--model B-DFS1.2]
//                       [--boot no] [--links HEX] [--econet STATION] SCRIPT...
//
// --links HEX fits the B's keyboard links so the OS reads HEX as its start-up
// options (OSBYTE 255) at power-on and CTRL+BREAK; with bit 3 clear a plain
// BREAK boots the disc and SHIFT+BREAK doesn't, and the autoboot is plain.
// --econet STATION fits an Econet interface (no file server), which wakes
// the NFS in the B's DNFS ROM: it then claims NETV, among other things.
//
// Each SCRIPT argument is one or more commands separated by ";":
//   wait SECS            run for SECS of emulated time (fractions allowed)
//   frames N             run until N more frames have been painted
//   key CODE [FRAMES]    press and release a key, held FRAMES frames (default 3);
//                        CODE is a KeyboardEvent.code: Space, KeyZ, Digit1, Enter...
//   down CODE / up CODE  hold or release a key
//   type TEXT            type at the keyboard (rest of the command is the text), then
//                        Return: a `key Enter` after it presses Return a second time
//   until ADDR           run until the PC reaches ADDR (hex, & or 0x optional)
//   prompt [SECS]        run until the machine waits for keyboard input
//   out                  print the text written to the screen since the last `out`
//   shot FILE            save a PNG of the active display
//   dump ADDR LEN FILE   save memory to FILE
//   hex ADDR LEN         print memory as hex
//   regs                 print the CPU registers
//   trace FILE           from here on, record every executed PC; written to FILE
//                        at the end as JSON {"executed": {"&ADDR": [opcode, count]}}
//   reads FILE           likewise every address read or written by an instruction,
//                        as {"read": [...], "written": [...]}
//   ssd FILE             save drive 0's disc as it is now, as an .ssd, to see what the
//                        program wrote to it (a sector an .ssd can't hold, say one with
//                        a CRC error, is left as zeros)
//   log ADDR             from here on, print the registers and the caller (the
//                        JSR before the return address on the stack) each time
//                        the PC reaches ADDR
//   poke ADDR BYTE...    write bytes (hex) to memory
//   break [shift|ctrl]   press BREAK, alone or with SHIFT or CTRL held for 1 s
//
// The disc is autobooted with SHIFT+BREAK (a power-on reset) before the script
// starts, unless --boot no, which leaves the machine at the BASIC prompt with
// the disc in.
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { MachineSession } from "jsbeeb/machine-session";
import { Econet } from "jsbeeb/src/econet.js";
import { BBC } from "jsbeeb/src/keymap.js";
import { toSsdOrDsd } from "jsbeeb/src/disc.js";
import { findModel } from "jsbeeb/src/models.js";

const CYCLES_PER_SEC = 2_000_000;

const parseAddr = (s) => parseInt(s.replace(/^(&|0x|\$)/i, ""), 16);
const hex2 = (n) => n.toString(16).toUpperCase().padStart(2, "0");
const hex4 = (n) => n.toString(16).toUpperCase().padStart(4, "0");

// jsbeeb's file server needs data the npm package doesn't carry, and nothing
// here needs one: a stand-in that does nothing, kept across hard resets.
function fitEconet(session, model, station) {
    const cpu = session._machine.processor;
    const noFileServer = { polltime() {}, reset() {} };
    cpu.econet = new Econet(station, findModel(model).cyclesPerSecond);
    cpu.filestore = noFileServer;
    const resetPeripherals = cpu.resetPeripherals.bind(cpu);
    cpu.resetPeripherals = (hard) => {
        resetPeripherals(hard);
        cpu.filestore = noFileServer;
    };
    cpu.polltime = cpu.buildPolltime();
}

// The B's eight links sit in the keyboard matrix as internal keys 2-9, row 0
// (which the OS's keyboard scan skips). MOS 1.20 reads them into the start-up
// options with key 9 as bit 0 up to key 2 as bit 7, a fitted link (a key
// held down) reading as 0. Typing lets go of every key, so `type` fits them
// again afterwards.
function fitLinks(session, options) {
    session.links = options;
    for (let bit = 0; bit < 8; bit++) {
        if (!(options & (1 << bit))) session.keyDownRaw([9 - bit, 0]);
    }
}

export async function startBeeb({
    disc = "original/pipeline.ssd",
    model = "B-DFS1.2",
    boot = "yes",
    links,
    econet,
} = {}) {
    const session = new MachineSession(model);
    if (econet !== undefined) fitEconet(session, model, parseInt(econet));
    await session.initialise();
    // Links with bit 3 clear swap the roles of BREAK and SHIFT+BREAK: SHIFT
    // then stops a boot rather than asking for one.
    const shiftBoots = links === undefined || (parseAddr(links) & 8) !== 0;
    if (links !== undefined) fitLinks(session, parseAddr(links));
    if (!shiftBoots) session.keyDownRaw(BBC.SHIFT);
    try {
        await session.boot(30);
    } finally {
        if (!shiftBoots) session.keyUpRaw(BBC.SHIFT);
    }
    session.loadDisc(resolve(disc));
    if (boot === "no") {
        session.drainOutput();
        return session;
    }
    if (shiftBoots) session.keyDownRaw(BBC.SHIFT);
    try {
        session.reset(true);
        await session.runFor(CYCLES_PER_SEC);
    } finally {
        if (shiftBoots) session.keyUpRaw(BBC.SHIFT);
    }
    return session;
}

// Every executed PC with the opcode found there, so a later reader can tell
// which of several programs loaded at the same address was the one running.
function recordExecution(session) {
    const executed = new Map();
    const cpu = session._machine.processor;
    const handler = cpu.debugInstruction.add((pc, opcode) => {
        const key = (pc << 8) | opcode;
        executed.set(key, (executed.get(key) ?? 0) + 1);
        return false;
    });
    return {
        stop() {
            handler.remove();
            const out = {};
            for (const [key, count] of [...executed].sort((a, b) => a[0] - b[0])) {
                const pc = key >>> 8;
                const opcode = key & 0xff;
                const name = `&${hex4(pc)}`;
                // The same address can run different code at different times.
                if (out[name]) out[`${name}/${opcode.toString(16)}`] = [opcode, count];
                else out[name] = [opcode, count];
            }
            return { executed: out };
        },
    };
}

function recordAccesses(session) {
    const read = new Set();
    const written = new Set();
    const cpu = session._machine.processor;
    const r = cpu.debugRead.add((addr) => {
        read.add(addr);
        return false;
    });
    const w = cpu.debugWrite.add((addr) => {
        written.add(addr);
        return false;
    });
    return {
        stop() {
            r.remove();
            w.remove();
            const sorted = (s) => [...s].sort((a, b) => a - b).map((a) => `&${hex4(a)}`);
            return { read: sorted(read), written: sorted(written) };
        },
    };
}

// Prints a line each time the PC reaches addr, until removed.
function logVisits(session, addr) {
    const cpu = session._machine.processor;
    return cpu.debugInstruction.add((pc) => {
        if (pc !== addr) return false;
        const [lo, hi] = session.readMemory(0x101 + cpu.s, 2);
        const caller = (((hi << 8) | lo) - 2) & 0xffff;
        console.log(
            `&${hex4(pc)} A=${hex2(cpu.a)} X=${hex2(cpu.x)} Y=${hex2(cpu.y)} S=${hex2(cpu.s)} ` +
                `from &${hex4(caller)}`,
        );
        return false;
    });
}

export async function runScript(session, commands) {
    const recorders = [];
    const logs = [];
    for (const command of commands) {
        const [op, ...args] = command.trim().split(/\s+/);
        switch (op) {
            case "":
                break;
            case "wait":
                await session.runFor(Math.round(parseFloat(args[0]) * CYCLES_PER_SEC));
                break;
            case "frames":
                await session.runFrames(parseInt(args[0]));
                break;
            case "key":
                session.keyDown(args[0]);
                await session.runFrames(parseInt(args[1] ?? "3"));
                session.keyUp(args[0]);
                await session.runFrames(2);
                break;
            case "down":
                session.keyDown(args[0]);
                break;
            case "up":
                session.keyUp(args[0]);
                break;
            case "type":
                await session.type(command.trim().slice(5));
                if (session.links !== undefined) fitLinks(session, session.links);
                break;
            case "prompt":
                await session.runUntilPrompt(parseFloat(args[0] ?? "60"), { clear: false });
                break;
            case "out":
                for (const element of session.drainOutput().elements) console.log(element.text);
                break;
            case "until":
                await session.runUntilAddress(parseAddr(args[0]));
                break;
            case "shot":
                writeFileSync(args[0], await session.screenshotActive());
                break;
            case "dump":
                writeFileSync(args[2], Buffer.from(session.readMemory(parseAddr(args[0]), parseAddr(args[1]))));
                break;
            case "hex": {
                const addr = parseAddr(args[0]);
                const bytes = session.readMemory(addr, parseAddr(args[1]));
                for (let i = 0; i < bytes.length; i += 16) {
                    const row = [...bytes.slice(i, i + 16)].map((b) => b.toString(16).padStart(2, "0"));
                    console.log(`${hex4(addr + i)}: ${row.join(" ")}`);
                }
                break;
            }
            case "regs":
                console.log(JSON.stringify(session.registers()));
                break;
            case "trace":
                recorders.push({ file: args[0], recorder: recordExecution(session) });
                break;
            case "reads":
                recorders.push({ file: args[0], recorder: recordAccesses(session) });
                break;
            case "ssd":
                writeFileSync(args[0], toSsdOrDsd(session._machine.processor.fdc._drives[0].disc, { force: true }));
                break;
            case "log":
                logs.push(logVisits(session, parseAddr(args[0])));
                break;
            case "poke":
                session.writeMemory(parseAddr(args[0]), args.slice(1).map(parseAddr));
                break;
            case "break": {
                const held = { shift: BBC.SHIFT, ctrl: BBC.CTRL }[args[0]];
                if (args[0] && !held) throw new Error(`break with what? ${command}`);
                if (held) session.keyDownRaw(held);
                try {
                    session.reset(false);
                    await session.runFor(CYCLES_PER_SEC);
                } finally {
                    if (held) session.keyUpRaw(held);
                }
                break;
            }
            default:
                throw new Error(`unknown command: ${command}`);
        }
    }
    for (const { file, recorder } of recorders) writeFileSync(file, JSON.stringify(recorder.stop(), null, 0) + "\n");
    for (const handler of logs) handler.remove();
}

async function main() {
    const argv = process.argv.slice(2);
    const opts = {};
    while (argv[0]?.startsWith("--")) {
        const flag = argv.shift().slice(2);
        opts[flag] = argv.shift();
    }
    const session = await startBeeb(opts);
    await runScript(session, argv.flatMap((a) => a.split(";")));
    session.destroy();
}

if (import.meta.url === `file://${process.argv[1]}`) await main();
