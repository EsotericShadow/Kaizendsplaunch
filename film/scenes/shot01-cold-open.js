// Shot 1, 0.00-2.00: HEADPHONES ON from frame 0; "Great sound" from 0.25 by hard cut, placed where
// it sits in the full centred tagline, so the right half of the line is empty. No motion (G1).
import { makeTagline } from "./part1-common.js";

export default {
  id: "shot01-cold-open",
  t0: 0,
  t1: 2,
  build(ctx) {
    const { lib } = ctx;
    const { util, type } = lib;
    const layer = ctx.layer("type", 30);
    type.eyebrow("HEADPHONES ON", { parent: layer, x: 960, baseline: 84, align: "center" });
    const line = makeTagline(lib, layer);
    line.accent.style.visibility = "hidden";
    return {
      render(t) {
        const on = t >= 0 && t < 2;
        util.show(layer, on);
        if (!on) return;
        util.show(line.el, t >= 0.25);
      },
    };
  },
};
