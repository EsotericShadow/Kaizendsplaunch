// Portrait (1080 x 1920) tokens for the v5 films: frame, safe zones, type scale, colours, and the
// safe-zone debug overlay.
//
// The overlay is OFF in renders. Open a composition with ?safe=1 (or #safe) in a browser to see
// it; it is never shown by tools/render.mjs, which loads the page without a query string.

import { el, px } from "./util.js";
import { C, HUE, FONT } from "./type.js";

export const W = 1080;
export const H = 1920;
export const FPS = 60;

/**
 * Safe zones. Platform UI (TikTok, Reels, Shorts) covers the top 220 px, the bottom 380 px and
 * the right-hand action rail (x 940 to 1080). Key text, prices and buttons stay inside TEXT; full
 * bleed pictures may run under the platform UI.
 */
export const SAFE = {
  top: 220, // platform top bar
  bottom: 1540, // captions, handle, music line start below this
  left: 60,
  right: 940, // the action rail starts here
  // The text rectangle, as { x0, y0, x1, y1 }.
  TEXT: { x0: 60, y0: 220, x1: 940, y1: 1540 },
  // Named vertical zones (both pitches' grids reconcile to these).
  ZONES: {
    platformTop: [0, 220],
    chip: [232, 262],
    type: [280, 660],
    hero: [560, 1240],
    support: [1240, 1540],
    platformBottom: [1540, 1920],
  },
  LEGAL: { y0: 1552, y1: 1640 }, // legal small print, end cards only, marked data-bleed
  railX: 940,
  marginX: 72, // default left text edge
};

/** Colour tokens. Engine hues: glow / label hue; READOUT: the product's own readout colours. */
export const COLOR = {
  ...C,
  white: "#ffffff",
  hue: { ...HUE },
  fill: { green: "#64e28b", blue: "#63b3ff", red: "#ff776d", purple: "#b88cff", black: "#9ca3af" },
  readout: { green: "#9dbd78", blue: "#7fb8ff", red: "#ff8d8b", purple: "#b88dd8", black: "#d4d4d4", white: "#303030" },
  family: { fold: "#64e28b", echolalia: "#f0a04a", echolaliaInk: "#080706", stovetop: "#ff7a2e", stovetopChar: "#151517" },
  scrim: "rgba(5,5,6,0.72)",
};

/**
 * Type scale in px at 1080 wide (1 px = 0.36 pt on a 390 pt phone). The minimums are the phone
 * test: nothing that must be read is set smaller.
 */
export const TYPE = {
  hook: { size: 180, font: FONT.display, weight: 600, tracking: -0.02, lineHeight: 0.94 }, // the frame-0 headline
  title: { size: 150, font: FONT.display, weight: 600, tracking: -0.02 },
  price: { size: 190, font: FONT.display, weight: 600, tracking: -0.02 },
  headline: { size: 104, font: FONT.display, weight: 600, tracking: -0.02, min: 96 },
  accent: { size: 104, font: FONT.display, weight: 400, style: "italic", color: C.lavender },
  body: { size: 44, font: FONT.body, weight: 500, min: 40 },
  button: { size: 44, font: FONT.body, weight: 600 },
  eyebrow: { size: 30, font: FONT.mono, weight: 600, tracking: 0.3, min: 28, color: C.purple },
  chip: { size: 26, font: FONT.mono, weight: 600, tracking: 0.12, min: 24 },
  tag: { size: 28, font: FONT.mono, weight: 600, tracking: 0.12, min: 26 },
  legal: { size: 22, font: FONT.body, weight: 400, min: 22 },
};

/** Minimum readable sizes, for QC. */
export const MIN_SIZE = Object.fromEntries(Object.entries(TYPE).filter(([, v]) => v.min).map(([k, v]) => [k, v.min]));

/** True when the page was opened with the safe-zone flag (?safe=1, ?safe, or #safe). */
export function safeFlag() {
  try {
    const q = new URLSearchParams(location.search);
    return q.has("safe") && q.get("safe") !== "0" ? true : location.hash.includes("safe");
  } catch {
    return false;
  }
}

/**
 * The safe-zone guides: red hatching over the platform zones, a cyan outline of the text safe
 * area, and dashed zone lines. Added on top of everything (z 9999). Returns the node, or null
 * when the flag is off (renders).
 */
export function createSafeOverlay(stage, { force = false } = {}) {
  if (!force && !safeFlag()) return null;
  const root = el("div", {
    parent: stage,
    attrs: { "data-layer": "safe-overlay" },
    style: { position: "absolute", left: "0px", top: "0px", width: `${W}px`, height: `${H}px`, zIndex: "9999", pointerEvents: "none" },
  });
  const hatch = "repeating-linear-gradient(45deg, rgba(255,40,40,0.28) 0 10px, rgba(255,40,40,0.08) 10px 20px)";
  const box = (x, y, w, h, style) => el("div", { parent: root, style: { position: "absolute", left: px(x), top: px(y), width: px(w), height: px(h), ...style } });
  box(0, 0, W, SAFE.top, { background: hatch });
  box(0, SAFE.bottom, W, H - SAFE.bottom, { background: hatch });
  box(SAFE.right, SAFE.top, W - SAFE.right, SAFE.bottom - SAFE.top, { background: hatch });
  box(SAFE.TEXT.x0, SAFE.TEXT.y0, SAFE.TEXT.x1 - SAFE.TEXT.x0, SAFE.TEXT.y1 - SAFE.TEXT.y0, { outline: "2px solid rgba(0,230,255,0.85)", outlineOffset: "-1px" });
  for (const [name, [y0]] of Object.entries(SAFE.ZONES)) {
    box(0, y0, W, 0, { borderTop: "1px dashed rgba(0,230,255,0.5)" });
    el("div", { parent: root, text: `${name} ${y0}`, style: { position: "absolute", left: "8px", top: px(y0 + 2), font: `600 18px ${FONT.mono}`, color: "rgba(0,230,255,0.9)" } });
  }
  return root;
}

/**
 * QC helper: every visible text node in `root` whose box leaves SAFE.TEXT. Returns
 * [{ text, rect }]. Skips nodes marked data-bleed (legal small print on end cards, full-bleed art).
 */
export function unsafeText(root = document.getElementById("stage")) {
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const stageRect = root.getBoundingClientRect();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.textContent.trim()) continue;
    const p = n.parentElement;
    if (!p || p.closest("[data-bleed]") || p.closest('[data-layer="safe-overlay"]')) continue;
    if (getComputedStyle(p).visibility === "hidden" || +getComputedStyle(p).opacity === 0) continue;
    const r = document.createRange();
    r.selectNodeContents(n);
    const b = r.getBoundingClientRect();
    if (!b.width) continue;
    const x0 = b.left - stageRect.left;
    const y0 = b.top - stageRect.top;
    const rect = { x0, y0, x1: x0 + b.width, y1: y0 + b.height };
    if (rect.x0 < SAFE.TEXT.x0 || rect.x1 > SAFE.TEXT.x1 || rect.y0 < SAFE.TEXT.y0 || rect.y1 > SAFE.TEXT.y1) out.push({ text: n.textContent.trim().slice(0, 40), rect });
  }
  return out;
}
