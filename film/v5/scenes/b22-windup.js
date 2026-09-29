// S22 Wind-up, refrain 3 (TREATMENT section 2, ACT VII). Bar 52, 83.107 to 84.725 (frames 4986-5082).
//
// f4986 (the bar-52 line, 83.107): a hard CUT from the family cards to the whole Green plate, still
// dry (bypass to 83.310: s 0.12). f4998 (crash + kick 83.310): Choroboros is back on (M13): the chip
// becomes ●, the colour floods, and six hard CUTs to Green macros accelerate into the stop (montage.js):
// RATE "0.62 Hz" (f4998), DEPTH "22%" (83.513), OFFSET "90°" (83.715), WIDTH "100%" (84.120),
// COLOR "35%" (84.324), MIX "40%" (84.526, with the lavender ring on). Each pushes 1.00 -> 1.05 over
// half a beat (faster than S02/S19) with a PUNCH (macro) on the kicks. FLASH Green (0.30) on f4998,
// 83.715 and 84.120 (three in this second: the PSE limit). The INHALE: on 84.324 and 84.526 the
// whole frame compresses to 0.97, then 0.95 (4 frames each, power2.out); S23 releases it on the stop.

import { hitAt, barT, inF, ev, flashBank, grad } from "./b00-common.js";

const AT = [540, 1100]; // the macro bleeds off the bottom; a scrim keeps the chip readable

export default {
  id: "b22-windup",
  t0: 4986 / 60,
  t1: 5083 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show, setStyle } = lib.util;
    const { COLOR } = P;
    const line = barT(b, 52);
    const stop = hitAt(b, 84.7251);
    const F0 = b.onsetFrame(line);
    const F1 = stop.frame;
    const shots = [
      ["rate", 83.3097, 2.0],
      ["depth", 83.5132, 2.0],
      ["offset", 83.715, 2.0],
      ["width", 84.1204, 2.0],
      ["color", 84.3242, 2.0],
      ["mix", 84.5259, 3.0],
    ].map(([on, x, zoom]) => ({ on, h: hitAt(b, x), zoom, at: AT, pushTo: 1.05, pushBeats: 0.5 }));
    const flashHits = [shots[0].h, shots[2].h, shots[3].h];
    const pre = [shots[4].h, shots[5].h];
    ev(this, b, line, "cut", "bar line 83.107 (the Green plate, dry)");
    shots.forEach((s) => ev(this, b, s.h, "cut", `${s.h.piece} ${s.h.tm} (${s.on.toUpperCase()} macro)`));
    flashHits.forEach((h) => ev(this, b, h, "flash", `${h.piece} ${h.tm} (FLASH Green)`));

    const L = ctx.layer("plate", 12);
    const inner = lib.util.el("div", { parent: L, style: { position: "absolute", inset: "0", transformOrigin: "540px 960px" } });
    const whole = lib.createPlate("green", { parent: inner, scale: 0.74, header: true, hiRes: false });
    whole.require(demos.statesIn(83.32, 83.4, "M13", 4)); // M13's values, shown dry until it starts
    const montage = lib.createMontage(inner, "green", shots, { push: [1.0, 1.05], punchAmp: M.MOTION.punch.macro, state: demos.plateState(83.4) });
    montage.plate.require(demos.statesIn(shots[0].h.t + 0.001, stop.t - 0.001, null, 8));
    const ring = lib.createRing(inner, { color: COLOR.lavender, width: 3, factor: 1.12 });
    grad(L, 0, 340, 0.85, 0);

    const flashes = flashBank(ctx, lib, flashHits.map((h) => ({ h, color: COLOR.fill.green, peak: 0.3 })));

    return {
      render(t) {
        const on = inF(b, t, F0, F1);
        show(L, on);
        flashes.render(t, on);
        if (!on) return;
        const f = b.frameAt(t);
        const k = montage.index(t);
        whole.el.style.visibility = k < 0 ? "" : "hidden";
        montage.plate.el.style.visibility = k >= 0 ? "" : "hidden";
        if (k < 0) {
          whole.place({ cx: 540, cy: 1000, scale: 0.74 });
          whole.setState(demos.plateState(t, "M13"));
          whole.setGrade(demos.grade("green", t));
        } else {
          montage.render(t, demos.plateState(t));
          montage.plate.setGrade(demos.grade("green", t));
        }
        const mixShot = shots[5];
        ring.render(t, { t0: mixShot.h.tf, t1: stop.tf, tIn: mixShot.h.tf, tOut: stop.tf, rect: k === 5 ? montage.plate.controlScreenRect("mix") : null });
        const s = M.inhale(t, pre, stop);
        setStyle(inner, "transform", s === 1 ? "" : `scale(${+s.toFixed(5)})`);
      },
    };
  },
};
