// Shot 14, 46.00-49.85: 26 custom looks, then the build. The 26 look previews (600x300 wall tiles)
// at 340x170 in rows of 7, 6, 7, 6 (tops y 250, 440, 630, 820, 20 px gaps), wider than the frame
// and drifting in alternating directions at 30 px/s. Every tile starts on -off; a lighting wave
// crosses left to right 46.25-47.75 and each tile cross-fades to -on in 0.15 s as it passes.
// The four looks awaiting provenance stay in the outer columns. Hard cut to black at 49.85.

import { inFrames, fadeIn, setAlpha, sceneGrain } from "./kit-late.js";

const T0 = 46.0;
const T1 = 49.85;
const TW = 340;
const TH = 170;
const GAP = 20;
const ROW_Y = [250, 440, 630, 820];
const DRIFT = 30; // px/s
const WAVE_T0 = 46.25;
const WAVE_T1 = 47.75;
const FADE = 0.15;

// Rows of 7, 6, 7, 6. Cyber Blue, Purple Samurai, Red Samurai and 90s Paper Cup sit in the outermost
// visible columns (never near the centre two).
const ROWS = [
  ["anime-red", "concrete", "sandstone", "chrome", "ink", "glacier", "moss"],
  ["ember", "velvet", "obsidian", "porcelain", "tidal", "anime-cyber-blue"],
  ["arcade", "nineties-paint", "deep-space", "midnight", "sakura", "noir", "circuit"],
  ["anime-purple", "brushed-silver", "moonbase", "hazard", "rust-bloom", "ember-ouroboros"],
];

export default {
  id: "shot14-looks",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib } = ctx;
    const { type, util } = lib;
    const { el, setStyle, px, show, clamp } = util;

    const wallL = ctx.layer("wall", 20);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [wallL, typeL, grainL];

    const tiles = [];
    ROWS.forEach((row, r) => {
      const n = row.length;
      row.forEach((id, i) => {
        const cx0 = 960 + (i - (n - 1) / 2) * (TW + GAP);
        const box = el("div", {
          parent: wallL,
          style: { position: "absolute", left: "0px", top: px(ROW_Y[r]), width: px(TW), height: px(TH) },
        });
        const mk = (state) =>
          el("img", {
            parent: box,
            attrs: { src: `/art/site/themes/wall/${id}-${state}.webp`, alt: "", draggable: "false" },
            style: { position: "absolute", left: "0px", top: "0px", width: px(TW), height: px(TH) },
          });
        mk("off");
        const onImg = mk("on");
        tiles.push({ id, r, cx0, box, onImg, dir: r % 2 === 0 ? 1 : -1 });
      });
    });

    // Bottom scrim y 980-1080 under the line.
    el("div", {
      parent: typeL,
      style: { position: "absolute", left: "0px", top: "980px", width: "1920px", height: "100px", background: "linear-gradient(180deg, rgba(5,5,6,0) 0%, rgba(5,5,6,0.92) 45%, #050506 100%)" },
    });

    const brow = type.eyebrow("ARTWORK PACKS FOR CREATE", { parent: typeL, x: 960, baseline: 110, align: "center" });
    const head = type.headline({ parent: typeL, text: "26 custom ", accent: "looks.", size: 84, x: 960, baseline: 200, align: "center" });
    const bottom = type.body("A custom look changes what Choroboros looks like, not how it sounds.", {
      parent: typeL,
      size: 28,
      weight: 400,
      color: "rgba(246,244,239,0.85)",
      x: 960,
      baseline: 1036,
      align: "center",
    });

    // Wave front: from the left edge of the leftmost visible tile to past the right edge.
    const waveX0 = -TW / 2;
    const waveX1 = 1920 + TW / 2;
    const waveSpeed = (waveX1 - waveX0) / (WAVE_T1 - WAVE_T0);

    return {
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        const dt = t - T0;
        const wave = waveX0 + waveSpeed * (t - WAVE_T0);
        for (const tile of tiles) {
          const cx = tile.cx0 + tile.dir * DRIFT * dt;
          setStyle(tile.box, "left", px(cx - TW / 2));
          const a = t < WAVE_T0 ? 0 : clamp((wave - cx) / (waveSpeed * FADE));
          setAlpha(tile.onImg, a);
        }
        setAlpha(brow, 1);
        setAlpha(head.el, 1);
        setAlpha(bottom, fadeIn(t, 46.5));
        grain.render(t);
      },
    };
  },
};
