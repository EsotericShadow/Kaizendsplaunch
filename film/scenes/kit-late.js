// Helpers shared by the scenes of shots 12-25 (36.00-86.00). Not a scene: the manifest does not
// list it. Windows are compared in whole video frames, so a cut at 49.85 lands on frame 2991
// whatever the float rounding of t.

import { util, type } from "/film/lib/index.js";

const { clamp, setStyle, el, px } = util;

export const FPS = 60;
export const frame = (t) => Math.round(t * FPS);

/** True when t is inside [t0, t1) counted in video frames. */
export const inFrames = (t, t0, t1) => {
  const f = frame(t);
  return f >= frame(t0) && f < frame(t1);
};

/** A time snapped to the nearest video frame (pops on 16ths). */
export const snap = (t) => frame(t) / FPS;

/** 0..1 fade-in that starts at tIn (0 before), over dur seconds. dur 0 is a hard cut. */
export function fadeIn(t, tIn, dur = 0.25) {
  if (frame(t) < frame(tIn)) return 0;
  if (dur <= 0) return 1;
  return clamp((t - tIn) / dur);
}

/** Opacity and visibility together; 0 hides the node. */
export function setAlpha(node, a) {
  setStyle(node, "opacity", a >= 1 ? "" : String(+clamp(a).toFixed(4)));
  setStyle(node, "visibility", a > 0 ? "" : "hidden");
}

/** A node's box in stage px (valid after fonts load, e.g. in setup()). */
export function stageBox(node, stage) {
  const s = stage.getBoundingClientRect();
  const r = node.getBoundingClientRect();
  return { x: r.left - s.left, y: r.top - s.top, w: r.width, h: r.height, right: r.right - s.left, bottom: r.bottom - s.top };
}

/** Full-frame radial glow div (brand .glow-purple recipe by default). */
export function radialGlow(parent, { cx, cy, w, h = w, stops = null, color = [184, 140, 255], a = [0.28, 0.06], blend = "" } = {}) {
  const [r, g, b] = color;
  const bg =
    stops ||
    `radial-gradient(closest-side, rgba(${r},${g},${b},${a[0]}) 0%, rgba(${r},${g},${b},${a[1]}) 55%, rgba(${r},${g},${b},0) 100%)`;
  const n = el("div", {
    parent,
    style: { position: "absolute", left: px(cx - w / 2), top: px(cy - h / 2), width: px(w), height: px(h), background: bg, pointerEvents: "none" },
  });
  if (blend) n.style.mixBlendMode = blend;
  return n;
}

/** Scene grain: the site tile at 5% overlay (G0), in its own layer. */
export function sceneGrain(ctx, lib, { z = 90, opacity = 0.05 } = {}) {
  const L = ctx.layer("grain", z);
  const grain = lib.createGrain(L, { opacity });
  return { layer: L, grain };
}

/** Rounded-rectangle path for clipping inside a canvas draw (no CSS mask around a canvas). */
export function roundRectPath(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.lineTo(x + w - r, y);
  c.arcTo(x + w, y, x + w, y + r, r);
  c.lineTo(x + w, y + h - r);
  c.arcTo(x + w, y + h, x + w - r, y + h, r);
  c.lineTo(x + r, y + h);
  c.arcTo(x, y + h, x, y + h - r, r);
  c.lineTo(x, y + r);
  c.arcTo(x, y, x + r, y, r);
  c.closePath();
}

/** Mono label in an engine hue (the lineup / offer-card plate labels). */
export function plateLabel(text, { parent, hue, x, baseline }) {
  return type.mono(text, { parent, size: 18, weight: 600, color: hue, tracking: 0.3, x, baseline, align: "center" });
}

/**
 * Centre y of a G3b hairline for an accent span: 4 px under the accent's lowest ink (descenders
 * included), plus the strand amplitude, so the moving strand never touches the letters.
 */
export function hairlineY(accent, baseline, { amp = 3, gap = 4 } = {}) {
  const cs = getComputedStyle(accent);
  const c = document.createElement("canvas").getContext("2d");
  c.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  const m = c.measureText(accent.textContent);
  return baseline + Math.max(0, m.actualBoundingBoxDescent) + gap + amp + 0.75;
}
