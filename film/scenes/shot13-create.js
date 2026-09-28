// Shot 13, 40.00-46.00: Create. The Create Review capture (1040x700, native size) at x 800-1840,
// y 190-890 as a window turning towards the type (perspective 2000 px, rotateY -6 to -3 deg) with a
// push 1.00 to 1.03. The capture is an <img> (no canvas), so the 3D transform is seek-safe.
// Left column x 96-720: headline, sub, footnote; the capture caption sits under the window.

import { inFrames, fadeIn, setAlpha, sceneGrain } from "./kit-late.js";

const T0 = 40.0;
const T1 = 46.0;
const WIN = { x: 800, y: 190, w: 1040, h: 700 };

export default {
  id: "shot13-create",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib } = ctx;
    const { type, util } = lib;
    const { el, setStyle, px, show, tweenAt, progress } = util;

    const winL = ctx.layer("window", 20);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [winL, typeL, grainL];

    // Window: rounded, 1 px hairline, product shadow (brand .shadow-product).
    const win = el("div", {
      parent: winL,
      style: {
        position: "absolute",
        left: px(WIN.x),
        top: px(WIN.y),
        width: px(WIN.w),
        height: px(WIN.h),
        borderRadius: "12px",
        overflow: "hidden",
        transformOrigin: "50% 50%",
        boxShadow: "0 30px 90px rgba(0,0,0,0.55), 0 0 0 1px rgba(184,140,255,0.06)",
        background: "#0c0d10",
      },
    });
    el("img", {
      parent: win,
      attrs: { src: "/art/site/product/create/review.webp", alt: "", draggable: "false" },
      style: { position: "absolute", left: "0px", top: "0px", width: px(WIN.w), height: px(WIN.h), display: "block" },
    });
    el("div", {
      parent: win,
      style: { position: "absolute", inset: "0", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.1)", pointerEvents: "none" },
    });

    const h1 = type.headline({ parent: typeL, text: "Build your own", size: 84, x: 96, baseline: 330 });
    const h2 = type.headline({ parent: typeL, text: "in ", accent: "Create.", size: 84, x: 96, baseline: 420 });

    const caption = type.mono("INTERFACE CAPTURE FROM CHOROBOROS 1.0.5", {
      parent: typeL,
      size: 13,
      weight: 600,
      color: "rgba(246,244,239,0.45)",
      tracking: 0.14,
      x: WIN.x + WIN.w / 2,
      baseline: 920,
      align: "center",
    });

    // Sub, set at 22ch as three short lines.
    const sub = ["Choose one or two cores.", "Modify recipes.", "Add artwork."].map((line, i) =>
      type.body(line, { parent: typeL, size: 28, weight: 400, color: type.C.muted, x: 96, baseline: 500 + 40 * i }),
    );

    const foot = ["INCLUDED WITH AN ACTIVE 30-DAY TRIAL", "OR A PAID LICENCE."].map((line, i) =>
      type.mono(line, { parent: typeL, size: 15, weight: 600, color: type.C.muted, tracking: 0.12, x: 96, baseline: 712 + 24 * i }),
    );

    return {
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;

        const u = progress(t, T0, T1);
        const rot = tweenAt(u, 0, 1, -6, -3, "sine.inOut");
        const s = tweenAt(u, 0, 1, 1.0, 1.03, "sine.inOut");
        setStyle(win, "transform", `perspective(2000px) rotateY(${rot.toFixed(4)}deg) scale(${s.toFixed(5)})`);

        setAlpha(h1.el, 1);
        setAlpha(h2.el, 1);
        setAlpha(caption, fadeIn(t, 40.25));
        const subA = fadeIn(t, 40.75);
        for (const n of sub) setAlpha(n, subA);
        const footA = fadeIn(t, 42.0);
        for (const n of foot) setAlpha(n, footA);
        grain.render(t);
      },
    };
  },
};
