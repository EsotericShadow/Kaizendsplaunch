// S16 Free (TREATMENT section 2, ACT V). Bars 31-34, 49.053 to 55.540 (frames 2943-3331).
//
// f2943 (crash + kick 49.054): FLASH Green (0.30). The Green plate (scale 0.56, 784 x 474, x 148 to
// 932, y 600 to 1074) SLAMs down from the top and the Purple plate (y 1090 to 1564) SLAMs up from
// the bottom (6 frames from +-160 px, power4.out, PUNCH on landing). Snares 49.459 and 50.270 STAMP
// the FREE pills on Green, then Purple (mono 26 px on engine-fill pills, each plate's top-left
// corner). f3137 (crash + kick 52.296): FLASH Purple (0.30); colour = sound swaps (M07: Purple lit,
// Green dimmed). Kicks PUNCH both plates. Every snare re-stamps the heard plate's pill and spreads
// the wet copies of "free." (+30 %, relaxing over 150 ms): the backbeat events of the verse. The
// pickups 55.338 and 55.417 SWEEP both plates up and out (two steps of 400 px; they fade over the
// second step, since 800 px leaves the Purple plate under the headline).
// Type: "Green and Purple / are free." on f2943 ("free." is chorustype at the heard engine's law);
// "No card or licence key needed." on 50.469, on a band over the Purple plate's lower edge.

import { hitAt, inF, ev, fitter, headLine, bodyLine, applyStamp, applyOn, flashBank, ctSettings, relax, band, pillLabel, LAW } from "./b00-common.js";

const PLATE = { scale: 0.56, x: 148, green: 600, purple: 1090 };

export default {
  id: "b16-free",
  t0: 2943 / 60,
  t1: 3332 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show, setStyle, px } = lib.util;
    const { COLOR } = P;
    const cut = hitAt(b, 49.0538);
    const swap = hitAt(b, 52.2962);
    const next = hitAt(b, 55.5404);
    const F0 = cut.frame;
    const F1 = next.frame;
    const tagG = hitAt(b, 49.4595);
    const tagP = hitAt(b, 50.2703);
    const dek = hitAt(b, 50.4687);
    const pickups = [55.3384, 55.417].map((x) => hitAt(b, x));
    const snares = b.hitsIn("snare", cut.t, pickups[0].t - 0.01, { minDb: -20 });
    const backbeat = snares.filter((h) => h.frame > tagP.frame);
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    ev(this, b, cut, "slam", "crash + kick 49.054 (Green and Purple slam in)");
    ev(this, b, cut, "flash", "crash + kick 49.054 (FLASH Green)");
    ev(this, b, cut, "stamp", "crash + kick 49.054 (headline)");
    ev(this, b, tagG, "stamp", "snare 49.459 (FREE on Green)");
    ev(this, b, tagP, "stamp", "snare 50.270 (FREE on Purple)");
    ev(this, b, dek, "text", "kick + crash 50.469 (No card or licence key needed.)");
    ev(this, b, swap, "flash", "crash + kick 52.296 (FLASH Purple, colour = sound swaps)");
    backbeat.forEach((h) => ev(this, b, h, "stamp", `snare ${h.tm} (the heard FREE pill re-stamps, free. spreads)`));
    pickups.forEach((h) => ev(this, b, h, "sweep", `snare pickup ${h.tm} (plates sweep up and out)`));

    const L = ctx.layer("plates", 12);
    const mk = (engine, id) => {
      const p = lib.createPlate(engine, { parent: L, scale: PLATE.scale, header: true, hiRes: false });
      p.require(demos.statesIn(cut.t, next.t, id, 4));
      return p;
    };
    const green = mk("green", "M06");
    const purple = mk("purple", "M07");
    const W = green.width * PLATE.scale;
    const H = green.height * PLATE.scale;

    const flashes = flashBank(ctx, lib, [
      { h: cut, color: COLOR.fill.green, peak: 0.3 },
      { h: swap, color: COLOR.fill.purple, peak: 0.3 },
    ]);

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const h1 = headLine(TL, fit, { text: "Green and Purple", size: 104, baseline: 380 });
    const h2 = headLine(TL, fit, { text: "are ", accent: "free.", size: 104, baseline: 490 });
    const ct = lib.createChorusType(h2.accent, { law: "SINE", engine: "green" });
    const bnd = band(TL, 1452, 1516, 0.78);
    setStyle(bnd, "zIndex", "-1");
    const d1 = bodyLine(TL, fit, "No card or licence key needed.", { size: 44, baseline: 1500 });
    const pills = {
      green: pillLabel(TL, "FREE", { fill: COLOR.fill.green, h: 44, padX: 14 }),
      purple: pillLabel(TL, "FREE", { fill: COLOR.fill.purple, h: 44, padX: 14 }),
    };

    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [L, TL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const f = b.frameAt(t);
        const heard = f >= swap.frame ? "purple" : "green";
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });
        const out = -400 * M.sweep(t, pickups);
        const place = (p, engine, y0, dir) => {
          const s = M.slam(t, cut, { dir: [0, dir] });
          const cy = y0 + H / 2 + s.y + out;
          p.place({ cx: 540, cy, scale: PLATE.scale * pu });
          p.setState(demos.plateState(t, engine === "green" ? "M06" : "M07"));
          p.setGrade(demos.grade(engine, t));
          return { x: 540 - (W * pu) / 2, y: cy - (H * pu) / 2 };
        };
        const gTL = place(green, "green", PLATE.green, -1);
        const pTL = place(purple, "purple", PLATE.purple, 1);
        // Two 400 px steps leave the Purple plate under the headline, so the plates also fade over
        // the second step: the last frames before the S17 cut are the type alone.
        const fade = Math.max(0, Math.min(1, 2 - M.sweep(t, pickups)));
        for (const p of [green, purple]) setStyle(p.el, "opacity", fade >= 1 ? "" : String(+fade.toFixed(4)));

        // FREE pills at each plate's top-left corner; the heard plate's pill re-stamps on the backbeat.
        const pill = (n, tl, tagHit, engine) => {
          const st = M.stamp(t, tagHit);
          let s = st.scale;
          if (engine === heard) {
            const last = backbeat.filter((h) => h.frame <= f).pop();
            if (last) s *= M.stamp(t, last, { from: 1.12 }).scale;
          }
          setStyle(n, "left", px(tl.x + 16));
          setStyle(n, "top", px(tl.y + 14));
          // The pills leave with the plates on the pickups: they fade over the first 400 px step.
          const out = M.sweep(t, pickups);
          applyStamp(n, { ...st, scale: s, opacity: st.opacity * Math.max(0, 1 - out) });
          if (out >= 1) setStyle(n, "visibility", "hidden");
        };
        pill(pills.green, gTL, tagG, "green");
        pill(pills.purple, pTL, tagP, "purple");

        const st = M.stamp(t, cut);
        applyStamp(h1.el, st);
        applyStamp(h2.el, st);
        ct.setLaw(LAW[heard]);
        for (const w of ct.wet) setStyle(w, "color", COLOR.hue[heard]);
        const s = ctSettings(demos, t, relax(b, t, snares, 0.15));
        if (s) ct.render(t, s);
        applyOn(b, t, d1, dek);
        applyOn(b, t, bnd, dek);
      },
    };
  },
};
