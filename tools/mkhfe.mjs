#!/usr/bin/env node
// Build an HFE flux image from the rebuilt sector image, putting back what an
// .ssd can't hold: the deleted data address marks the original disc has on
// every sector of its hidden runs (src/disc.toml `deleted = true`, listed by
// mkssd.py --marks). The tracks are laid out as jsbeeb lays out an .ssd: a
// standard single-density format, ten 256-byte sectors per track.
//
//   node tools/mkhfe.mjs IN.ssd MARKS.json OUT.hfe
import { readFileSync, writeFileSync } from "node:fs";
import { Disc, DiscConfig, IbmDiscFormat } from "jsbeeb/src/disc.js";
import { toHfe } from "jsbeeb/src/disc-hfe.js";

const SECTOR_SIZE = 256;
const SECTORS_PER_TRACK = 10;

const [input, marksPath, output] = process.argv.slice(2);
if (!output) {
    console.error("usage: mkhfe.mjs IN.ssd MARKS.json OUT.hfe");
    process.exit(1);
}
const data = new Uint8Array(readFileSync(input));
const deleted = new Set(JSON.parse(readFileSync(marksPath, "utf8")).deleted);
const numTracks = Math.ceil(data.length / (SECTOR_SIZE * SECTORS_PER_TRACK));

const disc = new Disc(true, new DiscConfig(), output);
for (let track = 0; track < numTracks; ++track) {
    const builder = disc.buildTrack(false, track);
    builder.appendRepeatFmByte(0xff, IbmDiscFormat.stdGap1FFs).appendRepeatFmByte(0x00, IbmDiscFormat.stdSync00s);
    for (let sector = 0; sector < SECTORS_PER_TRACK; ++sector) {
        const logical = track * SECTORS_PER_TRACK + sector;
        builder
            .resetCrc()
            .appendFmDataAndClocks(IbmDiscFormat.idMarkDataPattern, IbmDiscFormat.markClockPattern)
            .appendFmByte(track)
            .appendFmByte(0)
            .appendFmByte(sector)
            .appendFmByte(1) // 256-byte sectors
            .appendCrc();
        builder.appendRepeatFmByte(0xff, IbmDiscFormat.stdGap2FFs).appendRepeatFmByte(0x00, IbmDiscFormat.stdSync00s);
        const mark = deleted.has(logical)
            ? IbmDiscFormat.deletedDataMarkDataPattern
            : IbmDiscFormat.dataMarkDataPattern;
        builder
            .resetCrc()
            .appendFmDataAndClocks(mark, IbmDiscFormat.markClockPattern)
            .appendFmChunk(data.subarray(logical * SECTOR_SIZE, (logical + 1) * SECTOR_SIZE))
            .appendCrc();
        if (sector !== SECTORS_PER_TRACK - 1)
            builder
                .appendRepeatFmByte(0xff, IbmDiscFormat.std10SectorGap3FFs)
                .appendRepeatFmByte(0x00, IbmDiscFormat.stdSync00s);
    }
    builder.fillFmByte(0xff);
}
writeFileSync(output, toHfe(disc));
