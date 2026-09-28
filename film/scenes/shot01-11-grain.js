// Grain for shots 1-11 (G0): the site's grain tile at 5% in overlay blend over the whole frame.
// Frozen at one offset until the MIX turn (G1), animated after; off during the black stop.
// The blend sits on the layer itself so it composites against the picture below.
import { MIX_TURN } from "./part1-common.js";

const T0 = 0;
const T1 = 36;
const STOP = [7.85, 8.0];

export default {
  id: "shot01-11-grain",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { lib } = ctx;
    const { util } = lib;
    const layer = ctx.layer("grain", 90);
    Object.assign(layer.style, { mixBlendMode: "overlay", opacity: "0.05" });
    const grain = lib.createGrain(layer, { opacity: 1, blend: "normal" });
    return {
      render(t) {
        const on = t >= T0 && t < T1 && !(t >= STOP[0] && t < STOP[1]);
        util.show(layer, on);
        if (!on) return;
        grain.render(t, { frozen: t < MIX_TURN });
      },
    };
  },
};
