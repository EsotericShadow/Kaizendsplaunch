// S11 Purple (TREATMENT section 2, ACT III). Bars 19-20, 29.594 to 32.837 (frames 1775 to 1969).
//
// Bar line 29.594: the SMEAR from Red. Stillness: only data moves.
// M04: Purple Orbit, Color 10 % -> 45 %, 31.216 to 32.026 (bar 20, beats 1 to 3). Zone S cuts to a
// 2.0x macro across the COLOR slider (it crosses the portrait width) from f1872 to 32.432
// (bar 20.4): the thumb glides and the scope's figure flattens (real data). The ring rides the thumb.
// Copy: "ORBIT CORE" / "Purple. Orbits." (chorustype ORBIT) / "BEST FOR  STRANGE TEXTURES, SOUND
// DESIGN, WEIRDNESS" (two lines, broken at the last space that fits) / caption "COLOR 10% → 45%".
// The plate smears OUT for 0.25 s past 32.837 into S12.

import { tourScene } from "./a00-common.js";

export default tourScene({
  id: "a11-purple",
  f0: 1775,
  f1: 1970,
  engine: "purple",
  demoId: "M04",
  barA: 19,
  smearIn: true,
  smearOut: true,
  macroOn: "slider",
  ring: "color",
  macroZoom: 2.0,
  eyebrows: [["ORBIT CORE", null]],
  word: "Purple. ",
  accent: "Orbits.",
  law: "ORBIT",
  best: ["STRANGE TEXTURES, SOUND", "DESIGN, WEIRDNESS"],
  caption: "COLOR 10% → 45%",
});
