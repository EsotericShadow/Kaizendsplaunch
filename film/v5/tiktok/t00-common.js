// Helpers shared by the TikTok scenes (t01-t07). Not a scene: not in the manifest.
//
// Composition time tau = master - 123.648 (ctx.beats carries the offset). Hits are named by their
// MASTER time: hit(b, "snare", 124.865).

import { el, setStyle, px, clamp } from "/film/lib/util.js";
import { placeText } from "/film/lib/type.js";
import { COLOR } from "/film/lib/portrait.js";
export { applyStamp, PlateSmear, checkSafe, scrim, knobAnchor, sliderCentre, monoLine, bodyLine, ringSvg } from "../scenes/a00-common.js";

/** The hit of `piece` nearest master time tm. */
export const hit = (b, piece, tm) => {
  const h = b.hitNear(piece, b.comp(tm));
  if (!h) throw new Error(`tiktok: no ${piece} near ${tm}`);
  return h;
};

/**
 * The earliest attack of the drum cluster at master time tm (+-15 ms, any piece): the treatment
 * keys an event to the earliest attack in its cluster (a hat 3 ms before its kick sets the frame).
 */
export const cl = (b, tm, tol = 0.015) => {
  const hs = b.hitsIn("all", b.comp(tm) - tol, b.comp(tm) + tol);
  if (!hs.length) throw new Error(`tiktok: no hit near ${tm}`);
  return hs.reduce((a, h) => (h.t < a.t ? h : a));
};

/**
 * The type band at the bottom of a full-bleed macro: black from 0 at y 1120 to 93 % at 1210 and flat
 * below, so the caption (1300), the rolled readout and the tag (1470) sit on solid black, never on
 * the plate's own engravings and readouts. Add it to the type layer before the text.
 */
export function bottomScrim(parent) {
  return el("div", { parent, style: { position: "absolute", left: "0px", top: "1120px", width: "1080px", height: "800px", background: "linear-gradient(rgba(5,5,6,0), rgba(5,5,6,0.93) 90px, rgba(5,5,6,0.93))" } });
}

/** The big engine tag (mono 56 px, engine glow hue, x 72, baseline 1470) with a dark halo. */
export function bigTag(parent, text, color, { baseline = 1470, size = 56 } = {}) {
  const n = el("div", { parent, text, style: { font: `600 ${size}px "JetBrains Mono", monospace`, letterSpacing: "0.08em", color, textShadow: "0 0 18px rgba(5,5,6,0.95), 0 0 4px rgba(5,5,6,0.95)" } });
  placeText(n, { x: 72, baseline });
  return n;
}

/** The move caption (Fraunces italic 400, 110 px, engine hue, x 72, baseline 1300). */
export function moveCaption(parent, text, color, { baseline = 1300, size = 110 } = {}) {
  const n = el("div", { parent, text, style: { font: `italic 400 ${size}px "Fraunces", serif`, letterSpacing: "-0.02em", color, textShadow: "0 0 24px rgba(5,5,6,0.9)", transformOrigin: "0% 80%" } });
  placeText(n, { x: 72, baseline });
  return n;
}

/**
 * The value "rolled large": the plugin readout's text (with its 60 ms digit flip, from
 * demos.readoutIn) in JetBrains Mono 600 at 2.5x a macro readout, in the product's readout colour
 * with its glow. render(r) takes { text, from, progress }.
 */
export function bigReadout(parent, color, { x = 560, baseline = 1300, size = 104 } = {}) {
  const n = el("div", { parent, style: { font: `600 ${size}px "JetBrains Mono", monospace`, color, textShadow: `0 0 18px ${color}88, 0 0 40px rgba(5,5,6,0.9)`, transformOrigin: "0% 80%" } });
  placeText(n, { x, baseline });
  const cur = el("span", { parent: n, style: { display: "inline-block", transformOrigin: "50% 60%" } });
  return {
    el: n,
    render(r) {
      if (!r) return;
      // The flip: the old text squashes out over the first half, the new one in over the second.
      const p = r.progress ?? 1;
      const txt = p < 0.5 ? r.from : r.text;
      const k = p < 0.5 ? 1 - p * 2 * 0.2 : 0.8 + (p - 0.5) * 2 * 0.2;
      if (cur.textContent !== txt) cur.textContent = txt;
      setStyle(cur, "transform", p >= 1 ? "" : `scaleY(${+k.toFixed(4)})`);
      setStyle(cur, "opacity", p >= 1 ? "" : String(+(0.55 + 0.45 * Math.abs(p - 0.5) * 2).toFixed(4)));
    },
  };
}

/** A full-frame div (for grouping and whole-group transforms). */
export function frameDiv(parent, style = {}) {
  return el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", ...style } });
}

/**
 * WHIP on two groups (motion.whip): the outgoing slides `dist` px along dir (power2.in) and the
 * incoming arrives from -dir (power2.out), cut on the hit frame, with a motion blur that peaks
 * mid-whip (a CSS blur on DOM groups; canvases are never blurred). Returns true when the incoming
 * group is the one on screen.
 */
export function renderWhip(M, t, h, outG, inG, { dir = [1, 0] } = {}) {
  const w = M.whip(t, h, { dir });
  const blur = w.active ? 10 * Math.sin(Math.PI * w.u) : 0;
  const f = blur > 0.05 ? `blur(${+blur.toFixed(2)}px)` : "";
  if (outG) {
    setStyle(outG, "visibility", w.cut ? "hidden" : "");
    setStyle(outG, "transform", w.active && !w.cut ? `translate(${px(w.outX)}, ${px(w.outY)})` : "");
    setStyle(outG, "filter", w.cut ? "" : f);
  }
  if (inG) {
    setStyle(inG, "visibility", w.cut ? "" : "hidden");
    setStyle(inG, "transform", w.active && w.cut ? `translate(${px(w.inX)}, ${px(w.inY)})` : "");
    setStyle(inG, "filter", w.cut ? f : "");
  }
  return w.cut;
}

/** Smear u of a 0.25 s burst centred on tc (full-band sections), or null outside it. */
export const smearAt = (t, tc, len = 0.25) => {
  const u = (t - (tc - len / 2)) / len;
  return u > 0 && u < 1 ? u : null;
};

export { COLOR, el, setStyle, px, clamp };
