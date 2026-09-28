// Shot 22, 69.50-70.00: silence. #050506 and one 3 px #f6f4ef dot at (1390, 470): the line at rest,
// where the payoff scope opens. This module also owns the grain for the payoff and end card
// (69.50-86.00, a declared overlap into shots 23-25): frozen during the silence, running from 70.00.
// The end card's format row sits in a layer above it.

import { inFrames } from "./kit-late.js";

const T0 = 69.5;
const T1 = 70.0;
const END = 86.0;

export default {
  id: "shot22-silence",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib } = ctx;
    const { el, show } = lib.util;

    const dotL = ctx.layer("dot", 30);
    el("div", {
      parent: dotL,
      style: { position: "absolute", left: "1388.5px", top: "468.5px", width: "3px", height: "3px", borderRadius: "50%", background: "#f6f4ef" },
    });
    const grainL = ctx.layer("grain", 90);
    const grain = lib.createGrain(grainL, { opacity: 0.05 });

    return {
      render(t) {
        show(dotL, inFrames(t, T0, T1));
        const g = inFrames(t, T0, END);
        show(grainL, g);
        if (g) grain.render(t, { frozen: t < T1, frozenFrame: Math.round(T0 * 60) });
      },
    };
  },
};
