// Shot 20, 64.50-67.00: Echolalia. The Time + Sound preview cropped to x 0-1600, y 96-530 (engine
// selector, phosphor display, TIME knob and readout; the STUDY header, EST. 2023 panel and the
// burned-in caption stay outside the crop), at 1.1 scale centred (960, 640), radius 12, amber glow
// 10%. 64.50-64.75 frozen on clip time 9.50 at 15% saturation; from 64.75 it plays 9.50-11.75.

import { inFrames, setAlpha, sceneGrain, roundRectPath } from "./kit-late.js";

const T0 = 64.5;
const T1 = 67.0;
const CROP = { x: 0, y: 96, w: 1600, h: 434 };
const SCALE = 1.1;
const W = CROP.w * SCALE;
const H = CROP.h * SCALE;
const CX = 960;
const CY = 640;
const R = 12;

export default {
  id: "shot20-echolalia",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues } = ctx;
    const { type, util } = lib;
    const { el, px, show } = util;

    const winL = ctx.layer("window", 20);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [winL, typeL, grainL];

    const sec = cues.section("echolalia");
    const clipIn = sec?.clip_in ?? 9.5;
    const clipAt = sec?.clip_at ?? 64.75;
    const clip = await lib.clipSequence("echolalia", { canvas: null });

    const x = Math.round(CX - W / 2);
    const y = Math.round(CY - H / 2);
    const cw = Math.round(W);
    const ch = Math.round(H);
    el("div", {
      parent: winL,
      style: {
        position: "absolute",
        left: px(x),
        top: px(y),
        width: px(cw),
        height: px(ch),
        borderRadius: px(R),
        background: "#080706",
        boxShadow: "0 30px 90px rgba(0,0,0,0.55), 0 0 90px rgba(240,160,74,0.10)",
      },
    });
    const canvas = el("canvas", { parent: winL, style: { position: "absolute", left: px(x), top: px(y), width: px(cw), height: px(ch) } });
    canvas.width = cw;
    canvas.height = ch;
    const c2d = canvas.getContext("2d");

    const brow = type.eyebrow("ECHOLALIA · DELAY + REVERB · COMING SOON", { parent: typeL, color: "#f0a04a", x: 120, baseline: 118 });
    const head = type.headline({
      parent: typeL,
      text: "Echoes that change ",
      accent: "as they return.",
      size: 60,
      color: "#f4ecdc",
      accentColor: "#d8a066",
      x: 120,
      baseline: 185,
    });

    const draw = (tc, saturate) => {
      const i = Math.round((tc - clip.meta.start) * clip.meta.fps);
      const img = clip.seq.frames[Math.max(0, Math.min(clip.seq.count - 1, i))];
      // Source pixels are square after extraction (setsar=1); scale the crop to the canvas.
      const sx = img.naturalWidth / 1600;
      const sy = img.naturalHeight / 812;
      c2d.save();
      c2d.clearRect(0, 0, cw, ch);
      roundRectPath(c2d, 0, 0, cw, ch, R);
      c2d.clip();
      c2d.filter = saturate < 1 ? `saturate(${saturate})` : "none";
      c2d.imageSmoothingEnabled = true;
      c2d.imageSmoothingQuality = "high";
      c2d.drawImage(img, CROP.x * sx, CROP.y * sy, CROP.w * sx, CROP.h * sy, 0, 0, cw, ch);
      c2d.restore();
    };

    return {
      sequences: [clip.seq],
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        const playing = inFrames(t, clipAt, T1);
        draw(playing ? clipIn + (t - clipAt) : clipIn, playing ? 1 : 0.15);
        setAlpha(brow, 1);
        setAlpha(head.el, 1);
        grain.render(t);
      },
    };
  },
};
