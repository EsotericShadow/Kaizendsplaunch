// Shots 24-25, 74.00-86.00: the end card builds, then holds to the hard cut at 86.00.
// 74.00-74.50 the Green rebuild (Green (a), R01, HQ unlit) fades in at 0.6 scale at x 970-1810,
// y 250-685 and drifts per G2. Then on the beats: URL 74.50; CTA buttons (hard cut) and the
// availability line 75.00; facts 75.50; lockup and top-right eyebrow 76.00; the format row by hard
// cut at 76.00; footer and hairline 76.50; legal 77.00. The primary button gets one slow lavender
// ring pulse at 78.00 (the final chord), then everything holds; only the tagline's ChorusType
// (shot 23 module) and the plate drift move.
// Left column, re-spaced so the CTA row is the first thing after the tagline (which shrinks to
// 88 px, baselines 250 / 344 / 439, in the shot 23 module): buttons y 488-564 (76 px tall, the
// primary's label 30 px), URL baseline 642, availability 692, facts 736; the format row stays at
// y 800-930 in the top layer, above grain and glow, untouched. Footer band: hairline 956, footer
// (26 px) baseline 1000 on the left, the legal small print (14 px) as two right-aligned lines
// beside it, so it stays inside the 1800 px margin at the bigger size.

import { inFrames, fadeIn, setAlpha } from "./kit-late.js";

const T0 = 74.0;
const T1 = 86.0;
const BTN = { y: 488, h: 76, gap: 16, radius: 14, padX: 32, primary: 30, secondary: 28 };
const COL = { url: 642, avail: 692, facts: 736 };
const FOOT = { hair: 956, footer: 1000, legal: [990, 1012] };
const PULSE = { t: 78.0, len: 1.3, grow: 11 }; // stays inside the 16 px gap to the trial button

export default {
  id: "shot24-endcard",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues, stage } = ctx;
    const { type, util } = lib;
    const { el, show, setStyle, px } = util;

    const plateL = ctx.layer("plate", 20);
    const typeL = ctx.layer("type", 40);
    const topL = ctx.layer("formats", 100);

    const plate = lib.createPlate("green", { parent: plateL, scale: 0.6, x: 970, y: 250 });
    plate.requireRender(cues, "R01", T0, T1);

    const lockup = type.lockup({ parent: typeL, x: 120, y: 70, size: 44 });
    const topRight = type.eyebrow("CHOROBOROS · CHORUS PLUGIN", { parent: typeL, size: 18, x: 1800, baseline: 96, align: "right" });

    // CTA row, the site's own buttons and labels: "Buy Choroboros" is the dominant action (cream
    // primary, 30 px label, arrow); the outline trial button shares its height.
    const row = el("div", {
      parent: typeL,
      style: { position: "absolute", left: "120px", top: px(BTN.y), display: "flex", gap: px(BTN.gap), alignItems: "center" },
    });
    const mkBtn = (label, primary) => {
      const b = type.siteButton(label, { parent: row, primary, height: BTN.h, fontSize: primary ? BTN.primary : BTN.secondary, padX: BTN.padX, radius: BTN.radius });
      Object.assign(b.style, { position: "relative", left: "0px", top: "0px" });
      return b;
    };
    const buy = mkBtn("Buy Choroboros", true);
    mkBtn("Start your 30-day free trial", false);
    // Ring pulse around the primary button.
    const pulse = el("div", {
      parent: typeL,
      style: { position: "absolute", border: "1px solid #d0bdff", pointerEvents: "none", boxSizing: "border-box" },
    });

    const url = el("div", {
      parent: typeL,
      text: "kaizendsp.com/choroboros",
      style: {
        font: `600 44px ${type.FONT.body}`,
        color: type.C.fg,
        textDecorationLine: "underline",
        textDecorationColor: type.C.purple,
        textDecorationThickness: "2px",
        textUnderlineOffset: "10px",
      },
    });
    type.placeText(url, { x: 120, baseline: COL.url });
    const avail = type.body("Available now for macOS · Apple Silicon + Intel", { parent: typeL, size: 26, weight: 400, color: type.C.muted, x: 120, baseline: COL.avail });
    const facts = type.mono("GREEN AND PURPLE FREE · 30-DAY TRIAL · $49.99 USD ONE-TIME", {
      parent: typeL,
      size: 18,
      weight: 600,
      color: "rgba(246,244,239,0.8)",
      tracking: 0.12,
      x: 120,
      baseline: COL.facts,
    });

    const hair = el("div", { parent: typeL, style: { position: "absolute", left: "120px", top: px(FOOT.hair), width: "1680px", height: "1px", background: "rgba(255,255,255,0.1)" } });
    const footer = type.body("Five prebuilt engines · 17 sound cores · Version 1.0.5", { parent: typeL, size: 26, weight: 400, color: type.C.muted, x: 120, baseline: FOOT.footer });
    // One text block set in two lines (a line break between sentences; the words are verbatim).
    const legal = type.body(
      "VST is a trademark of Steinberg Media Technologies GmbH, registered in Europe and other countries. AAX is a trademark of Avid Technology, Inc.\nmacOS and Audio Units are trademarks of Apple Inc. © 2026 Kaizen Strategic AI Inc. All rights reserved. Made in Canada.",
      { parent: typeL, size: 14, weight: 400, color: "rgba(246,244,239,0.5)" },
    );
    legal.style.textAlign = "right";
    type.placeText(legal, { x: 1800, baseline: FOOT.legal[0], align: "right", lineHeight: (FOOT.legal[1] - FOOT.legal[0]) / 14 });

    // Format row: its own top layer, placed by hard cut, never faded, drifted or transformed.
    type.formatRow({ parent: topL, x0: 120, y: 800, gap: 20 });

    let buyBox = null;
    return {
      setup() {
        const s = stage.getBoundingClientRect();
        const r = buy.getBoundingClientRect();
        buyBox = { x: r.left - s.left, y: r.top - s.top, w: r.width, h: r.height };
      },
      render(t) {
        const on = inFrames(t, T0, T1);
        show(plateL, on);
        show(typeL, on);
        show(topL, inFrames(t, 76.0, T1));
        if (!on) return;

        const st = cues.plateStateAt("R01", t);
        plate.place({ dx: lib.driftPx(st) });
        plate.setState(st);
        const pa = fadeIn(t, T0, 0.5);
        setStyle(plate.el, "opacity", pa >= 1 ? "" : String(+pa.toFixed(4)));

        setAlpha(url, fadeIn(t, 74.5));
        setAlpha(row, fadeIn(t, 75.0, 0));
        setAlpha(avail, fadeIn(t, 75.0));
        setAlpha(facts, fadeIn(t, 75.5));
        setAlpha(lockup, fadeIn(t, 76.0));
        setAlpha(topRight, fadeIn(t, 76.0));
        const fa = fadeIn(t, 76.5);
        setAlpha(footer, fa);
        setAlpha(hair, fa);
        setAlpha(legal, fadeIn(t, 77.0));

        // One slow 1 px lavender ring pulse from the primary button at 78.00 (the final chord),
        // easing out from the button's edge and fading; then everything holds still.
        const u = (t - PULSE.t) / PULSE.len;
        if (u >= 0 && u < 1 && buyBox) {
          const grow = 2 + PULSE.grow * (1 - (1 - u) * (1 - u));
          setStyle(pulse, "visibility", "");
          setStyle(pulse, "left", px(buyBox.x - grow));
          setStyle(pulse, "top", px(buyBox.y - grow));
          setStyle(pulse, "width", px(buyBox.w + 2 * grow));
          setStyle(pulse, "height", px(buyBox.h + 2 * grow));
          setStyle(pulse, "borderRadius", px(BTN.radius + grow));
          setStyle(pulse, "opacity", String(+(0.95 * Math.min(1, u * 8) * (1 - u)).toFixed(4)));
        } else setStyle(pulse, "visibility", "hidden");
      },
    };
  },
};
