// T5 Black (TREATMENT section 7.2). tau 6.487 to 8.108, frames 389 to 485 (master 130.134 to
// 131.756). Demo T05: Black Linear Ensemble, Color 20 % -> 60 % from the snare 130.540 to 130.945.
//
// 130.134 (f389, the empty downbeat): SMEAR (0.25 s, centred) from the whole Green plate to the
//   full-bleed Black plate at 1.2x; tag "BLACK · ENSEMBLE".
// kick 130.338 (f401): PUNCH and a push step.
// snare + hat 130.540 (f413): CUT to the COLOR slider (1.3x); the RING rides the thumb; "Color."
//   STAMPs (110 px, #9aa0a6, baseline 1300); the readout rolls large beside it.
// hat + kick 130.943, 131.144 (f437, f449): PUNCH and a push step each.
// snare 131.351 (f462): WHIP out to the whole Black plate (1.2x).
// crash + kick 131.554 (f474): FLASH white (0.20).
// T6 hard-cuts to the totem on 131.756 (f486).

import { bottomScrim, cl, bigTag, moveCaption, bigReadout, frameDiv, renderWhip, smearAt, PlateSmear, sliderCentre, checkSafe, applyStamp, COLOR } from "./t00-common.js";

const FULL = { cx: 540, cy: 1000, scale: 1.2 };

export default {
  id: "t05-black",
  t0: 389 / 60,
  t1: 486 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show } = lib.util;

    const bar81 = b.bar(81);
    const bar82 = b.bar(82);
    const T0 = b.onsetTime(bar81);
    const T1 = b.onsetTime(bar82);
    this.t0 = T0;
    this.t1 = T1;
    const k1 = cl(b, 130.3379);
    const sCut = cl(b, 130.5404); // snare + hat
    const steps = [cl(b, 130.9427), cl(b, 131.1442)]; // hat + kick, twice
    const sWhip = cl(b, 131.3513);
    const crash = cl(b, 131.554);
    const d = demos.demoById("T05");
    const g = d._g.find((x) => x.param === "color");
    const g0 = b.comp(g.t0);
    const g1 = b.comp(g.t1);
    this.events.push(
      { t: b.master(bar81), kind: "cut", hit: "bar 81.1 130.134 (smear to the Black plate)" },
      { t: k1.tm, kind: "sweep", hit: "kick 130.338 (punch + push step)" },
      { t: sCut.tm, kind: "cut", hit: "snare + hat 130.540 (COLOR slider, Color.)" },
      { t: sCut.tm, kind: "gesture", hit: "snare 130.540 (Color 20 -> 60)" },
      ...steps.map((h) => ({ t: h.tm, kind: "sweep", hit: `hat + kick ${h.tm} (punch + push step)` })),
      { t: sWhip.tm, kind: "whip", hit: "snare 131.351 (out to the whole plate)" },
      { t: crash.tm, kind: "flash", hit: "crash + kick 131.554 (white 0.20)" },
    );
    lib.registerFlash({ t: crash.t, peak: 0.2, color: "#ffffff", id: "T5-flash" });

    const PL = ctx.layer("plate", 10);
    const fg = frameDiv(PL);
    const full = new PlateSmear(fg, lib, "black", { scale: FULL.scale, header: false, hiRes: true });
    full.require(demos.statesIn(T0 - 0.15, T1, "T05", 120));
    const sg = frameDiv(PL);
    const slider = lib.createPlate("black", { parent: sg, scale: 1.3, header: false, hiRes: true });
    slider.require(demos.statesIn(sCut.t - 0.05, sWhip.t + 0.1, "T05", 240));
    const SLIDER = sliderCentre(lib, "black");

    const RL = ctx.layer("ring", 16);
    const ring = lib.createRing(RL, { color: COLOR.lavender, width: 3, factor: 1.4 });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const TL = ctx.layer("type", 41);
    bottomScrim(TL);
    bigTag(TL, "BLACK · ENSEMBLE", COLOR.hue.black);
    const cap = moveCaption(TL, "Color.", COLOR.hue.black);
    const big = bigReadout(TL, COLOR.readout.black, { x: 420 });

    return {
      setup() {
        checkSafe([TL], "T5");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const plateOn = t >= bar81 - 0.125 && t < T1;
        show(PL, plateOn);
        show(RL, on);
        show(FL, on);
        show(TL, on);
        if (!plateOn) return;
        const st = demos.plateState(t, "T05");
        const kicks = b.hitsIn("kick", T0 - 0.01, T1);
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.macro });
        const push = 1 + 0.03 * M.sweep(t, [k1, ...steps], { frames: 4 });
        // The whole plate at 1.2x (smear in), the slider from the snare, the whole plate again.
        const onSlider = b.after(t, sCut.t) && !b.after(t, sWhip.t);
        // Before the snare: the whole plate only; from it, the slider, whipped out on 131.351.
        if (!b.after(t, sCut.t)) {
          lib.util.setStyle(sg, "visibility", "hidden");
          lib.util.setStyle(fg, "visibility", "");
        } else renderWhip(M, t, sWhip, sg, fg, { dir: [0, 1] });
        full.setState(st);
        full.setGrade(demos.grade("black", t));
        full.place({ cx: FULL.cx, cy: FULL.cy, scale: FULL.scale * pu * (b.after(t, sWhip.t) ? 1 : push) });
        const u = smearAt(t, bar81);
        full.render(u ?? 0, u == null ? null : "in");
        slider.setState(st);
        slider.setGrade(demos.grade("black", t));
        slider.focus({ on: SLIDER, zoom: 1.3 * push * pu, at: [540, 1000] });
        if (!on) return;
        const rp = onSlider ? slider : full.centre;
        ring.render(t, { t0: g0, t1: g1, rect: rp.controlScreenRect("color") });
        flash.render(t, M.flash(t, [crash], { peak: 0.2 }), "#ffffff", lib.flash.flashMode("T5-flash"));
        const stc = M.stamp(t, sCut);
        applyStamp(cap, stc);
        applyStamp(big.el, stc);
        if (stc.on) big.render(demos.readoutIn(d, "color", t));
      },
    };
  },
};
