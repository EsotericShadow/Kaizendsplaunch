// FLASH (v5): the full-frame additive flash layer and the photosensitivity (PSE) limiter.
//
//   const fl = createFlash(ctx.layer("flash", 40));       // a layer under the type
//   registerFlash({ t: h.t, peak: 0.3, color: COLOR.fill.green, id: "S06-a" });  // in build()
//   ...render(t): fl.render(t, motion.flash(t, [h], { peak }), color, flashMode("S06-a"));
//
// The limiter runs once at setup (boot.js calls resolveFlashes()): at most 3 qualifying flashes
// (luminance change above 10 % over more than 25 % of the frame) in any rolling 1 s. A 4th flash
// in a window becomes a 3 px edge glow in its hue. Fills never flash; they cut.

import { el, setStyle, hexToRgb, px } from "./util.js";

const FLASHES = [];
let resolved = false;

/** Relative luminance (sRGB) of a hex colour, 0..1. */
export function luminance(hex) {
  const lin = (c) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const [r, g, b] = hexToRgb(hex);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** Schedule a flash (composition time of its onset). area: fraction of the frame it covers (1 = full). */
export function registerFlash({ t, peak, color = "#ffffff", area = 1, id = null }) {
  FLASHES.push({ t, peak, color, area, id: id ?? `flash@${t.toFixed(4)}`, mode: "full" });
  resolved = false;
}

/** Run the limiter (boot.js calls this in setup). Returns the report. */
export function resolveFlashes({ maxPerWindow = 3, window = 1.0, minLum = 0.1, minArea = 0.25 } = {}) {
  FLASHES.sort((a, b) => a.t - b.t);
  const qualifying = [];
  const report = [];
  for (const f of FLASHES) {
    const q = f.peak * luminance(f.color) > minLum && f.area > minArea;
    if (!q) {
      f.mode = "full";
      continue;
    }
    const inWin = qualifying.filter((g) => f.t - g.t < window);
    if (inWin.length >= maxPerWindow) {
      f.mode = "edge";
      report.push({ id: f.id, t: f.t, mode: "edge" });
    } else {
      f.mode = "full";
      qualifying.push(f);
    }
  }
  resolved = true;
  return { flashes: FLASHES.map((f) => ({ ...f })), demoted: report };
}

/** "full" or "edge" for a registered flash id (after resolveFlashes). */
export function flashMode(id) {
  const f = FLASHES.find((x) => x.id === id);
  return f ? f.mode : "full";
}

export const flashes = () => FLASHES.map((f) => ({ ...f }));
export const flashesResolved = () => resolved;

export class Flash {
  constructor(parent, { blend = "plus-lighter" } = {}) {
    this.el = el("div", { parent, style: { position: "absolute", inset: "0", mixBlendMode: blend, pointerEvents: "none", visibility: "hidden" } });
  }

  /** alpha: layer opacity (0 hides). color: hex. mode "edge": a 3 px inner rim instead of a fill. */
  render(t, alpha, color = "#ffffff", mode = "full") {
    if (!(alpha > 0.002)) {
      setStyle(this.el, "visibility", "hidden");
      return;
    }
    setStyle(this.el, "visibility", "");
    const [r, g, b] = hexToRgb(color);
    if (mode === "edge") {
      setStyle(this.el, "background", "transparent");
      setStyle(this.el, "boxShadow", `inset 0 0 0 ${px(3)} rgba(${r},${g},${b},${+Math.min(1, alpha * 2.5).toFixed(4)})`);
    } else {
      setStyle(this.el, "boxShadow", "none");
      setStyle(this.el, "background", `rgba(${r},${g},${b},${+alpha.toFixed(4)})`);
    }
  }
}

export function createFlash(parent, opts) {
  return new Flash(parent, opts);
}
