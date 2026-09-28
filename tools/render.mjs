#!/usr/bin/env node
// Deterministic frame renderer for HTML compositions. See docs/brief/render-pipeline.md.

import path from "node:path";
import { parseArgs } from "node:util";
import { render, stills, checkDeterminism } from "./lib/pipeline.mjs";

const HELP = `Usage: node tools/render.mjs --comp path/to/index.html --out out.mp4 [options]

Render
  --comp <file>          composition HTML (must define window.__composition)
  --out <file>           output .mp4 (with --stills: output directory)
  --from <s> --to <s>    time range in seconds (default: whole composition)
  --fps <n>              frame rate (default: the composition's fps)
  --workers <n>          parallel browsers (default: CPU count - 1)
  --audio <file.wav>     mux this audio, AAC 320k, trimmed/padded to the range
  --scale <n>            device scale factor; 2 renders a 1920x1080 comp at 3840x2160
  --preview              half resolution, x264 veryfast crf 20, jpeg q85
Capture / encode
  --format png|jpeg      frame transport from Chromium (default png; jpeg with --preview)
  --quality <n>          jpeg quality (default 95; 85 with --preview)
  --crf <n> --preset <p> x264 settings (default 16, slow)
  --x264-threads <n>     threads per chunk encoder (default 4; keep fixed for identical output)
  --chunk <s>            chunk length in seconds; also the max GOP (default 2)
  --work-dir <dir>       chunk folder (default: next to --out, .chunks-<name>)
  --resume               reuse finished chunks from an interrupted run with the same settings
  --keep                 keep the chunk folder after success
  --retries <n>          retries per chunk after a worker failure (default 2)
  --fresh-page           reload the browser for every chunk (strict: no state carried between chunks)
  --frame-timeout <ms>   per seek/capture timeout (default 30000)
Stills / checks
  --stills <spec>        write PNG stills + contact-sheet.png instead of a video.
                         spec: "0,1.5,3" | "count:12" | "every:0.5"
  --columns <n>          contact sheet columns (default 4)
  --check-determinism <spec>  capture times in two browsers / orders and compare hashes
Serving
  --root <dir>           static root (default: repo root if the comp is inside it)
  --mount /prefix=/dir   extra static mount, repeatable (e.g. /build=/home/user/build)
  --allow-network        let the page reach non-localhost URLs (blocked by default)
  --allow-errors         do not fail on page errors / HTTP 4xx
  --browser shell|chrome headless_shell (default) or full chrome binary in headless mode
  --browser-path <file>  explicit Chromium executable
  --verbose
`;

const { values: v } = parseArgs({
  options: {
    comp: { type: "string" },
    out: { type: "string" },
    from: { type: "string" },
    to: { type: "string" },
    fps: { type: "string" },
    workers: { type: "string" },
    audio: { type: "string" },
    scale: { type: "string" },
    preview: { type: "boolean" },
    format: { type: "string" },
    quality: { type: "string" },
    crf: { type: "string" },
    preset: { type: "string" },
    "x264-threads": { type: "string" },
    chunk: { type: "string" },
    "work-dir": { type: "string" },
    resume: { type: "boolean" },
    keep: { type: "boolean" },
    retries: { type: "string" },
    "fresh-page": { type: "boolean" },
    "frame-timeout": { type: "string" },
    stills: { type: "string" },
    columns: { type: "string" },
    "check-determinism": { type: "string" },
    root: { type: "string" },
    mount: { type: "string", multiple: true },
    "allow-network": { type: "boolean" },
    "allow-errors": { type: "boolean" },
    browser: { type: "string" },
    "browser-path": { type: "string" },
    gpu: { type: "boolean" },
    "inject-fault": { type: "string" },
    verbose: { type: "boolean" },
    help: { type: "boolean", short: "h" },
  },
  strict: true,
});

if (v.help || !v.comp) {
  console.log(HELP);
  process.exit(v.help ? 0 : 2);
}

const num = (x) => (x == null ? undefined : Number(x));
const common = {
  comp: v.comp,
  from: num(v.from),
  to: num(v.to),
  fps: num(v.fps),
  workers: num(v.workers),
  scale: num(v.scale),
  preview: !!v.preview,
  root: v.root,
  mounts: v.mount || [],
  allowNetwork: !!v["allow-network"],
  allowErrors: !!v["allow-errors"],
  browser: v.browser,
  browserPath: v["browser-path"],
  gpu: !!v.gpu,
  frameTimeoutMs: num(v["frame-timeout"]),
  verbose: !!v.verbose,
};

try {
  if (v["check-determinism"]) {
    const r = await checkDeterminism({ ...common, times: v["check-determinism"] });
    for (const row of r.rows) console.log(`${row.ok ? "OK  " : "DIFF"} t=${row.t.toFixed(3)} f=${row.frame} ${row.hash} ${row.other}`);
    console.log(r.ok ? "deterministic: all captures identical" : "NOT deterministic");
    process.exit(r.ok ? 0 : 1);
  } else if (v.stills) {
    const out = v.out || path.join("out", "stills", path.basename(path.dirname(path.resolve(v.comp))));
    await stills({ ...common, times: v.stills, out, columns: num(v.columns) });
  } else {
    if (!v.out) throw new Error("--out is required");
    await render({
      ...common,
      out: v.out,
      audio: v.audio,
      format: v.format,
      quality: num(v.quality),
      crf: num(v.crf),
      preset: v.preset,
      x264Threads: num(v["x264-threads"]),
      chunkSeconds: num(v.chunk),
      workDir: v["work-dir"],
      resume: !!v.resume,
      keep: !!v.keep,
      retries: num(v.retries),
      freshPage: !!v["fresh-page"],
      injectFault: v["inject-fault"],
    });
  }
} catch (e) {
  console.error(`[render] FAILED: ${e.message}`);
  if (v.verbose && e.stack) console.error(e.stack);
  process.exit(1);
}
