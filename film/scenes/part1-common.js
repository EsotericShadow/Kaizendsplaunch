// Shared layout, copy and builders for shots 1-11 (0.00-36.00). Not a scene: the shot modules
// import it. Positions, sizes and copy follow docs/brief/treatment.md sections 3, 5 and 6.
// Single-line text is placed by baseline ("y" in the treatment), pills and boxes by their top.

export const MIX_TURN = 2.25;

// Shots 1-3: bottom-left scope group and the bottom-right footnote.
export const OPEN = {
  scope: { cx: 200, cy: 872, size: 160 },
  label: { x: 200, baseline: 975 },
  pill: { x: 80, y: 1000, w: 240, h: 44 },
  footnote: { x: 1824, baseline: 1036 },
};

export const TAGLINE = { text: "Great sound ", accent: "doesn’t sit still.", size: 96, x: 960, baseline: 200 };

/** The full centred tagline. Shot 1 hides the accent, shot 3 shows it moving. */
export function makeTagline(lib, parent) {
  const { text, accent, size, x, baseline } = TAGLINE;
  return lib.type.headline({ parent, text, accent, size, x, baseline, align: "center" });
}

// Tour layout (shots 7-11).
export const TOUR_T0 = 16;
export const TOUR_T1 = 36;
export const TOUR_LAYOUT = {
  plate: { x: 96, y: 350, scale: 0.9 },
  row: 96, // eyebrow / FREE pill baseline
  headline: { x: 96, size: 104, baseline: 214 },
  best: { baseline: 290 },
  col: { x0: 1440, x1: 1824, cx: 1632 },
  scope: { cx: 1632, cy: 520, size: 300 },
  caption: { size: 72, baseline: 790 },
  pill: { y: 850, w: 384, h: 56 },
  lines: [950, 978],
  dots: { x0: 1560, x1: 1800, cy: 100, size: 14 },
  footnote: { x: 96, baseline: 1040 },
};

// JetBrains Mono advances 0.6 em, so mono widths are exact without measuring.
export const monoWidth = (text, size, tracking) => text.length * 0.6 * size + Math.max(0, text.length - 1) * tracking * size;

export const BEST_FOR = { text: "BEST FOR", size: 14, tracking: 0.2 };
export const BEST_LINE_X = TOUR_LAYOUT.headline.x + monoWidth(BEST_FOR.text, BEST_FOR.size, BEST_FOR.tracking) + 18;

// FREE pill: mono 12 px, 0.2em tracking, padding from type.tag().
const TAG = { size: 12, tracking: 0.2 };
const tagWidth = (text) => text.length * (0.6 + TAG.tracking) * TAG.size + 0.75 * TAG.size + 0.55 * TAG.size + 2;
const tagBaselineShift = 0.45 * TAG.size + 1; // padding-top + border above the text line

export const TOUR = [
  { engine: "green", t0: 16, t1: 20, render: "R02", free: true, eyebrow: "LAGRANGE 3RD CORE", head: "Green. ", accent: "Sways.", law: "SINE", bestFor: "Warm acoustic and synth sends", caption: "Depth.", ring: "depth", gesture: "depth" },
  { engine: "blue", t0: 20, t1: 24, render: "R03", free: false, eyebrow: "CUBIC CORE", head: "Blue. ", accent: "Widens.", law: "SINE", bestFor: "Clean width on vocals and buses", caption: "Offset.", ring: "offset", gesture: "offset" },
  { engine: "red", t0: 24, t1: 28, render: "R04", free: false, eyebrow: null, head: "Red. ", accent: "Wavers.", law: "STEP", bestFor: "BBD AND TAPE. VINTAGE INSTABILITY.", caption: null, ring: "hq", gesture: "hq" },
  { engine: "purple", t0: 28, t1: 32, render: "R05", free: true, eyebrow: "ORBIT CORE", head: "Purple. ", accent: "Orbits.", law: "ORBIT", bestFor: "STRANGE TEXTURES, SOUND DESIGN, WEIRDNESS", caption: "Rate.", ring: "rate", gesture: "rate" },
  { engine: "black", t0: 32, t1: 36, render: "R06", free: false, eyebrow: "ENSEMBLE CORE", head: "Black. ", accent: "Multiplies.", law: "SINE", bestFor: "Dense ensembles. Low CPU.", caption: "Color.", ring: "color", gesture: "color" },
];

export const tourAt = (t) => TOUR.find((s) => t >= s.t0 && t < s.t1) || null;

/**
 * A scope's disc and 1 px outline drawn once into a canvas under the scope. As CSS (border-radius),
 * the circle's edge was rasterised differently from frame to frame wherever another element's
 * repaint rect cut across it (the shot 2 plate's filter, Red's pushed-in plate): a seek-history
 * dependence of up to 10/255. A canvas bitmap does not change with the repaint rect.
 */
export function scopeBackdrop(lib, parent, { cx, cy, size, fill = "rgba(5,5,6,0.6)", stroke = "rgba(246,244,239,0.14)" }) {
  const { el, px } = lib.util;
  const c = el("canvas", { parent });
  Object.assign(c.style, { position: "absolute", left: px(cx - size / 2), top: px(cy - size / 2), width: px(size), height: px(size) });
  const dpr = window.devicePixelRatio || 1;
  c.width = Math.round(size * dpr);
  c.height = Math.round(size * dpr);
  const g = c.getContext("2d");
  g.scale(dpr, dpr);
  g.beginPath();
  g.arc(size / 2, size / 2, size / 2, 0, 2 * Math.PI);
  g.fillStyle = fill;
  g.fill();
  g.beginPath();
  g.arc(size / 2, size / 2, size / 2 - 0.5, 0, 2 * Math.PI);
  g.lineWidth = 1;
  g.strokeStyle = stroke;
  g.stroke();
  return c;
}

/** Absolutely positioned full-frame box. */
export function box(lib, parent) {
  return lib.util.el("div", { parent, style: { position: "absolute", left: "0px", top: "0px", width: "100%", height: "100%" } });
}

/**
 * One copy of a tour shot's engine-specific type: FREE pill and eyebrow, headline with its
 * ChorusType accent, the Best-for line, the right-column caption, and Red's pill and lines.
 * Returns { el, render(t, settings) }.
 */
export function tourTypeCopy(lib, parent, spec, { gestureT0 = null, extras = null } = {}) {
  const { type, util } = lib;
  const L = TOUR_LAYOUT;
  const hue = type.HUE[spec.engine];
  const root = box(lib, parent);
  let x = L.headline.x;
  if (spec.free) {
    type.tag("FREE", { parent: root, color: hue, size: TAG.size, x, baseline: L.row - tagBaselineShift });
    x += tagWidth("FREE") + 16;
  }
  if (spec.eyebrow) type.eyebrow(spec.eyebrow, { parent: root, color: hue, x, baseline: L.row });
  const h = type.headline({ parent: root, text: spec.head, accent: spec.accent, size: L.headline.size, x: L.headline.x, baseline: L.headline.baseline });
  const ct = lib.createChorusType(h.accent, { law: spec.law, engine: spec.engine });
  type.body(spec.bestFor, { parent: root, size: 28, weight: 500, color: "rgba(246,244,239,0.85)", x: BEST_LINE_X, baseline: L.best.baseline });
  let caption = null;
  if (spec.caption) {
    caption = type.headline({ parent: root, accent: spec.caption, size: L.caption.size, x: L.col.cx, baseline: L.caption.baseline, align: "center" }).el;
  }
  const extra = extras ? extras(root) : null;
  return {
    el: root,
    ct,
    render(t, s) {
      if (extra && extra.law) ct.setLaw(extra.law(t));
      ct.render(t, s);
      if (caption) util.show(caption, gestureT0 != null && t >= gestureT0);
      if (extra) extra.render(t, s);
    },
  };
}

/**
 * A tour shot: plate and type as smear groups (G4), the gesture ring (G6), G2 drift, readouts and
 * knob frames from the cue sheet. smearIn / smearOut add the half-smear on each bar line.
 * opts.camera(t) -> { x, y, scale } overrides the fixed plate placement (Red's push).
 */
export function buildTourShot(ctx, spec, { smearIn = true, smearOut = true, camera = null, extras = null } = {}) {
  const { lib, cues } = ctx;
  const { util } = lib;
  const L = TOUR_LAYOUT;
  const plateL = ctx.layer("plate", 10);
  const ringL = ctx.layer("ring", 20);
  const typeL = ctx.layer("type", 30);
  const lo = spec.t0 - (smearIn ? lib.smear.SMEAR_LEN / 2 : 0);
  const hi = spec.t1 + (smearOut ? lib.smear.SMEAR_LEN / 2 : 0);

  const plates = new lib.SmearGroup(plateL, (parent) => {
    const p = lib.createPlate(spec.engine, { parent, scale: L.plate.scale, x: L.plate.x, y: L.plate.y });
    p.requireRender(cues, spec.render, lo, hi);
    return p;
  });
  const gesture = cues.gesture(spec.render, spec.gesture);
  if (!gesture) throw new Error(`${ctx.id}: no ${spec.gesture} gesture on ${spec.render} in cues.json`);
  const words = new lib.SmearGroup(typeL, (parent) => tourTypeCopy(lib, parent, spec, { gestureT0: gesture.t0, extras }));
  const ring = lib.createRing(ringL);

  return {
    render(t) {
      const on = t >= lo && t < hi;
      for (const layer of [plateL, ringL, typeL]) util.show(layer, on);
      if (!on) return;
      const s = cues.plateStateAt(spec.render, t);
      const cam = camera ? camera(t) : L.plate;
      const dx = lib.driftPx(s);
      const inU = smearIn ? lib.smearU(t, spec.t0) : 2;
      const outU = smearOut ? lib.smearU(t, spec.t1) : -1;
      const smearing = inU < 1 || outU > 0;
      plates.each((p, i) => {
        if (i > 0 && !smearing) return;
        p.place({ x: cam.x, y: cam.y, scale: cam.scale, dx });
        p.setState(s);
      });
      words.each((w, i) => {
        if (i > 0 && !smearing) return;
        w.render(t, s);
      });
      for (const g of [plates, words]) {
        if (inU < 1) g.render(Math.max(0, inU), "in");
        else if (outU > 0) g.render(Math.min(1, outU), "out");
        else g.hold();
      }
      ring.renderGesture(t, gesture, plates.centre.controlScreenRect(spec.ring));
    },
  };
}
