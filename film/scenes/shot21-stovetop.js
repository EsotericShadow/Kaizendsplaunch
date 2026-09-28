// Shot 21, 67.00-69.50: Stovetop. The underpass plate darkened to 15% with a 12% burner glow.
// The cold, warm and hot stills, uncropped and unaltered, at 0.45 scale (540x485) at x 1180-1720,
// y 330-815, stepping on the beats (67.00, 67.50, 68.00) with 4-frame cross-fades. At this size the
// "v0.1.0" strings render under 5 px. Stovetop's own palette and Sedgwick Ave Display headline.

import { inFrames, setAlpha, sceneGrain, radialGlow } from "./kit-late.js";

const T0 = 67.0;
const T1 = 69.5;
const XFADE = 4 / 60;
const STILL = { x: 1180, y: 330, w: 540, h: 1077 * 0.45 };
const STEPS = [
  ["cold", 67.0],
  ["warm", 67.5],
  ["hot", 68.0],
];
const FONT_URL = "/art/site/stovetop/SedgwickAveDisplay-Regular.ttf";

export default {
  id: "shot21-stovetop",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib } = ctx;
    const { type, util } = lib;
    const { el, px, show, clamp } = util;

    // Stovetop's display face (OFL, shipped with the site), loaded before text is placed.
    const face = new FontFace("Sedgwick Ave Display", `url("${FONT_URL}")`);
    await face.load();
    document.fonts.add(face);

    const bgL = ctx.layer("background", 10);
    const stillL = ctx.layer("stills", 20);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [bgL, stillL, typeL, grainL];

    el("img", {
      parent: bgL,
      attrs: { src: "/art/site/stovetop/underpass.jpg", alt: "", draggable: "false" },
      style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "1080px", filter: "brightness(0.15)" },
    });
    radialGlow(bgL, { cx: STILL.x + STILL.w / 2, cy: STILL.y + STILL.h * 0.72, w: 1100, h: 800, color: [255, 122, 46], a: [0.12, 0.03] });

    const stills = STEPS.map(([name, at]) => ({
      at,
      img: el("img", {
        parent: stillL,
        attrs: { src: `/art/site/stovetop/stovetop-${name}.jpg`, alt: "", draggable: "false" },
        style: { position: "absolute", left: px(STILL.x), top: px(STILL.y), width: px(STILL.w), height: px(STILL.h), boxShadow: "0 30px 90px rgba(0,0,0,0.55)" },
      }),
    }));

    const brow = type.eyebrow("STOVETOP · IN DEVELOPMENT", { parent: typeL, color: "#ff7a2e", x: 120, baseline: 400 });
    // Two graffiti lines, tilted -2 deg together about the left edge.
    const tilt = el("div", {
      parent: typeL,
      style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "1080px", transform: "rotate(-2deg)", transformOrigin: "120px 570px" },
    });
    const lines = ["Heats up", "as you play."].map((text, i) => {
      const n = el("div", {
        parent: tilt,
        text,
        style: {
          font: `400 88px "Sedgwick Ave Display", cursive`,
          color: "#f1e4cc",
          textShadow: "4px 4px 0 #51321f",
        },
      });
      type.placeText(n, { x: 120, baseline: 520 + 100 * i });
      return n;
    });

    return {
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        // Each later still fades in over the one below it, from its beat.
        stills.forEach((s, i) => setAlpha(s.img, i === 0 ? 1 : clamp((t - s.at) / XFADE)));
        setAlpha(brow, 1);
        for (const n of lines) setAlpha(n, 1);
        grain.render(t);
      },
    };
  },
};
