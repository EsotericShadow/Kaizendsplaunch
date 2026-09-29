// END CARD (v5, TREATMENT 4.3 main and 7.4 TikTok): the portrait end card with the Buy button.
//
//   const card = createEndcard(layer, { variant: "main" | "tiktok", demos, beats, span: [t0, t1],
//                                       topLayer, trialCta: true });
//   return { preload: card.preload, sequences: [], setup: card.setup,
//            render(t) { card.render(t, { build: [t5181, t5229, t5278] }) } };
//
// layer:     the card's layer (z about 40, above the picture and the flash).
// topLayer:  a layer ABOVE the grain (z 850; the chip is 900) for the format row, so no layer draws
//            over the VST tile. Without it the row goes in `layer` (and the grain covers it).
// span:      the composition times the card is on screen, to prepare the plate's frames.
// build:     the build times (composition s; frame-exact, hard cuts only). Main: [name, plate, scope,
//            Buy, trial button, status] / [offer, URL] / [format row, legal]. TikTok: [lockup, name,
//            plate, scope, Buy] / [offer, URL, platform line] / [format row, legal]. One entry
//            builds everything at once.
// scale:     an optional card scale (the TikTok slam: 0.95 -> 1.00 with a 1.01 overshoot) about the
//            frame centre. It scales the DOM group only: the scope canvas is moved, never
//            transformed, and the format row and the legal line are never scaled.
// card.buttonRect -> { x, y, w, h } of the Buy button (for a flash mask).
//
// The plate is the live Green plate, lit, with the heard values (demos.plateState: M13 in the main
// film, T06 in the TikTok) and the readouts' 60 ms digit flip. The name is chorustype SINE Green
// (live), the scope the heard guitar band, and the Buy button's hairline (G3b) runs at the heard
// Rate, 0.62 Hz: one cycle per bar. Nothing else moves. The VST Compatible logo is the supplied PNG
// in an <img>: never scaled after layout, blurred, flashed, tinted, cropped or covered.

import { el, setStyle, px } from "./util.js";
import * as type from "./type.js";
import { createPlate } from "./plate.js";
import { createScope } from "./scope.js";
import { createChorusType } from "./chorustype.js";
import { getBeats } from "./beats.js";
import { COLOR } from "./portrait.js";

export const VST_URL = "/art/site/brand/platforms/vst-compatible.png";
export const LEGAL = "VST is a trademark of Steinberg Media Technologies GmbH, registered in Europe and other countries. AAX is a trademark of Avid Technology, Inc. macOS and Audio Units are trademarks of Apple Inc.";
export const BUY = { x: 72, y: 1000, w: 856, h: 140 };

const LAYOUT = {
  main: {
    name: 440,
    status: { text: "Available now for macOS.", baseline: 505, size: 44 },
    plate: { x: 72, y: 548, scale: 0.5 },
    scope: { cx: 855, cy: 760, size: 170 },
    secondary: { x: 72, y: 1160, w: 548, h: 62 },
    offer: [{ text: "$49.99 USD · Green and Purple free", baseline: 1290, size: 40 }],
    url: 1350,
    formats: 1392,
    platform: null,
    lockup: null,
    hairline: 1150,
  },
  tiktok: {
    name: 440,
    status: null,
    plate: { x: 72, y: 470, scale: 0.6 },
    scope: { cx: 855, cy: 560, size: 170 },
    secondary: null,
    offer: [
      { text: "$49.99 USD one-time purchase", baseline: 1196, size: 36 },
      { text: "Green and Purple free · 30-day free trial", baseline: 1242, size: 36 },
    ],
    url: 1300,
    formats: 1330,
    platform: { text: "Available now for macOS.", baseline: 1490, size: 36 },
    lockup: { x: 72, top: 228, size: 48 },
    hairline: 1150,
  },
};

/** The format row: five 160 x 100 tiles (gap 16) with mono 24 px labels. Returns { el, vst }. */
export function formatRowPortrait({ parent, x0 = 72, y = 1392, tileW = 160, tileH = 100, gap = 16, vstUrl = VST_URL } = {}) {
  const row = el("div", { parent, cls: "v5-formats", style: { position: "absolute", left: "0px", top: "0px" } });
  const tile = (i) =>
    el("div", {
      parent: row,
      style: { position: "absolute", left: px(x0 + i * (tileW + gap)), top: px(y), width: px(tileW), height: px(tileH), boxSizing: "border-box", background: COLOR.surface, border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px" },
    });
  const label = (p, text, top) =>
    el("div", { parent: p, text, style: { font: `600 24px ${type.FONT.mono}`, position: "absolute", left: "0px", width: "100%", top: px(top), textAlign: "center", color: COLOR.muted, lineHeight: "28px", whiteSpace: "pre" } });
  const mark = (p, text) =>
    el("div", { parent: p, text, style: { font: `500 44px ${type.FONT.body}`, position: "absolute", left: "0px", width: "100%", top: "0px", height: px(tileH - 2), lineHeight: px(tileH - 2), textAlign: "center", letterSpacing: "-0.04em", color: "#e8e3ed" } });
  const glyph = (p, name) => {
    const g = type.lucide(name, { size: 40, stroke: 1.25, color: "#e8e3ed" });
    Object.assign(g.style, { position: "absolute", left: px((tileW - 40) / 2), top: "14px" });
    p.appendChild(g);
  };
  const t1 = tile(0);
  // The official VST Compatible logo exactly as supplied: an <img>, no filter, opacity, blend or transform.
  // 61 x 57 keeps the logo's own aspect (474 x 443) to 0.02 %: a uniform scale, whole pixels.
  const vh = 57;
  const vw = 61;
  const vst = el("img", { parent: t1, attrs: { src: vstUrl, alt: "VST Compatible", draggable: "false" } });
  Object.assign(vst.style, { position: "absolute", height: px(vh), width: px(vw), left: px(Math.round((tileW - vw) / 2)), top: "7px" });
  label(t1, "VST®3", 66);
  mark(tile(1), "AU");
  mark(tile(2), "AAX");
  const t4 = tile(3);
  glyph(t4, "appWindow");
  label(t4, "Standalone", 62);
  const t5 = tile(4);
  glyph(t5, "monitor");
  label(t5, "macOS", 62);
  return { el: row, vst };
}

export class Endcard {
  constructor(layer, { variant = "main", demos, beats = null, span = null, topLayer = null, trialCta = true, engine = "green" } = {}) {
    this.variant = variant;
    this.L = LAYOUT[variant];
    if (!this.L) throw new Error(`endcard: unknown variant ${variant}`);
    this.demos = demos;
    this.beats = beats;
    this.engine = engine;
    const L = this.L;
    this.buttonRect = { ...BUY };

    // The DOM group (scalable) and the fixed nodes (scope canvas, format row, legal).
    this.group = el("div", { parent: layer, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "540px 960px" } });
    const g = this.group;
    this.parts = [[], [], []]; // nodes per build step

    if (L.lockup) {
      // The lockup's DSP row hangs below the KAIZEN baseline; at baseline 290 it touched the 150 px
      // name, so the box starts at y 228: the KAIZEN glyph box (which rises ~6 px above the box) clears the
      // platform's top zone at y 220 (KAIZEN baseline ~268).
      const lk = type.lockup({ parent: g, x: L.lockup.x, y: L.lockup.top, size: L.lockup.size });
      this.parts[0].push(lk);
    }
    const name = type.headline({ text: "", accent: "Choroboros.", size: 150, parent: g, x: 72, baseline: L.name, color: COLOR.fg, accentColor: COLOR.fg });
    this.name = name;
    this.ct = createChorusType(name.accent, { law: "SINE", engine, dryColor: COLOR.fg });
    this.parts[0].push(name.el);
    if (L.status) this.parts[0].push(type.body(L.status.text, { parent: g, size: L.status.size, weight: 500, color: COLOR.muted, x: 72, baseline: L.status.baseline }));

    this.plate = createPlate(engine, { parent: g, scale: L.plate.scale, x: L.plate.x, y: L.plate.y, header: true, hiRes: false });
    if (span && demos) this.plate.require(demos.statesIn(span[0], span[1], null, 8));
    this.parts[0].push(this.plate.el);

    this.scopeLayer = el("div", { parent: layer, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px" } });
    this.scope = createScope(this.scopeLayer, { cx: L.scope.cx, cy: L.scope.cy, size: L.scope.size, stem: "guitar", color: COLOR.hue[engine], disc: "rgba(5,5,6,0.72)", labelSize: 11 });

    const buy = type.siteButton("Buy Choroboros", { parent: g, primary: true, x: BUY.x, y: BUY.y, height: BUY.h, fontSize: 56, radius: 20 });
    Object.assign(buy.style, { width: px(BUY.w), justifyContent: "center", borderRadius: "20px" });
    this.buy = buy;
    this.parts[0].push(buy);
    this.hairline = type.offerHairline({ parent: g, x: BUY.x + 28, y: L.hairline, width: BUY.w - 56, strands: [{ engine }], amp: 3, wavelength: 140, alpha: 0.8 });
    this.parts[0].push(this.hairline.el);
    if (L.secondary && trialCta) {
      const s = L.secondary;
      const b2 = type.siteButton("Start your 30-day free trial", { parent: g, primary: false, x: s.x, y: s.y, height: s.h, fontSize: 36, radius: 14 });
      Object.assign(b2.style, { width: px(s.w), justifyContent: "center", fontWeight: "500" });
      this.parts[0].push(b2);
    }

    for (const o of L.offer) this.parts[1].push(type.body(o.text, { parent: g, size: o.size, weight: 500, color: COLOR.fg, x: 72, baseline: o.baseline }));
    const url = type.body("kaizendsp.com/choroboros", { parent: g, size: 44, weight: 600, color: COLOR.fg, x: 72, baseline: L.url });
    Object.assign(url.style, { textDecoration: "underline", textDecorationColor: COLOR.purple, textDecorationThickness: "3px", textUnderlineOffset: "10px" });
    this.parts[1].push(url);
    if (L.platform) this.parts[1].push(type.body(L.platform.text, { parent: g, size: L.platform.size, weight: 500, color: COLOR.muted, x: 72, baseline: L.platform.baseline }));

    const fixed = topLayer || layer;
    this.formats = formatRowPortrait({ parent: fixed, y: L.formats });
    this.parts[2].push(this.formats.el);
    const legal = el("div", {
      parent: layer,
      text: LEGAL,
      attrs: { "data-bleed": "" },
      style: { position: "absolute", left: "72px", top: "1556px", width: "860px", font: `400 22px ${type.FONT.body}`, lineHeight: "27px", color: "rgba(246,244,239,0.5)", whiteSpace: "normal" },
    });
    this.parts[2].push(legal);
    this.preload = [VST_URL];
  }

  setup() {}

  /** Draw the card at t. build: the build times (1 or 3 entries). scale: the TikTok slam. */
  render(t, { build = [0], scale = 1 } = {}) {
    const b = this.beats || getBeats();
    const f = b.frameAt(t);
    const steps = build.length === 1 ? [build[0], build[0], build[0]] : build;
    const on = steps.map((h) => f >= (typeof h === "number" ? b.onsetFrame(h) : h.frame));
    this.parts.forEach((nodes, i) => nodes.forEach((n) => setStyle(n, "visibility", on[i] ? "" : "hidden")));
    setStyle(this.group, "transform", scale === 1 ? "" : `scale(${+scale.toFixed(5)})`);
    const L = this.L;
    // The scope canvas follows the scaled layout by position only.
    const sx = 540 + (L.scope.cx - 540) * scale;
    const sy = 960 + (L.scope.cy - 960) * scale;
    this.scope.moveTo(sx, sy);
    setStyle(this.scopeLayer, "visibility", on[0] ? "" : "hidden");
    if (!on[0]) return;
    const d = this.demos;
    const st = d ? d.plateState(t) : null;
    if (st) {
      this.plate.setState(st);
      this.plate.setGrade(d.grade(this.engine, t));
    }
    const s = d ? d.settingsAt(t) : null;
    if (s) this.ct.render(t, s);
    this.scope.draw(t, { stem: "guitar", color: COLOR.hue[this.engine] });
    this.hairline.render(t, [d ? d.cyclesAt(t) : 0]);
  }
}

export function createEndcard(layer, opts) {
  return new Endcard(layer, opts);
}
