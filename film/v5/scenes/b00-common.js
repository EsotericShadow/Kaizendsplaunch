// Helpers shared by the Unit B scenes (b13 to b24). Not a scene: it is not in the manifest.
//
// Every helper is a pure function of t (or builds DOM once in build()). Hits are named by their
// master time with hitAt(), the earliest attack of the cluster the treatment names (TREATMENT
// header: "h is the earliest attack in the cluster").

import { el, setStyle, px, clamp } from "/film/lib/util.js";
import * as type from "/film/lib/type.js";
import { COLOR } from "/film/lib/portrait.js";
import * as M from "/film/lib/motion.js";
import { PIECES } from "/film/lib/beats.js";

export const X = 72; // left text edge
export const MAX_X = 928; // line-fit limit (TREATMENT line-fit rule)

/** Chorustype law per engine (G3): Red BBD steps, Red Tape wows, Purple orbits. */
export const LAW = { green: "SINE", blue: "SINE", red: "STEP", purple: "ORBIT", black: "SINE" };

/**
 * The earliest drum attack in [tm - 2 ms, tm + 15 ms] (master time): the hit a treatment time
 * such as "kick + rack 36.081" names. Throws when there is none, so a typo fails the build.
 */
export function hitAt(b, tm, { tol = 0.015, pieces = PIECES } = {}) {
  const t = b.comp(tm);
  let best = null;
  for (const p of pieces) for (const h of b.hitsIn(p, t - 0.002, t + tol)) if (!best || h.t < best.t) best = h;
  if (!best) throw new Error(`b00: no hit near master ${tm}`);
  return best;
}

/** Time (composition) of a bar line or beat: a plain number the motion primitives accept. */
export const barT = (b, n, k = 1) => b.beat(n, k);

/** Frame of a hit object or a time. */
export const frameOf = (b, h) => (typeof h === "number" ? b.onsetFrame(h) : h.frame);

/** True while the frame at t is in [f0, f1). */
export function inF(b, t, f0, f1) {
  const f = b.frameAt(t);
  return f >= f0 && f < f1;
}

/** Record a designed event (master time) for the QC. */
export function ev(scene, b, h, kind, label) {
  const tm = typeof h === "number" ? b.master(h) : h.tm;
  scene.events.push({ t: +tm.toFixed(4), kind, hit: label });
}

// Type -------------------------------------------------------------------------------------------

/**
 * Line-fit (TREATMENT section 2): every line is measured once the fonts are in (setup). A line
 * that would pass MAX_X is set smaller, never under its minimum. A line that still does not fit is
 * reported (the copy deck's breaks are chosen so it never happens).
 */
export function fitter() {
  const list = [];
  return {
    add(node, { x = X, size, min, maxX = MAX_X }) {
      list.push({ node, x, size, min, maxX });
      return node;
    },
    run() {
      for (const f of list) {
        let s = f.size;
        const w = () => f.node.offsetWidth;
        while (f.x + w() > f.maxX && s > f.min) {
          s = Math.max(f.min, s - 2);
          f.node.style.fontSize = px(s);
          type.setBaseline(f.node, f.node.__place.baseline);
        }
        if (f.x + w() > f.maxX) console.warn(`[v5] line-fit: "${f.node.textContent}" is ${w()} px wide at its minimum ${f.min} px`);
      }
    },
  };
}

/** Headline line (Fraunces 600, -0.02 em) with an optional italic lavender accent. */
export function headLine(parent, fit, { text = "", accent = "", size = 104, baseline, x = X, color = COLOR.fg, accentColor = COLOR.lavender, min = 96 }) {
  const h = type.headline({ text, accent, size, parent, x, baseline, color, accentColor });
  setStyle(h.el, "transformOrigin", "0% 80%");
  if (fit) fit.add(h.el, { x, size, min });
  return h;
}

/** Body line (Inter). */
export function bodyLine(parent, fit, text, { size = 44, baseline, x = X, color = COLOR.fg, weight = 500, min = 40 }) {
  const n = type.body(text, { parent, size, weight, color, x, baseline });
  setStyle(n, "transformOrigin", "0% 80%");
  if (fit) fit.add(n, { x, size, min });
  return n;
}

/** Eyebrow (JetBrains Mono 600, uppercase, 0.3 em). */
export function eyebrowLine(parent, fit, text, { size = 30, baseline, x = X, color = COLOR.purple, min = 28 }) {
  const n = type.eyebrow(text, { parent, size, color, x, baseline });
  setStyle(n, "transformOrigin", "0% 80%");
  if (fit) fit.add(n, { x, size, min });
  return n;
}

/** Mono line (tags, captions). */
export function monoLine(parent, fit, text, { size = 28, baseline, x = X, color = COLOR.fg, tracking = 0.12, min = 26 }) {
  const n = type.mono(text, { parent, size, color, tracking, x, baseline });
  setStyle(n, "transformOrigin", "0% 80%");
  if (fit) fit.add(n, { x, size, min });
  return n;
}

/** A pill label: mono text on a filled or outlined rounded box, placed by its top-left. */
export function pillLabel(parent, text, { size = 26, fill = null, color = COLOR.bg, border = null, x = 0, y = 0, h = null, padX = 16 }) {
  const n = el("div", {
    parent,
    text,
    cls: "v5-pill",
    style: {
      font: `600 ${size}px ${type.FONT.mono}`, // before lineHeight: the shorthand resets it
      position: "absolute",
      left: px(x),
      top: px(y),
      height: h ? px(h) : "",
      lineHeight: h ? px(h - (border ? 4 : 0)) : "1.5",
      padding: `0 ${px(padX)} 0 ${px(padX + size * 0.12)}`,
      boxSizing: "border-box",
      letterSpacing: "0.12em",
      color,
      background: fill || "transparent",
      border: border ? `2px solid ${border}` : "none",
      borderRadius: px((h || size * 1.5) / 2),
      whiteSpace: "pre",
      transformOrigin: "0% 50%",
    },
  });
  return n;
}

/** Show/hide by visibility. */
export function vis(node, on) {
  setStyle(node, "visibility", on ? "" : "hidden");
}

/** Apply a STAMP ({ scale, opacity, on }) to a node, with an extra scale (PUNCH) and offset. */
export function applyStamp(node, st, { k = 1, dx = 0, dy = 0 } = {}) {
  setStyle(node, "visibility", st.on ? "" : "hidden");
  if (!st.on) return;
  setStyle(node, "opacity", st.opacity >= 1 ? "" : String(+st.opacity.toFixed(4)));
  const s = st.scale * k;
  setStyle(node, "transform", s === 1 && !dx && !dy ? "" : M.transform({ x: dx, y: dy, scale: s }));
}

/** A static node shown from hit h on (a hard cut in), with an optional transform. */
export function applyOn(b, t, node, h, { k = 1, dx = 0, dy = 0 } = {}) {
  const on = b.frameAt(t) >= frameOf(b, h);
  setStyle(node, "visibility", on ? "" : "hidden");
  if (on) setStyle(node, "transform", k === 1 && !dx && !dy ? "" : M.transform({ x: dx, y: dy, scale: k }));
  return on;
}

// Flashes -------------------------------------------------------------------------------------------

/**
 * A scene's flashes on one additive layer under the type (z 30). list: [{ h, color, peak } or
 * { h, color, frames: [..] }, edge: true for an edge glow that never qualifies for the PSE count].
 * Every flash is registered with the PSE limiter; render(t, on) draws the strongest one.
 */
export function flashBank(ctx, lib, list, { z = 30, prefix = ctx.id } = {}) {
  const L = ctx.layer("flash", z);
  const fl = lib.createFlash(L);
  const items = list.map((f, i) => {
    const id = `${prefix}-${i}`;
    const peak = f.frames ? f.frames[0] : f.peak ?? M.MOTION.flash.peak;
    lib.registerFlash({ t: typeof f.h === "number" ? f.h : f.h.t, peak, color: f.color, area: f.edge ? 0.02 : 1, id });
    return { ...f, id, peak };
  });
  return {
    layer: L,
    items,
    render(t, on = true) {
      lib.util.show(L, on);
      if (!on) return;
      let best = null;
      let ba = 0;
      for (const f of items) {
        const a = f.frames ? M.flash(t, [f.h], { frames: f.frames }) : M.flash(t, [f.h], { peak: f.peak });
        if (a > ba) {
          ba = a;
          best = f;
        }
      }
      const mode = best ? (best.edge ? "edge" : lib.flash.flashMode(best.id)) : "full";
      fl.render(t, ba, best ? best.color : "#ffffff", mode);
    },
  };
}

/** The chorustype settings heard at t, with the wet copies spread by `spread` (0..1, +30 % at 1). */
export function ctSettings(demos, t, spread = 0) {
  const s = demos.settingsAt(t);
  if (!s) return null;
  if (!spread) return s;
  return { ...s, depth: s.depth * (1 + 0.3 * spread), width: s.width * (1 + 0.3 * spread) + 60 * spread };
}

/** 0..1 envelope that relaxes linearly over `dur` s after each of `hits` (frame-exact). */
export function relax(b, t, hits, dur = 0.15) {
  let e = 0;
  for (const h of hits) {
    const s = b.since(t, typeof h === "number" ? h : h.t);
    if (s >= 0 && s < dur) e = Math.max(e, 1 - s / dur);
  }
  return e;
}

/** A soft black band behind a body line (y0 to y1), for type set over a picture. */
export function band(parent, y0, y1, alpha = 0.72, { x0 = 0, x1 = 1080, feather = 24 } = {}) {
  const h = y1 - y0 + 2 * feather;
  const f = (feather / h) * 100;
  return el("div", {
    parent,
    style: {
      position: "absolute",
      left: px(x0),
      top: px(y0 - feather),
      width: px(x1 - x0),
      height: px(h),
      background: `linear-gradient(rgba(5,5,6,0) 0%, rgba(5,5,6,${alpha}) ${f.toFixed(2)}%, rgba(5,5,6,${alpha}) ${(100 - f).toFixed(2)}%, rgba(5,5,6,0) 100%)`,
    },
  });
}

/** A vertical gradient from `a0` black at y0 to `a1` at y1. */
export function grad(parent, y0, y1, a0, a1) {
  return el("div", {
    parent,
    style: { position: "absolute", left: "0px", top: px(y0), width: "1080px", height: px(y1 - y0), background: `linear-gradient(rgba(5,5,6,${a0}), rgba(5,5,6,${a1}))` },
  });
}

/** A full-frame solid background. */
export function solid(parent, color) {
  return el("div", { parent, style: { position: "absolute", inset: "0", background: color } });
}

export { clamp };

// The 17-core ring (S13, and its collapse into the Create canvas in S14) ------------------------

/** Ring order clockwise from 12 o'clock: the ten prebuilt cores in lighting order, then Create's seven. */
export const CORES = {
  prebuilt: [
    ["lagrange3", "green"],
    ["lagrange5", "green"],
    ["cubic", "blue"],
    ["thiran", "blue"],
    ["bbd", "red"],
    ["tape", "red"],
    ["phase_warp", "purple"],
    ["orbit", "purple"],
    ["linear", "black"],
    ["ensemble", "black"],
  ],
  create: ["flange", "barber_pole", "multi_rate", "granular", "formant", "stochastic", "phase_vocoder"],
};
export const RING = { cx: 540, cy: 920, r: 358, icon: 104 }; // 820 px across the glyphs

/**
 * The ring of 17 core glyphs (v4 cores art, /art/rc/core_icons). render({ lit: [0..1 x 10],
 * flare: 0..1 (the seven Create glyphs to white), collapse: 0..1 (into the centre), scale }).
 * Unlit glyphs and the Create glyphs sit at 25 % white; a lit glyph is full white over a halo in
 * its engine hue.
 */
export function coreRing(parent) {
  const root = el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: `${RING.cx}px ${RING.cy}px` } });
  const all = [...CORES.prebuilt.map(([n, e]) => ({ name: n, engine: e })), ...CORES.create.map((n) => ({ name: n, engine: null }))];
  const N = all.length;
  const S = RING.icon;
  const icons = all.map((c, i) => {
    const a = (2 * Math.PI * i) / N;
    const x = RING.cx + RING.r * Math.sin(a);
    const y = RING.cy - RING.r * Math.cos(a);
    const box = el("div", { parent: root, style: { position: "absolute", left: px(x - S / 2), top: px(y - S / 2), width: px(S), height: px(S) } });
    const hue = c.engine ? COLOR.fill[c.engine] : "#ffffff";
    const halo = el("div", {
      parent: box,
      style: { position: "absolute", left: px(-S * 0.35), top: px(-S * 0.35), width: px(S * 1.7), height: px(S * 1.7), borderRadius: "50%", background: `radial-gradient(closest-side, ${hue}88 0%, ${hue}33 55%, ${hue}00 100%)`, opacity: "0" },
    });
    const img = el("img", { parent: box, attrs: { src: `/art/rc/core_icons/${c.name}.png`, alt: "", draggable: "false" }, style: { position: "absolute", left: "0px", top: "0px", width: px(S), height: px(S), opacity: "0.25" } });
    return { ...c, x, y, box, halo, img };
  });
  return {
    root,
    icons,
    render({ lit = [], flare = 0, collapse = 0, scale = 1, alpha = 1 } = {}) {
      setStyle(root, "transform", scale === 1 ? "" : `scale(${+scale.toFixed(5)})`);
      setStyle(root, "opacity", alpha >= 1 ? "" : String(+alpha.toFixed(4)));
      icons.forEach((ic, i) => {
        const l = ic.engine ? clamp(lit[i] || 0) : clamp(flare);
        setStyle(ic.img, "opacity", String(+(0.25 + 0.75 * l).toFixed(4)));
        setStyle(ic.halo, "opacity", String(+l.toFixed(4)));
        setStyle(ic.img, "filter", !ic.engine && l > 0 ? `brightness(${+(1 + 0.6 * l).toFixed(3)}) drop-shadow(0 0 ${+(14 * l).toFixed(2)}px #ffffff)` : "");
        if (collapse > 0) {
          const k = 1 - collapse;
          const dx = (RING.cx - ic.x) * collapse;
          const dy = (RING.cy - ic.y) * collapse;
          setStyle(ic.box, "transform", `translate(${px(dx)}, ${px(dy)}) scale(${+Math.max(0.05, k).toFixed(4)})`);
        } else setStyle(ic.box, "transform", "");
      });
    },
  };
}
