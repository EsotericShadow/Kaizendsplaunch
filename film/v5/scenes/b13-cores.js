// S13 17 sound cores (TREATMENT section 2, ACT IV). Bars 23-24, 36.080 to 39.324 (frames 2164-2358).
// Owns the 36.080 seam: a hard CUT to black on the drum re-entry (kick + rack 36.081, f2164).
//
// A ring of the 17 core glyphs (820 px across, centred (540, 920)) with "17" in its centre
// (Fraunces 600, 260 px). The ten prebuilt cores light one per hit on the ten listed hits, in
// engine-hue pairs; each light-up takes 4 frames with a PUNCH (1.03) on the ring. The seven
// Create-only glyphs stay at 25 % white. The floor tom at 39.133 pulses the ring.
// Type: the eyebrow (two lines: at 28 px it is 958 px wide, so the line-fit rule breaks it at the
// separator) and "17 sound cores." STAMP on f2164; the dek lands on 36.887. Heard: Black (M05).

import { hitAt, inF, ev, fitter, headLine, bodyLine, eyebrowLine, applyStamp, applyOn, coreRing, RING } from "./b00-common.js";

const LIGHTS = [36.0807, 36.4862, 36.8871, 37.2971, 37.5018, 37.6833, 37.9262, 38.3098, 38.5165, 38.9097];

export default {
  id: "b13-cores",
  t0: 2164 / 60,
  t1: 2359 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, motion: M } = ctx;
    const { show, el } = lib.util;
    const cut = hitAt(b, 36.0807);
    const next = hitAt(b, 39.3241);
    const F0 = cut.frame;
    const F1 = next.frame;
    const lights = LIGHTS.map((x) => hitAt(b, x));
    const floor = hitAt(b, 39.1325);
    const dek = hitAt(b, 36.8871);
    ev(this, b, cut, "cut", "kick + rack 36.081 (cut to black, the ring)");
    ev(this, b, cut, "stamp", "kick + rack 36.081 (eyebrow, headline)");
    lights.forEach((h, i) => ev(this, b, h, "sweep", `${h.piece} ${h.tm} (core ${i + 1} lights)`));
    ev(this, b, dek, "text", "rack + kick 36.887 (dek)");

    const RL = ctx.layer("ring", 20);
    const ring = coreRing(RL);
    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const seventeen = el("div", { parent: TL, text: "17", style: { font: `600 260px ${lib.type.FONT.display}`, letterSpacing: "-0.02em", fontFeatureSettings: '"ss01", "ss02", "lnum"', color: lib.type.C.fg, width: "1080px", textAlign: "center", transformOrigin: `${RING.cx}px 60%` } });
    lib.type.placeText(seventeen, { x: 0, baseline: RING.cy + 92 });
    const brow1 = eyebrowLine(TL, null, "FIVE PREBUILT ENGINES ·", { size: 28, baseline: 292 });
    const brow2 = eyebrowLine(TL, null, "17 SOUND CORES", { size: 28, baseline: 330 });
    const head = headLine(TL, fit, { text: "17 sound ", accent: "cores.", size: 104, baseline: 420 });
    const dek1 = bodyLine(TL, fit, "The ten cores inside the prebuilt", { size: 40, baseline: 1420 });
    const dek2 = bodyLine(TL, fit, "engines, plus seven more.", { size: 40, baseline: 1470 });

    const amp = 0.03; // "a PUNCH (1.03) on the ring"
    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        show(RL, on);
        show(TL, on);
        if (!on) return;
        const f = b.frameAt(t);
        const lit = lights.map((h) => Math.max(0, Math.min(1, (f - h.frame + 1) / 4)));
        const pu = M.punch(t, [...lights, floor], { amp });
        ring.render({ lit, scale: pu });
        const st = M.stamp(t, cut);
        for (const n of [brow1, brow2, head.el]) applyStamp(n, st);
        applyOn(b, t, seventeen, cut, { k: 1 + (pu - 1) * 0.4 });
        applyOn(b, t, dek1, dek);
        applyOn(b, t, dek2, dek);
      },
    };
  },
};
