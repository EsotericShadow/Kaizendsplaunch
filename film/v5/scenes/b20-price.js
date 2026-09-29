// S20 Price (TREATMENT section 2, ACT VII). Bars 45-48, 71.756 to 78.243 (frames 4305-4693).
// Heard: M12 Green.
//
// f4305 (crash + kick 71.757): a SLAM to the 3D hero (portrait crop, full colour, 70 % brightness,
// y 560 to 1920; the canvas moves by top only, the zoom is inside its draw) with FLASH Green (0.30)
// and SHAKE 10 px. "$49.99" SLAMs down in; "USD." with it. The term lines STAMP one per crash push:
// 72.364, 73.176, 75.000, 75.608. Every crash has a FLASH Green (0.30); the flashes on 77.228 and
// 77.634 are edge glows (PSE). Bar 46 is a hold: nothing new; the snares PUNCH the price at 1.012.
// The hero creeps and steps +2 source frames per kick; 76.418 jumps +24; bar 48 cuts between hero
// angles (jumps in the sequence) on 76.823, 77.228 and 77.634. The snares 77.838 and 78.041 SWEEP
// the term stack up 60 px, twice.

import { hitAt, inF, ev, fitter, headLine, bodyLine, applyStamp, flashBank, grad } from "./b00-common.js";

const HERO_Y = 560;
const TERMS = [
  [72.3636, "One-time purchase.", 860],
  [73.1756, "No subscription.", 924],
  [74.9999, "Lifetime updates.", 988],
  [75.6081, "30-day money-back guarantee.", 1052],
];

export default {
  id: "b20-price",
  t0: 4305 / 60,
  t1: 4694 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, motion: M, portrait: P } = ctx;
    const { show, el, setStyle, px } = lib.util;
    const { COLOR } = P;
    const cut = hitAt(b, 71.7572);
    const next = hitAt(b, 78.2437);
    const F0 = cut.frame;
    const F1 = next.frame;
    const terms = TERMS.map(([x, text, y]) => ({ h: hitAt(b, x), text, y }));
    const jump = hitAt(b, 76.418);
    const angles = [76.8232, 77.2285, 77.6339].map((x) => hitAt(b, x));
    const crashes = [cut, ...terms.map((x) => x.h), jump, ...angles];
    const sweeps = [77.8377, 78.0407].map((x) => hitAt(b, x));
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    const snares = b.hitsIn("snare", cut.t, next.t - 0.01, { minDb: -20 });
    ev(this, b, cut, "slam", "crash + kick 71.757 (the hero, $49.99)");
    ev(this, b, cut, "flash", "crash + kick 71.757 (FLASH Green)");
    terms.forEach((x) => ev(this, b, x.h, "stamp", `crash + kick ${x.h.tm} (${x.text})`));
    terms.forEach((x) => ev(this, b, x.h, "flash", `crash + kick ${x.h.tm} (FLASH Green)`));
    ev(this, b, jump, "sweep", "crash + kick 76.418 (hero scrub +24)");
    ev(this, b, jump, "flash", "crash + kick 76.418 (FLASH Green)");
    angles.forEach((h, i) => ev(this, b, h, "cut", `crash + kick ${h.tm} (hero angle ${i + 2})`));
    ev(this, b, angles[0], "flash", "crash + kick 76.823 (FLASH Green)");
    sweeps.forEach((h) => ev(this, b, h, "sweep", `snare ${h.tm} (term stack up 60 px)`));

    const L = ctx.layer("hero", 10);
    const hero = lib.createHero(L, { x: 0, y: HERO_Y, width: 1080, height: 1920 - HERO_Y });
    // Scrims so the type reads over the hero: black above y 560 fading in, and a left-hand band
    // behind the terms (gradients, never masks, over a canvas).
    const SL = ctx.layer("scrim", 11);
    grad(SL, HERO_Y - 4, HERO_Y + 300, 1, 0);
    el("div", { parent: SL, style: { position: "absolute", left: "0px", top: "800px", width: "1080px", height: "300px", background: "linear-gradient(90deg, rgba(5,5,6,0.78) 0%, rgba(5,5,6,0.62) 60%, rgba(5,5,6,0) 92%)" } });

    const flashes = flashBank(ctx, lib, crashes.map((h, i) => ({ h, color: COLOR.fill.green, peak: 0.3, edge: i >= crashes.length - 2 })));

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const price = headLine(TL, null, { text: "$49.99", size: 190, baseline: 520 });
    const usd = headLine(TL, null, { text: "", accent: "USD.", size: 190, baseline: 720 });
    const termNodes = terms.map((x) => {
      const n = bodyLine(TL, fit, x.text, { size: 48, baseline: x.y, weight: 600, min: 40 });
      return n;
    });

    const frameOfSrc = (t) => {
      // The scrub: 20 at the cut, +2 per kick, a slow creep, +24 on 76.418, then three angle jumps.
      const f = b.frameAt(t);
      if (f >= angles[2].frame) return 42 + 1.5 * (t - angles[2].t);
      if (f >= angles[1].frame) return 8 + 1.5 * (t - angles[1].t);
      if (f >= angles[0].frame) return 82 + 1.5 * (t - angles[0].t);
      const steps = M.sweep(t, kicks, { frames: 5 });
      return 20 + 2 * steps + 1.2 * (t - cut.t) + 24 * M.sweep(t, [jump], { frames: 5 });
    };

    return {
      sequences: [hero.seq],
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [L, SL, TL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const sh = M.shake(t, [cut], { amp: M.MOTION.shake.amp });
        const ts = M.shake(t, [cut], { amp: M.MOTION.shake.type, salt: 5 });
        const sl = M.slam(t, cut, { dir: [0, 1] });
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });
        setStyle(hero.canvas, "top", px(HERO_Y + sl.y + sh.y));
        setStyle(hero.canvas, "left", px(sh.x));
        hero.draw(Math.min(96, frameOfSrc(t)), { scale: pu, originX: 0.5, originY: 0.35, grade: { brightness: 0.7 } });

        // Price: slams down from above, PUNCHes (type) on the snares.
        const ps = M.slam(t, cut, { dir: [0, -1] });
        const pk = M.punch(t, snares, { amp: M.MOTION.punch.type });
        const st = { on: ps.on, opacity: 1, scale: pk };
        applyStamp(price.el, st, { dx: ts.x, dy: ps.y + ts.y });
        applyStamp(usd.el, st, { dx: ts.x, dy: ps.y + ts.y });
        const up = -60 * M.sweep(t, sweeps);
        terms.forEach((x, i) => applyStamp(termNodes[i], M.stamp(t, x.h), { dy: up }));
      },
    };
  },
};
