// Shot 5, 8.00-12.00: title over the hero move. Top-left at x 96: eyebrow from 8.25; H1 "Meet
// Choroboros." with the accent in ChorusType SINE (Green, R01), revealed by a 0.6 s mask from 8.50;
// sub from 9.25. All type fades out over 11.75-12.00.
const T0 = 8;
const T1 = 12;
const EYEBROW_T = 8.25;
const H1 = { t: 8.5, len: 0.6, size: 112, baseline: 232 };
const SUB_T = 9.25;
const FADE = [11.75, 12];

export default {
  id: "shot05-title",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util, type } = lib;
    const layer = ctx.layer("type", 30);
    const eyebrow = type.eyebrow("KAIZEN DSP · FIRST RELEASE", { parent: layer, x: 96, baseline: 110 });
    // The mask: a clip box around the H1 line; the line rises into it from below.
    const mask = util.el("div", { parent: layer, style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "1080px" } });
    const clipTop = H1.baseline - 1.05 * H1.size;
    const clipBottom = H1.baseline + 0.3 * H1.size;
    const h1 = type.headline({ parent: mask, text: "Meet ", accent: "Choroboros.", size: H1.size, x: 96, baseline: H1.baseline });
    const ct = lib.createChorusType(h1.accent, { law: "SINE", engine: "green" });
    const sub = type.body("A chorus and modulation plugin for macOS.", { parent: layer, size: 32, weight: 500, color: type.C.muted, x: 96, baseline: 292 });
    const rise = 1.05 * H1.size;

    return {
      render(t) {
        const on = t >= T0 && t < T1;
        util.show(layer, on);
        if (!on) return;
        const fade = t < FADE[0] ? 1 : util.clamp((FADE[1] - t) / (FADE[1] - FADE[0]));
        util.setStyle(layer, "opacity", fade >= 1 ? "" : String(+fade.toFixed(4)));
        util.show(eyebrow, t >= EYEBROW_T);
        util.show(sub, t >= SUB_T);
        util.show(mask, t >= H1.t);
        const u = (t - H1.t) / H1.len;
        if (u < 1) {
          const e = util.ease("power2.out", u);
          util.setStyle(mask, "clipPath", `inset(${util.px(clipTop)} 0px ${util.px(1080 - clipBottom)} 0px)`);
          util.setStyle(h1.el, "transform", `translateY(${util.px((1 - e) * rise)})`);
        } else {
          util.setStyle(mask, "clipPath", "");
          util.setStyle(h1.el, "transform", "");
        }
        ct.render(t, cues.settingsAt("R01", t));
      },
    };
  },
};
