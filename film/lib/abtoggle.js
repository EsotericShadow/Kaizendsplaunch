// A/B TOGGLE (v5, TREATMENT S18): a film graphic, not plugin UI. A segmented pill (default 856 x 96
// at x 72, y 560) reading "BYPASS │ CHOROBOROS" in JetBrains Mono 600, 40 px. The active segment
// is a sliding thumb: filled in the hue (#79b8ff) with #0b1420 text when CHOROBOROS is on, a
// #a8a7a0 outline when BYPASS is on. The thumb slides over 3 frames (power3.out) from the slam's
// hit frame. Plain DOM (no canvas), so the layer may be shaken or scaled.
//
//   const ab = createABToggle(layer, { x: 72, y: 560, w: 856, h: 96, hue: "#79b8ff" });
//   ab.render(t, { on: !demos.bypassAt(t), slamHit, pulse, glow });
//     on:      the state now (true = CHOROBOROS);
//     slamHit: the hit (or time) of the latest switch, for the 3-frame slide (null: no slide);
//     pulse:   0..1, the snare border pulse (border alpha 0.34 -> 0.94 at 1, plus a white halo);
//     glow:    0..1, the fill's stepped glow (SWEEP): the pill glows in the hue, and while BYPASS
//              is on the CHOROBOROS label brightens toward it.
// Everything is a function of its arguments: nothing is carried from the previous frame.
// (Styles set `font` before `lineHeight`: the shorthand resets line-height.)

import { el, setStyle, px, clamp, lerp, ease, rgba } from "./util.js";
import { getBeats } from "./beats.js";
import { FONT } from "./type.js";
import "./motion.js"; // registers power3.out

export class ABToggle {
  constructor(parent, { x = 72, y = 560, w = 856, h = 96, hue = "#79b8ff", ink = "#0b1420", bypassColor = "#a8a7a0", size = 40, labels = ["BYPASS", "CHOROBOROS"], split = 0.4, beats = null } = {}) {
    this.beats = beats;
    this.box = { x, y, w, h };
    this.hue = hue;
    this.ink = ink;
    this.bypassColor = bypassColor;
    this.split = split; // BYPASS segment share of the width
    this.root = el("div", {
      parent,
      cls: "v5-abtoggle",
      style: { position: "absolute", left: px(x), top: px(y), width: px(w), height: px(h), boxSizing: "border-box", borderRadius: px(h / 2), border: "2px solid rgba(246,244,239,0.34)", background: "rgba(12,13,16,0.82)" },
    });
    this.thumb = el("div", { parent: this.root, style: { position: "absolute", top: "6px", height: px(h - 16), boxSizing: "border-box", borderRadius: px((h - 16) / 2) } });
    const segW = [w * split, w * (1 - split)];
    const mk = (text, left, width) =>
      el("div", {
        parent: this.root,
        text,
        style: { font: `600 ${size}px ${FONT.mono}`, position: "absolute", left: px(left), top: "0px", width: px(width), height: px(h - 4), lineHeight: px(h - 4), textAlign: "center", letterSpacing: "0.1em", paddingLeft: "0.1em", boxSizing: "border-box", whiteSpace: "pre" },
      });
    this.labels = [mk(labels[0], 0, segW[0] - 2), mk(labels[1], segW[0] - 2, segW[1])];
    // The divider "│" sits on the segment boundary, under the thumb.
    this.divider = el("div", { parent: this.root, text: "│", style: { font: `400 ${size}px ${FONT.mono}`, position: "absolute", left: px(segW[0] - 2 - size * 0.3), top: "0px", width: px(size * 0.6), height: px(h - 4), lineHeight: px(h - 4), textAlign: "center", color: "rgba(246,244,239,0.3)" } });
    this.root.insertBefore(this.divider, this.thumb);
    this.segW = segW;
  }

  _thumbRect(on) {
    const { w } = this.box;
    const [a] = this.segW;
    return on ? { left: a + 4, width: w - a - 14 } : { left: 6, width: a - 14 };
  }

  get rect() {
    return { ...this.box };
  }

  render(t, { on = true, slamHit = null, pulse = 0, glow = 0 } = {}) {
    const b = this.beats || getBeats();
    let u = 1;
    if (slamHit != null) {
      const hf = typeof slamHit === "number" ? b.onsetFrame(slamHit) : slamHit.frame;
      const df = b.frameAt(t) - hf;
      if (df >= 0 && df < 3) u = ease("power3.out", (df + 1) / 3);
    }
    const from = this._thumbRect(!on);
    const to = this._thumbRect(on);
    setStyle(this.thumb, "left", px(lerp(from.left, to.left, u)));
    setStyle(this.thumb, "width", px(lerp(from.width, to.width, u)));
    const g = clamp(glow);
    if (on) {
      setStyle(this.thumb, "background", this.hue);
      setStyle(this.thumb, "border", "none");
      setStyle(this.thumb, "boxShadow", g > 0 ? `0 0 ${px(12 + 36 * g)} ${this.hue}${Math.round(0x40 + 0x80 * g).toString(16)}` : `0 0 12px ${this.hue}40`);
    } else {
      setStyle(this.thumb, "background", "transparent");
      setStyle(this.thumb, "border", `3px solid ${this.bypassColor}`);
      setStyle(this.thumb, "boxShadow", "none");
    }
    // Labels: the active one in ink on the fill (ON) or in the outline grey (BYPASS).
    const settled = u >= 1;
    setStyle(this.labels[1], "color", on ? (settled ? this.ink : "rgba(246,244,239,0.6)") : "rgba(246,244,239,0.5)");
    setStyle(this.labels[0], "color", !on ? this.bypassColor : "rgba(246,244,239,0.5)");
    // Snare pulse: the border's alpha +0.6 (0.34 -> 0.94). The fill's glow steps light the whole
    // pill in the hue, in either state (the bar-40 fill runs while BYPASS is on).
    const p = clamp(pulse);
    setStyle(this.root, "borderColor", `rgba(246,244,239,${+(0.34 + 0.6 * p).toFixed(4)})`);
    // With no fill glow, the pulse also throws a soft white halo, so the backbeat reads on a phone.
    setStyle(this.root, "boxShadow", g > 0 ? `0 0 ${px(10 + 30 * g)} ${this.hue}${Math.round(0x30 + 0x90 * g).toString(16).padStart(2, "0")}` : p > 0 ? `0 0 ${px(28 * p)} rgba(246,244,239,${+(0.5 * p).toFixed(4)})` : "none");
    if (!on && g > 0) setStyle(this.labels[1], "color", rgba(this.hue, 0.5 + 0.5 * g));
  }
}

export function createABToggle(parent, opts) {
  return new ABToggle(parent, opts);
}
