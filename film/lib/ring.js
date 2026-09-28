// Gesture highlight (treatment G6): a 1 px #d0bdff ring, diameter = control x 1.12. It draws on
// clockwise from 12 o'clock over the 0.10 s before the move and leaves 0.30 s after the move
// (a short fade ending at that moment).
//
//   const ring = createRing(layer);
//   ring.render(t, { t0: 18.0, t1: 18.5, rect: plate.controlScreenRect("depth") });
//   ring.renderGesture(t, cues.gesture("R02", "depth"), plate.controlScreenRect("depth"));

import { svg, setStyle, px, clamp } from "./util.js";

export const RING_IN = 0.1;
export const RING_OUT = 0.3;
const FADE = 0.12;

export class Ring {
  constructor(parent, { color = "#d0bdff", width = 1, factor = 1.12 } = {}) {
    this.factor = factor;
    this.svg = svg("svg", { width: 10, height: 10 });
    Object.assign(this.svg.style, { position: "absolute", left: "0px", top: "0px", overflow: "visible", pointerEvents: "none" });
    parent.appendChild(this.svg);
    this.circle = svg("circle", { fill: "none", stroke: color, "stroke-width": width, "stroke-linecap": "butt" }, this.svg);
  }

  /** t0/t1: the move. rect: { cx, cy, size } in the parent's px. tIn/tOut override the defaults. */
  render(t, { t0, t1, rect, tIn = t0 - RING_IN, tOut = t1 + RING_OUT }) {
    if (!rect || t < tIn || t >= tOut) {
      setStyle(this.svg, "visibility", "hidden");
      return;
    }
    const r = (rect.size * this.factor) / 2;
    const C = 2 * Math.PI * r;
    const draw = clamp((t - tIn) / Math.max(1e-6, t0 - tIn));
    const alpha = clamp((tOut - t) / FADE);
    setStyle(this.svg, "visibility", "");
    setStyle(this.svg, "left", px(rect.cx));
    setStyle(this.svg, "top", px(rect.cy));
    this.circle.setAttribute("r", r.toFixed(3));
    // Start at 12 o'clock, run clockwise.
    this.circle.setAttribute("transform", "rotate(-90)");
    this.circle.setAttribute("stroke-dasharray", `${(C * draw).toFixed(3)} ${(C + 1).toFixed(3)}`);
    setStyle(this.circle, "opacity", String(+alpha.toFixed(4)));
  }

  /** Convenience for a cue gesture ({ t0, t1 } from cues.json). */
  renderGesture(t, gesture, rect) {
    if (!gesture) return this.render(t, { t0: -1, t1: -1, rect: null });
    this.render(t, { t0: gesture.t0, t1: gesture.t1, rect });
  }
}

export function createRing(parent, opts) {
  return new Ring(parent, opts);
}
