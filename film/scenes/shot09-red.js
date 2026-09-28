// Shot 9, 24.00-28.00: Red. BBD in bar 13, HQ steps to Tape at 26.00 (switch 17 -> 0 over 420 ms,
// lit plate and _on knob sheets fade in with the lever). Camera pushes 0.9 -> 1.1 about the HQ
// switch over 25.40-26.00 and eases back over 26.50-27.50. Knobs and readouts do not move.
import { TOUR, TOUR_LAYOUT, buildTourShot } from "./part1-common.js";

const spec = TOUR[2];
const SWITCH = [713.2, 251.9]; // HQ switch centre, plate px (visual-assets 3.3, Red)
const LINES = ["TWO SOUND CORES PER ENGINE", "SAME KNOBS, DIFFERENT CORE"];
const LINES_T = 25.25;

export default {
  id: "shot09-red",
  t0: spec.t0,
  t1: spec.t1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util, type } = lib;
    const L = TOUR_LAYOUT;
    const P = L.plate;
    const hqT = cues.gesture(spec.render, "hq").t0;

    // Zoom about the switch: its screen point stays where it is at 0.9.
    const ax = P.x + SWITCH[0] * P.scale;
    const ay = P.y + SWITCH[1] * P.scale;
    const camera = (t) => {
      const s = t < 26.5 ? util.tweenAt(t, 25.4, 26.0, 0.9, 1.1, "sine.inOut") : util.tweenAt(t, 26.5, 27.5, 1.1, 0.9, "sine.inOut");
      return { x: ax - SWITCH[0] * s, y: ay - SWITCH[1] * s, scale: s };
    };

    const extras = (root) => {
      const pill = type.pill(["BBD", "TAPE"], { parent: root, x: L.col.x0, y: L.pill.y, w: L.pill.w, h: L.pill.h, size: 16, fill: type.HUE.red });
      // Dark backing so the pill reads cleanly where the pushed-in plate passes under it.
      pill.el.style.background = "rgba(5,5,6,0.85)";
      const lines = LINES.map((text, i) => type.mono(text, { parent: root, size: 15, color: type.C.lavender, x: L.col.cx, baseline: L.lines[i], align: "center" }));
      return {
        law: (t) => (t < hqT ? "STEP" : "WOW"),
        render(t) {
          pill.setActive(t < hqT ? 0 : 1, type.HUE.red);
          for (const n of lines) util.show(n, t >= LINES_T);
        },
      };
    };

    // While pushed in, the plate reaches under the bottom-left footnote: a low scrim keeps it legible.
    const scrimL = ctx.layer("scrim", 15);
    util.el("div", {
      parent: scrimL,
      style: { position: "absolute", left: "0px", top: "990px", width: "1920px", height: "90px", background: "linear-gradient(to bottom, rgba(5,5,6,0), rgba(5,5,6,0.8) 45%, rgba(5,5,6,0.8))" },
    });
    const shot = buildTourShot(ctx, spec, { camera, extras });
    return {
      render(t) {
        shot.render(t);
        const k = t >= spec.t0 && t < spec.t1 ? util.clamp((camera(t).scale - P.scale) / 0.2) : 0;
        util.show(scrimL, k > 0);
        util.setStyle(scrimL, "opacity", String(+k.toFixed(4)));
      },
    };
  },
};
