// Shot 7, 16.00-20.00: Green. Hard cut in, smear out at 20.00. Depth 20% -> 35% at 18.00-18.50.
import { TOUR, buildTourShot } from "./part1-common.js";

const spec = TOUR[0];

export default {
  id: "shot07-green",
  t0: spec.t0,
  t1: spec.t1,
  build(ctx) {
    return buildTourShot(ctx, spec, { smearIn: false, smearOut: true });
  },
};
