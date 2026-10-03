#!/usr/bin/env node
// Compare two flux images (.hfe) as a disc controller reads them: per track,
// every sector's ID (track, side, sector, size), its data, whether its data
// mark is deleted, and any CRC error. Gaps and timing don't matter to the
// software and won't match a real capture, so they're not compared.
//
//   node tools/disccmp.mjs ORIGINAL.hfe REBUILT.hfe
// Exits 0 only when every track reads the same.
import { readFileSync } from "node:fs";
import { Disc, DiscConfig } from "jsbeeb/src/disc.js";
import { loadHfe } from "jsbeeb/src/disc-hfe.js";

function readSectors(path) {
    const disc = new Disc(false, new DiscConfig(), path);
    // jsbeeb logs as it loads; this tool's output is the comparison.
    const log = console.log;
    console.log = () => {};
    try {
        loadHfe(disc, new Uint8Array(readFileSync(path)));
    } finally {
        console.log = log;
    }
    const tracks = [];
    for (let t = 0; t < disc.tracksUsed; ++t) {
        tracks.push(
            disc
                .getTrack(false, t)
                .findSectors()
                .map((s) => ({
                    id: [...s.header.slice(0, 4)].join("/"), // track/head/sector/size code
                    deleted: s.isDeleted,
                    crcError: s.hasDataCrcError || s.hasHeaderCrcError,
                    data: s.sectorData ? Buffer.from(s.sectorData).toString("hex") : "",
                })),
        );
    }
    return tracks;
}

const [a, b] = process.argv.slice(2);
if (!b) {
    console.error("usage: disccmp.mjs ORIGINAL.hfe REBUILT.hfe");
    process.exit(1);
}
const original = readSectors(a);
const rebuilt = readSectors(b);
const problems = [];
// A track with no sectors at all is unformatted; captures often have one more.
const formatted = (tracks) => tracks.length - [...tracks].reverse().findIndex((t) => t.length > 0);
const numTracks = Math.max(formatted(original), formatted(rebuilt));
let sectors = 0;
let deleted = 0;
for (let t = 0; t < numTracks; ++t) {
    const x = original[t] ?? [];
    const y = rebuilt[t] ?? [];
    if (x.length !== y.length) problems.push(`track ${t}: ${x.length} sectors originally, ${y.length} rebuilt`);
    for (let i = 0; i < Math.min(x.length, y.length); ++i) {
        const where = `track ${t} sector ${i} (${x[i].id})`;
        if (x[i].id !== y[i].id) problems.push(`${where}: ID rebuilt as ${y[i].id}`);
        if (x[i].deleted !== y[i].deleted)
            problems.push(`${where}: data mark ${x[i].deleted ? "deleted" : "normal"} originally`);
        if (x[i].crcError !== y[i].crcError) problems.push(`${where}: CRC error differs`);
        if (x[i].data !== y[i].data) problems.push(`${where}: data differs`);
        sectors++;
        if (x[i].deleted) deleted++;
    }
}
if (problems.length) {
    for (const p of problems.slice(0, 20)) console.log(p);
    if (problems.length > 20) console.log(`... and ${problems.length - 20} more`);
    process.exit(1);
}
console.log(`identical as read: ${numTracks} tracks, ${sectors} sectors, ${deleted} with deleted data marks`);
