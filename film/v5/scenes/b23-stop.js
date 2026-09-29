// S23 THE STOP: payoff (TREATMENT section 2, ACT VII). Bar 53, 84.725 to 86.351 (frames 5083-5180).
//
// f5083 (snare 84.7251 + kick 84.7296 + the loudest crash 84.733): the frame releases from the
// wind-up's 0.95 to 1.00 with a single 1.01 overshoot (motion.inhale), a white FLASH [0.45, 0.15],
// and a hard CUT to near-black stillness. The band stops; the guitar plays on alone through Green.
// The scope, 760 px centred at (540, 1060), shows the dry band as a white ghost plus the heard
// guitar in Green: the only moving picture. The grain is frozen (manifest). No PUNCH, SHAKE or FLASH
// after the stop.
// Type: "Great sound / doesn’t / sit still." (Fraunces 600, 120 px, baselines 400, 530, 660);
// "sit still." is chorustype SINE Green at the heard 0.62 Hz.

import { hitAt, barT, inF, ev, fitter, headLine, flashBank } from "./b00-common.js";

const SCOPE = { cx: 540, cy: 1060, size: 760 };

export default {
  id: "b23-stop",
  t0: 5083 / 60,
  t1: 5181 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show, setStyle, el } = lib.util;
    const { COLOR } = P;
    const stop = hitAt(b, 84.7251);
    const pre = [hitAt(b, 84.3242), hitAt(b, 84.5259)];
    const F0 = stop.frame;
    const F1 = b.onsetFrame(barT(b, 54));
    ev(this, b, stop, "cut", "snare + kick + crash 84.725 (THE STOP: cut to stillness)");
    ev(this, b, stop, "flash", "snare + kick + crash 84.725 (white FLASH [0.45, 0.15])");
    ev(this, b, stop, "text", "84.725 (Great sound / doesn’t / sit still.)");

    const BG = ctx.layer("bg", 8);
    el("div", { parent: BG, style: { position: "absolute", inset: "0", background: "radial-gradient(circle at 540px 1060px, #0d0e12 0px, #070709 520px, #050506 900px)" } });
    const SL = ctx.layer("scope", 14);
    const ghost = lib.createScope(SL, { cx: SCOPE.cx, cy: SCOPE.cy, size: SCOPE.size, stem: "dry", color: "#f6f4ef", disc: null, labelSize: 20 });
    const wet = lib.createScope(SL, { cx: SCOPE.cx, cy: SCOPE.cy, size: SCOPE.size, stem: "guitar", color: COLOR.hue.green, disc: null, outline: null, graticule: false });

    const flashes = flashBank(ctx, lib, [{ h: stop, color: "#ffffff", frames: M.MOTION.flash.stop }]);

    const TL = ctx.layer("type", 40);
    const inner = el("div", { parent: TL, style: { position: "absolute", inset: "0", transformOrigin: "540px 960px" } });
    const fit = fitter();
    headLine(inner, fit, { text: "Great sound", size: 120, baseline: 400 });
    headLine(inner, fit, { text: "doesn’t", size: 120, baseline: 530 });
    const h3 = headLine(inner, fit, { text: "", accent: "sit still.", size: 120, baseline: 660 });
    const ct = lib.createChorusType(h3.accent, { law: "SINE", engine: "green" });

    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [BG, SL, TL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const s = M.inhale(t, pre, stop);
        setStyle(inner, "transform", s === 1 ? "" : `scale(${+s.toFixed(5)})`);
        ghost.draw(t, { stem: "dry", color: "#f6f4ef", alpha: 0.22, gratAlpha: 4 });
        wet.draw(t, { stem: "guitar", color: COLOR.hue.green });
        const st = demos.settingsAt(t);
        if (st) ct.render(t, st);
      },
    };
  },
};
