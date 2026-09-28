// Shot 19, 62.00-64.50: Fold. The Fold clip (1080x640) at 1.25 scale, centred (960, 615), as a
// floating window: radius 14 (clipped inside the canvas draw), product shadow, green glow 12%.
// 62.00-62.25 frozen on clip time 1.00 at 15% saturation; from 62.25 the clip plays 1.00-3.25 at 1x
// in full colour. The window cuts before the clip's orange CLIP label.
// This module also owns the family eyebrow "MORE FROM KAIZEN DSP", held 62.00-69.50 over shots
// 19-21 (a declared overlap into shots 20 and 21).

import { inFrames, setAlpha, sceneGrain, roundRectPath } from "./kit-late.js";

const T0 = 62.0;
const T1 = 64.5;
const FAMILY_T1 = 69.5;
const WIN = { cx: 960, cy: 615, w: 1350, h: 800, r: 14 };
const GREEN = "#64e28b";

export default {
  id: "shot19-fold",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues } = ctx;
    const { type, util } = lib;
    const { el, px, show } = util;

    const winL = ctx.layer("window", 20);
    const typeL = ctx.layer("type", 40);
    const familyL = ctx.layer("family", 45);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [winL, typeL, grainL];

    const sec = cues.section("fold");
    const clipIn = sec?.clip_in ?? 1.0;
    const clipAt = sec?.clip_at ?? 62.25;
    const clip = await lib.clipSequence("fold", { canvas: null });

    const x = WIN.cx - WIN.w / 2;
    const y = WIN.cy - WIN.h / 2;
    // Shadow and glow on an untransformed box under the canvas (no purple ring: family palette).
    el("div", {
      parent: winL,
      style: {
        position: "absolute",
        left: px(x),
        top: px(y),
        width: px(WIN.w),
        height: px(WIN.h),
        borderRadius: px(WIN.r),
        background: "#0b0d0c",
        boxShadow: `0 30px 90px rgba(0,0,0,0.55), 0 0 90px rgba(100,226,139,0.12)`,
      },
    });
    const canvas = el("canvas", { parent: winL, style: { position: "absolute", left: px(x), top: px(y), width: px(WIN.w), height: px(WIN.h) } });
    canvas.width = WIN.w;
    canvas.height = WIN.h;
    const c2d = canvas.getContext("2d");

    const brow = type.eyebrow("FOLD · COMING SOON", { parent: typeL, color: GREEN, x: 120, baseline: 118 });
    const head = type.headline({ parent: typeL, text: "A free spectral ", accent: "stereo shaper.", accentColor: GREEN, size: 60, x: 120, baseline: 185 });

    const family = type.eyebrow("MORE FROM KAIZEN DSP", { parent: familyL, size: 16, color: "rgba(246,244,239,0.5)", x: 120, baseline: 80 });

    const draw = (tc, saturate) => {
      const i = Math.round((tc - clip.meta.start) * clip.meta.fps);
      const img = clip.seq.frames[Math.max(0, Math.min(clip.seq.count - 1, i))];
      c2d.save();
      c2d.clearRect(0, 0, WIN.w, WIN.h);
      roundRectPath(c2d, 0, 0, WIN.w, WIN.h, WIN.r);
      c2d.clip();
      c2d.filter = saturate < 1 ? `saturate(${saturate})` : "none";
      c2d.imageSmoothingEnabled = true;
      c2d.imageSmoothingQuality = "high";
      c2d.drawImage(img, 0, 0, WIN.w, WIN.h);
      c2d.restore();
    };

    return {
      sequences: [clip.seq],
      render(t) {
        show(familyL, inFrames(t, T0, FAMILY_T1));
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        const playing = inFrames(t, clipAt, T1);
        draw(playing ? clipIn + (t - clipAt) : clipIn, playing ? 1 : 0.15);
        setAlpha(brow, 1);
        setAlpha(head.el, 1);
        setAlpha(family, 1);
        grain.render(t);
      },
    };
  },
};
