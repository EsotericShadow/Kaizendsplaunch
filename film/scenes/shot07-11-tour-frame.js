// Shots 7-11, 16.00-36.00: what persists across the tour and never smears (G4): the BEST FOR
// label, the footnote, the dot row with the current engine ringed, and the scope in the right
// column. The ring and the scope hue switch on the bar line.
import { TOUR, TOUR_T0, TOUR_T1, TOUR_LAYOUT, BEST_FOR, tourAt, scopeBackdrop } from "./part1-common.js";

export default {
  id: "shot07-11-tour-frame",
  t0: TOUR_T0,
  t1: TOUR_T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util, type } = lib;
    const { el, px } = util;
    const L = TOUR_LAYOUT;
    const layer = ctx.layer("frame", 40);

    type.mono(BEST_FOR.text, { parent: layer, size: BEST_FOR.size, tracking: BEST_FOR.tracking, x: L.headline.x, baseline: L.best.baseline });
    type.mono(cues.footnote("tour"), { parent: layer, size: 14, x: L.footnote.x, baseline: L.footnote.baseline });

    // The dot row sits in its own compositing layer: the smearing type's repaint rect reaches the
    // last dot, and a CSS circle cut by a repaint rect rasterises differently from frame to frame.
    const D = L.dots;
    const RING = 26;
    const row = el("div", { parent: layer, style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "200px", willChange: "transform" } });
    const step = (D.x1 - D.x0 - D.size) / (TOUR.length - 1);
    const dotX = TOUR.map((s, i) => D.x0 + D.size / 2 + i * step);
    TOUR.forEach((s, i) => {
      el("div", {
        parent: row,
        style: { position: "absolute", left: px(dotX[i] - D.size / 2), top: px(D.cy - D.size / 2), width: px(D.size), height: px(D.size), borderRadius: "50%", background: type.HUE[s.engine] },
      });
    });
    // One fixed SVG ring per dot, shown by visibility (a CSS ring moved between dots was not
    // reproducible to the pixel).
    const rings = TOUR.map((s, i) => {
      const g = util.svg("svg", { width: RING, height: RING, viewBox: `0 0 ${RING} ${RING}` }, row);
      Object.assign(g.style, { position: "absolute", left: px(dotX[i] - RING / 2), top: px(D.cy - RING / 2), visibility: "hidden" });
      util.svg("circle", { cx: RING / 2, cy: RING / 2, r: RING / 2 - 0.75, fill: "none", stroke: type.HUE[s.engine], "stroke-width": 1.5 }, g);
      return g;
    });

    const S = L.scope;
    scopeBackdrop(lib, layer, S);
    const scope = lib.createScope(layer, { cx: S.cx, cy: S.cy, size: S.size, disc: null, frame: false });

    return {
      render(t) {
        const on = t >= TOUR_T0 && t < TOUR_T1;
        util.show(layer, on);
        if (!on) return;
        const s = tourAt(t);
        const hue = type.HUE[s.engine];
        rings.forEach((r, i) => util.show(r, TOUR[i] === s));
        scope.draw(t, { stem: cues.featuredStemAt(t) || "gtr", color: hue, render: s.render });
      },
    };
  },
};
