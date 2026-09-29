// S19 The settings, refrain 2 (TREATMENT section 2, ACT VI). Bars 43-44, 68.513 to 71.756
// (frames 4110-4304). Heard: M11 ON.
//
// f4110 (crash + kick 68.514): the ON slam. The A/B frame (toggle, scope, zone S plate) is drawn by
// b18-ab.js up to f4194; this module owns the type from f4110: eyebrow "CUBIC CORE" and
// "Blue. Widens." (104 px, baseline 420, "Widens." as chorustype SINE Blue), STAMPed on the slam.
// f4195 (crash + kick 69.931): CUT to the whole Blue plate at scale 0.74 with a FLASH (Blue 0.30);
// kicks PUNCH it.
// Bar 44: five hard CUTs to Blue macros, one per hit (montage.js): RATE "1.23 Hz" (70.337), DEPTH
// "12%" (70.540), OFFSET "120°" (70.938), COLOR "45%" (71.139), MIX "40%" (71.352). Each pushes
// 1.00 -> 1.03 with a PUNCH (macro). The knobs and the COLOR thumb are framed at 2.0x; the MIX knob,
// 51 editor px across, at 3.0x so it reads at phone size. This rhymes with S02.

import { hitAt, inF, ev, fitter, headLine, eyebrowLine, applyStamp, flashBank, grad } from "./b00-common.js";

const WHOLE = { scale: 0.74, cy: 1000 };
const AT = [540, 1150]; // low enough that the macro bleeds off the bottom of the frame

export default {
  id: "b19-settings",
  t0: 4110 / 60,
  t1: 4305 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show } = lib.util;
    const { COLOR } = P;
    const slam = hitAt(b, 68.5138);
    const cut = hitAt(b, 69.9313);
    const next = hitAt(b, 71.7572);
    const F0 = slam.frame;
    const FC = cut.frame;
    const F1 = next.frame;
    const shots = [
      ["rate", 70.3365, 2.0],
      ["depth", 70.5405, 2.0],
      ["offset", 70.9382, 2.0],
      ["color", 71.1394, 2.0],
      ["mix", 71.3519, 3.0],
    ].map(([on, x, zoom]) => ({ on, h: hitAt(b, x), zoom, at: AT }));
    const snares = b.hitsIn("snare", slam.t, cut.t - 0.01, { minDb: -20 });
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    ev(this, b, slam, "slam", "crash + kick 68.514 (ON slam; drawn by b18-ab.js)");
    ev(this, b, slam, "flash", "crash + kick 68.514 (FLASH Blue; drawn by b18-ab.js)");
    ev(this, b, slam, "stamp", "crash + kick 68.514 (CUBIC CORE / Blue. Widens.)");
    snares.forEach((h) => ev(this, b, h, "sweep", `snare ${h.tm} (toggle border pulse; drawn by b18-ab.js)`));
    ev(this, b, cut, "cut", "crash + kick 69.931 (the whole Blue plate)");
    ev(this, b, cut, "flash", "crash + kick 69.931 (FLASH Blue)");
    shots.forEach((s) => ev(this, b, s.h, "cut", `${s.h.piece} ${s.h.tm} (${s.on.toUpperCase()} macro)`));

    const PL = ctx.layer("plate", 12);
    const whole = lib.createPlate("blue", { parent: PL, scale: WHOLE.scale, header: true, hiRes: false });
    whole.require(demos.statesIn(cut.t, next.t, "M11", 4));
    const ML = ctx.layer("macros", 13);
    const montage = lib.createMontage(ML, "blue", shots, { push: [1.0, 1.03], punchAmp: M.MOTION.punch.macro, state: demos.plateState(70.4, "M11") });
    montage.plate.require(demos.statesIn(shots[0].h.t, next.t, "M11", 4));
    // The macro rises out of black under the type.
    grad(ML, 0, 480, 1, 1);
    grad(ML, 480, 760, 1, 0);

    const flashes = flashBank(ctx, lib, [{ h: cut, color: COLOR.fill.blue, peak: 0.3 }]);

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const brow = eyebrowLine(TL, fit, "CUBIC CORE", { baseline: 300 });
    const head = headLine(TL, fit, { text: "Blue. ", accent: "Widens.", size: 104, baseline: 420 });
    const ct = lib.createChorusType(head.accent, { law: "SINE", engine: "blue" });

    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        show(TL, on);
        flashes.render(t, on);
        const f = b.frameAt(t);
        const wholeOn = on && f >= FC && f < shots[0].h.frame;
        const macroOn = on && f >= shots[0].h.frame;
        show(PL, wholeOn);
        show(ML, macroOn);
        if (!on) return;
        if (wholeOn) {
          const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });
          whole.place({ cx: 540, cy: WHOLE.cy, scale: WHOLE.scale * pu });
          whole.setState(demos.plateState(t, "M11"));
          whole.setGrade(demos.grade("blue", t));
        }
        if (macroOn) {
          montage.render(t, demos.plateState(t, "M11"));
          montage.plate.setGrade(demos.grade("blue", t));
        }
        const ts = M.shake(t, [slam], { amp: M.MOTION.shake.type, salt: 5 });
        const st = M.stamp(t, slam);
        applyStamp(brow, st, { dx: ts.x, dy: ts.y });
        applyStamp(head.el, st, { dx: ts.x, dy: ts.y });
        const s = demos.settingsAt(t);
        if (s) ct.render(t, s);
      },
    };
  },
};
