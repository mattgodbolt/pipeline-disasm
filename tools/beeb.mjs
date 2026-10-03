#!/usr/bin/env node
// Drive a headless jsbeeb from a little script, for seeing what the game does:
// screenshots, memory dumps, and a record of every address executed (which is
// what separates code from data when disassembling).
//
//   node tools/beeb.mjs [--disc original/pipeline.ssd] [--model B-DFS1.2] SCRIPT...
//
// Each SCRIPT argument is one or more commands separated by ";":
//   wait SECS            run for SECS of emulated time (fractions allowed)
//   frames N             run until N more frames have been painted
//   key CODE [FRAMES]    press and release a key, held FRAMES frames (default 3);
//                        CODE is a KeyboardEvent.code: Space, KeyZ, Digit1, Enter...
//   down CODE / up CODE  hold or release a key
//   type TEXT            type at the keyboard (rest of the command is the text)
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
//
// The disc is autobooted with SHIFT+BREAK before the script starts, unless
// --boot no, which leaves the machine at the BASIC prompt with the disc in.
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { MachineSession } from "jsbeeb/machine-session";
import { BBC } from "jsbeeb/src/keymap.js";

const CYCLES_PER_SEC = 2_000_000;

const parseAddr = (s) => parseInt(s.replace(/^(&|0x|\$)/i, ""), 16);
const hex4 = (n) => n.toString(16).toUpperCase().padStart(4, "0");

export async function startBeeb({ disc = "original/pipeline.ssd", model = "B-DFS1.2", boot = "yes" } = {}) {
    const session = new MachineSession(model);
    await session.initialise();
    await session.boot(30);
    session.loadDisc(resolve(disc));
    if (boot === "no") {
        session.drainOutput();
        return session;
    }
    session.keyDownRaw(BBC.SHIFT);
    try {
        session.reset(true);
        await session.runFor(CYCLES_PER_SEC);
    } finally {
        session.keyUpRaw(BBC.SHIFT);
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

export async function runScript(session, commands) {
    const recorders = [];
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
            default:
                throw new Error(`unknown command: ${command}`);
        }
    }
    for (const { file, recorder } of recorders) writeFileSync(file, JSON.stringify(recorder.stop(), null, 0) + "\n");
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
