// Shot 3, 3.00-7.85: the full tagline over the moving hero. "Great sound" static; the accent
// "doesn’t sit still." lands at 3.00 by hard cut and moves by ChorusType SINE at the heard Green
// settings (R01: 0.60 Hz, Depth 20%, Offset 90°, Width 130%, Mix 45%).
import { makeTagline } from "./part1-common.js";

const T0 = 3;
const T1 = 7.85;

export default {
  id: "shot03-tagline",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util } = lib;
    const layer = ctx.layer("type", 30);
    const line = makeTagline(lib, layer);
    const ct = lib.createChorusType(line.accent, { law: "SINE", engine: "green" });
    return {
      render(t) {
        const on = t >= T0 && t < T1;
        util.show(layer, on);
        if (!on) return;
        ct.render(t, cues.settingsAt("R01", t));
      },
    };
  },
};
