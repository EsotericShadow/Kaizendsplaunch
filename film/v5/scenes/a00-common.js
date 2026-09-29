// Helpers shared by the Unit A scenes (a01-a12) and the TikTok (tiktok/t*.js). Not a scene: not in
// the manifest.

import { el, svg, setStyle, px, clamp } from "/film/lib/util.js";
import { headline, placeText, setBaseline } from "/film/lib/type.js";
import { COLOR } from "/film/lib/portrait.js";
import { ease } from "/film/lib/util.js";
import "/film/lib/motion.js"; // registers power3.out etc. in util's EASES

/** The five engine hues in burst order, with their sideways spray (px). */
export const BURST = [
  ["green", -40],
  ["blue", 40],
  ["red", -22],
  ["purple", 22],
  ["black", 8],
];

/**
 * The hook headline: one dry Fraunces 600 line per entry, placed by baseline at x 72, and (burst)
 * five copies per line in the engine hues behind it. render(t, { dx, dy, burstHit, beats, scale })
 * moves the block and plays the burst: copies at full spray on the hit frame, snapping back into
 * the dry word over 10 frames (power3.out) while they fade.
 */
export function hookHeadline(parent, lib, { lines, size, baselines, x = 72, burst = false, color = COLOR.fg } = {}) {
  const root = el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: `${x}px ${baselines[0]}px` } });
  const copies = [];
  if (burst) {
    for (const [eng, dxOff] of BURST) {
      for (let i = 0; i < lines.length; i++) {
        const h = headline({ text: lines[i], size, parent: root, x, baseline: baselines[i], color: COLOR.hue[eng] });
        setStyle(h.el, "mixBlendMode", "screen");
        setStyle(h.el, "visibility", "hidden");
        copies.push({ node: h.el, dx: dxOff });
      }
    }
  }
  const dry = lines.map((text, i) => headline({ text, size, parent: root, x, baseline: baselines[i], color }).el);
  return {
    root,
    dry,
    render(t, { dx = 0, dy = 0, burstHit = null, beats = null, scale = 1 } = {}) {
      setStyle(root, "transform", `translate(${px(dx)}, ${px(dy)})${scale !== 1 ? ` scale(${+scale.toFixed(5)})` : ""}`);
      if (!copies.length) return;
      const df = burstHit && beats ? beats.frameAt(t) - burstHit.frame : -1;
      const live = df >= 0 && df < 10;
      const k = live ? 1 - ease("power3.out", df / 10) : 0;
      for (const c of copies) {
        setStyle(c.node, "visibility", live ? "" : "hidden");
        if (!live) continue;
        setStyle(c.node, "transform", `translateX(${px(c.dx * k)})`);
        setStyle(c.node, "opacity", String(+(0.9 * clamp(k * 1.4)).toFixed(4)));
      }
    },
  };
}

/** A plain SVG ring: render({ cx, cy, d, alpha }). */
export function ringSvg(parent, { color = COLOR.lavender, width = 3 } = {}) {
  const s = svg("svg", { width: 10, height: 10 });
  Object.assign(s.style, { position: "absolute", left: "0px", top: "0px", overflow: "visible", pointerEvents: "none" });
  parent.appendChild(s);
  const c = svg("circle", { fill: "none", stroke: color, "stroke-width": width }, s);
  return {
    render({ cx, cy, d, alpha = 1 }) {
      if (!(alpha > 0)) {
        setStyle(s, "visibility", "hidden");
        return;
      }
      setStyle(s, "visibility", "");
      setStyle(s, "left", px(cx));
      setStyle(s, "top", px(cy));
      c.setAttribute("r", (d / 2).toFixed(3));
      setStyle(c, "opacity", String(+alpha.toFixed(4)));
    },
  };
}

/** The L-MACRO scrim: black at `top` opacity at y 0, fading to 0 at y `to`. */
export function scrim(parent, { top = 0.72, to = 720 } = {}) {
  return el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: px(to), background: `linear-gradient(rgba(5,5,6,${top}), rgba(5,5,6,0))` } });
}

/** Draw only the scope's graticule (the empty scope before the band enters). */
export function drawGraticule(scope, alpha = 1) {
  const ctx = scope.ctx;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, scope.canvas.width, scope.canvas.height);
  scope._drawGraticule(alpha);
}

// ---------------------------------------------------------------------------------------------
// Unit A helpers for S04-S12 and the TikTok (tiktok/t*.js import this file too).

/** Apply a motion.stamp() result to a node (hidden before the hit). */
export function applyStamp(node, st) {
  setStyle(node, "visibility", st.on ? "" : "hidden");
  if (!st.on) return;
  setStyle(node, "opacity", st.opacity >= 1 ? "" : String(+st.opacity.toFixed(4)));
  setStyle(node, "transform", st.scale === 1 ? "" : `scale(${+st.scale.toFixed(5)})`);
}

/** Show a node from the frame of hit h on (hard cut), hidden before; `until` (a hit or time) hides it again. */
export function cutIn(node, beats, t, h, until = null) {
  const on = beats.after(t, typeof h === "number" ? h : h.t) && (until == null || !beats.after(t, typeof until === "number" ? until : until.t));
  setStyle(node, "visibility", on ? "" : "hidden");
  return on;
}

/** The side-copy tint of a smear in an engine hue (sepia base about 38 deg, rotated to the hue). */
export const HUE_TINT = {
  green: "sepia(1) saturate(4) hue-rotate(100deg)",
  blue: "sepia(1) saturate(4.5) hue-rotate(171deg)",
  red: "sepia(1) saturate(5) hue-rotate(-34deg)",
  purple: "sepia(1) saturate(4) hue-rotate(226deg)",
  black: "grayscale(1) brightness(1.3)",
  white: "grayscale(1) brightness(1.4)",
};

/**
 * A plate with two side copies for the chorus SMEAR (TREATMENT 5.4): three plates in one group,
 * sides under the centre. place()/focus()/setState()/setGrade()/require() go to all three.
 * render(u, role): role "in" / "out" (engine change, smear.js numbers), "burst" (the centre stays
 * at full opacity with half the blur: a hit on a plate that stays), or null (crisp centre only).
 * tint: the side copies take the engine hue.
 */
export class PlateSmear {
  constructor(parent, lib, engine, { tint = true, ...plateOpts } = {}) {
    this.lib = lib;
    this.engine = engine;
    this.tint = tint ? HUE_TINT[engine] || "" : "";
    this.root = el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px" } });
    this.wraps = [0, 1, 2].map(() => el("div", { parent: this.root, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px" } }));
    this.plates = this.wraps.map((w) => lib.createPlate(engine, { parent: w, ...plateOpts }));
  }
  get centre() {
    return this.plates[2];
  }
  require(states) {
    for (const p of this.plates) p.require(states);
    return this;
  }
  setState(s) {
    if (s) for (const p of this.plates) p.setState(s);
    return this;
  }
  setGrade(g) {
    for (const p of this.plates) p.setGrade(g);
    return this;
  }
  place(o) {
    for (const p of this.plates) p.place(o);
    return this;
  }
  focus(o) {
    for (const p of this.plates) p.focus(o);
    return this;
  }
  show(on) {
    setStyle(this.root, "visibility", on ? "" : "hidden");
  }
  render(u, role = null) {
    const [l, r, c] = this.wraps;
    const k = role && u > 0 && u < 1 ? Math.sin(Math.PI * u) : 0;
    const off = 48 * k;
    const blur = 6 * k;
    let centreA = 1;
    let centreBlur = blur;
    if (role === "out") centreA = 1 - clamp((u - 0.3) / 0.3);
    else if (role === "in") centreA = clamp((u - 0.4) / 0.3);
    else centreBlur = blur * 0.5;
    if (!role) centreA = 1;
    setStyle(c, "visibility", centreA > 0 ? "" : "hidden");
    setStyle(c, "opacity", centreA >= 1 ? "" : String(+centreA.toFixed(4)));
    setStyle(c, "filter", centreBlur > 0.001 ? `blur(${+centreBlur.toFixed(3)}px)` : "");
    const side = 0.35 * k;
    [[l, -1], [r, 1]].forEach(([w, dir]) => {
      const on = side > 0.0005;
      setStyle(w, "visibility", on ? "" : "hidden");
      if (!on) return;
      setStyle(w, "opacity", String(+side.toFixed(4)));
      setStyle(w, "filter", `blur(${+blur.toFixed(3)}px) ${this.tint}`.trim());
      setStyle(w, "transform", `translateX(${px(dir * off)})`);
    });
  }
}

/** A clipping box (overflow hidden) placed in frame px: for macros in a zone and the strips. */
export function clipBox(parent, { x = 0, y = 0, w = 1080, h = 1920 } = {}) {
  const n = el("div", { parent, style: { position: "absolute", overflow: "hidden", left: px(x), top: px(y), width: px(w), height: px(h) } });
  return {
    el: n,
    place({ x: X = x, y: Y = y, w: Wd = w, h: Ht = h }) {
      setStyle(n, "left", px(X));
      setStyle(n, "top", px(Y));
      setStyle(n, "width", px(Wd));
      setStyle(n, "height", px(Ht));
    },
  };
}

/**
 * The "BEST FOR" line (TREATMENT 2, ACT III): mono 26 px "BEST FOR" then Inter 36 px text, first
 * baseline `baseline`. `lines` is the text already broken by the line-fit rule (a line that would
 * pass x 928 breaks at the last space that fits; 36 px is already under the body minimum).
 * Continuation lines hang under the text, 44 px apart. Returns the nodes.
 */
export function bestFor(parent, lines, { x = 72, baseline = 490, lead = 44, labelColor = "rgba(246,244,239,0.6)", color = COLOR.fg } = {}) {
  const label = el("div", { parent, text: "BEST FOR", style: { font: `600 26px "JetBrains Mono", monospace`, letterSpacing: "0.12em", color: labelColor } });
  placeTextAt(label, x, baseline);
  const textX = x + 172;
  const nodes = [label];
  lines.forEach((ln, i) => {
    const n = el("div", { parent, text: ln, style: { font: `500 36px "Inter", sans-serif`, color } });
    placeTextAt(n, textX, baseline + i * lead);
    nodes.push(n);
  });
  return nodes;
}

function placeTextAt(node, x, baseline) {
  placeText(node, { x, baseline });
}

/** Mono label (captions, tags) in px, placed by baseline. */
export function monoLine(parent, text, { x = 72, baseline, size = 26, color = "rgba(246,244,239,0.6)", tracking = 0.12, weight = 600, align = "left" } = {}) {
  const n = el("div", { parent, text, style: { font: `${weight} ${size}px "JetBrains Mono", monospace`, letterSpacing: `${tracking}em`, color } });
  placeText(n, { x, baseline, align });
  return n;
}

/** Inter body line placed by baseline. */
export function bodyLine(parent, text, { x = 72, baseline, size = 44, weight = 500, color = COLOR.muted, align = "left" } = {}) {
  const n = el("div", { parent, text, style: { font: `${weight} ${size}px "Inter", sans-serif`, color } });
  placeText(n, { x, baseline, align });
  return n;
}

/**
 * Line-fit rule (TREATMENT 2), run in setup() once the fonts are in: lower the size of each node
 * that passes x `right` in 2 px steps, never below `min`; warn (console.warn, surfaced by the
 * renderer) if it still does not fit. Nodes: [{ node, min }].
 */
export function fitNodes(items, { right = 928, label = "" } = {}) {
  const stage = document.getElementById("stage");
  const s0 = stage.getBoundingClientRect();
  for (const { node, min } of items) {
    let size = parseFloat(getComputedStyle(node).fontSize);
    const right0 = () => node.getBoundingClientRect().right - s0.left;
    let guard = 0;
    while (right0() > right + 0.5 && size - 2 >= min && guard++ < 40) {
      size -= 2;
      node.style.fontSize = `${size}px`;
      if (node.__place) setBaseline(node, node.__place.baseline);
    }
    if (right0() > right + 0.5) console.warn(`[v5 ${label}] line-fit: "${node.textContent.slice(0, 40)}" still ends at x ${right0().toFixed(1)} at ${size}px`);
  }
}

/**
 * Static safe-zone check in setup (QC gate 3 before any transform): warn about every text node in
 * `layers` whose box leaves the text-safe rectangle x 60-940, y 220-1540 (data-bleed skipped).
 */
export function checkSafe(layers, label = "") {
  const stage = document.getElementById("stage");
  const s0 = stage.getBoundingClientRect();
  for (const L of layers) {
    const w = document.createTreeWalker(L, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.textContent.trim()) continue;
      const p = n.parentElement;
      if (!p || p.closest("[data-bleed]")) continue;
      const r = document.createRange();
      r.selectNodeContents(n);
      const b = r.getBoundingClientRect();
      if (!b.width) continue;
      const x0 = b.left - s0.left;
      const y0 = b.top - s0.top;
      if (x0 < 60 - 0.5 || x0 + b.width > 940 + 0.5 || y0 < 220 - 0.5 || y0 + b.height > 1540 + 0.5) {
        console.warn(`[v5 ${label}] text outside the safe rectangle: "${n.textContent.trim().slice(0, 30)}" x ${x0.toFixed(0)}-${(x0 + b.width).toFixed(0)} y ${y0.toFixed(0)}-${(y0 + b.height).toFixed(0)}`);
      }
    }
  }
}

/** Body plate px of the centre of an engine's COLOR slider track (for a macro across the slider). */
export function sliderCentre(lib, engine) {
  const G = lib.plate.plateGeometry(engine);
  const K = lib.plate.K;
  const [x, y, w, h] = G.color;
  return [(x + w / 2) * K, (y + h / 2 - 56) * K];
}

/** Hide/show several layers. */
export function showAll(layers, on) {
  for (const l of layers) setStyle(l, "visibility", on ? "" : "hidden");
}
