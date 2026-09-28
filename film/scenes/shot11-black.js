// Shot 11, 32.00-36.00: Black (Ensemble). Color 20% -> 60% at 34.00-34.50, ring on the thumb.
// Hard cut out at 36.00.
import { TOUR, buildTourShot } from "./part1-common.js";

const spec = TOUR[4];

export default {
  id: "shot11-black",
  t0: spec.t0,
  t1: spec.t1,
  build(ctx) {
    return buildTourShot(ctx, spec, { smearIn: true, smearOut: false });
  },
};
