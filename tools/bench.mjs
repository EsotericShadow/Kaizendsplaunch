#!/usr/bin/env node
// Throughput benchmark for the render pipeline.
//
//   node tools/bench.mjs [--comp tools/demo/index.html] [--to 5] [--workers 1,2,3,4] [--variants]
//                        [--capture-only]
//
// Each configuration runs `node tools/render.mjs` end to end (browser launch, page load, capture,
// x264, concat) and records wall time, frames/s and the output SHA-256. Results go to
// out/bench/bench.json. The 1-minute load average is recorded before every run: this machine
// can be shared, so compare runs only when it is near zero.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { parseArgs } from "node:util";
import { REPO, startCompServer } from "./lib/pipeline.mjs";
import { launchBrowser, openComposition, seekAndCapture, closeBrowser } from "./lib/browser.mjs";

const { values: v } = parseArgs({
  options: {
    comp: { type: "string", default: "tools/demo/index.html" },
    to: { type: "string", default: "5" },
    workers: { type: "string", default: "1,2,3,4" },
    variants: { type: "boolean" },
    "capture-only": { type: "boolean" },
    repeat: { type: "string", default: "1" },
  },
});

const OUT = path.join(REPO, "out/bench");
fs.mkdirSync(OUT, { recursive: true });
const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
const load1 = () => os.loadavg()[0];

function runRender(args) {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    const p = spawn(process.execPath, [path.join(REPO, "tools/render.mjs"), ...args], { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] });
    let out = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (out += d));
    p.on("close", (code) => {
      const wall = (Date.now() - t0) / 1000;
      if (code !== 0) return reject(new Error(out.slice(-2000)));
      const m = out.match(/capture\+encode ([\d.]+)(m?)s?([\d.]*)s? = ([\d.]+) fps/);
      resolve({ wall, out, fps: m ? Number(m[4]) : NaN });
    });
  });
}

async function captureOnly(nWorkers, frames, fps) {
  const { server, url } = await startCompServer({ comp: v.comp });
  const sessions = [];
  try {
    for (let i = 0; i < nWorkers; i++) {
      const b = await launchBrowser({ kind: "shell" });
      sessions.push({ b, ...(await openComposition(b, { url, origin: server.url })) });
    }
    const per = Math.ceil(frames / nWorkers);
    const t0 = Date.now();
    await Promise.all(
      sessions.map(async (s, i) => {
        for (let f = i * per; f < Math.min(frames, (i + 1) * per); f++) await seekAndCapture(s.page, s.cdp, f / fps, { format: "jpeg", quality: 95 });
      }),
    );
    return frames / ((Date.now() - t0) / 1000);
  } finally {
    for (const s of sessions) await closeBrowser(s.b);
    await server.close();
  }
}

const configs = [];
for (const w of v.workers.split(",").map(Number)) configs.push({ name: `w${w}`, args: ["--workers", String(w)] });
if (v.variants) {
  configs.push({ name: "w4 x264-threads 2", args: ["--workers", "4", "--x264-threads", "2"] });
  configs.push({ name: "w4 x264-threads 1", args: ["--workers", "4", "--x264-threads", "1"] });
  configs.push({ name: "w4 png", args: ["--workers", "4", "--format", "png"] });
  configs.push({ name: "w4 chrome", args: ["--workers", "4", "--browser", "chrome"] });
  configs.push({ name: "w4 preset medium", args: ["--workers", "4", "--preset", "medium"] });
  configs.push({ name: "w4 chunk 2s", args: ["--workers", "4", "--chunk", "2"] });
  configs.push({ name: "w4 preview", args: ["--workers", "4", "--preview"] });
  configs.push({ name: "w3 x264-threads 2", args: ["--workers", "3", "--x264-threads", "2"] });
}

const results = [];
const frames = Math.round(Number(v.to) * 60);
if (v["capture-only"]) {
  for (const w of v.workers.split(",").map(Number)) {
    const l = load1();
    const fps = await captureOnly(w, frames, 60);
    results.push({ name: `capture-only w${w}`, fps, load: l });
    console.log(`capture-only w${w}: ${fps.toFixed(1)} fps (load ${l.toFixed(2)})`);
  }
}
for (const c of configs) {
  for (let r = 0; r < Number(v.repeat); r++) {
    const out = path.join(OUT, `${c.name.replace(/\s+/g, "_")}.mp4`);
    const l = load1();
    const res = await runRender(["--comp", v.comp, "--out", out, "--to", v.to, ...c.args]);
    const row = { name: c.name, wall: res.wall, fps: res.fps, frames, load: l, sha: sha(out).slice(0, 16), bytes: fs.statSync(out).size };
    results.push(row);
    console.log(`${c.name}: wall ${row.wall.toFixed(1)} s, ${row.fps.toFixed(1)} fps capture+encode, ${(row.bytes / 1e6).toFixed(2)} MB, sha ${row.sha}, load before ${l.toFixed(2)}`);
  }
}
fs.writeFileSync(path.join(OUT, "bench.json"), JSON.stringify({ date: new Date().toISOString(), cpus: os.cpus().length, comp: v.comp, seconds: Number(v.to), results }, null, 2));
console.log("\n| config | wall s | fps (capture+encode) | MB | sha256 (16) | load before |\n|---|---|---|---|---|---|");
for (const r of results) {
  if (r.wall != null) console.log(`| ${r.name} | ${r.wall.toFixed(1)} | ${r.fps.toFixed(1)} | ${(r.bytes / 1e6).toFixed(2)} | ${r.sha} | ${r.load.toFixed(2)} |`);
  else console.log(`| ${r.name} | - | ${r.fps.toFixed(1)} | - | - | ${r.load.toFixed(2)} |`);
}
