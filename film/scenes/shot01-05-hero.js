// Shots 1, 3 and 5: the 3D hero move (public/film/hero-frames/desktop, 97 frames) on one canvas.
//   Shot 1 (0.00-2.00): frame 0 frozen, grade saturate 0.15, brightness 0.85, contrast 1.05.
//   Shot 3 (3.00-7.85): f = 96 (t - 3) / 9, blended neighbours, full colour, zoom 1.00 -> 1.04.
//   Shot 5 (8.00-12.00): same formula (frames 53 -> 96), zoom 1.04 -> 1.08, bloom at 8.00.
// Top scrim #050506 80% -> 0 over y 0-300 in all three. Zooms happen inside the draw call, about a
// point high in the frame so the unit's top edge stays clear of the title type.

const SHOTS = [
  { t0: 0, t1: 2, frame: () => 0, scale: () => 1, saturate: 0.15 },
  { t0: 3, t1: 7.85, frame: (t) => (96 * (t - 3)) / 9, scale: (t) => 1 + (0.04 * (t - 3)) / 4.85, saturate: 1 },
  { t0: 8, t1: 12, frame: (t) => (96 * (t - 3)) / 9, scale: (t) => 1.04 + (0.04 * (t - 8)) / 4, saturate: 1 },
];
const GRADE = { brightness: 0.85, contrast: 1.05 };
const BLOOM_T = 8.0;
const BLOOM_LEN = 0.4;

export default {
  id: "shot01-05-hero",
  t0: 0,
  t1: 12,
  build(ctx) {
    const { lib } = ctx;
    const { util } = lib;
    const layer = ctx.layer("hero", 0);
    const hero = lib.createHero(layer, { width: 1920, height: 1080 });
    util.el("div", {
      parent: layer,
      style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "300px", background: "linear-gradient(to bottom, rgba(5,5,6,0.8), rgba(5,5,6,0))" },
    });
    // One of the film's two blooms: radial #eaffe9 at 20%, decaying over 0.4 s.
    const bloom = util.el("div", {
      parent: layer,
      style: {
        position: "absolute",
        left: "0px",
        top: "0px",
        width: "1920px",
        height: "1080px",
        background: "radial-gradient(ellipse 1300px 900px at 960px 600px, rgba(234,255,233,0.2), rgba(234,255,233,0.08) 45%, rgba(234,255,233,0) 100%)",
        mixBlendMode: "screen",
        visibility: "hidden",
      },
    });

    return {
      sequences: [hero.seq],
      render(t) {
        const shot = SHOTS.find((s) => t >= s.t0 && t < s.t1);
        util.show(layer, !!shot);
        if (!shot) return;
        hero.draw(shot.frame(t), { scale: shot.scale(t), originX: 0.5, originY: 0.4, grade: { saturate: shot.saturate, ...GRADE } });
        const u = (t - BLOOM_T) / BLOOM_LEN;
        const a = u >= 0 && u < 1 ? (1 - u) * (1 - u) : 0;
        util.show(bloom, a > 0);
        util.setStyle(bloom, "opacity", String(+a.toFixed(4)));
      },
    };
  },
};
