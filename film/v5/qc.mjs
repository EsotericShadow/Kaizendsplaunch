#!/usr/bin/env node
// Picture QC for the v5 portrait films (TREATMENT section 8, gates 1 to 5 and 7; gate 6 is
// `film/v5/v5.sh check`). It opens the composition in the renderer's browser, reads the scenes'
// `events` lists (window.__v5.events), seeks through the film and inspects the DOM and pixels.
//
//   node film/v5/qc.mjs [main|tiktok] [--step 0.5] [--sync-only] [--no-sync] [--range 36.08,91.216]
//
//   1. Never boring: the longest gap between designed events per section (main: 0.407-23.108 and
//      36.080-84.725 at <= 2 beats, the holds of bar 6 and bar 46 excluded; the tour at <= 2 bars;
//      TikTok: tau 0-11.352 at <= 1 beat, the freeze excluded). One frame of tolerance (the sync
//      tolerance), since a 2-beat snare-to-snare gap is 48.65 frames and lands on 48 or 49.
//   2. Sync: every event is anchored to a hit in hits.json (within 1 ms) or a grid time (2 ms), and
//      the picture changes ON the event's frame floor(60 h): the pixel change from f-1 to f is
//      measured against the change from f-2 to f-1 (quarter-size captures, grain hidden), over the
//      whole frame or, for small events, in one 30 x 30 block (the block test is logged separately).
//   3. Readability: portrait.unsafeText() on every sample (plate UI and chorustype wet copies
//      excepted); every visible text node (plate UI and
//      data-bleed excepted) at or above 24 px on screen (the legal line: 22 px, data-bleed).
//   4. Claims: the forbidden-list scan (section 4.2) over every visible string; every sample that
//      shows "VST" shows the VST tile, unscaled (natural aspect), unfiltered, fully opaque, not
//      transformed, and on top at its centre (nothing draws over it).
//   5. Colour = sound: every visible plate's grade equals demos.grade(engine, t) (frame 0 excepted).
//   7. PSE: at most 3 qualifying flashes in any rolling 1 s (after the limiter); the looks swap area.
//
// Output: $V5_OUT/qc/picture-<comp>.json (V5_OUT defaults to /home/user/build/v5).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startCompServer, parseMounts } from "../../tools/lib/pipeline.mjs";
import { launchBrowser, openComposition, closeBrowser, seekAndCapture } from "../../tools/lib/browser.mjs";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const OUT = process.env.V5_OUT || "/home/user/build/v5";
const args = process.argv.slice(2);
const which = args.find((a) => a === "main" || a === "tiktok") || "main";
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : dflt;
};
const STEP = parseFloat(opt("--step", "0.5"));
const SYNC = !args.includes("--no-sync");
const ONLY_SYNC = args.includes("--sync-only");
const RANGE = (opt("--range", "") || "").split(",").filter(Boolean).map(Number); // master s: limit the sync pixel check
const COMP = path.join(REPO, which === "main" ? "film/v5/main.html" : "film/v5/tiktok.html");
const DATA = path.join(OUT, which === "main" ? "data" : "data-tiktok");
const MOUNTS = ["/art/rc=/home/user/choroboros-rc/Assets", "/art/site=/home/user/kaizendsp/public", `/data=${DATA}`];

const grid = JSON.parse(fs.readFileSync(path.join(REPO, "film/v5/grid.json"), "utf8"));
const hits = JSON.parse(fs.readFileSync(path.join(REPO, "film/v5/hits.json"), "utf8"));
const FPS = 60;
const BEAT = grid.period_s;
const BAR = 4 * BEAT;
const T0M = grid.t0;
const allHits = [];
for (const [p, rows] of Object.entries(hits)) if (Array.isArray(rows) && ["kick", "snare", "racktom", "floortom", "hihat", "crash", "cymbal"].includes(p)) for (const r of rows) allHits.push(r[0]);
allHits.sort((a, b) => a - b);

const FORBIDDEN = [/\bwindows\b/i, /\blinux\b/i, /17 engines/i, /\blush\b/i, /shimmer/i, /ethereal/i, /cosmic/i, /spacetime/i, /updates forever/i, /\bAI\b/, /artificial intelligence/i, /\bbeta\b/i, /\bdev panel\b/i, /\bv?\d+\.\d+\.\d+\b/, /\b(44\.1|48|96) ?kHz\b/i, /\bdiscount\b/i, /\b\d+% off\b/i, /\blimited time\b/i, /\$50\b/, /\$49\b(?!\.)/, /\bableton\b|\blogic pro\b|\bpro tools\b|\breaper\b|\bfl studio\b|\bcubase\b/i, /alderson|monopoli/i];

function sections() {
  if (which === "main") {
    return [
      { name: "ACT I-II (0.407-23.108)", t0: 0.407, t1: 23.108, max: 2 * BEAT, holds: [[8.513, 10.135]] },
      { name: "ACT III tour (23.108-36.080)", t0: 23.108, t1: 36.08, max: 2 * BAR, holds: [] },
      { name: "ACT IV-VII (36.080-84.725)", t0: 36.08, t1: 84.725, max: 2 * BEAT, holds: [[73.378, 74.999]] },
    ];
  }
  return [{ name: "TikTok (tau 0-11.352)", t0: 0, t1: 11.352, max: BEAT, holds: [[4.865, 5.676]] }];
}

function anchored(tm) {
  const i = allHits.findIndex((h) => Math.abs(h - tm) <= 0.001);
  if (i >= 0) return "hit";
  const k = (tm - T0M) / (BEAT / 2); // beats and "ands"
  if (Math.abs(k - Math.round(k)) * (BEAT / 2) <= 0.002) return "grid";
  return null;
}

async function main() {
  const { server, url } = await startCompServer({ comp: COMP, mounts: parseMounts(MOUNTS) });
  const browser = await launchBrowser({ kind: "shell" });
  const logs = [];
  const s = await openComposition(browser, { url, origin: server.url, viewport: { width: 1080, height: 1920 }, log: (m) => logs.push(m) });
  if (s.errors.length) throw new Error(s.errors.join("\n"));
  const { page, cdp, meta } = s;
  const offset = await page.evaluate(() => window.__v5.manifest.offset || 0);
  const report = { comp: which, created: null, duration: meta.duration, gates: {} };

  // Gate 1: events.
  const scenes = await page.evaluate(() => window.__v5.events);
  const events = [];
  for (const sc of scenes) for (const e of sc.events) events.push({ ...e, scene: sc.id, tc: e.t - offset });
  events.sort((a, b) => a.t - b.t);
  const tol = 1 / FPS;
  const g1 = [];
  for (const sec of sections()) {
    const pts = events.filter((e) => e.tc >= sec.t0 - 1e-6 && e.tc <= sec.t1 + 1e-6).map((e) => e.tc);
    for (const [a, b] of sec.holds) pts.push(a, b);
    pts.push(sec.t0, sec.t1);
    pts.sort((a, b) => a - b);
    let worst = { gap: 0, from: null, to: null };
    const fails = [];
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1];
      const b = pts[i];
      if (sec.holds.some(([h0, h1]) => a >= h0 - 1e-6 && b <= h1 + 1e-6)) continue;
      const gap = b - a;
      if (gap > worst.gap) worst = { gap: +gap.toFixed(4), from: +(a + offset).toFixed(4), to: +(b + offset).toFixed(4) };
      if (gap > sec.max + tol) fails.push({ gap: +gap.toFixed(4), from: +(a + offset).toFixed(4), to: +(b + offset).toFixed(4) });
    }
    g1.push({ section: sec.name, limit_s: +sec.max.toFixed(4), events: pts.length, longest: worst, pass: fails.length === 0, fails });
  }
  const perScene = scenes.map((sc) => ({ id: sc.id, events: sc.events.length }));
  report.gates["1-never-boring"] = { pass: g1.every((x) => x.pass), sections: g1, perScene };

  // Gate 7: PSE (after the limiter ran in setup).
  const pse = await page.evaluate(async () => {
    const f = await import("/film/lib/flash.js");
    const list = f.flashes();
    const q = list.filter((x) => x.mode === "full" && x.peak * f.luminance(x.color) > 0.1 && x.area > 0.25).map((x) => x.t).sort((a, b) => a - b);
    let worst = 0;
    let at = null;
    for (let i = 0; i < q.length; i++) {
      let n = 0;
      for (let j = i; j < q.length && q[j] - q[i] < 1; j++) n++;
      if (n > worst) {
        worst = n;
        at = q[i];
      }
    }
    return { registered: list.length, qualifying: q.length, demoted: list.filter((x) => x.mode === "edge").map((x) => ({ id: x.id, t: +x.t.toFixed(3) })), maxPerSecond: worst, worstWindowAt: at };
  });
  report.gates["7-pse"] = { pass: pse.maxPerSecond <= 3, ...pse, looksSwapArea: which === "main" ? +((880 * 440) / (1080 * 1920)).toFixed(4) : null };

  // Probe: plates' last grade; the DOM checks at a time.
  await page.evaluate(async () => {
    const m = await import("/film/lib/plate.js");
    const orig = m.Plate.prototype.setGrade;
    window.__qcPlates = new Set();
    m.Plate.prototype.setGrade = function (g) {
      this.__qcGrade = { sat: g.sat ?? 1, bright: g.bright ?? 1 };
      window.__qcPlates.add(this);
      return orig.call(this, g);
    };
  });
  const probe = async (t) =>
    page.evaluate(async (tt) => {
      const P = await import("/film/lib/portrait.js");
      const stage = document.getElementById("stage");
      const sr = stage.getBoundingClientRect();
      // portrait.unsafeText() with the plate UI excepted (the plate's readouts and top bar are
      // picture: close-ups run them off the frame by design).
      const unsafe = [];
      {
        const T = P.SAFE.TEXT;
        const w = document.createTreeWalker(stage, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode(); n; n = w.nextNode()) {
          if (!n.textContent.trim()) continue;
          const p = n.parentElement;
          if (!p || p.closest("[data-bleed]") || p.closest('[data-layer="safe-overlay"]') || p.closest(".cb-plate")) continue;
          // Chorustype wet copies (absolute, screen-blended duplicates after the dry span) move with
          // the LFO by up to Depth x 0.5 em; the dry text they copy is checked.
          if (p.style.mixBlendMode === "screen" && p.style.position === "absolute" && p.parentElement && p.parentElement.firstElementChild !== p) continue;
          if (!p.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
          const r = document.createRange();
          r.selectNodeContents(n);
          const b = r.getBoundingClientRect();
          if (!b.width) continue;
          const x0 = b.left - sr.left;
          const y0 = b.top - sr.top;
          const rect = { x0: +x0.toFixed(1), y0: +y0.toFixed(1), x1: +(x0 + b.width).toFixed(1), y1: +(y0 + b.height).toFixed(1) };
          if (rect.x0 < T.x0 || rect.x1 > T.x1 || rect.y0 < T.y0 || rect.y1 > T.y1) unsafe.push({ text: n.textContent.trim().slice(0, 40), rect });
        }
      }
      const small = [];
      const texts = [];
      const walker = document.createTreeWalker(stage, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const txt = n.textContent.trim();
        if (!txt) continue;
        const p = n.parentElement;
        if (!p || !p.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
        const r = document.createRange();
        r.selectNodeContents(n);
        const b = r.getBoundingClientRect();
        if (!b.width || b.right < sr.left || b.left > sr.right || b.bottom < sr.top || b.top > sr.bottom) continue;
        if (p.closest('[data-layer="safe-overlay"]')) continue;
        const plateUI = !!p.closest(".cb-plate");
        if (!plateUI) texts.push(txt);
        if (plateUI || p.closest("[data-bleed]")) continue;
        // On-screen size: the font size times the element's accumulated scale.
        const fs = parseFloat(getComputedStyle(p).fontSize);
        const scale = p.getBoundingClientRect().height / (p.offsetHeight || 1);
        const px = fs * (isFinite(scale) && scale > 0 ? scale : 1);
        // The Kaizen DSP lockup is a logo, not set text: its "DSP" row is a fixed part of the mark.
        if (px < 23.5 && !p.closest(".t-lockup")) small.push({ text: txt.slice(0, 40), px: +px.toFixed(1) });
      }
      // VST tile.
      const vst = [...stage.querySelectorAll('img[alt="VST Compatible"]')].filter((i) => i.checkVisibility({ opacityProperty: true, visibilityProperty: true }));
      const vstInfo = vst.map((img) => {
        const r = img.getBoundingClientRect();
        let filtered = false;
        let transformed = false;
        let op = 1;
        for (let e = img; e && e !== stage; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.filter !== "none") filtered = true;
          if (cs.transform !== "none") transformed = true;
          if (cs.mixBlendMode !== "normal") filtered = true;
          op *= parseFloat(cs.opacity);
        }
        // Nothing draws over it: no visible element of a higher layer (or later in its own layer)
        // intersects the logo.
        const layerOf = (e) => e.closest("[data-layer]");
        const myLayer = layerOf(img);
        const myZ = parseInt(getComputedStyle(myLayer).zIndex, 10) || 0;
        let covered = [];
        for (const L of stage.querySelectorAll(":scope > [data-layer]")) {
          if (getComputedStyle(L).visibility === "hidden") continue;
          const z = parseInt(getComputedStyle(L).zIndex, 10) || 0;
          const later = L === myLayer || (z === myZ && L.compareDocumentPosition(myLayer) & Node.DOCUMENT_POSITION_PRECEDING);
          if (z < myZ || (z === myZ && !later)) continue;
          for (const e of L.querySelectorAll("*")) {
            if (e === img || img.contains(e) || e.contains(img)) continue;
            if (L === myLayer && !(img.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
            if (!e.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
            const q = e.getBoundingClientRect();
            if (q.width && q.height && q.left < r.right && q.right > r.left && q.top < r.bottom && q.bottom > r.top) covered.push(`${L.dataset.layer}: ${e.tagName}`);
          }
        }
        const top = covered.length ? null : img;
        const aspect = r.width / r.height;
        return { w: +r.width.toFixed(2), h: +r.height.toFixed(2), aspectErr: +Math.abs(aspect / (img.naturalWidth / img.naturalHeight) - 1).toFixed(4), filtered, transformed, opacity: +op.toFixed(3), onTop: top === img, covered: covered.slice(0, 5) };
      });
      // Colour = sound.
      const { getDemos } = await import("/film/lib/demos.js");
      const demos = getDemos();
      const grades = [];
      for (const pl of window.__qcPlates || []) {
        if (!pl.el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
        const r = pl.el.getBoundingClientRect();
        if (r.right < sr.left || r.left > sr.right || r.bottom < sr.top || r.top > sr.bottom) continue;
        const want = demos.grade(pl.engine, tt);
        const got = pl.__qcGrade || { sat: 1, bright: 1 };
        // A Mix move (S01, T04) grades by the knob: compare against the same rule.
        grades.push({ engine: pl.engine, got, want, ok: Math.abs(got.sat - want.sat) < 0.02 || (pl.engine === "white" && Math.abs(got.bright - want.bright) < 0.02) });
      }
      return { unsafe, small, texts, vst: vstInfo, grades };
    }, t);

  // Gates 3, 4, 5: sample the film.
  const g3 = { unsafe: [], small: [] };
  const g4 = { forbidden: [], vst: [] };
  const g5 = { mismatches: [] };
  const strings = new Set();
  const times = [];
  if (!ONLY_SYNC) {
    for (let t = 0; t < meta.duration - 1e-6; t += STEP) times.push(Math.round(t * FPS) / FPS);
    times.push((Math.round(meta.duration * FPS) - 1) / FPS);
  }
  for (const t of times) {
    await page.evaluate((tt) => window.__composition.seek(tt), t);
    const r = await probe(t);
    const tag = +(t + offset).toFixed(3);
    for (const u of r.unsafe) g3.unsafe.push({ t: tag, ...u });
    for (const u of r.small) g3.small.push({ t: tag, ...u });
    for (const s1 of r.texts) {
      strings.add(s1);
      for (const re of FORBIDDEN) if (re.test(s1)) g4.forbidden.push({ t: tag, text: s1, rule: String(re) });
    }
    const hasVstText = r.texts.some((x) => /\bVST/.test(x));
    if (hasVstText) {
      const ok = r.vst.length > 0 && r.vst.every((v) => !v.filtered && !v.transformed && v.opacity === 1 && v.onTop && v.aspectErr < 0.002);
      if (!ok) g4.vst.push({ t: tag, vst: r.vst });
    }
    if (t > 0) for (const g of r.grades) if (!g.ok) g5.mismatches.push({ t: tag, ...g });
  }
  report.gates["3-readability"] = { pass: !g3.unsafe.length && !g3.small.length, samples: times.length, unsafe: g3.unsafe.slice(0, 200), small: g3.small.slice(0, 200) };
  report.gates["4-claims"] = { pass: !g4.forbidden.length && !g4.vst.length, forbidden: g4.forbidden, vstFailures: g4.vst.slice(0, 50), strings: [...strings].sort() };
  report.gates["5-colour-sound"] = { pass: !g5.mismatches.length, mismatches: g5.mismatches.slice(0, 200) };

  // Gate 2: anchoring and the pixel change on the event frame.
  const g2 = { unanchored: [], late: [], checked: 0 };
  for (const e of events) if (!anchored(e.t)) g2.unanchored.push({ scene: e.scene, t: e.t, kind: e.kind, hit: e.hit });
  if (SYNC) {
    // The grain changes every frame and would mask small events: hide it for these captures.
    await page.addStyleTag({ content: '[data-layer="kit:grain"] { display: none !important; }' });
    const inRange = (e) => RANGE.length < 2 || (e.t >= RANGE[0] && e.t < RANGE[1]);
    const frames = [...new Set(events.filter(inRange).map((e) => Math.floor(e.tc * FPS + 1e-6)))].filter((f) => f >= 2 && f < Math.round(meta.duration * FPS));
    const clip = { x: 0, y: 0, width: meta.width, height: meta.height, scale: 0.25 };
    const grab = async (f) => (await seekAndCapture(page, cdp, f / FPS, { format: "png", clip })).toString("base64");
    // The three captures are decoded and compared in the page; only the two means come back.
    const diffs = (pngs) =>
      page.evaluate(async (list) => {
        const px = [];
        for (const b64 of list) {
          const img = new Image();
          img.src = `data:image/png;base64,${b64}`;
          await img.decode();
          const c = document.createElement("canvas");
          c.width = img.width;
          c.height = img.height;
          const x = c.getContext("2d");
          x.drawImage(img, 0, 0);
          px.push(x.getImageData(0, 0, c.width, c.height).data);
        }
        const d = (a, b) => {
          let s1 = 0;
          let n = 0;
          for (let i = 0; i < a.length; i++) {
            if (i % 4 === 3) continue;
            s1 += Math.abs(a[i] - b[i]);
            n++;
          }
          return s1 / n;
        };
        // Small events (a pill, a readout, a border) under a decaying PUNCH: the same test per
        // 30 x 30 block (quarter size). A block whose change on f is at least 2x its change on f-1
        // and visible (mean > 4 of 255) shows the event landing on its frame in its own region.
        const W = 270;
        const H = Math.floor(px[0].length / 4 / W);
        const B = 30;
        let region = false;
        for (let by = 0; by + B <= H && !region; by += B) {
          for (let bx = 0; bx + B <= W && !region; bx += B) {
            let s0 = 0;
            let s1 = 0;
            for (let y = by; y < by + B; y++) {
              for (let xx = bx; xx < bx + B; xx++) {
                const i = (y * W + xx) * 4;
                for (let ch = 0; ch < 3; ch++) {
                  s0 += Math.abs(px[0][i + ch] - px[1][i + ch]);
                  s1 += Math.abs(px[1][i + ch] - px[2][i + ch]);
                }
              }
            }
            const n = B * B * 3;
            if (s1 / n > 4 && s1 >= 2 * s0) region = true;
          }
        }
        return [d(px[0], px[1]), d(px[1], px[2]), region];
      }, pngs);
    for (const f of frames) {
      const [before, on, region] = await diffs([await grab(f - 2), await grab(f - 1), await grab(f)]);
      g2.checked++;
      const evs = events.filter((e) => Math.floor(e.tc * FPS + 1e-6) === f);
      // The change must land on f: larger than the frame before and visible (> 0.3 of 255 mean),
      // over the whole frame or in one 30 x 30 block (small events; see diffs()).
      if (!(on > before && on > 0.3)) g2.regionOnly = (g2.regionOnly || 0) + (region ? 1 : 0);
      if (!(on > before && on > 0.3) && !region) g2.late.push({ frame: f, t: +(f / FPS + offset).toFixed(3), before: +before.toFixed(3), on: +on.toFixed(3), events: evs.map((e) => `${e.scene}: ${e.kind} ${e.hit}`) });
    }
  }
  report.gates["2-sync"] = { pass: !g2.unanchored.length && !g2.late.length, checkedFrames: g2.checked, landedInRegionOnly: g2.regionOnly || 0, unanchored: g2.unanchored, notOnFrame: g2.late };
  report.created = new Date().toISOString();

  fs.mkdirSync(path.join(OUT, "qc"), { recursive: true });
  const out = path.join(OUT, "qc", `picture-${which}.json`);
  fs.writeFileSync(out, JSON.stringify(report, null, 1));
  for (const [k, v] of Object.entries(report.gates)) {
    const extra =
      k === "1-never-boring" ? v.sections.map((x) => `${x.section}: longest ${x.longest.gap} s (${x.longest.from}-${x.longest.to})${x.pass ? "" : ` FAIL x${x.fails.length}`}`).join("; ")
      : k === "2-sync" ? `${v.checkedFrames} frames; unanchored ${v.unanchored.length}; not on frame ${v.notOnFrame.length}`
      : k === "3-readability" ? `unsafe ${v.unsafe.length}, small ${v.small.length} over ${v.samples} samples`
      : k === "4-claims" ? `forbidden ${v.forbidden.length}, VST ${v.vstFailures.length}`
      : k === "5-colour-sound" ? `mismatches ${v.mismatches.length}`
      : `max ${v.maxPerSecond}/s, demoted ${v.demoted.length}`;
    console.log(`${v.pass ? "PASS" : "FAIL"}  ${k}  ${extra}`);
  }
  console.log(out);
  await closeBrowser(browser);
  await server.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
