// T3 Purple (TREATMENT section 7.2). tau 3.244 to 4.865, frames 194 to 290 (master 126.892 to
// 128.513). Demo T03: Purple Orbit, Color 10 % -> 45 % from the snare 127.297 to 128.108.
//
// crash + kick 126.892 (f194): SMEAR (0.25 s, centred) from the whole Blue plate to a full-bleed
//   Purple L-MACRO across the COLOR slider; FLASH Purple (0.30); tag "PURPLE · ORBIT".
// snare 127.297 (f218): "Color." STAMPs (110 px, #c9b1ff, baseline 1300); the RING rides the
//   thumb; the thumb glides. On the "and" (127.500) the readout STAMPs in large beside the caption
//   and rolls (an event every beat: no drum plays between 127.297 and 127.704).
// kick 127.704 (f243), hat + kick 127.885 (f254): PUNCH and a push step each.
// snare 128.110 (f267): WHIP out to the whole Purple plate (0.77, full width).
// The frame hard-cuts to T4's freeze on 128.513 (f291).

import { bottomScrim, hit, cl, bigTag, moveCaption, bigReadout, frameDiv, renderWhip, smearAt, PlateSmear, sliderCentre, checkSafe, applyStamp, COLOR } from "./t00-common.js";
import { WHOLE } from "./t01-totem-red.js";

export default {
  id: "t03-purple",
  t0: 194 / 60,
  t1: 291 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show } = lib.util;

    const cut = hit(b, "kick", 126.8918);
    const sCap = hit(b, "snare", 127.2972);
    const steps = [cl(b, 127.7039), cl(b, 127.885)]; // kick (f243), hat + kick (f254)
    const andBeat = b.beat(79, 2.5); // the readout pops in on the "and" (an event every beat)
    const sWhip = cl(b, 128.11); // snare + hat
    const freeze = hit(b, "kick", 128.5135);
    const T0 = cut.tf;
    const T1 = freeze.tf;
    this.t0 = T0;
    this.t1 = T1;
    const d = demos.demoById("T03");
    const g0 = b.comp(d._g[0].t0);
    const g1 = b.comp(d._g[0].t1);
    this.events.push(
      { t: cut.tm, kind: "cut", hit: "crash + kick 126.892 (smear to Purple COLOR)" },
      { t: cut.tm, kind: "flash", hit: "crash + kick 126.892 (Purple 0.30)" },
      { t: sCap.tm, kind: "stamp", hit: "snare 127.297 (Color.)" },
      { t: sCap.tm, kind: "gesture", hit: "snare 127.297 (Color 10 -> 45)" },
      { t: b.master(andBeat), kind: "stamp", hit: "beat 79.2.5 127.500 (the readout rolls large)" },
      ...steps.map((h) => ({ t: h.tm, kind: "sweep", hit: `${h.piece} ${h.tm} (punch + push step)` })),
      { t: sWhip.tm, kind: "whip", hit: "snare 128.110 (to the whole plate)" },
    );
    lib.registerFlash({ t: cut.t, peak: 0.3, color: COLOR.fill.purple, id: "T3-flash" });

    const PL = ctx.layer("plate", 10);
    const mg = frameDiv(PL);
    const macro = new PlateSmear(mg, lib, "purple", { scale: 2.0, hiRes: true, header: false });
    macro.require(demos.statesIn(T0 - 0.15, T1, "T03", 240));
    const SLIDER = sliderCentre(lib, "purple");
    const wg = frameDiv(PL);
    const whole = lib.createPlate("purple", { parent: wg, scale: WHOLE.scale });
    whole.require(demos.statesIn(sWhip.t - 0.1, T1, "T03", 120));

    const RL = ctx.layer("ring", 16);
    const ring = lib.createRing(RL, { color: COLOR.lavender, width: 3, factor: 1.4 });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const TL = ctx.layer("type", 41);
    bottomScrim(TL);
    bigTag(TL, "PURPLE · ORBIT", COLOR.hue.purple);
    const cap = moveCaption(TL, "Color.", COLOR.hue.purple);
    const big = bigReadout(TL, COLOR.readout.purple, { x: 420 });

    return {
      setup() {
        checkSafe([TL], "T3");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const tc = cut.t;
        const plateOn = (t >= tc - 0.125 && t < T1);
        show(PL, plateOn);
        show(RL, on);
        show(FL, on);
        show(TL, on);
        if (!plateOn) return;
        const st = demos.plateState(t, "T03");
        macro.setState(st);
        macro.setGrade(demos.grade("purple", t));
        const kicks = b.hitsIn("kick", T0 - 0.01, T1);
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.macro });
        const z = 2.0 * (1 + 0.04 * M.sweep(t, steps, { frames: 4 })) * pu;
        macro.focus({ on: SLIDER, zoom: z, at: [540, 900] }); // the COLOR label and readout clear the caption row
        const u = smearAt(t, tc);
        macro.render(u ?? 0, u == null ? null : "in");
        const inWhole = renderWhip(M, t, sWhip, mg, wg, { dir: [0, -1] });
        if (b.frameAt(t) >= sWhip.frame - 2) {
          whole.setState(st);
          whole.setGrade(demos.grade("purple", t));
          whole.place({ cx: WHOLE.cx, cy: WHOLE.cy, scale: WHOLE.scale });
        }
        if (!on) return;
        ring.render(t, { t0: g0, t1: g1, rect: (inWhole ? whole : macro.centre).controlScreenRect("color") });
        flash.render(t, M.flash(t, [cut], { peak: 0.3 }), COLOR.fill.purple, lib.flash.flashMode("T3-flash"));
        const stc = M.stamp(t, sCap);
        applyStamp(cap, stc);
        const stb = M.stamp(t, andBeat);
        applyStamp(big.el, stb);
        if (stb.on) big.render(demos.readoutIn(d, "color", t));
      },
    };
  },
};
