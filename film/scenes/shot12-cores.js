// Shot 12, 36.00-40.00: 17 sound cores. The 17 core icons on a ring (radius 330 around (960, 470)),
// grouped by family clockwise from 12 o'clock. The ten engine cores pop on 16ths from 36.00, the
// seven Create cores on 16ths from 37.25 with a lavender halo, one per bell. Lagrange 5th, the core
// the pad plays through, glows green. The ring turns clockwise at 0.02 Hz; the glow breathes at 0.10 Hz.

import { inFrames, fadeIn, setAlpha, snap, radialGlow, sceneGrain } from "./kit-late.js";

const T0 = 36.0;
const T1 = 40.0;
const CX = 960;
const CY = 470;
const RADIUS = 330;
const ICON = 96;
const FAMILIES = [
  ["lagrange3", "lagrange5", "cubic", "thiran"],
  ["bbd", "tape"],
  ["phase_warp", "orbit", "flange", "barber_pole"],
  ["ensemble", "multi_rate", "granular", "formant"],
  ["linear", "stochastic", "phase_vocoder"],
];
const ENGINE_CORES = new Set(["lagrange3", "lagrange5", "cubic", "thiran", "bbd", "tape", "phase_warp", "orbit", "linear", "ensemble"]);
const FAMILY_GAP = 0.4; // extra spacing between families, in icon steps
const SIXTEENTH = 0.125;

export default {
  id: "shot12-cores",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib } = ctx;
    const { type, util } = lib;
    const { el, setStyle, px, TAU, show, clamp } = util;

    const glowL = ctx.layer("glow", 5);
    const ringL = ctx.layer("ring", 20);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [glowL, ringL, typeL, grainL];

    const glow = radialGlow(glowL, { cx: CX, cy: CY, w: 1300 });

    // Ring order and angles (family gaps included).
    const order = [];
    FAMILIES.forEach((fam, gi) => fam.forEach((name) => order.push({ name, gi })));
    const units = order.length + FAMILY_GAP * FAMILIES.length;
    let engineN = 0;
    let createN = 0;
    const icons = order.map(({ name, gi }, i) => {
      const angle = (TAU * (i + FAMILY_GAP * gi)) / units;
      const engine = ENGINE_CORES.has(name);
      const pop = engine ? snap(T0 + SIXTEENTH * engineN++) : snap(37.25 + SIXTEENTH * createN++);
      const box = el("div", {
        parent: ringL,
        style: { position: "absolute", width: px(ICON), height: px(ICON), left: "0px", top: "0px" },
      });
      if (!engine) {
        // Lavender halo behind a Create core.
        el("div", {
          parent: box,
          style: {
            position: "absolute",
            left: px(-22),
            top: px(-22),
            width: px(ICON + 44),
            height: px(ICON + 44),
            borderRadius: "50%",
            background: "radial-gradient(closest-side, rgba(208,189,255,0.30) 0%, rgba(208,189,255,0.10) 60%, rgba(208,189,255,0) 100%)",
          },
        });
      }
      const img = el("img", {
        parent: box,
        attrs: { src: `/art/rc/core_icons/${name}.png`, alt: "", draggable: "false" },
        style: { position: "absolute", left: "0px", top: "0px", width: px(ICON), height: px(ICON) },
      });
      if (name === "lagrange5") img.style.filter = "drop-shadow(0 0 18px #7ee0a0)";
      else if (!engine) img.style.filter = "drop-shadow(0 0 8px rgba(208,189,255,0.55))";
      return { name, angle, pop, box, engine };
    });
    const l5 = icons.find((i) => i.name === "lagrange5");

    // Centre: 17 over SOUND CORES.
    const seventeen = el("div", {
      parent: typeL,
      text: "17",
      style: { font: `600 200px ${type.FONT.display}`, letterSpacing: "-0.02em", fontFeatureSettings: '"ss01", "ss02"', color: type.C.fg },
    });
    type.placeText(seventeen, { x: CX, baseline: 522, align: "center" });
    const cores = type.mono("SOUND CORES", { parent: typeL, size: 20, weight: 600, color: type.C.purple, tracking: 0.3, x: CX, baseline: 566, align: "center" });

    // Tag next to the lagrange5 icon, which it follows round the ring.
    const tag = type.mono("NOW PLAYING · LAGRANGE 5TH", { parent: typeL, size: 18, weight: 600, color: "#7ee0a0", tracking: 0.14, x: 0, baseline: 0 });

    const bottom = type.body("The ten cores inside the prebuilt engines, plus seven more.", {
      parent: typeL,
      size: 28,
      weight: 400,
      color: type.C.muted,
      x: CX,
      baseline: 1000,
      align: "center",
    });

    const iconPos = (angle, t) => {
      const a = angle + TAU * 0.02 * (t - T0);
      return [CX + RADIUS * Math.sin(a), CY - RADIUS * Math.cos(a)];
    };

    let tagTop0 = 0; // top of the tag for baseline 0, known once fonts have loaded
    return {
      setup() {
        tagTop0 = parseFloat(tag.style.top) || 0;
      },
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;

        setStyle(glow, "opacity", String(+(0.85 * (1 + 0.15 * Math.sin(TAU * 0.1 * (t - T0)))).toFixed(4)));

        for (const ic of icons) {
          const vis = t >= ic.pop - 1e-6;
          setStyle(ic.box, "visibility", vis ? "" : "hidden");
          if (!vis) continue;
          const [x, y] = iconPos(ic.angle, t);
          // 30 ms scale-in from the popping frame.
          const u = clamp((t - ic.pop) / 0.03);
          const s = 0.5 + 0.5 * (1 - (1 - u) * (1 - u));
          setStyle(ic.box, "left", px(x - ICON / 2));
          setStyle(ic.box, "top", px(y - ICON / 2));
          setStyle(ic.box, "transform", s >= 1 ? "" : `scale(${+s.toFixed(4)})`);
        }

        setAlpha(seventeen, 1);
        setAlpha(cores, 1);

        const tagA = fadeIn(t, 36.5, 0.2);
        setAlpha(tag, tagA);
        if (tagA > 0) {
          const [x, y] = iconPos(l5.angle, t);
          setStyle(tag, "left", px(x + ICON / 2 + 14));
          setStyle(tag, "top", px(y + 5 + tagTop0));
        }
        // Hard cut at 37.50: the line has exactly its 2.5 s reading minimum (10 words), so no fade.
        setAlpha(bottom, fadeIn(t, 37.5, 0));
        grain.render(t);
      },
    };
  },
};
