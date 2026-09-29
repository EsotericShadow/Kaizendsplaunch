// Shot 6, 12.00-16.00: the five engines, static, each in the state it has at the start of its tour
// shot. Headline with a static italic accent, one label per beat from 12.00, footnote from 13.00,
// a faint purple glow behind the row.
// The row fills the frame's width: five plates with one even 20 px gap between them and at both
// frame edges, so each plate is 360 px wide (scale 0.2571, up from the treatment's 0.24). The
// headline (baseline 360) and the row (centre y 600) sit 30-40 px lower than the treatment's, so
// the group is optically centred in the frame above the footnote.
import { TOUR } from "./part1-common.js";

const T0 = 12;
const T1 = 16;
const GAP = 20;
const PLATE_W = (1920 - 6 * GAP) / 5;
const SCALE = PLATE_W / 1400;
const XS = [0, 1, 2, 3, 4].map((i) => GAP + PLATE_W / 2 + i * (PLATE_W + GAP));
const ROW_Y = 600;
const HEAD_BASELINE = 360;
const LABEL_BASELINE = 742;
const BEAT = 0.5;
const FOOT_T = 13;

export default {
  id: "shot06-lineup",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util, type } = lib;
    const glowL = ctx.layer("glow", 5);
    util.el("div", {
      parent: glowL,
      style: {
        position: "absolute",
        left: "0px",
        top: "0px",
        width: "1920px",
        height: "1080px",
        background: "radial-gradient(ellipse 1250px 340px at 960px 600px, rgba(184,140,255,0.16), rgba(184,140,255,0.04) 55%, rgba(184,140,255,0) 100%)",
      },
    });
    const plateL = ctx.layer("plates", 10);
    TOUR.forEach((s, i) => {
      lib.createPlate(cues.plateStateAt(s.render, s.t0), { parent: plateL, scale: SCALE, cx: XS[i], cy: ROW_Y });
    });
    const typeL = ctx.layer("type", 30);
    type.headline({ parent: typeL, text: "Five prebuilt ", accent: "engines.", size: 96, x: 960, baseline: HEAD_BASELINE, align: "center" });
    const labels = TOUR.map((s, i) =>
      type.mono(s.engine.toUpperCase(), { parent: typeL, size: 18, color: type.HUE[s.engine], x: XS[i], baseline: LABEL_BASELINE, align: "center", tracking: 0.3 }),
    );
    const foot = type.mono("EVERY ENGINE DEMO IS LEVEL MATCHED TO THE ORIGINAL MIX.", { parent: typeL, size: 18, color: type.C.muted, tracking: 0.1, x: 960, baseline: 1000, align: "center" });

    return {
      render(t) {
        const on = t >= T0 && t < T1;
        for (const L of [glowL, plateL, typeL]) util.show(L, on);
        if (!on) return;
        labels.forEach((n, i) => util.show(n, t >= T0 + i * BEAT));
        util.show(foot, t >= FOOT_T);
      },
    };
  },
};
