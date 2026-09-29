// T7 BUY (TREATMENT sections 7.2 and 7.4). tau 11.352 to 15.000, frames 681 to 899 (master 135.000
// to 138.648). Demo T06: Green on the solo guitar; the audio fades 138.243 -> 138.630 and loops
// into the crash at frame 0.
//
// kick + snare 135.000 (f681), the full-band stop: the TikTok end card (film/lib/endcard.js,
// variant "tiktok", Unit B) SLAMs in, releasing T6's inhale from 0.95 to 1.00 with a one-frame
// 1.01 overshoot; a white FLASH [0.40, 0.12] under the card (so under the Buy button). Then HOLD:
// only the scope inset, the plate readouts, the chorustype and the Buy hairline move; the grain is
// frozen (manifest). Everything builds at once on the stop. No trial button in this variant.

import { cl, COLOR } from "./t00-common.js";

export default {
  id: "t07-buy",
  t0: 681 / 60,
  t1: 15.0,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show } = lib.util;

    const stop = cl(b, 134.9998);
    const T0 = stop.tf;
    const T1 = ctx.manifest.duration;
    this.t0 = T0;
    this.events.push(
      { t: stop.tm, kind: "slam", hit: "kick + snare 135.000 (the stop: the end card)" },
      { t: stop.tm, kind: "flash", hit: "kick + snare 135.000 (white [0.40, 0.12] under the card)" },
    );
    lib.registerFlash({ t: stop.t, peak: 0.4, color: "#ffffff", id: "T7-flash" });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);
    const CL = ctx.layer("card", 40);
    const TOP = ctx.layer("card-top", 850);
    const card = lib.createEndcard(CL, { variant: "tiktok", demos, beats: b, span: [T0, T1], topLayer: TOP, trialCta: false });

    return {
      preload: card.preload,
      setup() {
        if (card.setup) return card.setup();
      },
      render(t) {
        const on = t >= T0 && t < T1 + 1;
        for (const l of [FL, CL, TOP]) show(l, on);
        if (!on) return;
        const f = b.frameAt(t);
        const scale = f === stop.frame ? M.MOTION.inhale.overshoot : 1;
        card.render(t, { build: [stop], scale });
        const df = f - stop.frame;
        const a = df === 0 ? 0.4 : df === 1 ? 0.12 : 0;
        flash.render(t, a, "#ffffff", lib.flash.flashMode("T7-flash"));
        void COLOR;
      },
    };
  },
};
