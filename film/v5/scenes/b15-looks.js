// S15 26 custom looks (TREATMENT section 2, ACT IV). Bars 29-30, 45.810 to 49.053 (frames 2748-2942).
//
// The wall: a 4 x 7 grid of the 26 look thumbnails (/art/site/themes/<id>-thumb.webp), tiles
// 200 x 100, 16 px gaps, x 72 to 920, y 560 to 1356. It builds ONE ROW PER HIT: rows 1-6 on the six
// bar-29 hits, row 7 (2 tiles) on the fill's first snare (f2844). Each row drops 24 px over 4
// frames (power3.out). On f2858 the wall collapses (4 frames) into one large look (<id>-on.webp,
// 880 x 440, centred at y 960: 18.7 % of the frame, under the PSE area limit), which swaps with a
// hard CUT and a PUNCH on each remaining fill hit. The six looks are ordered by mean luminance, so
// neighbours differ by less than 0.10 (PSE; no flash: fills cut). The sound does not change.
// Type: "26 custom / looks." and the two Inter lines on a 60 % black band, from f2748.

import { hitAt, inF, ev, fitter, headLine, bodyLine, applyStamp, band, vis } from "./b00-common.js";

const LOOKS = [
  "anime-cyber-blue", "anime-purple", "anime-red", "arcade", "brushed-silver", "chrome", "circuit",
  "concrete", "deep-space", "ember", "ember-ouroboros", "glacier", "hazard", "ink", "midnight",
  "moonbase", "moss", "nineties-paint", "noir", "obsidian", "porcelain", "rust-bloom", "sakura",
  "sandstone", "tidal", "velvet",
];
// The large-look sequence, by mean luminance (0.143, 0.163, 0.187, 0.218, 0.252, 0.270).
const SWAP = ["deep-space", "anime-red", "anime-cyber-blue", "moss", "hazard", "arcade"];
const TILE = { w: 200, h: 100, gap: 16, x0: 72, y0: 560 };

export default {
  id: "b15-looks",
  t0: 2748 / 60,
  t1: 2943 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, motion: M } = ctx;
    const { show, el, setStyle, px, ease, clamp } = lib.util;
    const cut = hitAt(b, 45.8106);
    const next = hitAt(b, 49.0538);
    const F0 = cut.frame;
    const F1 = next.frame;
    const rows = [45.8106, 46.216, 46.4179, 46.6219, 46.832, 47.0268, 47.4142].map((x) => hitAt(b, x));
    const collapse = hitAt(b, 47.6369);
    const swaps = [47.8347, 48.0422, 48.2358, 48.4462, 48.6485].map((x) => hitAt(b, x));
    ev(this, b, cut, "cut", "cymbal + kick 45.811 (the wall, row 1)");
    ev(this, b, cut, "stamp", "cymbal + kick 45.811 (headline)");
    rows.slice(1).forEach((h, i) => ev(this, b, h, "stamp", `${h.piece} ${h.tm} (row ${i + 2})`));
    ev(this, b, collapse, "cut", "floor tom 47.637 (the wall collapses into one look)");
    swaps.forEach((h, i) => ev(this, b, h, "cut", `${h.piece} ${h.tm} (look ${i + 2})`));

    const WL = ctx.layer("wall", 12);
    const tiles = LOOKS.map((id, i) => {
      const r = Math.floor(i / 4);
      const c = i % 4;
      const x = TILE.x0 + c * (TILE.w + TILE.gap);
      const y = TILE.y0 + r * (TILE.h + TILE.gap);
      const n = el("img", { parent: WL, attrs: { src: `/art/site/themes/${id}-thumb.webp`, alt: "", draggable: "false" }, style: { position: "absolute", left: px(x), top: px(y), width: px(TILE.w), height: px(TILE.h), borderRadius: "8px", boxShadow: "0 8px 24px rgba(0,0,0,0.5)" } });
      return { n, r, x, y };
    });
    const LL = ctx.layer("look", 14);
    const looks = SWAP.map((id) => el("img", { parent: LL, attrs: { src: `/art/site/themes/${id}-on.webp`, alt: "", draggable: "false" }, style: { position: "absolute", left: px(100), top: px(960 - 220), width: px(880), height: px(440), borderRadius: "14px", boxShadow: "0 30px 90px rgba(0,0,0,0.6)", transformOrigin: "50% 50%", visibility: "hidden" } }));

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const h1 = headLine(TL, fit, { text: "26 custom", size: 104, baseline: 380 });
    const h2 = headLine(TL, fit, { text: "", accent: "looks.", size: 104, baseline: 490 });
    const bnd = band(TL, 1382, 1486, 0.6);
    setStyle(bnd, "zIndex", "-1");
    const b1 = bodyLine(TL, fit, "A custom look changes what Choroboros", { size: 40, baseline: 1420 });
    const b2 = bodyLine(TL, fit, "looks like, not how it sounds.", { size: 40, baseline: 1470 });

    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [WL, LL, TL]) show(l, on);
        if (!on) return;
        const f = b.frameAt(t);

        // Wall rows, then the collapse into the centre (4 frames).
        const dc = f - collapse.frame;
        const cu = dc < 0 ? 0 : ease("power3.in", clamp((dc + 1) / 4));
        show(WL, dc < 4);
        for (const tl of tiles) {
          const h = rows[tl.r];
          const df = f - h.frame;
          vis(tl.n, df >= 0 && dc < 4);
          if (df < 0 || dc >= 4) continue;
          const drop = df >= 4 ? 0 : -24 * (1 - ease("power3.out", (df + 1) / 4));
          const dx = (540 - (tl.x + TILE.w / 2)) * cu;
          const dy = (960 - (tl.y + TILE.h / 2)) * cu + drop;
          setStyle(tl.n, "transform", dx || dy || cu ? `translate(${px(dx)}, ${px(dy)}) scale(${+(1 - 0.6 * cu).toFixed(4)})` : "");
          setStyle(tl.n, "opacity", df === 0 ? "0.6" : cu > 0 ? String(+(1 - cu).toFixed(4)) : "");
        }

        // The large look: grows out of the collapse, then hard cuts with a PUNCH on each fill hit.
        const k = dc < 0 ? -1 : b.stepIndex(swaps, t) + 1;
        const grow = dc < 0 ? 0 : ease("expo.out", clamp((dc + 1) / 4));
        const pu = M.punch(t, swaps, { amp: M.MOTION.punch.plate });
        looks.forEach((n, i) => {
          vis(n, i === k);
          if (i === k) setStyle(n, "transform", `scale(${+((0.45 + 0.55 * grow) * pu).toFixed(5)})`);
        });

        const st = M.stamp(t, cut);
        for (const n of [h1.el, h2.el, b1, b2]) applyStamp(n, st);
        vis(bnd, true);
      },
    };
  },
};
