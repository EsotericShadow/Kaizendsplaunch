// S14 Create (TREATMENT section 2, ACT IV). Bars 25-28, 39.324 to 45.810 (frames 2359-2747).
//
// f2359 (kick 39.324): the seven Create-only glyphs flare white, the ring collapses (8 frames,
// expo.in) into the white Create canvas plate (scale 0.72, x 540 centred, y 640 to 1250). The
// canvas ASSEMBLES on the kicks: each part drops in 40 px (6 frames, power4.out) with a PUNCH:
// RATE 39.324, DEPTH 39.730, OFFSET 40.135, WIDTH 40.540, then (the other kicks, so an event lands
// at least every 2 beats) COLOR 41.352, MIX 41.752 and the HQ lever 42.163. Readouts #303030 (the
// white canvas's own). The canvas is on screen but not heard: graded s 0.35 / b 0.75.
// f2554 (kick 42.567): CUT to the real Create capture core-recipe.webp (936 px wide, centred at
// y 900); the white plate shrinks into zone S (scale 0.40, y 1250 to 1590, picture only, behind a
// band that keeps the lines readable). f2650 (floor + kick 44.171): CUT to review.webp. Kicks PUNCH
// the captures at 1.02; the kick + rack hits step a push-in (SWEEP, +4 % each, anchored on the capture's top edge so it
// never grows into the headline).
// Type: "Build your own / engines / in Create." (96 px) STAMP on f2359; the Inter lines on 40.934,
// replaced by the mono trial lines on 42.974. Heard: Black (M05).

import { hitAt, inF, ev, fitter, headLine, bodyLine, monoLine, applyStamp, applyOn, coreRing, band, vis } from "./b00-common.js";

const WHITE_STATE = { rate: 0.45, depth: 30, offset: 60, width: 100, color: 50, mix: 40, hq: 1 };
const DROP = 40; // px on screen

export default {
  id: "b14-create",
  t0: 2359 / 60,
  t1: 2748 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, el, setStyle, px, ease, clamp } = lib.util;
    const cut = hitAt(b, 39.3241);
    const next = hitAt(b, 45.8106);
    const F0 = cut.frame;
    const F1 = next.frame;
    const drops = [
      ["rate", 39.3241],
      ["depth", 39.7296],
      ["offset", 40.1349],
      ["width", 40.5404],
      ["color", 41.352],
      ["mix", 41.7519],
      ["hq", 42.1629],
    ].map(([part, x]) => ({ part, h: hitAt(b, x) }));
    const lines1 = hitAt(b, 40.9342);
    const capA = hitAt(b, 42.5674);
    const lines2 = hitAt(b, 42.9736);
    const capB = hitAt(b, 44.1712);
    const pushA = [43.3757, 43.7843].map((x) => hitAt(b, x));
    const pushB = [44.5944, 44.9983, 45.4053].map((x) => hitAt(b, x));
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);

    ev(this, b, cut, "cut", "kick 39.324 (ring collapses into the Create canvas)");
    ev(this, b, cut, "stamp", "kick 39.324 (headline)");
    drops.forEach((d) => ev(this, b, d.h, "slam", `${d.h.piece} ${d.h.tm} (${d.part} drops in)`));
    ev(this, b, lines1, "text", "floor + kick 40.934 (Choose one or two cores.)");
    ev(this, b, capA, "cut", "kick + rack 42.567 (core-recipe capture)");
    ev(this, b, lines2, "text", "kick 42.974 (trial / licence lines)");
    pushA.forEach((h) => ev(this, b, h, "sweep", `${h.piece} ${h.tm} (push-in)`));
    ev(this, b, capB, "cut", "floor + kick 44.171 (review capture)");
    pushB.forEach((h) => ev(this, b, h, "sweep", `${h.piece} ${h.tm} (push-in)`));

    // The ring (as S13 left it: all ten prebuilt cores lit) collapses into the canvas.
    const RL = ctx.layer("ring", 22);
    const ring = coreRing(RL);

    // The white Create canvas.
    const PL = ctx.layer("plate", 12);
    const plate = lib.createPlate("white", { parent: PL, scale: 0.72, header: true, hiRes: false });
    plate.require(WHITE_STATE);
    plate.setState(WHITE_STATE);
    const partNodes = {
      rate: [plate.knobs.rate.off.node.parentElement, plate.readouts.rate.node],
      depth: [plate.knobs.depth.off.node.parentElement, plate.readouts.depth.node],
      offset: [plate.knobs.offset.off.node.parentElement, plate.readouts.offset.node],
      width: [plate.knobs.width.off.node.parentElement, plate.readouts.width.node],
      color: [plate.thumb, plate.readouts.color.node].filter(Boolean),
      mix: [plate.mix.node, plate.readouts.mix.node],
      hq: [plate.sw[0].node.parentElement],
    };

    // The captures (plain images: a transform is safe).
    const CL = ctx.layer("capture", 16);
    const cap = (src, w, h) => {
      const H = (936 / w) * h;
      const n = el("img", { parent: CL, attrs: { src, alt: "", draggable: "false" }, style: { position: "absolute", left: px(72), top: px(900 - H / 2), width: px(936), height: px(H), borderRadius: "14px", boxShadow: "0 24px 80px rgba(0,0,0,0.6)", transformOrigin: "50% 0%" } });
      return n;
    };
    const imgA = cap("/art/site/product/create/core-recipe.webp", 1151, 768);
    const imgB = cap("/art/site/product/create/review.webp", 1040, 700);

    // Type.
    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const h1 = headLine(TL, fit, { text: "Build your own", size: 96, baseline: 380 });
    const h2 = headLine(TL, fit, { text: "engines", size: 96, baseline: 480 });
    const h3 = headLine(TL, fit, { text: "in ", accent: "Create.", size: 96, baseline: 580 });
    const bandL = band(TL, 1336, 1528, 0.9);
    setStyle(bandL, "zIndex", "-1");
    const b1 = bodyLine(TL, fit, "Choose one or two cores.", { size: 40, baseline: 1380 });
    const b2 = bodyLine(TL, fit, "Modify recipes. Pair them with artwork.", { size: 40, baseline: 1430 });
    const m1 = monoLine(TL, fit, "Included with an active 30-day trial", { size: 28, baseline: 1470, color: "#f6f4ef" });
    const m2 = monoLine(TL, fit, "or a paid licence.", { size: 28, baseline: 1510, color: "#f6f4ef" });

    const PU = M.MOTION.punch.plate * M.MOTION.tomGroove;
    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [RL, PL, CL, TL]) show(l, on);
        if (!on) return;
        const f = b.frameAt(t);

        // Ring: flare and collapse over 8 frames (expo.in), then gone.
        const dfc = f - cut.frame;
        const rOn = dfc < 8;
        show(RL, rOn);
        if (rOn) ring.render({ lit: new Array(10).fill(1), flare: 1, collapse: ease("expo.in", (dfc + 1) / 8) });

        // Plate: place, punch, then the shrink into zone S on the capture cut.
        const pu = M.punch(t, kicks, { amp: PU });
        const sh = f >= capA.frame ? ease("power4.out", clamp((f - capA.frame + 1) / 6)) : 0;
        const scale = (0.72 + (0.4 - 0.72) * sh) * (sh > 0 ? 1 : pu);
        const cy = 945 + (1420 - 945) * sh;
        plate.place({ cx: 540, cy, scale });
        plate.setGrade(demos.grade("white", t));
        for (const d of drops) {
          const df = f - d.h.frame;
          const u = df < 0 ? 0 : ease("power4.out", clamp((df + 1) / 6));
          for (const n of partNodes[d.part]) {
            setStyle(n, "visibility", df < 0 ? "hidden" : "");
            setStyle(n, "opacity", df < 0 ? "0" : df >= 1 ? "" : "0.5");
            setStyle(n, "transform", u >= 1 ? "" : `translateY(${px((-DROP / 0.72) * (1 - u))})`);
          }
        }

        // Captures.
        const k = M.punch(t, kicks, { amp: 0.02 });
        const showA = f >= capA.frame && f < capB.frame;
        const showB = f >= capB.frame;
        vis(imgA, showA);
        vis(imgB, showB);
        if (showA) setStyle(imgA, "transform", `scale(${+((1 + 0.04 * M.sweep(t, pushA)) * k).toFixed(5)})`);
        if (showB) setStyle(imgB, "transform", `scale(${+((1 + 0.04 * M.sweep(t, pushB)) * k).toFixed(5)})`);

        // Type.
        const st = M.stamp(t, cut);
        for (const n of [h1.el, h2.el, h3.el]) applyStamp(n, st);
        const firstLines = f >= lines1.frame && f < lines2.frame;
        vis(b1, firstLines);
        vis(b2, firstLines);
        applyOn(b, t, m1, lines2);
        applyOn(b, t, m2, lines2);
        vis(bandL, f >= capA.frame);
      },
    };
  },
};
