// Shot 16, 50.00-54.00: Free. Hard cut on the impact with the second and last bloom (20%). Green
// (HQ unlit, Green (a), render R01) and Purple (HQ lit, Purple (a), render R08) at 0.62 scale
// (868x449.5, even 61 px gaps at the frame edges and between), each on a 14% glow in its hue and
// drifting per G2. A 180 px scope under each plate reads that plate's own stem. "free." is static;
// the G3b hairline under it carries one strand per audible engine. The header sits a little higher
// than the treatment's (eyebrow 90, headline 188, sub 256) to give the bigger plates room.

import { inFrames, fadeIn, setAlpha, radialGlow, sceneGrain, stageBox, hairlineY, plateLabel } from "./kit-late.js";

const T0 = 50.0;
const T1 = 54.0;
const SCALE = 0.62;
const PLATE_Y = 306;
const LABEL_BASELINE = 798;
const SCOPE = { cy: 910, size: 180 };
const HEAD = { eyebrow: 90, headline: 188, sub: 256 };
const GAP = (1920 - 2 * 1400 * SCALE) / 3;
const PLATES = [
  { engine: "green", render: "R01", x: GAP, y: PLATE_Y, label: "GREEN", stem: "gtr", rgb: [126, 224, 160] },
  { engine: "purple", render: "R08", x: 2 * GAP + 1400 * SCALE, y: PLATE_Y, label: "PURPLE", stem: "pad", rgb: [201, 177, 255] },
];

export default {
  id: "shot16-free",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues, stage } = ctx;
    const { type, util } = lib;
    const { el, setStyle, show, clamp } = util;

    const glowL = ctx.layer("glow", 5);
    const plateL = ctx.layer("plates", 20);
    const scopeL = ctx.layer("scopes", 30);
    const typeL = ctx.layer("type", 40);
    const bloomL = ctx.layer("bloom", 60);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [glowL, plateL, scopeL, typeL, bloomL, grainL];

    const W = 1400 * SCALE;
    const H = 725 * SCALE;
    const items = PLATES.map((d) => {
      const cx = d.x + W / 2;
      const cy = d.y + H / 2;
      radialGlow(glowL, { cx, cy, w: W * 1.35, h: H * 1.8, color: d.rgb, a: [0.14, 0.04] });
      const plate = lib.createPlate(d.engine, { parent: plateL, scale: SCALE, x: d.x, y: d.y });
      plate.requireRender(cues, d.render, T0, T1);
      const label = plateLabel(d.label, { parent: typeL, hue: type.HUE[d.engine], x: cx, baseline: LABEL_BASELINE });
      const scope = lib.createScope(scopeL, { cx, cy: SCOPE.cy, size: SCOPE.size, disc: null, color: type.HUE[d.engine], stem: d.stem });
      return { ...d, plate, label, scope };
    });

    const brow = type.eyebrow("FREE MODE", { parent: typeL, x: 960, baseline: HEAD.eyebrow, align: "center" });
    const head = type.headline({ parent: typeL, text: "Green and Purple are ", accent: "free.", size: 92, x: 960, baseline: HEAD.headline, align: "center" });
    const sub = type.body("No card or licence key needed.", { parent: typeL, size: 30, weight: 400, color: type.C.muted, x: 960, baseline: HEAD.sub, align: "center" });

    // Bloom: radial #eaffe9 at 20%, decaying over 0.4 s from the cut.
    const bloom = el("div", {
      parent: bloomL,
      style: {
        position: "absolute",
        inset: "0",
        background: "radial-gradient(ellipse 62% 70% at 50% 50%, rgba(234,255,233,1) 0%, rgba(234,255,233,0.35) 45%, rgba(234,255,233,0) 100%)",
        mixBlendMode: "screen",
      },
    });

    let hair = null;
    return {
      setup() {
        const b = stageBox(head.accent, stage);
        hair = type.offerHairline({
          parent: typeL,
          x: b.x,
          y: hairlineY(head.accent, HEAD.headline),
          width: b.w,
          strands: [{ engine: "green" }, { engine: "purple" }],
        });
      },
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        for (const it of items) {
          const s = cues.plateStateAt(it.render, t);
          it.plate.place({ dx: lib.driftPx(s) });
          it.plate.setState(s);
          it.scope.draw(t, { stem: it.stem, render: it.render });
        }
        setAlpha(brow, 1);
        setAlpha(head.el, 1);
        setAlpha(sub, fadeIn(t, 50.75));
        hair.render(t, [cues.cyclesAt("R01", t), cues.cyclesAt("R08", t)]);
        const u = clamp((t - T0) / 0.4);
        const k = (1 - u) * (1 - u);
        setAlpha(bloom, 0.2 * k);
        grain.render(t);
      },
    };
  },
};
