// Shot 18, 58.00-62.00: Price. The product hero render (2500x1400) at 0.7714, the unit on the
// right, pushed 1.00 -> 1.05 inside the canvas draw (the canvas itself never transforms). At cover
// the unit starts at x 987 and the 160 px headline ends near x 1005, so the render sits 80 px
// further right (the unit moves towards the right third) and the plain studio wall is mirrored
// into the strip this uncovers on the left, under a dark edge scrim. A
// purple glow reinforces the render's underglow, breathing +-15% at 0.50 Hz. Grain 6% over the
// palette banding. Left column: eyebrow, "$49.99 USD." with the five-strand G3b hairline, sub.

import { ImageSequence } from "/__render/composition.js";
import { inFrames, fadeIn, setAlpha, sceneGrain, stageBox, hairlineY } from "./kit-late.js";

const T0 = 58.0;
const T1 = 62.0;
const IMG_W = 2500;
const IMG_H = 1400;
const COVER = 0.7714;
const SHIFT = 80;
// Push origin: the unit's centre (screen px at scale 1, after the shift). With the shift this keeps
// the unit clear of the headline and the WIDTH knob inside the frame for the whole push.
const ORIGIN = [1470, 560];
// Underglow of the render, screen px at scale 1.
const UNDERGLOW = { cx: 1470 + SHIFT, cy: 842, w: 1150, h: 230 };

export default {
  id: "shot18-price",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues, stage } = ctx;
    const { type, util } = lib;
    const { el, setStyle, px, show, TAU, progress, ease } = util;

    const bgL = ctx.layer("render", 10);
    const glowL = ctx.layer("glow", 15);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib, { opacity: 0.06 });
    const layers = [bgL, glowL, typeL, grainL];

    const canvas = el("canvas", { parent: bgL, style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "1080px" } });
    canvas.width = 1920;
    canvas.height = 1080;
    const c2d = canvas.getContext("2d", { alpha: false });
    const seq = new ImageSequence({ urls: ["/art/site/choroboros_product_hero.png"], fps: 1 });

    // Dark left edge: hides the mirror seam and keeps the type side calm.
    el("div", {
      parent: glowL,
      style: { position: "absolute", left: "0px", top: "0px", width: "320px", height: "1080px", background: "linear-gradient(90deg, rgba(5,5,6,0.92) 0%, rgba(5,5,6,0.55) 40%, rgba(5,5,6,0) 100%)" },
    });
    const glow = el("div", {
      parent: glowL,
      style: {
        position: "absolute",
        left: "0px",
        top: "0px",
        width: px(UNDERGLOW.w),
        height: px(UNDERGLOW.h),
        background: "radial-gradient(closest-side, rgba(184,140,255,0.28) 0%, rgba(184,140,255,0.06) 60%, rgba(184,140,255,0) 100%)",
        mixBlendMode: "screen",
        transformOrigin: "50% 50%",
      },
    });

    const brow = type.eyebrow("ONE-TIME PURCHASE · NO SUBSCRIPTION", { parent: typeL, x: 120, baseline: 360 });
    const head = type.headline({ parent: typeL, text: "$49.99 ", accent: "USD.", size: 160, x: 120, baseline: 540 });
    const sub = type.body("Lifetime updates. 30-day refund.", { parent: typeL, size: 32, weight: 400, color: type.C.muted, x: 120, baseline: 620 });

    let hair = null;
    const strands = [
      ["green", "R01"],
      ["blue", "R11"],
      ["red", "R10"],
      ["purple", "R12"],
      ["black", "R09"],
    ];

    return {
      sequences: [seq],
      setup() {
        const b = stageBox(head.accent, stage);
        hair = type.offerHairline({
          parent: typeL,
          x: b.x,
          y: hairlineY(head.accent, 540),
          width: b.w,
          strands: strands.map(([engine]) => ({ engine })),
        });
      },
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;

        const s = 1 + 0.05 * ease("sine.inOut", progress(t, T0, T1));
        const k = COVER * s;
        const dw = IMG_W * COVER;
        const dh = IMG_H * COVER;
        const x0 = (1920 - dw) / 2 + SHIFT;
        const y0 = (1080 - dh) / 2;
        const dx = ORIGIN[0] + (x0 - ORIGIN[0]) * s;
        const dy = ORIGIN[1] + (y0 - ORIGIN[1]) * s;
        c2d.fillStyle = "#050506";
        c2d.fillRect(0, 0, 1920, 1080);
        c2d.imageSmoothingEnabled = true;
        c2d.imageSmoothingQuality = "high";
        const img = seq.frames[0];
        c2d.drawImage(img, dx, dy, IMG_W * k, IMG_H * k);
        if (dx > 0) {
          // Mirror the wall into the uncovered strip on the left (seamless at the image edge).
          const sw = Math.ceil(dx / k) + 2;
          c2d.save();
          c2d.translate(dx, 0);
          c2d.scale(-1, 1);
          c2d.drawImage(img, 0, 0, sw, IMG_H, 0, dy, sw * k, IMG_H * k);
          c2d.restore();
        }

        // Glow follows the push.
        const gx = ORIGIN[0] + (UNDERGLOW.cx - ORIGIN[0]) * s;
        const gy = ORIGIN[1] + (UNDERGLOW.cy - ORIGIN[1]) * s;
        setStyle(glow, "left", px(gx - UNDERGLOW.w / 2));
        setStyle(glow, "top", px(gy - UNDERGLOW.h / 2));
        setStyle(glow, "transform", `scale(${s.toFixed(5)})`);
        setStyle(glow, "opacity", String(+(0.85 * (1 + 0.15 * Math.sin(TAU * 0.5 * (t - T0)))).toFixed(4)));

        setAlpha(brow, 1);
        setAlpha(head.el, 1);
        setAlpha(sub, fadeIn(t, 58.5));
        hair.render(t, strands.map(([, r]) => cues.cyclesAt(r, t)));
        grain.render(t);
      },
    };
  },
};
