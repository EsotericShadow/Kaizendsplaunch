// S10 Red (TREATMENT section 2, ACT III). Bars 17-18, 26.351 to 29.594 (frames 1581 to 1774).
//
// Bar line 26.351: the SMEAR from Blue (0.5 s centred on the bar line). Stillness: only data moves.
// M03: Red, HQ BBD -> Tape at 27.972 (bar 18.1). The lever throws on its own 18-frame sheet (the
// plugin's smootherstep, 420 ms) and the lit plate blends in by (1 - frame / 17) (plate.js via
// demos.plateState). Zone S cuts to a 2.0x macro on the lever from f1678 to 29.189 (bar 18.4); the
// ring comes in 0.1 s before the throw. The chorustype on "Wavers." changes law from STEP (BBD) to
// WOW (Tape) on the throw, and the eyebrow "BBD CORE" becomes "TAPE CORE" on f1678.
// Copy: "BBD CORE" / "Red. Wavers." / "BEST FOR  BBD AND TAPE. VINTAGE INSTABILITY." (broken at the
// last space that fits: 36 px is already under the body minimum) / caption "HQ · BBD → TAPE".
// The plate smears OUT for 0.25 s past 29.594 into S11.

import { tourScene } from "./a00-common.js";

const THROW = 27.9723; // demos.json M03 hq_switch (master = comp in the main film)

export default tourScene({
  id: "a10-red",
  f0: 1581,
  f1: 1775,
  engine: "red",
  demoId: "M03",
  barA: 17,
  smearIn: true,
  smearOut: true,
  macroOn: "hq",
  ring: "hq",
  macroZoom: 2.0,
  eyebrows: [
    ["BBD CORE", null],
    ["TAPE CORE", THROW],
  ],
  word: "Red. ",
  accent: "Wavers.",
  law: (t, { b }) => (b.after(t, THROW) ? "WOW" : "STEP"),
  best: ["BBD AND TAPE. VINTAGE", "INSTABILITY."],
  caption: "HQ · BBD → TAPE",
});
