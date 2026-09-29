// S02 Set-up montage, refrain 1 (TREATMENT section 2, ACT I). The bar-2 kicks (frames 121 to 217).
//
// Four hard CUTs to 2.0x Green macros, one per kick: RATE "0.62 Hz" (f121), DEPTH "22%" (f145),
// OFFSET "90°" (f170), WIDTH "100%" (f194). Each pushes 1.00 -> 1.03 over its beat (sine.inOut)
// and PUNCHes (macro, x 0.6 in the tom groove) on its kick. On the floor toms (2.637, 3.445) the
// framed readout's glow blinks +40 % for 3 frames. The scope inset holds at SCOPE (a01).
// "Great sound" drops to one line: 120 px, baseline 400.

import { scrim } from "./a00-common.js";
import { SCOPE } from "./a01-still-mixturn.js";

const KY = 1090; // knob centre y: the body runs from about y 496 to 1944 at 2.0x (full bleed below)

export default {
  id: "a02-montage",
  t0: 2.0253,
  t1: 3.6485,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { COLOR } = ctx.portrait;
    const { el, setStyle, show } = lib.util;

    const kicks = [2.0253, 2.4326, 2.8376, 3.2431].map((x) => b.hitNear("kick", x));
    const toms = [2.6368, 3.4445].map((x) => b.hitNear("floortom", x));
    const next = b.hitNear("kick", 3.6485); // S03 cuts in on its frame
    const T0 = kicks[0].tf;
    const T1 = next.tf;
    this.events.push(...kicks.map((k, i) => ({ t: k.tm, kind: "cut", hit: `kick ${k.tm} (macro ${i + 1})` })));
    this.events.push(...toms.map((h) => ({ t: h.tm, kind: "sweep", hit: `floor tom ${h.tm} (readout blink)` })));

    const L = ctx.layer("plate", 10);
    // Knob x per shot keeps the plate's edges off the frame at 2.0x (RATE left, WIDTH right).
    const shots = [
      { h: kicks[0], on: "rate", zoom: 2.0, at: [360, KY] },
      { h: kicks[1], on: "depth", zoom: 2.0, at: [540, KY] },
      { h: kicks[2], on: "offset", zoom: 2.0, at: [540, KY] },
      { h: kicks[3], on: "width", zoom: 2.0, at: [744, KY] },
    ];
    const state0 = demos.plateState(T0 + 0.1);
    const montage = lib.createMontage(L, "green", shots, { push: [1.0, 1.03], punchAmp: M.MOTION.punch.macro * M.MOTION.tomGroove, state: state0 });
    // The macro edge above the body: the plate rises out of black under the type.
    el("div", { parent: L, style: { position: "absolute", left: "0px", top: "440px", width: "1080px", height: "330px", background: "linear-gradient(#050506 30%, rgba(5,5,6,0.6) 60%, rgba(5,5,6,0))" } });
    scrim(L, { top: 0.72, to: 720 });

    const SL = ctx.layer("scope", 14);
    const scope = lib.createScope(SL, { cx: SCOPE[0], cy: SCOPE[1], size: 300, stem: "wet", color: COLOR.hue.green, disc: "rgba(5,5,6,0.55)", labelSize: 16 });

    const TL = ctx.layer("type", 40);
    lib.type.headline({ text: "Great sound", size: 120, parent: TL, x: 72, baseline: 400 });

    const NAMES = ["rate", "depth", "offset", "width"];
    return {
      render(t) {
        const on = t >= T0 && t < T1;
        for (const l of [L, SL, TL]) show(l, on);
        if (!on) return;
        const k = montage.render(t, demos.plateState(t));
        montage.plate.setGrade(demos.grade("green", t));
        // Floor-tom blink: the framed readout +40 % brightness for 3 frames.
        const f = b.frameAt(t);
        const blink = toms.some((h) => f >= h.frame && f < h.frame + 3);
        for (const n of NAMES) setStyle(montage.plate.readouts[n].node, "filter", blink && n === NAMES[k] ? "brightness(1.4)" : "");
        scope.draw(t, { stem: "wet", color: COLOR.hue.green });
      },
    };
  },
};
