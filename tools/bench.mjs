#!/usr/bin/env node
// Throughput benchmark for the render pipeline.
//
//   node tools/bench.mjs [--comp tools/demo/index.html] [--to 5] [--workers 1,2,3,4] [--variants]
//                        [--capture-only]
//
// Each configuration runs `node tools/render.mjs` end to end (browser launch, page load, capture,
// x264, concat) and records wall time, frames/s and the output SHA-256. Results go to
// out/bench/bench.json. The machine-wide CPU busy share is recorded for 3 s before every run:
// this machine can be shared, so compare runs only when it is near 0%.

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
    chunk: { type: "string" },
  },
});

const OUT = path.join(REPO, "out/bench");
fs.mkdirSync(OUT, { recursive: true });
const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
// CPU busy share of the whole machine over 3 s, measured right before a run. The load average
// is useless here because it still contains the previous run.
async function busyBefore(ms = 3000) {
  const snap = () => fs.readFileSync("/proc/stat", "utf8").split("\n")[0].trim().split(/\s+/).slice(1).map(Number);
  const a = snap();
  await new Promise((r) => setTimeout(r, ms));
  const b = snap();
  const d = b.map((x, i) => x - a[i]);
  const idle = d[3] + d[4];
  const total = d.reduce((x, y) => x + y, 0);
  return total ? 1 - idle / total : 0;
}

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
for (const w of v.workers.split(",").map(Number)) configs.push({ name: `w${w}`, args: ["--workers", String(w), ...(v.chunk ? ["--chunk", v.chunk] : [])] });
if (v.variants) {
  // Variants around the defaults (png transport, 2 s chunks, x264 slow crf 16, 4 x264 threads).
  configs.push({ name: "w3 default", args: ["--workers", "3"] });
  configs.push({ name: "w4 default", args: ["--workers", "4"] });
  configs.push({ name: "w3 jpeg q95", args: ["--workers", "3", "--format", "jpeg"] });
  configs.push({ name: "w3 chrome binary", args: ["--workers", "3", "--browser", "chrome"] });
  configs.push({ name: "w3 x264-threads 2", args: ["--workers", "3", "--x264-threads", "2"] });
  configs.push({ name: "w3 preset medium", args: ["--workers", "3", "--preset", "medium"] });
  configs.push({ name: "w3 chunk 1s", args: ["--workers", "3", "--chunk", "1"] });
  configs.push({ name: "w3 fresh-page", args: ["--workers", "3", "--fresh-page"] });
  configs.push({ name: "w3 preview", args: ["--workers", "3", "--preview"] });
}

const results = [];
const frames = Math.round(Number(v.to) * 60);
if (v["capture-only"]) {
  for (const w of v.workers.split(",").map(Number)) {
    const l = await busyBefore();
    const fps = await captureOnly(w, frames, 60);
    results.push({ name: `capture-only w${w}`, fps, load: l });
    console.log(`capture-only w${w}: ${fps.toFixed(1)} fps (cpu busy before ${(100 * l).toFixed(0)}%)`);
  }
}
for (const c of configs) {
  for (let r = 0; r < Number(v.repeat); r++) {
    const out = path.join(OUT, `${c.name.replace(/\s+/g, "_")}.mp4`);
    const l = await busyBefore();
    const res = await runRender(["--comp", v.comp, "--out", out, "--to", v.to, ...c.args]);
    const row = { name: c.name, wall: res.wall, fps: res.fps, frames, load: l, sha: sha(out).slice(0, 16), bytes: fs.statSync(out).size };
    results.push(row);
    console.log(`${c.name}: wall ${row.wall.toFixed(1)} s, ${row.fps.toFixed(1)} fps capture+encode, ${(row.bytes / 1e6).toFixed(2)} MB, sha ${row.sha}, cpu busy before ${(100 * l).toFixed(0)}%`);
  }
}
fs.writeFileSync(path.join(OUT, "bench.json"), JSON.stringify({ date: new Date().toISOString(), cpus: os.cpus().length, comp: v.comp, seconds: Number(v.to), results }, null, 2));
console.log("\n| config | wall s | fps (capture+encode) | MB | sha256 (16) | CPU busy before |\n|---|---|---|---|---|---|");
for (const r of results) {
  if (r.wall != null) console.log(`| ${r.name} | ${r.wall.toFixed(1)} | ${r.fps.toFixed(1)} | ${(r.bytes / 1e6).toFixed(2)} | ${r.sha} | ${(100 * r.load).toFixed(0)}% |`);
  else console.log(`| ${r.name} | - | ${r.fps.toFixed(1)} | - | - | ${(100 * r.load).toFixed(0)}% |`);
}
