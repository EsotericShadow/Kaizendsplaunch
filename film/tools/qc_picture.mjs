#!/usr/bin/env node
// Picture QC for the main film: frame-by-frame scan of which layers and text blocks are on screen,
// the section cuts, the readout / knob-frame / caption check at the treatment's QC times (gate 5),
// the reading budget (gate 9) and the VST tile (gate 8). Gates 6, 7 and 11 are added by
// film/tools/qc_picture.py and film/film.sh check.
//
//   node film/tools/qc_picture.mjs scan      # every frame -> $OUT/qc/scan.json (about 4 min)
//   node film/tools/qc_picture.mjs gates     # gate 5 and gate 8 -> $OUT/qc/gates.json
//   node film/tools/qc_picture.mjs report    # merge into film/qc-picture.json
//
// The expected values in gate 5 are computed here from film/cues.json with their own formulas,
// not with film/lib/cues.js, so the check is independent of the code it checks.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { startCompServer, parseMounts } from "../../tools/lib/pipeline.mjs";
import { launchBrowser, openComposition, closeBrowser, seekAndCapture } from "../../tools/lib/browser.mjs";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const OUT = process.env.FILM_OUT || "/home/user/build/film";
const QC = path.join(OUT, "qc");
const COMP = path.join(REPO, "film/main/index.html");
const MOUNTS = [
  "/art/rc=/home/user/choroboros-rc/Assets",
  "/art/site=/home/user/kaizendsp/public",
  `/data=${path.join(OUT, "data")}`,
];
const cues = JSON.parse(fs.readFileSync(path.join(REPO, "film/cues.json"), "utf8"));
const FPS = cues.fps;
const FRAMES = Math.round(cues.duration * FPS);

async function session() {
  const { server, url } = await startCompServer({ comp: COMP, mounts: parseMounts(MOUNTS) });
  const browser = await launchBrowser({ kind: "shell" });
  const s = await openComposition(browser, { url, origin: server.url, log: (m) => /error/i.test(m) && console.log(m) });
  if (s.errors.length) throw new Error(s.errors.join("\n"));
  await s.page.evaluate(installProbe);
  return { server, browser, ...s, close: async () => (await closeBrowser(browser), await server.close()) };
}

// Runs in the page. Records every plate's last state and reads what is on screen.
async function installProbe() {
  const m = await import("/film/lib/plate.js");
  const plates = new Set();
  const orig = m.Plate.prototype.setState;
  m.Plate.prototype.setState = function (state) {
    this.__qcLast = state;
    plates.add(this);
    return orig.call(this, state);
  };
  const stage = document.getElementById("stage");
  const effOpacity = (n) => {
    let a = 1;
    for (let e = n; e && e !== stage; e = e.parentElement) a *= parseFloat(getComputedStyle(e).opacity);
    return a;
  };
  const visible = (n) => n.checkVisibility({ opacityProperty: true, visibilityProperty: true });
  const onStage = (n) => {
    const r = n.getBoundingClientRect();
    return r.width > 0 && r.right > 0 && r.left < 1920 && r.bottom > 0 && r.top < 1080;
  };
  const textOf = (n) => {
    if (n.classList.contains("t-headline")) {
      let s = "";
      for (const c of n.children) {
        if (!visible(c)) continue;
        s += c.firstElementChild ? c.firstElementChild.textContent : c.textContent;
      }
      return s;
    }
    if (n.classList.contains("t-pill")) return [...n.children].map((c) => c.textContent.trim()).filter(Boolean).join(" | ");
    return n.textContent.replace(/\s+/g, " ").trim();
  };
  const SEL = ".t-eyebrow,.t-headline,.t-body,.t-mono,.t-pill,.t-tag,.t-lockup,.t-btn";
  const EXTRA = ["17", "kaizendsp.com/choroboros", "Heats up", "as you play."];
  window.__qc = {
    async scan(t) {
      await window.__composition.seek(t);
      const layers = [];
      for (const l of stage.querySelectorAll(":scope > [data-layer]")) {
        const cs = getComputedStyle(l);
        if (cs.visibility !== "hidden" && parseFloat(cs.opacity) > 0) layers.push(l.dataset.layer);
      }
      const texts = {};
      for (const n of stage.querySelectorAll(SEL)) {
        if (n.parentElement.closest(SEL) && !n.classList.contains("t-btn")) continue;
        if (!visible(n) || !onStage(n)) continue;
        const a = effOpacity(n);
        if (a < 0.02) continue;
        const k = textOf(n);
        if (!k) continue;
        texts[k] = Math.max(texts[k] || 0, +a.toFixed(3));
      }
      // Blocks set as plain leaf elements rather than the type classes.
      for (const n of stage.querySelectorAll("div, span")) {
        if (n.childElementCount || !EXTRA.includes(n.textContent.trim())) continue;
        if (!visible(n) || !onStage(n)) continue;
        const a = effOpacity(n);
        if (a < 0.02) continue;
        const k = n.textContent.trim();
        texts[k] = Math.max(texts[k] || 0, +a.toFixed(3));
      }
      // The format row and the VST logo (gate 8: the logo is on screen in every frame "VST®3" is).
      let formats = 0;
      for (const row of stage.querySelectorAll(".t-formats")) {
        for (const n of row.querySelectorAll("*")) {
          if (n.childElementCount || n.textContent.trim() !== "VST®3") continue;
          if (visible(n) && onStage(n)) formats = Math.max(formats, +effOpacity(n).toFixed(3));
        }
      }
      if (formats >= 0.02) texts["VST®3 · AU · Audio Units · AAX · Standalone · macOS"] = formats;
      let vst = 0;
      for (const img of stage.querySelectorAll("img")) {
        if (!/vst-compatible\.png$/.test(img.src)) continue;
        if (visible(img) && onStage(img)) vst = Math.max(vst, +effOpacity(img).toFixed(3));
      }
      return { layers, texts, vst };
    },
    plates() {
      const out = [];
      for (const p of plates) {
        if (!visible(p.el) || !onStage(p.el) || effOpacity(p.el) < 0.5) continue;
        const st = p.__qcLast;
        const fr = p._framesOf(st);
        const readouts = {};
        for (const [k, r] of Object.entries(p.readouts || {})) {
          const v = r.last;
          readouts[k] = v == null ? null : typeof v === "string" ? v : v.text;
        }
        const r = p.el.getBoundingClientRect();
        out.push({
          engine: p.engine,
          box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
          frames: { ...fr.knobs, mix: fr.mix },
          switch: st.switchFrame ?? null,
          thumbX: p.cur && p.cur.thumbX != null ? +p.cur.thumbX.toFixed(2) : null,
          readouts,
        });
      }
      return out;
    },
  };
}

// Independent cue maths ------------------------------------------------------------------------

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = {
  toP: {
    rate: (v) => clamp(Math.pow(Math.max(0, (v - 0.005) / 19.995), 1 / 4.35)),
    offset: (v) => clamp(v / 180),
    width: (v) => clamp(v / 200),
    depth: (v) => clamp(v / 100),
    color: (v) => clamp(v / 100),
    mix: (v) => clamp(v / 100),
  },
  fromP: {
    rate: (p) => 0.005 + 19.995 * Math.pow(p, 4.35),
    offset: (p) => 180 * p,
    width: (p) => 200 * p,
    depth: (p) => 100 * p,
    color: (p) => 100 * p,
    mix: (p) => 100 * p,
  },
};
const sineInOut = (u) => -(Math.cos(Math.PI * u) - 1) / 2;
function expectValue(render, param, t) {
  let v = cues.renders[render].knobs[param];
  for (const g of cues.gestures.filter((g) => g.render === render && g.param === param)) {
    if (t >= g.t1) v = g.to;
    else if (t >= g.t0) {
      const u = sineInOut((t - g.t0) / (g.t1 - g.t0));
      const p = P.toP[param](g.from) + (P.toP[param](g.to) - P.toP[param](g.from)) * u;
      v = P.fromP[param](p);
    }
  }
  return v;
}
const fmt = (param, v) =>
  param === "rate" ? (v < 1 ? `${v.toFixed(2)} Hz` : `${v.toFixed(1)} Hz`) : param === "offset" ? `${Math.floor(v + 1e-6)}°` : `${Math.floor(v + 1e-6)}%`;
const mainFrame = (p) => Math.round(((14 + 332 * p) / 360) * 99);
const mixFrame = (p) => Math.round(155 - ((14 + 332 * p) / 360) * 155);
const thumbX = (p) => 473.8 + 498.5 * p;
const KNOBS = ["rate", "depth", "offset", "width"];

function expectPlate(render, t) {
  const frames = {};
  const readouts = {};
  for (const k of [...KNOBS, "color", "mix"]) {
    const v = expectValue(render, k, t);
    readouts[k] = fmt(k, v);
    if (KNOBS.includes(k)) frames[k] = mainFrame(P.toP[k](v));
  }
  frames.mix = mixFrame(P.toP.mix(expectValue(render, "mix", t)));
  return { frames, readouts, thumbX: +thumbX(P.toP.color(expectValue(render, "color", t))).toFixed(2) };
}

// Which render each visible plate shows at the gate-5 times (treatment 5 and 8.3).
function renderFor(engine, t) {
  if (t >= 2 && t < 3) return "R01";
  if (t >= 16 && t < 36) return { green: "R02", blue: "R03", red: "R04", purple: "R05", black: "R06" }[engine];
  if (t >= 50 && t < 54) return { green: "R01", purple: "R08" }[engine];
  if (t >= 54 && t < 58) return { blue: "R03", red: "R10", black: "R09" }[engine] || null;
  if (t >= 74) return "R01";
  return null;
}

// Gate 5 times and the caption each must show (treatment 11 and 5).
const GATE5 = [
  [0.25, { texts: ["HEADPHONES ON", "Great sound", "STEREO FIELD", "DRY | CHOROBOROS"] }],
  [2.5, { texts: ["LEVEL MATCHED", "DRY | CHOROBOROS"] }],
  [3.5, { texts: ["Great sound doesn’t sit still.", "LEVEL MATCHED"] }],
  [16.1, { texts: ["Green. Sways.", "Warm acoustic and synth sends", "SAME TAKE · LEVEL MATCHED"], absent: ["Depth."] }],
  [18.6, { texts: ["Depth."] }],
  [22.6, { texts: ["Blue. Widens.", "Offset."] }],
  [26.5, { texts: ["Red. Wavers.", "BBD | TAPE", "TWO SOUND CORES PER ENGINE", "SAME KNOBS, DIFFERENT CORE"] }],
  [30.6, { texts: ["Purple. Orbits.", "Rate."] }],
  [34.6, { texts: ["Black. Multiplies.", "Color.", "Dense ensembles. Low CPU."] }],
  [37.6, { texts: ["17", "SOUND CORES", "NOW PLAYING · LAGRANGE 5TH", "The ten cores inside the prebuilt engines, plus seven more."] }],
  [41.0, { texts: ["Build your own", "in Create.", "INTERFACE CAPTURE FROM CHOROBOROS 1.0.5"] }],
  [47.0, { texts: ["ARTWORK PACKS FOR CREATE", "26 custom looks.", "A custom look changes what Choroboros looks like, not how it sounds."] }],
  [50.8, { texts: ["FREE MODE", "Green and Purple are free.", "No card or licence key needed.", "GREEN", "PURPLE"] }],
  [55.0, { texts: ["30-day free trial. No payment card.", "Unlocks Blue, Red, Black and Create.", "BLUE", "RED", "BLACK", "CREATE"] }],
  [58.8, { texts: ["ONE-TIME PURCHASE · NO SUBSCRIPTION", "$49.99 USD.", "Lifetime updates. 30-day refund."] }],
  [63.0, { texts: ["MORE FROM KAIZEN DSP", "FOLD · COMING SOON", "A free spectral stereo shaper."] }],
  [65.5, { texts: ["MORE FROM KAIZEN DSP", "ECHOLALIA · DELAY + REVERB · COMING SOON", "Echoes that change as they return."] }],
  [68.5, { texts: ["MORE FROM KAIZEN DSP", "STOVETOP · IN DEVELOPMENT"] }],
  [72.0, { texts: ["Great sound", "doesn’t", "sit still."] }],
  [80.0, { texts: ["kaizendsp.com/choroboros", "Available now for macOS · Apple Silicon + Intel", "GREEN AND PURPLE FREE · 30-DAY TRIAL · $49.99 USD ONE-TIME", "Five prebuilt engines · 17 sound cores · Version 1.0.5", "CHOROBOROS · CHORUS PLUGIN"] }],
];

// Commands --------------------------------------------------------------------------------------

async function scan() {
  const s = await session();
  const frames = [];
  const t0 = Date.now();
  try {
    for (let f = 0; f < FRAMES; f++) {
      frames.push(await s.page.evaluate((t) => window.__qc.scan(t), f / FPS));
      if (f % 600 === 0) console.log(`scan ${f}/${FRAMES} ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
  } finally {
    await s.close();
  }
  fs.mkdirSync(QC, { recursive: true });
  fs.writeFileSync(path.join(QC, "scan.json"), JSON.stringify({ fps: FPS, frames }));
  console.log(`scan done: ${frames.length} frames`);
}

async function gates() {
  const s = await session();
  const out = { gate5: [], gate8: null };
  try {
    for (const [t, want] of GATE5) {
      const t2 = Math.round(t * FPS) / FPS;
      const { texts } = await s.page.evaluate((tt) => window.__qc.scan(tt), t2);
      const plates = await s.page.evaluate(() => window.__qc.plates());
      const rows = [];
      for (const p of plates) {
        const render = renderFor(p.engine, t2);
        if (!render) {
          rows.push({ engine: p.engine, render: null, note: "static art (no render at this time)" });
          continue;
        }
        const e = expectPlate(render, t2);
        const diffs = [];
        for (const [k, v] of Object.entries(e.frames)) if (p.frames[k] !== v) diffs.push(`${k} frame ${p.frames[k]} != ${v}`);
        for (const [k, v] of Object.entries(e.readouts)) if (p.readouts[k] != null && p.readouts[k] !== v) diffs.push(`${k} readout "${p.readouts[k]}" != "${v}"`);
        if (p.thumbX != null && Math.abs(p.thumbX - e.thumbX) > 0.05) diffs.push(`thumb x ${p.thumbX} != ${e.thumbX}`);
        rows.push({ engine: p.engine, render, frames: p.frames, readouts: p.readouts, thumbX: p.thumbX, expected: e, ok: diffs.length === 0, diffs });
      }
      const onScreen = Object.keys(texts);
      const missing = (want.texts || []).filter((w) => !onScreen.some((x) => x === w || x.includes(w)));
      const unexpected = (want.absent || []).filter((w) => onScreen.includes(w));
      out.gate5.push({ t: t2, plates: rows, texts: onScreen, missing, unexpected, ok: rows.every((r) => r.ok !== false) && !missing.length && !unexpected.length });
    }

    // Gate 8: the VST tile. Style chain, size, and pixels against the same <img> drawn alone by
    // the same browser (so only the scaling is shared; any tint, filter, overlay or blend would differ).
    const t8 = 80;
    await s.page.evaluate((tt) => window.__composition.seek(tt), t8);
    const info = await s.page.evaluate(() => {
      const img = [...document.querySelectorAll("img")].find((i) => /vst-compatible\.png$/.test(i.src));
      if (!img) return null;
      const chain = [];
      for (let e = img; e && e.id !== "stage"; e = e.parentElement) {
        const cs = getComputedStyle(e);
        chain.push({ tag: e.tagName.toLowerCase(), cls: e.className || e.dataset.layer || "", opacity: cs.opacity, filter: cs.filter, transform: cs.transform, blend: cs.mixBlendMode, visibility: cs.visibility, z: cs.zIndex });
      }
      const r = img.getBoundingClientRect();
      const tile = img.parentElement;
      const tcs = getComputedStyle(tile);
      let tileBg = null;
      for (let e = img.parentElement; e; e = e.parentElement) {
        const bg = getComputedStyle(e).backgroundColor;
        if (bg && bg !== "rgba(0, 0, 0, 0)") {
          tileBg = bg;
          break;
        }
      }
      return { src: img.getAttribute("src"), natural: [img.naturalWidth, img.naturalHeight], rect: [r.left, r.top, r.width, r.height], chain, tileBg, tileRadius: tcs.borderRadius };
    });
    let pixel = null;
    if (info) {
      const [x, y, w, h] = info.rect;
      const clip = { x: Math.floor(x), y: Math.floor(y), width: Math.ceil(x + w) - Math.floor(x), height: Math.ceil(y + h) - Math.floor(y), scale: 1 };
      const film = await seekAndCapture(s.page, s.cdp, t8, { format: "png", clip });
      const ref = await s.context.newPage();
      await ref.setViewportSize({ width: 1920, height: 1080 });
      await ref.setContent(
        `<html><body style="margin:0;background:#050506"><div style="position:absolute;left:0;top:0;width:1920px;height:1080px;background:${info.tileBg}"></div>` +
          `<img src="${new URL(info.src, s.page.url()).href}" style="position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px"></body></html>`,
      );
      await ref.evaluate(async () => {
        const i = document.querySelector("img");
        await i.decode();
      });
      const refCdp = await ref.context().newCDPSession(ref);
      const { data } = await refCdp.send("Page.captureScreenshot", { format: "png", fromSurface: true, clip });
      const refBuf = Buffer.from(data, "base64");
      fs.mkdirSync(QC, { recursive: true });
      fs.writeFileSync(path.join(QC, "vst-film.png"), film);
      fs.writeFileSync(path.join(QC, "vst-ref.png"), refBuf);
      pixel = { clip, filmPng: path.join(QC, "vst-film.png"), refPng: path.join(QC, "vst-ref.png") };
      await ref.close();
    }
    out.gate8 = { t: t8, info, pixel };
  } finally {
    await s.close();
  }
  fs.mkdirSync(QC, { recursive: true });
  fs.writeFileSync(path.join(QC, "gates.json"), JSON.stringify(out, null, 1));
  const bad = out.gate5.filter((g) => !g.ok);
  console.log(`gate 5: ${out.gate5.length - bad.length}/${out.gate5.length} ok`);
  for (const g of bad) console.log(JSON.stringify({ t: g.t, missing: g.missing, unexpected: g.unexpected, plates: g.plates.filter((p) => p.ok === false).map((p) => [p.engine, p.diffs]) }));
}

const cmd = process.argv[2];
if (cmd === "scan") await scan();
else if (cmd === "gates") await gates();
else {
  console.log("usage: node film/tools/qc_picture.mjs scan|gates");
  process.exit(2);
}
