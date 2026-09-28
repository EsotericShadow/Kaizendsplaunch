#!/usr/bin/env node
// QA stills and a labelled contact sheet for a composition.
//
//   node tools/stills.mjs --comp tools/demo/index.html                 # 12 evenly spaced stills
//   node tools/stills.mjs --comp X --at 0,1.5,3.25 --out out/stills/x   # exact times
//   node tools/stills.mjs --comp X --every 0.5 --columns 6
//
// Stills are PNG, snapped to frame times, so a still matches the same frame of the video.

import path from "node:path";
import { parseArgs } from "node:util";
import { stills } from "./lib/pipeline.mjs";

const { values: v } = parseArgs({
  options: {
    comp: { type: "string" },
    out: { type: "string" },
    at: { type: "string" },
    count: { type: "string" },
    every: { type: "string" },
    from: { type: "string" },
    to: { type: "string" },
    fps: { type: "string" },
    workers: { type: "string" },
    scale: { type: "string" },
    columns: { type: "string" },
    "thumb-width": { type: "string" },
    "no-sheet": { type: "boolean" },
    root: { type: "string" },
    mount: { type: "string", multiple: true },
    browser: { type: "string" },
    "allow-network": { type: "boolean" },
    "allow-errors": { type: "boolean" },
    verbose: { type: "boolean" },
    help: { type: "boolean", short: "h" },
  },
});

if (v.help || !v.comp) {
  console.log(`Usage: node tools/stills.mjs --comp <index.html> [--at t1,t2 | --count N | --every S]
  [--out dir] [--from s] [--to s] [--columns 4] [--thumb-width 480] [--scale 1] [--workers 2]
  [--no-sheet] [--mount /prefix=/dir] [--browser shell|chrome]`);
  process.exit(v.help ? 0 : 2);
}

const num = (x) => (x == null ? undefined : Number(x));
const times = v.at ? v.at : v.every ? `every:${v.every}` : `count:${v.count || 12}`;
try {
  await stills({
    comp: v.comp,
    times,
    out: v.out || path.join("out", "stills", path.basename(path.dirname(path.resolve(v.comp)))),
    from: num(v.from),
    to: num(v.to),
    fps: num(v.fps),
    workers: num(v.workers) ?? 2,
    scale: num(v.scale),
    columns: num(v.columns),
    thumbWidth: num(v["thumb-width"]),
    sheet: !v["no-sheet"],
    root: v.root,
    mounts: v.mount || [],
    browser: v.browser,
    allowNetwork: !!v["allow-network"],
    allowErrors: !!v["allow-errors"],
    verbose: !!v.verbose,
  });
} catch (e) {
  console.error(`[stills] FAILED: ${e.message}`);
  process.exit(1);
}
