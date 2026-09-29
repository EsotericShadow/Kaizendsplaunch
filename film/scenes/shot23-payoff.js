// Shot 23, 70.00-74.00: payoff. The dot opens into the moving ellipse of the guitar (scope 560 px at
// (1390, 470), #f6f4ef, R01 at Mix 45%; bigger than the treatment's 360 px so the payoff reads as
// the film's biggest trace), fading out 74.00-74.50 as the end card's plate fades in. The scope's
// graticule fades up round the dot over 70.00-70.60, so the cut from the silence stays one dot.
// Share-card tagline at x 120, Fraunces 112 px, baselines 300 / 420 / 540: "Great sound" fades in at
// 70.00 (0.25 s); the italic "doesn't" / "sit still." cut in at 70.50 and move by ChorusType SINE
// (Green, R01) to the last frame. A 1400 px purple glow fades in behind the type, breathing +-15% at
// 0.60 Hz until the end-card hold, where it settles.
// The tagline and glow run on through the end card (declared overlap to 86.00). At 74.00-74.75 the
// tagline moves up and shrinks to 88 px (baselines 250 / 344 / 439) to make room for the CTA row.

import { inFrames, fadeIn, setAlpha, radialGlow } from "./kit-late.js";

const T0 = 70.0;
const T1 = 74.0;
const END = 86.0;
const SCOPE = { cx: 1390, cy: 470, size: 560 };
const BASE = [300, 420, 540];
const SHRINK = { t0: 74.0, t1: 74.75, scale: 88 / 112, dy: 250 - 300 };
const GRAT_IN = [70.0, 0.6];

export default {
  id: "shot23-payoff",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues } = ctx;
    const { type, util } = lib;
    const { el, show, setStyle, TAU, clamp, tweenAt } = util;

    const glowL = ctx.layer("glow", 5);
    const scopeL = ctx.layer("scope", 20);
    const typeL = ctx.layer("tagline", 40);

    const glow = radialGlow(glowL, { cx: 430, cy: 400, w: 1400 });

    const scope = lib.createScope(scopeL, { cx: SCOPE.cx, cy: SCOPE.cy, size: SCOPE.size, disc: null, color: "#f6f4ef", stem: "gtr" });
    const dot = el("div", {
      parent: scopeL,
      style: { position: "absolute", left: "1388.5px", top: "468.5px", width: "3px", height: "3px", borderRadius: "50%", background: "#f6f4ef" },
    });

    // Tagline block; its transform only ever holds text (no canvas).
    const block = el("div", {
      parent: typeL,
      style: { position: "absolute", left: "0px", top: "0px", width: "1920px", height: "1080px", transformOrigin: `120px ${BASE[0]}px` },
    });
    const l1 = type.headline({ parent: block, text: "Great sound", size: 112, x: 120, baseline: BASE[0] });
    const l2 = type.headline({ parent: block, accent: "doesn’t", size: 112, x: 120, baseline: BASE[1] });
    const l3 = type.headline({ parent: block, accent: "sit still.", size: 112, x: 120, baseline: BASE[2] });
    const ct = [l2, l3].map((l) => lib.createChorusType(l.accent, { law: "SINE", engine: "green" }));

    return {
      render(t) {
        const on = inFrames(t, T0, END);
        show(glowL, on);
        show(typeL, on);
        const scopeOn = inFrames(t, T0, 74.5);
        show(scopeL, scopeOn);
        if (!on) return;

        // Glow: in over 1 s, breathing at 0.60 Hz, settling to still by the 78.00 hold.
        const breath = 0.15 * clamp((78.0 - t) / 1.0) * Math.sin(TAU * 0.6 * (t - T0));
        setStyle(glow, "opacity", String(+(0.85 * (1 + breath) * fadeIn(t, T0, 1.0)).toFixed(4)));

        if (scopeOn) {
          const a = t < T1 ? 1 : clamp(1 - (t - T1) / 0.5);
          const g = util.ease("sine.inOut", clamp((t - GRAT_IN[0]) / GRAT_IN[1]));
          scope.draw(t, { alpha: a, gratAlpha: g, render: "R01" });
          setAlpha(dot, a);
        }

        const u = clamp((t - SHRINK.t0) / (SHRINK.t1 - SHRINK.t0));
        const s = tweenAt(u, 0, 1, 1, SHRINK.scale, "sine.inOut");
        const dy = tweenAt(u, 0, 1, 0, SHRINK.dy, "sine.inOut");
        setStyle(block, "transform", u > 0 ? `translate(0px, ${dy.toFixed(3)}px) scale(${s.toFixed(5)})` : "");

        setAlpha(l1.el, fadeIn(t, T0, 0.25));
        const italic = fadeIn(t, 70.5, 0);
        setAlpha(l2.el, italic);
        setAlpha(l3.el, italic);
        if (italic > 0) {
          const st = cues.settingsAt("R01", t);
          for (const c of ct) c.render(t, st);
        }
      },
    };
  },
};
