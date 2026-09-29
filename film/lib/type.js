// Brand type and small brand components (brand-and-copy 2, 3, 4.1; treatment G0, G3b, shot 24).
//
// Text is placed by BASELINE, the way the treatment specifies it: placeText() records the wanted
// baseline and settleText() (run by the stage after fonts load) sets `top` from the real font
// metrics, so a 96 px headline with baseline 200 has its baseline on y = 200.

import { el, svg, setStyle, px, TAU, rgba } from "./util.js";

export const C = {
  bg: "#050506",
  surface: "#0c0d10",
  surface2: "#12141a",
  fg: "#f6f4ef",
  muted: "#a8a7a0",
  purple: "#b88cff",
  lavender: "#d0bdff",
  primaryBtn: "#f5f2ea",
  primaryBtnText: "#171817",
};

/** Cycler hues (G0): glows, labels, scopes, ChorusType wet layers. */
export const HUE = {
  green: "#7ee0a0",
  blue: "#79b8ff",
  red: "#ff8a80",
  purple: "#c9b1ff",
  black: "#9aa0a6",
  white: "#f6f4ef",
};

export const FONT = {
  display: '"Fraunces", serif',
  body: '"Inter", sans-serif',
  mono: '"JetBrains Mono", monospace',
  readout: "Technology",
};

/** Font specs the stage must load before frame 0. */
export const FONT_SPECS = [
  "600 100px Fraunces",
  "italic 400 100px Fraunces",
  "400 20px Inter",
  "500 20px Inter",
  "600 20px Inter",
  "700 20px Inter",
  "400 20px 'JetBrains Mono'",
  "600 20px 'JetBrains Mono'",
  "30px Technology",
];

// Baseline placement -------------------------------------------------------------------------

const pending = [];
let settled = false;
let mctx = null;

function metrics(node) {
  const cs = getComputedStyle(node);
  if (!mctx) mctx = document.createElement("canvas").getContext("2d");
  mctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  const m = mctx.measureText("Hg");
  return { A: m.fontBoundingBoxAscent, D: m.fontBoundingBoxDescent, size: parseFloat(cs.fontSize) };
}

function applyPlacement(node, spec) {
  const { A, D, size } = metrics(node);
  const L = size * spec.lineHeight;
  node.style.lineHeight = `${spec.lineHeight}`;
  node.style.top = px(spec.baseline - ((L - A - D) / 2 + A));
}

/**
 * Put a text node's first baseline on y = baseline. align: "left" (x is the left edge), "center"
 * or "right". The node gets position absolute and white-space nowrap.
 */
export function placeText(node, { x, baseline, align = "left", lineHeight = 1 }) {
  Object.assign(node.style, { position: "absolute", whiteSpace: "pre", left: px(x) });
  if (align === "center") node.style.transform = "translateX(-50%)";
  else if (align === "right") node.style.transform = "translateX(-100%)";
  const spec = { baseline, lineHeight };
  node.__place = spec;
  if (settled) applyPlacement(node, spec);
  else pending.push(node);
  return node;
}

/** Called once after fonts are loaded (the stage does this in setup). */
export function settleText() {
  settled = true;
  for (const n of pending.splice(0)) applyPlacement(n, n.__place);
}

/** Move an already placed node to a new baseline (after settleText). */
export function setBaseline(node, baseline) {
  node.__place.baseline = baseline;
  if (settled) applyPlacement(node, node.__place);
}

// Blocks -------------------------------------------------------------------------------------

/** Eyebrow: JetBrains Mono 600 uppercase, 0.3em tracking, purple unless a hue is given. */
export function eyebrow(text, { parent = null, color = C.purple, size = 18, weight = 600, tracking = 0.3, x, baseline, align = "left" } = {}) {
  const n = el("div", {
    parent,
    text,
    cls: "t-eyebrow",
    style: {
      font: `${weight} ${size}px ${FONT.mono}`,
      letterSpacing: `${tracking}em`,
      color,
      // Balance the trailing tracking so centred and right-aligned lines sit true.
      marginRight: align === "left" ? "0" : `-${tracking}em`,
    },
  });
  if (baseline != null) placeText(n, { x, baseline, align });
  return n;
}

/**
 * Headline: Fraunces 600, -0.02em, ss01 ss02, with an italic 400 lavender accent at the end.
 * Returns { el, upright, accent }. `accent` is the element ChorusType takes over.
 */
export function headline({ text = "", accent = "", size = 96, parent = null, x, baseline, align = "left", color = C.fg, accentColor = C.lavender, lineHeight = 1 } = {}) {
  const n = el("div", {
    parent,
    cls: "t-headline",
    style: {
      font: `600 ${size}px ${FONT.display}`,
      letterSpacing: "-0.02em",
      fontFeatureSettings: '"ss01", "ss02"',
      color,
    },
  });
  const upright = el("span", { parent: n, text });
  let acc = null;
  if (accent) {
    acc = el("span", {
      parent: n,
      text: accent,
      style: { fontStyle: "italic", fontWeight: "400", color: accentColor },
    });
  }
  if (baseline != null) placeText(n, { x, baseline, align, lineHeight });
  return { el: n, upright, accent: acc };
}

/** Body line: Inter, muted by default. */
export function body(text, { parent = null, size = 28, weight = 400, color = C.muted, x, baseline, align = "left", tracking = 0 } = {}) {
  const n = el("div", {
    parent,
    text,
    cls: "t-body",
    style: { font: `${weight} ${size}px ${FONT.body}`, color, letterSpacing: tracking ? `${tracking}em` : "normal" },
  });
  if (baseline != null) placeText(n, { x, baseline, align });
  return n;
}

/** Mono label (footnotes, scope labels, captions). */
export function mono(text, { parent = null, size = 14, weight = 600, color = "rgba(246,244,239,0.45)", tracking = 0.12, x, baseline, align = "left" } = {}) {
  const n = el("div", {
    parent,
    text,
    cls: "t-mono",
    style: {
      font: `${weight} ${size}px ${FONT.mono}`,
      letterSpacing: `${tracking}em`,
      color,
      marginRight: align === "left" ? "0" : `-${tracking}em`,
    },
  });
  if (baseline != null) placeText(n, { x, baseline, align });
  return n;
}

/**
 * Segmented pill, e.g. DRY | CHOROBOROS or BBD | TAPE. setActive(i, fill) lights one segment
 * (fill colour, #050506 text). Placed by its top-left (x, y) and fixed size.
 */
export function pill(labels, { parent = null, x = 0, y = 0, w = 240, h = 44, size = 14, active = 0, fill = C.fg, border = "rgba(246,244,239,0.35)" } = {}) {
  const box = el("div", {
    parent,
    cls: "t-pill",
    style: {
      position: "absolute",
      left: px(x),
      top: px(y),
      width: px(w),
      height: px(h),
      display: "flex",
      boxSizing: "border-box",
      border: `1px solid ${border}`,
      borderRadius: px(h / 2),
      overflow: "hidden",
      font: `600 ${size}px ${FONT.mono}`,
      letterSpacing: "0.14em",
    },
  });
  const segs = labels.map((label, i) => {
    const s = el("div", {
      parent: box,
      text: label,
      style: {
        flex: `${label.length + 3} 1 0`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        paddingLeft: "0.14em",
        borderLeft: i ? `1px solid ${border}` : "none",
      },
    });
    return s;
  });
  const api = {
    el: box,
    segs,
    setActive(i, color = fill) {
      segs.forEach((s, k) => {
        setStyle(s, "background", k === i ? color : "transparent");
        setStyle(s, "color", k === i ? C.bg : "rgba(246,244,239,0.6)");
      });
    },
  };
  api.setActive(active, fill);
  return api;
}

/** Small outlined tag (the FREE pill: mono 12 px, 1 px engine-hue border, radius 4). */
export function tag(text, { parent = null, color = HUE.green, size = 12, padY = 0.45, x, baseline, align = "left" } = {}) {
  const n = el("div", {
    parent,
    text,
    cls: "t-tag",
    style: {
      font: `600 ${size}px ${FONT.mono}`,
      letterSpacing: "0.2em",
      color,
      border: `1px solid ${color}`,
      borderRadius: "4px",
      padding: `${px(size * padY)} ${px(size * 0.55)} ${px(size * padY)} ${px(size * 0.75)}`,
    },
  });
  if (baseline != null) placeText(n, { x, baseline, align });
  return n;
}

/**
 * The typeset KAIZEN DSP lockup (brand-and-copy 4.1): KAIZEN in Fraunces 600, -0.075em, off-white,
 * over DSP in Inter 700, 0.45em tracking, purple, between 1 px rules fading to purple.
 * size is the KAIZEN font size; every other measure scales from the site's 1.52rem mark.
 * (x, y) is the top-left of the lockup box.
 */
export function lockup({ parent = null, x = 0, y = 0, size = 44 } = {}) {
  const k = size / (1.52 * 16);
  const rem = 16 * k;
  const box = el("div", {
    parent,
    cls: "t-lockup",
    style: { position: "absolute", left: px(x), top: px(y), display: "inline-flex", flexDirection: "column", alignItems: "stretch" },
  });
  el("div", {
    parent: box,
    text: "KAIZEN",
    style: {
      font: `600 ${px(size)} ${FONT.display}`,
      letterSpacing: "-0.075em",
      color: C.fg,
      lineHeight: "1",
      textAlign: "center",
      paddingRight: "0.075em",
      fontFeatureSettings: '"ss01", "ss02"',
    },
  });
  const row = el("div", {
    parent: box,
    style: { display: "flex", alignItems: "center", gap: px(0.5 * rem), marginTop: px(0.22 * rem) },
  });
  const rule = (flip) =>
    el("div", {
      parent: row,
      style: {
        flex: "1 1 0",
        height: "1px",
        background: `linear-gradient(90deg, transparent, ${C.purple})`,
        transform: flip ? "rotate(180deg)" : "",
      },
    });
  rule(false);
  el("div", {
    parent: row,
    text: "DSP",
    style: {
      font: `700 ${px(0.56 * rem)} ${FONT.body}`,
      letterSpacing: "0.45em",
      paddingLeft: "0.45em",
      color: C.purple,
      lineHeight: "1",
    },
  });
  rule(true);
  return box;
}

/**
 * G3b offer hairline: one strand per audible engine, a 1.5 px travelling sine at that engine's
 * Rate, amplitude 3 px, 80% alpha, engine hue. The words above stay static.
 *   const h = offerHairline({ parent, x, y, width, strands: [{ engine: "green" }, { engine: "purple" }] });
 *   h.render(t, [cyclesGreen, cyclesPurple]);
 */
export function offerHairline({ parent = null, x = 0, y = 0, width = 300, strands = [], amp = 3, wavelength = 140, alpha = 0.8, stroke = 1.5 } = {}) {
  const h = amp * 2 + 8;
  const root = svg("svg", { width: width, height: h, viewBox: `0 0 ${width} ${h}` });
  Object.assign(root.style, { position: "absolute", left: px(x), top: px(y - h / 2), overflow: "visible" });
  if (parent) parent.appendChild(root);
  const paths = strands.map((s, i) =>
    svg("path", {
      fill: "none",
      stroke: s.hue || HUE[s.engine],
      "stroke-width": stroke,
      "stroke-opacity": alpha,
      "stroke-linecap": "round",
      style: "mix-blend-mode: screen",
    }, root),
  );
  const cy = h / 2;
  return {
    el: root,
    render(t, cycles) {
      paths.forEach((p, i) => {
        const c = cycles[i] ?? 0;
        const phase0 = (i * Math.PI) / Math.max(1, strands.length);
        let d = "";
        for (let xx = 0; xx <= width; xx += 3) {
          const yy = cy + amp * Math.sin((TAU * xx) / wavelength - TAU * c + phase0);
          d += `${xx ? "L" : "M"}${xx.toFixed(1)} ${yy.toFixed(2)}`;
        }
        if (p.__d !== d) {
          p.__d = d;
          p.setAttribute("d", d);
        }
      });
    },
  };
}

// Lucide glyphs (ISC), inlined.
const LUCIDE = {
  arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  appWindow: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 4v4"/><path d="M2 8h20"/><path d="M6 4v4"/>',
  monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
};
export function lucide(name, { size = 24, stroke = 1.25, color = "currentColor" } = {}) {
  const n = document.createElement("span");
  n.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round">${LUCIDE[name]}</svg>`;
  n.style.display = "inline-flex";
  return n;
}

/**
 * Site button (site.css .btn / .btn--primary): Inter 600, radius 0.45rem, 1 px border, ArrowRight
 * after the label on the primary. scale 1 = the site's 16 px rem. For the film's end card the
 * size can be set directly: height (px), fontSize (label px), padX (px), radius (px).
 */
export function siteButton(label, { parent = null, primary = false, scale = 1.6, x = 0, y = 0, arrow = primary, height = null, fontSize = null, padX = null, radius = null } = {}) {
  const rem = 16 * scale;
  const fs = fontSize ?? 0.91 * rem;
  const k = fs / 0.91 / 16; // the rem this label size implies
  const h = height ?? 48 * scale;
  const b = el("div", {
    parent,
    cls: primary ? "t-btn t-btn--primary" : "t-btn",
    style: {
      position: "absolute",
      left: px(x),
      top: px(y),
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: px(0.6 * 16 * k),
      height: height != null ? px(h) : "",
      minHeight: px(h),
      boxSizing: "border-box",
      padding: height != null ? `0px ${px(padX ?? 1.2 * 16 * k)}` : `${px(0.75 * rem)} ${px(1.2 * rem)}`,
      borderRadius: px(radius ?? 0.45 * 16 * k),
      border: `1px solid ${primary ? C.primaryBtn : "rgba(255,255,255,0.32)"}`,
      background: primary ? C.primaryBtn : "transparent",
      color: primary ? C.primaryBtnText : C.fg,
      font: `600 ${px(fs)} ${FONT.body}`,
      lineHeight: "1",
      whiteSpace: "nowrap",
    },
  });
  el("span", { parent: b, text: label });
  if (arrow) b.appendChild(lucide("arrowRight", { size: Math.round(1.05 * 16 * k), stroke: 2 }));
  return b;
}

/**
 * End-card format row (treatment shot 24): five 200x130 tiles. Tile 1 holds the official VST
 * Compatible logo exactly as supplied (an <img>, 72 px tall, no filter, opacity, blend or
 * transform) with "VST®3" under it. Put this row in the top layer, above grain and glow.
 */
export function formatRow({ parent = null, x0 = 120, y = 800, gap = 20, tileW = 200, tileH = 130, vstUrl = "/art/site/brand/platforms/vst-compatible.png" } = {}) {
  const row = el("div", { parent, cls: "t-formats", style: { position: "absolute", left: "0px", top: "0px" } });
  const tile = (i) =>
    el("div", {
      parent: row,
      style: {
        position: "absolute",
        left: px(x0 + i * (tileW + gap)),
        top: px(y),
        width: px(tileW),
        height: px(tileH),
        boxSizing: "border-box",
        background: C.surface,
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "10px",
      },
    });
  const label = (parent, text, top) =>
    el("div", {
      parent,
      text,
      style: {
        position: "absolute",
        left: "0px",
        width: "100%",
        top: px(top),
        textAlign: "center",
        font: `500 19px ${FONT.body}`,
        color: C.muted,
        lineHeight: "22px",
      },
    });
  const typeset = (parent, text) =>
    el("div", {
      parent,
      text,
      style: {
        position: "absolute",
        left: "0px",
        width: "100%",
        top: "26px",
        height: "56px",
        lineHeight: "56px",
        textAlign: "center",
        font: `500 44px ${FONT.body}`,
        letterSpacing: "-0.065em",
        color: "#e8e3ed",
      },
    });
  const glyph = (parent, name) => {
    const g = lucide(name, { size: 44, stroke: 1.25, color: "#e8e3ed" });
    Object.assign(g.style, { position: "absolute", left: px((tileW - 44) / 2), top: "32px" });
    parent.appendChild(g);
  };

  const t1 = tile(0);
  const vst = el("img", { parent: t1, attrs: { src: vstUrl, alt: "VST Compatible", draggable: "false" } });
  const vw = Math.round((474 / 443) * 72);
  Object.assign(vst.style, { position: "absolute", height: "72px", width: `${vw}px`, left: px(Math.round((tileW - vw) / 2)), top: "16px" });
  label(t1, "VST®3", 96);

  const t2 = tile(1);
  typeset(t2, "AU");
  label(t2, "Audio Units", 96);

  const t3 = tile(2);
  typeset(t3, "AAX");

  const t4 = tile(3);
  glyph(t4, "appWindow");
  label(t4, "Standalone", 96);

  const t5 = tile(4);
  glyph(t5, "monitor");
  label(t5, "macOS", 96);

  return { el: row, vst };
}

export { rgba };
