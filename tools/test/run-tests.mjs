#!/usr/bin/env node
// End-to-end checks for the render pipeline.
//
//   node tools/test/run-tests.mjs [--only name,name] [--keep-output]
//
// Outputs go to out/test/ (gitignored). The demo tests need `npm run demo:assets` first.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { parseArgs } from "node:util";
import { render, stills, checkDeterminism, REPO } from "../lib/pipeline.mjs";
import { findFfmpeg, runFfmpeg, probeVideo } from "../lib/ffmpeg.mjs";

const { values: v } = parseArgs({ options: { only: { type: "string" }, "keep-output": { type: "boolean" } } });
const only = v.only ? new Set(v.only.split(",")) : null;
const OUT = path.join(REPO, "out/test");
fs.mkdirSync(OUT, { recursive: true });
const TESTCARD = path.join(REPO, "tools/test/testcard/index.html");
const DEMO = path.join(REPO, "tools/demo/index.html");
const EFFECTS = path.join(REPO, "tools/test/effects/index.html");
const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");

// Values mirrored from testcard/index.html
const PATCHES = ["#000000", "#ffffff", "#808080", "#202020", "#ff0000", "#00ff00", "#0000ff", "#ffff00",
  "#64e28b", "#b88cff", "#d0bdff", "#f6f4ef", "#07070a", "#ff776d", "#63b3ff", "#f0a04a"];
const BITS = 12;
const bitPos = (i) => ({ x: 40 + i * 72 + 32, y: 72 });
const patchPos = (i) => ({ x: 40 + (i % 8) * 230 + 100, y: 200 + Math.floor(i / 8) * 190 + 75 });
const hex = (h) => [1, 3, 5].map((k) => parseInt(h.slice(k, k + 2), 16));

/** Decode a video to RGB (BT.709 limited -> full RGB) and call fn(frameIndex, buf, w, h) per frame. */
async function eachFrame(file, fn, { crop = null } = {}) {
  const probe = await probeVideo(file);
  const m = probe.video.match(/(\d{2,5})x(\d{2,5})/);
  let w = Number(m[1]);
  let h = Number(m[2]);
  const vf = [`scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=bicubic+accurate_rnd+full_chroma_int`];
  if (crop) {
    vf.push(`crop=${crop.w}:${crop.h}:0:0`);
    w = crop.w;
    h = crop.h;
  }
  vf.push("format=rgb24");
  const size = w * h * 3;
  await new Promise((resolve, reject) => {
    const p = spawn(findFfmpeg(), ["-hide_banner", "-loglevel", "error", "-i", file, "-vf", vf.join(","), "-f", "rawvideo", "-"], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let pending = Buffer.alloc(0);
    let idx = 0;
    let err = "";
    p.stderr.on("data", (d) => (err += d));
    p.stdout.on("data", (d) => {
      pending = Buffer.concat([pending, d]);
      while (pending.length >= size) {
        fn(idx++, pending.subarray(0, size), w, h);
        pending = pending.subarray(size);
      }
    });
    p.on("close", (code) => (code === 0 ? resolve(idx) : reject(new Error(err))));
  });
}

function sampleRGB(buf, w, x, y, r = 8) {
  const acc = [0, 0, 0];
  let n = 0;
  for (let yy = y - r; yy < y + r; yy++) {
    for (let xx = x - r; xx < x + r; xx++) {
      const o = (yy * w + xx) * 3;
      acc[0] += buf[o];
      acc[1] += buf[o + 1];
      acc[2] += buf[o + 2];
      n++;
    }
  }
  return acc.map((a) => a / n);
}

/** Check barcode frame indices and colour patches in an encoded testcard render. */
async function verifyTestcard(file, { expectFrames, expectIndex, tol, scale = 1 }) {
  const seen = [];
  let maxErr = 0;
  let worst = "";
  const crop = { w: Math.round(1920 * scale), h: Math.round(560 * scale) };
  await eachFrame(
    file,
    (i, buf, w) => {
      let code = 0;
      for (let b = 0; b < BITS; b++) {
        const p = bitPos(b);
        const [r] = sampleRGB(buf, w, Math.round(p.x * scale), Math.round(p.y * scale), Math.max(2, Math.round(8 * scale)));
        code = (code << 1) | (r > 128 ? 1 : 0);
      }
      seen.push(code);
      if (i % 15 === 0) {
        PATCHES.forEach((c, k) => {
          const p = patchPos(k);
          const got = sampleRGB(buf, w, Math.round(p.x * scale), Math.round(p.y * scale), Math.max(2, Math.round(12 * scale)));
          const want = hex(c);
          const e = Math.max(...got.map((g, j) => Math.abs(g - want[j])));
          if (e > maxErr) {
            maxErr = e;
            worst = `${c} -> rgb(${got.map((g) => g.toFixed(1)).join(",")}) at frame ${i}`;
          }
        });
      }
    },
    { crop },
  );
  const problems = [];
  if (seen.length !== expectFrames) problems.push(`decoded ${seen.length} frames, expected ${expectFrames}`);
  seen.forEach((code, i) => {
    const want = expectIndex(i);
    if (code !== want && problems.length < 10) problems.push(`frame ${i}: barcode ${code}, expected ${want}`);
  });
  if (maxErr > tol) problems.push(`colour error ${maxErr.toFixed(1)} > ${tol}: ${worst}`);
  return { ok: problems.length === 0, problems, maxErr, worst };
}

const tests = [];
const test = (name, fn) => tests.push({ name, fn });

test("frames-jpeg-fault", async () => {
  // 3 workers, 0.5 s chunks, and one browser killed mid-chunk: the retry must produce the
  // exact frame sequence with no gaps, duplicates or reordering.
  const out = path.join(OUT, "testcard-jpeg.mp4");
  const r = await render({ comp: TESTCARD, out, from: 0, to: 3, workers: 3, chunkSeconds: 0.5, injectFault: 2 });
  if (r.stats.retries < 1) throw new Error("fault injection did not trigger a retry");
  const v = await verifyTestcard(out, { expectFrames: 180, expectIndex: (i) => i, tol: 6 });
  if (!v.ok) throw new Error(v.problems.join("; "));
  return `180 frames in order after ${r.stats.retries} retry; max colour error ${v.maxErr.toFixed(1)}/255 (${v.worst})`;
});

test("frames-png", async () => {
  const out = path.join(OUT, "testcard-png.mp4");
  await render({ comp: TESTCARD, out, from: 1, to: 2, workers: 2, format: "png", chunkSeconds: 0.5 });
  const v = await verifyTestcard(out, { expectFrames: 60, expectIndex: (i) => 60 + i, tol: 4 });
  if (!v.ok) throw new Error(v.problems.join("; "));
  return `60 frames (60..119) in order; max colour error ${v.maxErr.toFixed(1)}/255 (${v.worst})`;
});

test("fps-override", async () => {
  const out = path.join(OUT, "testcard-30.mp4");
  await render({ comp: TESTCARD, out, from: 0, to: 1, fps: 30, workers: 2 });
  const p = await probeVideo(out);
  const v = await verifyTestcard(out, { expectFrames: 30, expectIndex: (i) => 2 * i, tol: 6 });
  if (!v.ok || !/30 fps/.test(p.video)) throw new Error(v.problems.join("; ") + ` ${p.video}`);
  return `30 fps output, composition frame index = 2 x output frame`;
});

test("preview", async () => {
  const out = path.join(OUT, "testcard-preview.mp4");
  await render({ comp: TESTCARD, out, from: 0, to: 1, workers: 2, preview: true });
  const p = await probeVideo(out);
  if (!/960x540/.test(p.video)) throw new Error(`expected 960x540, got ${p.video}`);
  const v = await verifyTestcard(out, { expectFrames: 60, expectIndex: (i) => i, tol: 8, scale: 0.5 });
  if (!v.ok) throw new Error(v.problems.join("; "));
  return p.video;
});

test("audio-mux", async () => {
  const wav = path.join(OUT, "tone.wav");
  await runFfmpeg(["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5", "-ac", "2", "-c:a", "pcm_s24le", wav]);
  const out = path.join(OUT, "testcard-audio.mp4");
  await render({ comp: TESTCARD, out, from: 1, to: 3, workers: 2, audio: wav });
  const p = await probeVideo(out);
  if (!/aac/.test(p.audio) || !/48000 Hz/.test(p.audio)) throw new Error(`audio stream: ${p.audio}`);
  if (Math.abs(p.duration - 2) > 0.03) throw new Error(`duration ${p.duration}, expected 2.0`);
  return `${p.audio}; container duration ${p.duration.toFixed(3)} s`;
});

test("resume", async () => {
  const out = path.join(OUT, "testcard-resume.mp4");
  const workDir = path.join(OUT, ".chunks-resume");
  await render({ comp: TESTCARD, out, from: 0, to: 2, workers: 2, keep: true, workDir });
  const h1 = sha(out);
  const chunks = fs.readdirSync(workDir).filter((f) => /^chunk-.*\.mp4$/.test(f) && !f.includes(".part"));
  fs.rmSync(path.join(workDir, chunks[1]));
  const r = await render({ comp: TESTCARD, out, from: 0, to: 2, workers: 2, resume: true, workDir });
  const h2 = sha(out);
  if (h1 !== h2) throw new Error(`resumed output differs: ${h1.slice(0, 12)} vs ${h2.slice(0, 12)}`);
  return `re-rendered 1 of ${chunks.length} chunks; output byte-identical (${h1.slice(0, 12)})`;
});

test("determinism-workers", async () => {
  // Same settings, 1 vs 4 workers: the file must be byte-identical.
  const a = path.join(OUT, "demo-w1.mp4");
  const b = path.join(OUT, "demo-w4.mp4");
  await render({ comp: DEMO, out: a, from: 0, to: 2, workers: 1, chunkSeconds: 0.5 });
  await render({ comp: DEMO, out: b, from: 0, to: 2, workers: 4, chunkSeconds: 0.5 });
  const ha = sha(a);
  const hb = sha(b);
  if (ha !== hb) throw new Error(`outputs differ: w1 ${ha.slice(0, 12)} vs w4 ${hb.slice(0, 12)}`);
  return `1 and 4 workers give identical files (${ha.slice(0, 12)})`;
});

test("determinism-seek-order", async () => {
  const r = await checkDeterminism({ comp: DEMO, times: "0,0.5,1.2,2.5,3.7,4.98" });
  if (!r.ok) throw new Error(r.rows.filter((x) => !x.ok).map((x) => `t=${x.t}`).join(", "));
  return `${r.rows.length} times identical across 2 browsers and 3 seek orders`;
});

test("determinism-effects", async () => {
  // 16 common CSS/GSAP/canvas effects; see tools/test/effects/index.html.
  const r = await checkDeterminism({ comp: EFFECTS, times: "0.1,0.9,1.7,2.5,3.3,3.95" });
  if (!r.ok) throw new Error(r.rows.filter((x) => !x.ok).map((x) => `t=${x.t}`).join(", "));
  return `${r.rows.length} times identical across 2 browsers and 3 seek orders`;
});

test("scale-2x-stills", async () => {
  const dir = path.join(OUT, "stills-4k");
  fs.rmSync(dir, { recursive: true, force: true });
  const r = await stills({ comp: DEMO, times: "2.5", out: dir, workers: 1, scale: 2, sheet: false });
  const buf = fs.readFileSync(r.files[0].file);
  const w = buf.readUInt32BE(16);
  const h = buf.readUInt32BE(20);
  if (w !== 3840 || h !== 2160) throw new Error(`still is ${w}x${h}, expected 3840x2160`);
  return `${w}x${h} still (device scale 2, re-rastered, not upscaled)`;
});

test("stills", async () => {
  const dir = path.join(OUT, "stills");
  fs.rmSync(dir, { recursive: true, force: true });
  const r = await stills({ comp: DEMO, times: "count:6", out: dir, workers: 2, columns: 3 });
  if (r.files.length !== 6 || !fs.existsSync(r.sheet)) throw new Error("missing stills or sheet");
  return `6 stills + ${path.relative(REPO, r.sheet)}`;
});

test("missing-asset-fails", async () => {
  const dir = path.join(OUT, "broken");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, "index.html"),
    `<!doctype html><body style="margin:0;background:#000"><img src="does-not-exist.png">
<script type="module">import { defineComposition } from "/__render/composition.js";
defineComposition({ width: 1920, height: 1080, fps: 30, duration: 1 });</script></body>`,
  );
  const t0 = Date.now();
  try {
    await render({ comp: path.join(dir, "index.html"), out: path.join(OUT, "broken.mp4"), workers: 1 });
  } catch (e) {
    if (!/404|Broken image/.test(e.message)) throw new Error(`unexpected error: ${e.message}`);
    return `failed fast in ${((Date.now() - t0) / 1000).toFixed(1)} s: ${e.message.split("\n")[0]}`;
  }
  throw new Error("render of a composition with a missing image did not fail");
});

let failed = 0;
const results = [];
for (const t of tests) {
  if (only && !only.has(t.name)) continue;
  const t0 = Date.now();
  process.stdout.write(`\n=== ${t.name}\n`);
  try {
    const msg = await t.fn();
    results.push({ name: t.name, ok: true, msg, s: (Date.now() - t0) / 1000 });
  } catch (e) {
    failed++;
    results.push({ name: t.name, ok: false, msg: e.message, s: (Date.now() - t0) / 1000 });
  }
}
console.log("\n--- results");
for (const r of results) console.log(`${r.ok ? "PASS" : "FAIL"} ${r.name} (${r.s.toFixed(1)} s): ${r.msg}`);
if (!v["keep-output"]) {
  for (const f of fs.readdirSync(OUT)) if (f.startsWith(".chunks")) fs.rmSync(path.join(OUT, f), { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
