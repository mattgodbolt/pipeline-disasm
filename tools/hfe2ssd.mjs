#!/usr/bin/env node
// Decode an HFE flux capture to an .ssd using jsbeeb's own disc code, which is
// how original/pipeline.ssd was made. Needs a jsbeeb checkout (with its
// node_modules installed): JSBEEB=/path/to/jsbeeb, default ../jsbeeb.
//
//   node tools/hfe2ssd.mjs E447ED5E.hfe original/pipeline.ssd
//
// The capture is https://bbc.xania.org/archive/bbcdiscs/hfe/E447ED5E.hfe
// (served brotli-compressed: fetch with `curl --compressed`).
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const jsbeeb = resolve(process.env.JSBEEB ?? new URL("../../jsbeeb", import.meta.url).pathname);
const { Disc, DiscConfig, toSsdOrDsd, ssdOrDsdShortfalls } = await import(pathToFileURL(`${jsbeeb}/src/disc.js`));
const { loadHfe } = await import(pathToFileURL(`${jsbeeb}/src/disc-hfe.js`));

const [input, output] = process.argv.slice(2);
if (!input || !output) {
    console.error("usage: hfe2ssd.mjs IN.hfe OUT.ssd");
    process.exit(1);
}
const disc = new Disc(false, new DiscConfig(), input);
loadHfe(disc, new Uint8Array(readFileSync(input)));
// Anything a sector image can't hold (a CRC error, an odd sector) would be
// lost silently, and that's usually where copy protection lives.
const shortfalls = ssdOrDsdShortfalls(disc);
if (shortfalls.length) {
    console.error(`cannot convert losslessly: ${shortfalls.join(", ")}`);
    process.exit(1);
}
writeFileSync(output, toSsdOrDsd(disc));
