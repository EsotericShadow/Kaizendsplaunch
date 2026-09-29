// The persistent "now hearing" chip (v5): x 72, baseline 256, JetBrains Mono 600, 26 px, 70 %
// white; the dot in the heard engine's hue. Its text comes from demos.chipText(t) at every frame:
//   "● GUITAR · CHOROBOROS GREEN · LAGRANGE 3RD", "○ GUITAR · BYPASS", and in S01-S02 the
//   " · MIX n%" form. boot.js adds it as a kit layer (z 900) when the manifest asks for it.

import { el, setStyle, setText } from "./util.js";
import { placeText, FONT } from "./type.js";
import { COLOR } from "./portrait.js";

export class Chip {
  constructor(parent, demos, { x = 72, baseline = 256, size = 26, color = "rgba(246,244,239,0.7)", tracking = 0.12 } = {}) {
    this.demos = demos;
    this.el = el("div", { parent, cls: "v5-chip", style: { font: `600 ${size}px ${FONT.mono}`, letterSpacing: `${tracking}em`, color } });
    this.dot = el("span", { parent: this.el });
    this.text = el("span", { parent: this.el });
    placeText(this.el, { x, baseline });
  }

  render(t, { visible = true, alpha = 1 } = {}) {
    setStyle(this.el, "visibility", visible ? "" : "hidden");
    if (!visible) return;
    setStyle(this.el, "opacity", alpha === 1 ? "" : String(+alpha.toFixed(4)));
    const s = this.demos.chipText(t);
    const dot = s.slice(0, 1);
    setText(this.dot, dot);
    setText(this.text, s.slice(1));
    const st = this.demos.demoAt(t);
    const on = dot === "●" && st;
    setStyle(this.dot, "color", on ? COLOR.hue[st.engine] : "");
  }
}

export function createChip(parent, demos, opts) {
  return new Chip(parent, demos, opts);
}
