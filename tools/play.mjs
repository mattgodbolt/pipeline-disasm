#!/usr/bin/env node
// Play PIPELINE headless for execution traces: tools/beeb.mjs's script
// language, plus keys pressed by their place in the BBC keyboard matrix
// (a game scanning the matrix sees exactly that key, whatever the host
// layout), plus a little random play.
//
//   node tools/play.mjs [--disc X.ssd] [--seed N] SCRIPT...
//
// Extra commands (the rest are beeb.mjs's; `trace`/`reads` run to the end):
//   game                 from boot: menu option 1, Return, run until &3000
//   bkey NAME [FRAMES]   press and release BBC key NAME (Z, X, COLON_STAR,
//                        SLASH, RETURN, SPACE, CTRL, ... as jsbeeb's BBC table)
//   bdown NAME / bup NAME
//   random SECS [KEYS]   hold random keys from KEYS (comma list, default the
//                        four directions) for random short spells
//   shots SECS EVERY PREFIX   run SECS, saving PREFIX-N.png every EVERY secs
//   peek ADDR [LEN]      print memory as hex on one line
//   poke ADDR BYTE...    write bytes (hex) to memory
//   save NAME / restore NAME   snapshot the machine, and go back to it
import { writeFileSync } from "node:fs";
import { BBC } from "jsbeeb/src/keymap.js";
import { runScript, startBeeb } from "./beeb.mjs";

const CYCLES_PER_SEC = 2_000_000;
const parseAddr = (s) => parseInt(s.replace(/^(&|0x|\$)/i, ""), 16);

function bbcKey(name) {
    const key = BBC[name];
    if (!key) throw new Error(`no BBC key ${name}`);
    return key;
}

// A small deterministic generator so a run can be repeated exactly.
function rng(seed) {
    let s = seed >>> 0 || 1;
    return () => {
        s ^= s << 13;
        s ^= s >>> 17;
        s ^= s << 5;
        return (s >>> 0) / 0x100000000;
    };
}

async function main() {
    const argv = process.argv.slice(2);
    const opts = {};
    while (argv[0]?.startsWith("--")) {
        const flag = argv.shift().slice(2);
        opts[flag] = argv.shift();
    }
    const random = rng(parseInt(opts.seed ?? "1"));
    delete opts.seed;
    const session = await startBeeb(opts);
    const commands = argv.flatMap((a) => a.split(";"));
    // beeb.mjs's commands go to its runScript in batches between ours. Its
    // recorders stop at the end of each batch, so `trace` is handled here
    // and spans the whole run.
    const plain = [];
    const flush = async () => {
        if (plain.length) await runScript(session, plain.splice(0));
    };
    let tracing = null;
    const snapshots = {};
    for (const command of commands) {
        const [op, ...args] = command.trim().split(/\s+/);
        switch (op) {
            case "game":
                await flush();
                await session.runFor(27 * CYCLES_PER_SEC);
                await session.type("1");
                await session.runFor(CYCLES_PER_SEC);
                session.keyDownRaw(BBC.RETURN);
                await session.runFrames(10);
                session.keyUpRaw(BBC.RETURN);
                await session.runFor(4 * CYCLES_PER_SEC);
                await session.runUntilAddress(0x3000);
                break;
            case "trace":
                await flush();
                tracing = { file: args[0], recorder: recordExecution(session) };
                break;
            case "bkey":
                await flush();
                session.keyDownRaw(bbcKey(args[0]));
                await session.runFrames(parseInt(args[1] ?? "3"));
                session.keyUpRaw(bbcKey(args[0]));
                await session.runFrames(2);
                break;
            case "bdown":
                await flush();
                session.keyDownRaw(bbcKey(args[0]));
                break;
            case "bup":
                await flush();
                session.keyUpRaw(bbcKey(args[0]));
                break;
            case "random": {
                await flush();
                const keys = (args[1] ?? "Z,X,COLON_STAR,SLASH").split(",");
                const end = parseFloat(args[0]) * 50;
                for (let frames = 0; frames < end; ) {
                    const key = bbcKey(keys[Math.floor(random() * keys.length)]);
                    const hold = 5 + Math.floor(random() * 40);
                    session.keyDownRaw(key);
                    await session.runFrames(hold);
                    session.keyUpRaw(key);
                    await session.runFrames(1);
                    frames += hold + 1;
                }
                break;
            }
            case "shots": {
                await flush();
                const every = parseFloat(args[1]);
                const n = Math.round(parseFloat(args[0]) / every);
                for (let i = 0; i < n; i++) {
                    await session.runFor(Math.round(every * CYCLES_PER_SEC));
                    writeFileSync(`${args[2]}-${i}.png`, await session.screenshotActive());
                }
                break;
            }
            case "peek": {
                await flush();
                const bytes = session.readMemory(parseAddr(args[0]), parseAddr(args[1] ?? "1"));
                console.log(`&${args[0]}: ${[...bytes].map((b) => b.toString(16).padStart(2, "0")).join(" ")}`);
                break;
            }
            case "poke":
                await flush();
                session.writeMemory(parseAddr(args[0]), args.slice(1).map(parseAddr));
                break;
            case "save":
                await flush();
                snapshots[args[0]] = session.snapshot();
                break;
            case "restore":
                await flush();
                session.restore(snapshots[args[0]]);
                break;
            default:
                plain.push(command);
        }
    }
    await flush();
    if (tracing) writeFileSync(tracing.file, JSON.stringify(tracing.recorder.stop()) + "\n");
    session.destroy();
}

// As beeb.mjs's `trace`: every executed PC with the opcode found there.
function recordExecution(session) {
    const executed = new Map();
    const cpu = session._machine.processor;
    const handler = cpu.debugInstruction.add((pc, opcode) => {
        const key = (pc << 8) | opcode;
        executed.set(key, (executed.get(key) ?? 0) + 1);
        return false;
    });
    const hex4 = (n) => n.toString(16).toUpperCase().padStart(4, "0");
    return {
        stop() {
            handler.remove();
            const out = {};
            for (const [key, count] of [...executed].sort((a, b) => a[0] - b[0])) {
                const pc = key >>> 8;
                const opcode = key & 0xff;
                const name = `&${hex4(pc)}`;
                if (out[name]) out[`${name}/${opcode.toString(16)}`] = [opcode, count];
                else out[name] = [opcode, count];
            }
            return { executed: out };
        },
    };
}

await main();
