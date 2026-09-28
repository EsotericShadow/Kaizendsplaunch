// Shot 8, 20.00-24.00: Blue. Smears in at 20.00 and out at 24.00. Offset 0 -> 90 deg at 22.00-22.50.
import { TOUR, buildTourShot } from "./part1-common.js";

const spec = TOUR[1];

export default {
  id: "shot08-blue",
  t0: spec.t0,
  t1: spec.t1,
  build(ctx) {
    return buildTourShot(ctx, spec);
  },
};
