// S12 Black (TREATMENT section 2, ACT III). Bars 21-22, 32.837 to 36.080 (frames 1970 to 2163).
//
// Bar line 32.837: the SMEAR from Purple. Stillness: only data moves.
// M05: Black Linear Ensemble, Depth 15 % -> 30 %, 34.459 to 35.270 (bar 22, beats 1 to 3). Zone S
// cuts to a macro on DEPTH (1.6x: Black has no 2x plate art) from f2067 to 35.675 (bar 22.4).
// From 35.675 the whole frame pulls back 3 % (sine.in, about the frame centre) into the drums; the
// scope is moved and zoomed in its draw call (never scaled by a transform). The drums re-enter on
// 36.081: Unit B's S13 owns frame 2164 (a hard CUT), so this scene ends on frame 2163.
// Copy: "ENSEMBLE CORE" / "Black. Multiplies." / "BEST FOR  Dense ensembles. Low CPU." / caption
// "DEPTH 15% → 30%".

import { tourScene } from "./a00-common.js";

export default tourScene({
  id: "a12-black",
  f0: 1970,
  f1: 2164,
  engine: "black",
  demoId: "M05",
  barA: 21,
  endHit: ["kick", 36.081],
  smearIn: true,
  smearOut: false,
  pullBack: true,
  macroOn: "depth",
  ring: "depth",
  macroZoom: 1.6,
  withReadout: true,
  eyebrows: [["ENSEMBLE CORE", null]],
  word: "Black. ",
  accent: "Multiplies.",
  law: "SINE",
  best: ["Dense ensembles. Low CPU."],
  caption: "DEPTH 15% → 30%",
});
