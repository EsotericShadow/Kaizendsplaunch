// S24 End card + Buy (TREATMENT section 2, ACT VII, and 4.3). Bars 54-56, 86.351 to 91.216
// (frames 5181-5472). Heard: M13 Green on the solo guitar; the mix fades 89.900 to 91.080.
//
// f5181 (the bar-54 line): a HARD build of the name, the live Green plate, the scope, the Buy
// button and the trial button, all together. f5229 (bar 54 beat 3, 87.162): the offer and the URL.
// f5278 (the bar-55 line, 87.972): the format row (above the grain: no layer draws over the VST
// tile) and the legal line. Bars 55 and 56 hold everything. The only movement: the plate readouts,
// the chorustype on the name, the scope and the Buy button's hairline (one cycle per bar at
// 0.62 Hz). The picture holds to the last frame (5472), the thumbnail and loop frame.

import { barT, inF, ev } from "./b00-common.js";

export const TRIAL_CTA = true; // the lead confirms the site's trial switch before release

export default {
  id: "b24-endcard",
  t0: 5181 / 60,
  t1: 5473 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos } = ctx;
    const { show } = lib.util;
    const build = [barT(b, 54), barT(b, 54, 3), barT(b, 55)];
    const F0 = b.onsetFrame(build[0]);
    const F1 = 5473;
    ev(this, b, build[0], "cut", "bar line 86.351 (end card: name, plate, Buy)");
    ev(this, b, build[1], "text", "bar 54 beat 3, 87.162 (offer, URL)");
    ev(this, b, build[2], "text", "bar line 87.972 (format row, legal)");

    const L = ctx.layer("card", 40);
    const top = ctx.layer("formats", 850);
    const card = lib.createEndcard(L, { variant: "main", demos, beats: b, span: [build[0], 91.2], topLayer: top, trialCta: TRIAL_CTA });

    return {
      preload: card.preload,
      render(t) {
        const on = inF(b, t, F0, F1);
        show(L, on);
        show(top, on);
        if (!on) return;
        card.render(t, { build });
      },
    };
  },
};
