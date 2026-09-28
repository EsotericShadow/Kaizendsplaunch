// Shot 10, 28.00-32.00: Purple (Orbit). Rate 0.12 -> 1.5 Hz at 30.00-30.50; Offset never moves.
import { TOUR, buildTourShot } from "./part1-common.js";

const spec = TOUR[3];

export default {
  id: "shot10-purple",
  t0: spec.t0,
  t1: spec.t1,
  build(ctx) {
    return buildTourShot(ctx, spec);
  },
};
