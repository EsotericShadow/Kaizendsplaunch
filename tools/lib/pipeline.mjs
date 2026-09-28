// Core render pipeline: parallel capture of a composition into H.264 chunks, lossless concat,
// audio mux, stills and contact sheets. The CLIs (render.mjs, stills.mjs) are thin wrappers.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { startServer } from "./server.mjs";
import { findFfmpeg, videoEncodeArgs, runFfmpeg, probeVideo } from "./ffmpeg.mjs";
import { launchBrowser, openComposition, seekAndCapture, withTimeout, closeBrowser } from "./browser.mjs";

export const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const log = (...a) => console.log("[render]", ...a);
const warn = (...a) => console.warn("[render] WARN", ...a);

class FatalError extends Error {
  constructor(msg) {
    super(msg);
    this.fatal = true;
  }
}

function fmtTime(s) {
  if (!Number.isFinite(s)) return "?";
  const m = Math.floor(s / 60);
  return m ? `${m}m${String(Math.round(s % 60)).padStart(2, "0")}s` : `${s.toFixed(1)}s`;
}

// ---------------------------------------------------------------------------------------------
// Server + page setup shared by render and stills

/** Pick the static root: the repo if the composition is inside it, else the composition's folder. */
function resolveRoot(compAbs, rootOpt) {
  if (rootOpt) return path.resolve(rootOpt);
  if (compAbs.startsWith(REPO + path.sep)) return REPO;
  return path.dirname(compAbs);
}

export async function startCompServer({ comp, root, mounts = [], verbose = false }) {
  const compAbs = path.resolve(comp);
  if (!fs.existsSync(compAbs)) throw new FatalError(`Composition not found: ${compAbs}`);
  const rootAbs = resolveRoot(compAbs, root);
  if (!compAbs.startsWith(rootAbs + path.sep)) {
    throw new FatalError(`Composition ${compAbs} is not inside the static root ${rootAbs}`);
  }
  const table = [
    { prefix: "/", dir: rootAbs },
    { prefix: "/__render", dir: path.join(REPO, "tools/runtime") },
    { prefix: "/__node_modules", dir: path.join(REPO, "node_modules") },
    { prefix: "/__repo", dir: REPO },
    ...mounts,
  ];
  const server = await startServer({ mounts: table, log: verbose ? (m) => log(m) : () => {} });
  const rel = path.relative(rootAbs, compAbs).split(path.sep).map(encodeURIComponent).join("/");
  return { server, url: `${server.url}/${rel}`, rootAbs, compAbs };
}

export function parseMounts(list = []) {
  return list.map((m) => {
    const i = m.indexOf("=");
    if (i <= 0) throw new FatalError(`--mount expects /prefix=/dir, got "${m}"`);
    const prefix = m.slice(0, i);
    const dir = path.resolve(m.slice(i + 1));
    if (!prefix.startsWith("/")) throw new FatalError(`--mount prefix must start with "/": ${m}`);
    if (!fs.existsSync(dir)) throw new FatalError(`--mount directory missing: ${dir}`);
    return { prefix, dir };
  });
}

/** One browser + one page, ready to seek. */
async function openSession(o, tag) {
  const browser = await launchBrowser({ kind: o.browser, executablePath: o.browserPath, gpu: o.gpu });
  try {
    const s = await openComposition(browser, {
      url: o.url,
      origin: o.server.url,
      viewport: o.viewport,
      scale: o.scale,
      allowNetwork: o.allowNetwork,
      readyTimeoutMs: o.readyTimeoutMs,
      // Page errors always; [composition] warnings once (from the probe page); the rest with --verbose.
      log: (m) => (o.verbose || /error/i.test(m) || (tag === "[probe]" && /\[composition\]/.test(m)) ? log(m) : null),
      tag,
    });
    if (s.errors.length && !o.allowErrors) {
      throw new FatalError(`Composition reported errors while loading:\n  ${s.errors.join("\n  ")}\n(--allow-errors to ignore)`);
    }
    let crashed = null;
    s.page.on("crash", () => (crashed = "page crashed"));
    browser.on("disconnected", () => (crashed = crashed || "browser disconnected"));
    return { browser, ...s, isDead: () => crashed, errorCount: s.errors.length };
  } catch (e) {
    await closeBrowser(browser);
    throw e;
  }
}

async function closeSession(s) {
  if (s) await closeBrowser(s.browser);
}

/**
 * Read width/height/fps/duration. Opens at 1920x1080 and the requested scale; returns the live
 * session too, so a caller can reuse it when the composition really is 1920x1080.
 */
async function probeComposition(o, { keep = false } = {}) {
  const s = await openSession({ ...o, viewport: { width: 1920, height: 1080 } }, "[probe]");
  if (keep && s.meta.width === 1920 && s.meta.height === 1080) return { meta: s.meta, session: s };
  await closeSession(s);
  return { meta: s.meta, session: null };
}

// ---------------------------------------------------------------------------------------------
// Options

export function normalizeOptions(raw) {
  const o = { ...raw };
  o.workers = Math.max(1, Number(o.workers ?? Math.max(1, os.cpus().length)));
  o.browser = o.browser || "shell";
  o.format = o.format || "jpeg";
  if (!["jpeg", "png"].includes(o.format)) throw new FatalError(`--format must be jpeg or png`);
  o.quality = Number(o.quality ?? 95);
  o.scale = Number(o.scale ?? 1);
  o.crf = Number(o.crf ?? 16);
  o.preset = o.preset || "slow";
  o.x264Threads = Number(o.x264Threads ?? 4);
  o.retries = Number(o.retries ?? 2);
  o.frameTimeoutMs = Number(o.frameTimeoutMs ?? 30_000);
  o.readyTimeoutMs = Number(o.readyTimeoutMs ?? 180_000);
  if (o.preview) {
    o.scale = raw.scale != null ? o.scale : 0.5;
    o.preset = raw.preset || "veryfast";
    o.crf = raw.crf != null ? o.crf : 20;
    o.quality = raw.quality != null ? o.quality : 85;
  }
  return o;
}

// ---------------------------------------------------------------------------------------------
// Video render

/**
 * render(opts) -> { out, frames, seconds, fps, stats }
 * opts: comp, out, from, to, fps, workers, audio, scale, preview, format, quality, crf, preset,
 *       x264Threads, chunkSeconds, workDir, resume, keep, browser, browserPath, gpu, root, mounts,
 *       allowNetwork, allowErrors, retries, frameTimeoutMs, freshPage, verbose, injectFault
 */
export async function render(rawOpts) {
  const o = normalizeOptions(rawOpts);
  const ffmpeg = findFfmpeg();
  const t0 = Date.now();
  const outAbs = path.resolve(o.out);
  fs.mkdirSync(path.dirname(outAbs), { recursive: true });
  if (o.audio && !fs.existsSync(o.audio)) throw new FatalError(`Audio file not found: ${o.audio}`);

  const { server, url } = await startCompServer({ comp: o.comp, root: o.root, mounts: parseMounts(o.mounts), verbose: o.verbose });
  o.server = server;
  o.url = url;
  const children = new Set();
  const sessions = new Set();
  let aborted = false;
  const onSignal = async () => {
    if (aborted) return;
    aborted = true;
    warn("interrupted: stopping workers. Completed chunks are kept; rerun with --resume.");
    for (const c of children) c.kill("SIGKILL");
    await Promise.all([...sessions].map(closeSession));
    process.exit(130);
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  try {
    const probed = await probeComposition(o, { keep: true });
    const meta = probed.meta;
    let spare = probed.session; // handed to the first worker
    if (spare) sessions.add(spare);
    const fps = Number(o.fps || meta.fps);
    const from = Number(o.from ?? 0);
    const to = Number(o.to ?? meta.duration);
    const startFrame = Math.round(from * fps);
    const endFrame = Math.round(to * fps);
    const total = endFrame - startFrame;
    if (!(total > 0)) throw new FatalError(`Empty frame range: from ${from}s to ${to}s at ${fps} fps`);
    o.viewport = { width: meta.width, height: meta.height };
    o.clip = o.scale === 1 ? null : { x: 0, y: 0, width: meta.width, height: meta.height, scale: o.scale };
    const outW = Math.round(meta.width * o.scale);
    const outH = Math.round(meta.height * o.scale);
    if (outW % 2 || outH % 2) throw new FatalError(`Output size ${outW}x${outH} must be even for yuv420p; adjust --scale`);

    // Chunks have a fixed length in frames, independent of the worker count, so the encoded
    // bitstream is identical whether you render with 1 or 8 workers.
    const chunkFrames = Math.max(1, Math.round((o.chunkSeconds ?? 1) * fps));
    const chunks = [];
    for (let s = startFrame, i = 0; s < endFrame; s += chunkFrames, i++) {
      chunks.push({ index: i, start: s, end: Math.min(endFrame, s + chunkFrames), attempts: 0 });
    }

    const key = {
      comp: path.resolve(o.comp), fps, width: meta.width, height: meta.height, scale: o.scale, format: o.format,
      quality: o.quality, crf: o.crf, preset: o.preset, x264Threads: o.x264Threads, chunkFrames, browser: o.browser,
      freshPage: !!o.freshPage,
    };
    const keyHash = crypto.createHash("sha1").update(JSON.stringify(key)).digest("hex").slice(0, 10);
    const workDir = path.resolve(o.workDir || path.join(path.dirname(outAbs), `.chunks-${path.basename(outAbs, path.extname(outAbs))}`));
    fs.mkdirSync(workDir, { recursive: true });
    const manifestPath = path.join(workDir, "manifest.json");
    let prev = null;
    try {
      prev = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    } catch {}
    if (!o.resume || !prev || prev.keyHash !== keyHash) {
      if (o.resume && prev) warn("render settings changed since the last run; not resuming");
      for (const f of fs.readdirSync(workDir)) if (f.startsWith("chunk-")) fs.rmSync(path.join(workDir, f));
    }
    fs.writeFileSync(manifestPath, JSON.stringify({ keyHash, key }, null, 2));
    const chunkPath = (c) => path.join(workDir, `chunk-${String(c.start).padStart(6, "0")}-${String(c.end).padStart(6, "0")}.mp4`);

    const todo = chunks.filter((c) => !fs.existsSync(chunkPath(c)));
    const reused = chunks.length - todo.length;
    log(
      `${path.relative(process.cwd(), path.resolve(o.comp))}: ${meta.width}x${meta.height} -> ${outW}x${outH} @ ${fps} fps, ` +
        `frames ${startFrame}..${endFrame - 1} (${total}), ${chunks.length} chunks of ${chunkFrames}` +
        (reused ? `, ${reused} reused` : "") + `, ${o.workers} workers, ${o.browser}, ${o.format}` +
        (o.format === "jpeg" ? ` q${o.quality}` : "") + `, x264 ${o.preset} crf ${o.crf}`,
    );

    // Progress
    const doneFrames = { n: chunks.filter((c) => !todo.includes(c)).reduce((a, c) => a + c.end - c.start, 0) };
    const baseDone = doneFrames.n;
    const renderStart = Date.now();
    let lastPrint = 0;
    const stats = { retries: 0, captureMs: 0, seekMs: 0 };
    const progress = (force = false) => {
      const now = Date.now();
      if (!force && now - lastPrint < 2000) return;
      lastPrint = now;
      const el = (now - renderStart) / 1000;
      const rate = (doneFrames.n - baseDone) / Math.max(el, 1e-3);
      const eta = (total - doneFrames.n) / Math.max(rate, 1e-6);
      log(`${doneFrames.n}/${total} frames (${((100 * doneFrames.n) / total).toFixed(1)}%) ${rate.toFixed(1)} fps, elapsed ${fmtTime(el)}, ETA ${fmtTime(eta)}${stats.retries ? `, retries ${stats.retries}` : ""}`);
    };

    const queue = [...todo];
    let fatal = null;
    const faultState = { injected: false };

    async function renderChunk(s, c) {
      const part = chunkPath(c).replace(/\.mp4$/, ".part.mp4");
      const args = [
        "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "image2pipe", "-framerate", String(fps), "-c:v", o.format === "jpeg" ? "mjpeg" : "png", "-i", "-",
        ...videoEncodeArgs({ fps, crf: o.crf, preset: o.preset, threads: o.x264Threads, inputIsJpeg: o.format === "jpeg", gop: chunkFrames }),
        "-an", "-f", "mp4", part,
      ];
      const ff = spawn(ffmpeg, args, { stdio: ["pipe", "ignore", "pipe"] });
      children.add(ff);
      let ffErr = "";
      ff.stderr.on("data", (d) => (ffErr = (ffErr + d).slice(-4000)));
      const ffDone = new Promise((resolve) => ff.on("close", (code) => resolve(code)));
      let ffDead = false;
      ff.on("close", () => (ffDead = true));
      ff.stdin.on("error", () => {});
      const framesInChunk = [];
      try {
        for (let f = c.start; f < c.end; f++) {
          if (fatal || aborted) throw new Error("aborted");
          const dead = s.isDead();
          if (dead) throw new Error(dead);
          if (ffDead) throw new Error(`ffmpeg exited early: ${ffErr}`);
          if (o.injectFault != null && !faultState.injected && c.index === Number(o.injectFault) && f === c.start + Math.floor((c.end - c.start) / 2)) {
            faultState.injected = true;
            warn(`injecting fault: crashing the browser during chunk ${c.index} at frame ${f}`);
            const bc = await s.browser.newBrowserCDPSession();
            await bc.send("Browser.crash").catch(() => {});
          }
          const t = f / fps;
          const buf = await seekAndCapture(s.page, s.cdp, t, { format: o.format, quality: o.quality, timeoutMs: o.frameTimeoutMs, clip: o.clip });
          framesInChunk.push(f);
          if (!ff.stdin.write(buf)) {
            await new Promise((resolve, reject) => {
              const onDrain = () => { cleanup(); resolve(); };
              const onClose = () => { cleanup(); reject(new Error(`ffmpeg exited while writing: ${ffErr}`)); };
              const cleanup = () => { ff.stdin.off("drain", onDrain); ff.off("close", onClose); };
              ff.stdin.once("drain", onDrain);
              ff.once("close", onClose);
            });
          }
          doneFrames.n++;
          progress();
        }
        ff.stdin.end();
        const code = await withTimeout(ffDone, 300_000, `ffmpeg finish chunk ${c.index}`);
        if (code !== 0) throw new Error(`ffmpeg failed on chunk ${c.index} (exit ${code}): ${ffErr}`);
        const probe = await probeVideo(part);
        if (probe.frames !== c.end - c.start) throw new Error(`chunk ${c.index}: encoded ${probe.frames} frames, expected ${c.end - c.start}`);
        fs.renameSync(part, chunkPath(c));
        if (s.errors.length > s.errorCount && !o.allowErrors) {
          throw new FatalError(`Composition errors during render:\n  ${s.errors.slice(s.errorCount).join("\n  ")}`);
        }
      } catch (e) {
        doneFrames.n -= framesInChunk.length;
        try { ff.kill("SIGKILL"); } catch {}
        await ffDone.catch(() => {});
        fs.rmSync(part, { force: true });
        throw e;
      } finally {
        children.delete(ff);
      }
    }

    async function worker(id) {
      const tag = `[w${id}]`;
      let s = null;
      if (spare && !o.freshPage) {
        s = spare;
        spare = null;
      }
      try {
        while (queue.length && !fatal && !aborted) {
          const c = queue.shift();
          try {
            if (!s) {
              s = await openSession(o, tag);
              sessions.add(s);
            }
            await renderChunk(s, c);
            if (o.freshPage) {
              // Strict mode: every chunk starts from a freshly loaded page, so its pixels cannot
              // depend on which chunks this worker rendered before.
              sessions.delete(s);
              await closeSession(s);
              s = null;
            }
          } catch (e) {
            if (aborted) return;
            if (e.fatal) {
              fatal = e;
              return;
            }
            c.attempts++;
            stats.retries++;
            warn(`${tag} chunk ${c.index} (frames ${c.start}-${c.end - 1}) failed (attempt ${c.attempts}): ${e.message.split("\n")[0]}`);
            if (s) {
              sessions.delete(s);
              await closeSession(s);
              s = null;
            }
            if (c.attempts > o.retries) {
              fatal = new Error(`chunk ${c.index} failed ${c.attempts} times; giving up. Last error: ${e.message}`);
              return;
            }
            queue.unshift(c); // retry next, on a fresh browser
          }
        }
      } finally {
        if (s) {
          sessions.delete(s);
          await closeSession(s);
        }
      }
    }

    const nWorkers = Math.min(o.workers, Math.max(1, todo.length));
    await Promise.all(Array.from({ length: nWorkers }, (_, i) => worker(i + 1)));
    if (spare) {
      sessions.delete(spare);
      await closeSession(spare);
      spare = null;
    }
    if (fatal) throw fatal;
    progress(true);
    const captureSeconds = (Date.now() - renderStart) / 1000;

    // Concat (stream copy, no re-encode) + optional audio.
    const listPath = path.join(workDir, "concat.txt");
    fs.writeFileSync(listPath, chunks.map((c) => `file '${chunkPath(c).replace(/'/g, "'\\''")}'`).join("\n") + "\n");
    const exactDur = (total / fps).toFixed(6);
    const args = ["-f", "concat", "-safe", "0", "-i", listPath];
    if (o.audio) args.push("-ss", String(startFrame / fps), "-i", path.resolve(o.audio));
    args.push("-map", "0:v:0");
    if (o.audio) args.push("-map", "1:a:0", "-c:a", "aac", "-b:a", "320k", "-af", "apad");
    args.push("-c:v", "copy", "-t", exactDur, "-movflags", "+faststart", "-metadata", "encoder=kaizendsp-launch-render");
    args.push("-f", "mp4", outAbs);
    await runFfmpeg(args, { ffmpeg });
    const probe = await probeVideo(outAbs);
    if (probe.frames !== total) throw new Error(`Output has ${probe.frames} frames, expected ${total}`);
    if (!o.keep) fs.rmSync(workDir, { recursive: true, force: true });
    const seconds = (Date.now() - t0) / 1000;
    log(`wrote ${outAbs} (${(fs.statSync(outAbs).size / 1e6).toFixed(1)} MB, ${probe.frames} frames, ${probe.video})`);
    if (probe.audio) log(`audio: ${probe.audio}`);
    log(`total ${fmtTime(seconds)}, capture+encode ${fmtTime(captureSeconds)} = ${((total - baseDone) / captureSeconds).toFixed(1)} fps`);
    return { out: outAbs, frames: total, seconds, captureSeconds, fps: (total - baseDone) / captureSeconds, stats, probe };
  } finally {
    process.off("SIGINT", onSignal);
    process.off("SIGTERM", onSignal);
    await Promise.all([...sessions].map(closeSession));
    for (const c of children) c.kill("SIGKILL");
    await server.close();
  }
}

// ---------------------------------------------------------------------------------------------
// Stills + contact sheet

/** Parse "0,1.5,3" | "count:12" | "every:0.5" into seconds. */
export function parseTimes(spec, from, to) {
  spec = String(spec).trim();
  if (spec.startsWith("count:")) {
    const n = Math.max(1, parseInt(spec.slice(6), 10));
    const span = to - from;
    return Array.from({ length: n }, (_, i) => (n === 1 ? from : from + (span * i) / n + span / (2 * n)));
  }
  if (spec.startsWith("every:")) {
    const step = Number(spec.slice(6));
    const out = [];
    for (let t = from; t < to - 1e-9; t += step) out.push(Number(t.toFixed(6)));
    return out;
  }
  return spec.split(",").filter(Boolean).map(Number);
}

/**
 * stills(opts) -> { dir, files, sheet }
 * opts: comp, times (spec string), out (directory), from, to, fps (to snap times to frames),
 *       workers, scale, columns, thumbWidth, sheet (bool), plus the browser/server options.
 */
export async function stills(rawOpts) {
  const o = normalizeOptions({ ...rawOpts, format: "png" });
  const outDir = path.resolve(o.out);
  fs.mkdirSync(outDir, { recursive: true });
  const { server, url } = await startCompServer({ comp: o.comp, root: o.root, mounts: parseMounts(o.mounts), verbose: o.verbose });
  o.server = server;
  o.url = url;
  const sessions = [];
  try {
    const { meta } = await probeComposition(o);
    o.viewport = { width: meta.width, height: meta.height };
    o.clip = o.scale === 1 ? null : { x: 0, y: 0, width: meta.width, height: meta.height, scale: o.scale };
    const fps = Number(o.fps || meta.fps);
    const from = Number(o.from ?? 0);
    const to = Number(o.to ?? meta.duration);
    // Snap to frame times so a still equals the corresponding video frame.
    const times = parseTimes(o.times || "count:12", from, to).map((t) => Math.round(t * fps) / fps);
    const n = Math.min(o.workers, times.length);
    for (let i = 0; i < n; i++) sessions.push(await openSession(o, `[s${i + 1}]`));
    const files = new Array(times.length);
    let next = 0;
    await Promise.all(
      sessions.map(async (s) => {
        while (next < times.length) {
          const i = next++;
          const t = times[i];
          const buf = await seekAndCapture(s.page, s.cdp, t, { format: "png", timeoutMs: o.frameTimeoutMs, clip: o.clip });
          const name = `still-${String(i).padStart(3, "0")}-t${t.toFixed(3)}-f${String(Math.round(t * fps)).padStart(5, "0")}.png`;
          fs.writeFileSync(path.join(outDir, name), buf);
          files[i] = { t, frame: Math.round(t * fps), file: path.join(outDir, name), sha256: crypto.createHash("sha256").update(buf).digest("hex") };
        }
      }),
    );
    let sheet = null;
    if (o.sheet !== false) {
      sheet = path.join(outDir, "contact-sheet.png");
      await contactSheet(sessions[0].browser, files, sheet, { columns: o.columns, thumbWidth: o.thumbWidth, title: path.basename(path.dirname(path.resolve(o.comp))) + "/" + path.basename(o.comp), aspect: meta.height / meta.width });
    }
    fs.writeFileSync(path.join(outDir, "stills.json"), JSON.stringify({ comp: path.resolve(o.comp), fps, files }, null, 2));
    log(`wrote ${files.length} stills to ${outDir}${sheet ? ` and ${path.basename(sheet)}` : ""}`);
    return { dir: outDir, files, sheet };
  } finally {
    await Promise.all(sessions.map(closeSession));
    await server.close();
  }
}

/** Tile PNG stills into one labelled PNG using Chromium itself (no drawtext dependency). */
export async function contactSheet(browser, files, outPath, { columns = 4, thumbWidth = 480, title = "", aspect = 9 / 16 } = {}) {
  const cols = Math.min(columns || 4, files.length);
  const thumbH = Math.round(thumbWidth * aspect);
  const cells = files
    .map((f) => {
      const b64 = fs.readFileSync(f.file).toString("base64");
      return `<figure><img src="data:image/png;base64,${b64}"><figcaption><b>${f.t.toFixed(3)} s</b><span>frame ${f.frame}</span></figcaption></figure>`;
    })
    .join("");
  const html = `<!doctype html><meta charset="utf-8"><style>
    body{margin:0;background:#101014;color:#e8e6e1;font:13px/1.2 "DejaVu Sans Mono","Liberation Mono",monospace}
    header{padding:12px 16px 4px;color:#9a98a0}
    main{display:grid;grid-template-columns:repeat(${cols},${thumbWidth}px);gap:10px;padding:10px 16px 16px}
    figure{margin:0} img{display:block;width:${thumbWidth}px;height:${thumbH}px;object-fit:contain;background:#000}
    figcaption{display:flex;justify-content:space-between;padding:5px 2px 0} b{color:#fff}
  </style><header>${title} · ${files.length} stills</header><main>${cells}</main>`;
  const ctx = await browser.newContext({ viewport: { width: cols * (thumbWidth + 10) + 22, height: 400 }, deviceScaleFactor: 1 });
  try {
    const page = await ctx.newPage();
    await page.setContent(html, { waitUntil: "load" });
    await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode())));
    await page.screenshot({ path: outPath, fullPage: true, type: "png" });
  } finally {
    await ctx.close();
  }
  return outPath;
}

// ---------------------------------------------------------------------------------------------
// Determinism check

/**
 * Capture the given times in two separate browsers, in opposite orders, plus a revisit in the
 * first browser. All three PNG hashes must match per time.
 */
export async function checkDeterminism(rawOpts) {
  const o = normalizeOptions({ ...rawOpts, format: "png" });
  const { server, url } = await startCompServer({ comp: o.comp, root: o.root, mounts: parseMounts(o.mounts), verbose: o.verbose });
  o.server = server;
  o.url = url;
  const sessions = [];
  try {
    const { meta } = await probeComposition(o);
    o.viewport = { width: meta.width, height: meta.height };
    const fps = Number(o.fps || meta.fps);
    const times = parseTimes(o.times || "count:6", 0, meta.duration).map((t) => Math.round(t * fps) / fps);
    const A = await openSession(o, "[A]");
    sessions.push(A);
    const B = await openSession(o, "[B]");
    sessions.push(B);
    const hash = (b) => crypto.createHash("sha256").update(b).digest("hex");
    const a = {}, b = {}, a2 = {};
    for (const t of times) a[t] = hash(await seekAndCapture(A.page, A.cdp, t, { format: "png" }));
    for (const t of [...times].reverse()) b[t] = hash(await seekAndCapture(B.page, B.cdp, t, { format: "png" }));
    const shuffled = [...times].sort((x, y) => ((x * 7919) % 1) - ((y * 7919) % 1) || y - x);
    for (const t of shuffled) a2[t] = hash(await seekAndCapture(A.page, A.cdp, t, { format: "png" }));
    const rows = times.map((t) => ({ t, frame: Math.round(t * fps), ok: a[t] === b[t] && a[t] === a2[t], hash: a[t].slice(0, 16), other: b[t] === a[t] ? "" : b[t].slice(0, 16) }));
    return { ok: rows.every((r) => r.ok), rows };
  } finally {
    await Promise.all(sessions.map(closeSession));
    await server.close();
  }
}
