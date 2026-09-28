// Shots 1-3, 0.00-7.85: the bottom-left scope group (scope hairline from the first frame, STEREO
// FIELD label and DRY | CHOROBOROS pill from 0.25) and the LEVEL MATCHED footnote from the MIX turn.
// It overlays the hero and the MIX macro and cuts to black with them at 7.85.
import { OPEN, MIX_TURN } from "./part1-common.js";

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
    const scope = lib.createScope(layer, { cx: OPEN.scope.cx, cy: OPEN.scope.cy, size: OPEN.scope.size });
    const label = type.mono("STEREO FIELD", { parent: layer, size: 13, x: OPEN.label.x, baseline: OPEN.label.baseline, align: "center" });
    const pill = type.pill(["DRY", "CHOROBOROS"], { parent: layer, x: OPEN.pill.x, y: OPEN.pill.y, w: OPEN.pill.w, h: OPEN.pill.h });
    pill.el.style.background = "rgba(5,5,6,0.6)";
    const footText = cues.footnote("opening");
    const foot = footText ? type.mono(footText, { parent: layer, size: 14, x: OPEN.footnote.x, baseline: OPEN.footnote.baseline, align: "right" }) : null;

    return {
      render(t) {
        const on = t >= 0 && t < T1;
        util.show(layer, on);
        if (!on) return;
        const wet = t >= MIX_TURN;
        util.show(label, t >= LABEL_T);
        util.show(pill.el, t >= LABEL_T);
        pill.setActive(wet ? 1 : 0, wet ? type.HUE.green : type.C.fg);
        if (foot) util.show(foot, wet);
        scope.draw(t, { stem: cues.featuredStemAt(t) || "gtr", color: type.C.fg, render: "R01" });
      },
    };
  },
};
