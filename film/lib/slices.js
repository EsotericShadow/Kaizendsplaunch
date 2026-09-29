// SLICES (v5): a plate clipped to a horizontal band around its knob row (S08's five strips, the
// TikTok totem). Uses plate.height and the plate geometry, never a hard-coded body height.
//
//   const s = createSlice(layer, "green", { x: 36, y: 560, w: 1008, h: 200, scale: 0.72 });
//   s.plate.setState(...); s.plate.setGrade(...); s.place({ y: 600 }); s.show(true);
//
// The band is centred on the knob row (editor y 128 to 255, the four big knobs) unless centreY
// (body plate px) is given. The plate is centred horizontally in the band.

import { el, setStyle, px } from "./util.js";
import { createPlate, plateGeometry, K, HEADER_PX } from "./plate.js";

const HEADER_EDITOR = 56;

/** Body plate y of the knob-row centre for an engine (the average of the four knob centres). */
export function knobRowCentre(engine) {
  const G = plateGeometry(engine);
  const ys = ["rate", "depth", "offset", "width"].map((k) => G[k][1] + G[k][3] / 2);
  return ((ys.reduce((a, b) => a + b, 0) / ys.length) - HEADER_EDITOR) * K;
}

export class Slice {
  constructor(parent, engine, { x = 0, y = 0, w = 1080, h = 220, scale = 0.77, centreY = null, header = false, hiRes = false, state = null, plateX = null } = {}) {
    this.engine = engine;
    this.el = el("div", { parent, cls: `v5-slice v5-slice-${engine}`, style: { position: "absolute", overflow: "hidden" } });
    this.plate = createPlate(engine, { parent: this.el, scale, header, hiRes, state });
    this.headerH = header ? HEADER_PX : 0;
    this.centreY = centreY ?? knobRowCentre(engine);
    this.scale = scale;
    this.plateX = plateX;
    this.box = { x, y, w, h };
    this.place({});
  }

  /** Move or resize the band ({ x, y, w, h }), or change the plate scale / offset inside it. */
  place({ x, y, w, h, scale, dx = 0, dy = 0 } = {}) {
    const B = this.box;
    if (x != null) B.x = x;
    if (y != null) B.y = y;
    if (w != null) B.w = w;
    if (h != null) B.h = h;
    if (scale != null) this.scale = scale;
    setStyle(this.el, "left", px(B.x));
    setStyle(this.el, "top", px(B.y));
    setStyle(this.el, "width", px(B.w));
    setStyle(this.el, "height", px(B.h));
    const s = this.scale;
    const px0 = this.plateX ?? (B.w - this.plate.width * s) / 2;
    const py0 = B.h / 2 - (this.headerH + this.centreY) * s;
    this.plate.place({ x: px0 + dx, y: py0 + dy, scale: s });
    return this;
  }

  show(on) {
    setStyle(this.el, "visibility", on ? "" : "hidden");
  }
}

export function createSlice(parent, engine, opts) {
  return new Slice(parent, engine, opts);
}
