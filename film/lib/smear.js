// Chorus smear (treatment G4): the engine-change transition, 0.5 s centred on the bar line.
// For u in 0..1 the outgoing and the incoming group each show a centre copy and two side copies
// offset +-48 px sin(pi u), blurred 6 px sin(pi u), side opacity 0.35 sin(pi u). The outgoing
// centre fades out over u 0.3..0.6, the incoming centre fades in over u 0.4..0.7.
// Only the plate and the engine-specific type smear; persistent elements stay crisp.
//
//   const out = new SmearGroup(layer, () => createPlate("green", {...}));
//   out.setState(state)            // forwarded to all three copies
//   out.render(u, "out")           // or "in"; u = smearU(t, 20.0)
//   out.hold()                     // plain, un-smeared centre copy only

import { el, setStyle, px, clamp } from "./util.js";

export const SMEAR_LEN = 0.5;

/** u for a smear centred on the bar line at tBar; <0 before, >1 after. */
export const smearU = (t, tBar, len = SMEAR_LEN) => (t - (tBar - len / 2)) / len;

/** Numbers of G4 at u: { offset, blur, side, outCentre, inCentre }. */
export function smearParams(u) {
  const k = u <= 0 || u >= 1 ? 0 : Math.sin(Math.PI * u);
  return {
    offset: 48 * k,
    blur: 6 * k,
    side: 0.35 * k,
    outCentre: 1 - clamp((u - 0.3) / 0.3),
    inCentre: clamp((u - 0.4) / 0.3),
  };
}

export class SmearGroup {
  /**
   * parent: the layer. factory(copyParent, index) builds one copy (a plate, a text block...) and
   * returns an object with .el, and optionally .setState(s) / .render(t, s). Index 0 is the centre.
   */
  constructor(parent, factory) {
    this.root = el("div", { parent, cls: "smear-group", style: { position: "absolute", left: "0px", top: "0px", width: "100%", height: "100%" } });
    this.copies = [0, 1, 2].map((i) => {
      const wrap = el("div", { parent: this.root, style: { position: "absolute", left: "0px", top: "0px", width: "100%", height: "100%" } });
      const item = factory(wrap, i);
      return { wrap, item };
    });
    // Sides under the centre.
    this.root.appendChild(this.copies[0].wrap);
  }

  get centre() {
    return this.copies[0].item;
  }

  /** Call fn(item, index) on every copy (e.g. setState, place). */
  each(fn) {
    this.copies.forEach((c, i) => fn(c.item, i));
  }

  setState(s) {
    this.each((it) => it.setState && it.setState(s));
  }

  /** No smear: centre copy crisp at full opacity, sides hidden. */
  hold(opacity = 1) {
    const [c, l, r] = this.copies;
    setStyle(c.wrap, "opacity", opacity >= 1 ? "" : String(opacity));
    setStyle(c.wrap, "filter", "");
    setStyle(c.wrap, "transform", "");
    setStyle(c.wrap, "visibility", opacity > 0 ? "" : "hidden");
    for (const s of [l, r]) setStyle(s.wrap, "visibility", "hidden");
  }

  /** role "out" or "in". */
  render(u, role) {
    const p = smearParams(u);
    const centreA = role === "out" ? p.outCentre : p.inCentre;
    const [c, l, r] = this.copies;
    const blur = p.blur > 0.001 ? `blur(${+p.blur.toFixed(3)}px)` : "";
    setStyle(c.wrap, "visibility", centreA > 0 ? "" : "hidden");
    setStyle(c.wrap, "opacity", String(+centreA.toFixed(4)));
    setStyle(c.wrap, "filter", blur);
    setStyle(c.wrap, "transform", "");
    [[l, -1], [r, 1]].forEach(([s, dir]) => {
      const on = p.side > 0.0005;
      setStyle(s.wrap, "visibility", on ? "" : "hidden");
      setStyle(s.wrap, "opacity", String(+p.side.toFixed(4)));
      setStyle(s.wrap, "filter", blur);
      setStyle(s.wrap, "transform", `translateX(${px(dir * p.offset)})`);
    });
  }
}
