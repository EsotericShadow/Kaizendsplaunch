// S09 Blue (TREATMENT section 2, ACT III). Bars 15-16, 23.108 to 26.351 (frames 1386 to 1580).
//
// The stop: kick + crash 23.108 (f1386), the last hit before the silence. The five strips collapse
// into the Blue strip (a08 draws the other four), which opens into L-TOUR over 10 frames (expo.out).
// FLASH Blue (0.30), a SMEAR burst and a STAMP of the type block: the one flash of the act, because
// it is a real hit. Then stillness (from 24.0: only data moves).
// M02: Blue Cubic, Offset 0° -> 120°, 24.729 to 25.540 (bar 16, beats 1 to 3). Zone S cuts to a macro
// on OFFSET from f1483 to 25.945 (bar 16.4), at 1.75x (not 2.0x) so the knob AND its readout fit
// the 510 px zone: the viewer sees 0° become 120°; the ring comes in 0.1 s before the move and
// leaves 0.3 s after it. The scope's two sides pull apart (real data).
// Copy: "CUBIC CORE" / "Blue. Widens." / "BEST FOR  Clean width on vocals and buses" / caption
// "OFFSET 0° → 120°" (mono 32 px, #79b8ff, x 72, baseline 1000, in place of LEVEL MATCHED, which
// shows in bar 15 only if measured.json passes M02).
// The plate smears OUT for 0.25 s past 26.351 into S10 (the engine-change smear).

import { tourScene } from "./a00-common.js";
import { STRIP, stripY } from "./a08-five-voices.js";

export default tourScene({
  id: "a09-blue",
  f0: 1386,
  f1: 1581,
  engine: "blue",
  demoId: "M02",
  barA: 15,
  startHit: ["kick", 23.1083],
  openFrom: { x: STRIP.x, y: stripY(1), w: STRIP.w, h: STRIP.h, scale: STRIP.scale },
  smearIn: false,
  smearOut: true,
  macroOn: "offset",
  ring: "offset",
  macroZoom: 1.75,
  withReadout: true,
  eyebrows: [["CUBIC CORE", null]],
  word: "Blue. ",
  accent: "Widens.",
  law: "SINE",
  best: ["Clean width on vocals and buses"],
  caption: "OFFSET 0° → 120°",
});
