// Shots 7-11, 16.00-36.00: what persists across the tour and never smears (G4): the BEST FOR
// label, the footnote, the dot row with the current engine ringed, and the scope in the right
// column. The ring and the scope hue switch on the bar line.
import { TOUR, TOUR_T0, TOUR_T1, TOUR_LAYOUT, BEST_FOR, tourAt } from "./part1-common.js";

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

    const D = L.dots;
    const step = (D.x1 - D.x0 - D.size) / (TOUR.length - 1);
    const dotX = TOUR.map((s, i) => D.x0 + D.size / 2 + i * step);
    TOUR.forEach((s, i) => {
      el("div", {
        parent: layer,
        style: { position: "absolute", left: px(dotX[i] - D.size / 2), top: px(D.cy - D.size / 2), width: px(D.size), height: px(D.size), borderRadius: "50%", background: type.HUE[s.engine] },
      });
    });
    const RING = 26;
    const ring = el("div", {
      parent: layer,
      style: { position: "absolute", top: px(D.cy - RING / 2), width: px(RING), height: px(RING), borderRadius: "50%", border: "1.5px solid transparent" },
    });

    const scope = lib.createScope(layer, { cx: L.scope.cx, cy: L.scope.cy, size: L.scope.size });

    return {
      render(t) {
        const on = t >= TOUR_T0 && t < TOUR_T1;
        util.show(layer, on);
        if (!on) return;
        const s = tourAt(t);
        const i = TOUR.indexOf(s);
        const hue = type.HUE[s.engine];
        util.setStyle(ring, "left", px(dotX[i] - RING / 2));
        util.setStyle(ring, "borderColor", hue);
        scope.draw(t, { stem: cues.featuredStemAt(t) || "gtr", color: hue, render: s.render });
      },
    };
  },
};
