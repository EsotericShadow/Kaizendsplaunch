// Shots 1-3, 0.00-7.85: the bottom-left scope group (scope hairline from the first frame, STEREO
// FIELD label and DRY | CHOROBOROS pill from 0.25) and the LEVEL MATCHED footnote from the MIX turn.
// It overlays the hero and the MIX macro and cuts to black with them at 7.85. The footnote sits
// bottom-centre (the shot 2 plate fills the frame and its MIX readout owns the bottom-right), and
// the overlay type carries a soft dark shadow so it reads over the plate art.
import { OPEN, MIX_TURN, scopeBackdrop } from "./part1-common.js";

const T1 = 7.85;
const LABEL_T = 0.25;

export default {
  id: "shot01-03-scope-group",
  t0: 0,
  t1: T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util, type } = lib;
    const layer = ctx.layer("scope-group", 40);
    scopeBackdrop(lib, layer, OPEN.scope);
    const scope = lib.createScope(layer, { cx: OPEN.scope.cx, cy: OPEN.scope.cy, size: OPEN.scope.size, disc: null });
    const SHADOW = "0 1px 3px rgba(5,5,6,0.9), 0 0 12px rgba(5,5,6,0.7)";
    const label = type.mono("STEREO FIELD", { parent: layer, size: OPEN.textSize, x: OPEN.label.x, baseline: OPEN.label.baseline, align: "center" });
    label.style.textShadow = SHADOW;
    // One pill per state, swapped by visibility, so the flip repaints the whole pill (a lit segment
    // repainted on its own cut its rect across the rounded border, which then rasterised
    // differently from a full repaint).
    const pills = [
      [0, type.C.fg],
      [1, type.HUE.green],
    ].map(([i, fill]) => {
      const p = type.pill(["BYPASS", "CHOROBOROS"], { parent: layer, x: OPEN.pill.x, y: OPEN.pill.y, w: OPEN.pill.w, h: OPEN.pill.h, size: OPEN.pill.size, active: i, fill });
      p.el.style.background = "rgba(5,5,6,0.72)";
      return p.el;
    });
    const footText = cues.footnote("opening");
    const foot = footText ? type.mono(footText, { parent: layer, size: OPEN.textSize, color: "rgba(246,244,239,0.6)", x: OPEN.footnote.x, baseline: OPEN.footnote.baseline, align: "center" }) : null;
    if (foot) foot.style.textShadow = SHADOW;

    return {
      render(t) {
        const on = t >= 0 && t < T1;
        util.show(layer, on);
        if (!on) return;
        const wet = t >= MIX_TURN;
        util.show(label, t >= LABEL_T);
        util.show(pills[0], t >= LABEL_T && !wet);
        util.show(pills[1], t >= LABEL_T && wet);
        if (foot) util.show(foot, wet);
        scope.draw(t, { stem: cues.featuredStemAt(t) || "gtr", color: type.C.fg, render: "R01" });
      },
    };
  },
};
