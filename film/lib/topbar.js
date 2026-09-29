// The Choroboros editor's top bar (TopHeaderBar + TopBarDrawer, release-candidate f984c9a) rebuilt
// for the film plate: 638 x 56 editor px, drawn in plate px (x K). Everything below follows the
// paint code at the editor's default size (header design scale 1.0):
//
//   TopHeaderBar::paint           flat #1a1a1c bar, 0.5 px bottom hairline #3a3a40 @ 0.78
//   paintProceduralHeader         shell surfaces (radius 4, 1 px drop @ 0.22, #26262a fill,
//                                 0.5 px #3a3a40 @ 0.76 rim; disabled: saturation x0.35,
//                                 brightness x0.75, rim @ 0.34), +/- glyphs (1.12 px, arm 3.5),
//                                 chevrons (header_icon_chevron_down.svg in 9 x 9, #888890 @ 0.9),
//                                 KAIZEN DSP wordmark (kaizen_wordmark_white.png @ 0.96),
//                                 TRIM label, 24-segment output meter, "0.00 dB"
//   HeaderLookAndFeel             combo text: IBM Plex Sans Condensed SemiBold 12.5, #f0f0f2
//                                 (placeholder x 0.5 alpha), centred-left after the label border
//   TopBarDrawer::paint           collapsed drawer: right-rounded pill, rail, pinned Create well
//                                 (header_icon_flask.svg 15.6 px, #fbfbfb @ 0.85), > chevron
//
// Component bounds are the real editor's at 638 x 386 (dumped from a render of the editor; see
// film/UI_FIDELITY.md). No hover, press, popup, drawer-open or trial states: the film never shows
// the cursor. Icons, wordmark and fonts are the product's own files under /art/rc, loaded once at
// import (top-level await), so a plate can build its bar synchronously.

import { el, px } from "./util.js";

const ART = "/art/rc";
export const HEADER_EDITOR_W = 638;
export const HEADER_EDITOR_H = 56;

// HeaderTheme::shell
const BG = "#1a1a1c";
const SURFACE = [0x26, 0x26, 0x2a];
const BORDER = [0x3a, 0x3a, 0x40];
const TEXT_PRIMARY = [0xf0, 0xf0, 0xf2];
const TEXT_SECONDARY = [0x88, 0x88, 0x90];
const rgba = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${+a.toFixed(4)})`;

// Product fonts. Families are private to the film plate. emPerHeight: JUCE font height is
// ascent + descent (hhea), so CSS px = JUCE height x em / (ascent + descent).
//   cond: IBM Plex Sans Condensed SemiBold, the editor's own BinaryData copy (OFL).
//   mono: the value readouts. ProductTypography::valueTextFont maps the layout's "technology" font
//         id to JetBrains Mono SemiBold (the editor never loads Technology.ttf). The film loads
//         the npm @fontsource/jetbrains-mono 600 face (OFL, v2.211): same metrics as the editor's
//         v2.305 copy (600 advance, 1020 / -300 hhea) and outlines that differ only by a few
//         redundant points (film/UI_FIDELITY.md).
export const PLATE_FONTS = {
  cond: { family: "CB Plex Condensed", weight: 600, url: `${ART}/fonts/ui/IBMPlexSansCondensed-SemiBold.ttf`, format: "truetype", emPerHeight: 1 / 1.3 },
  mono: { family: "CB JetBrains Mono", weight: 600, url: "/__node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-600-normal.woff2", format: "woff2", emPerHeight: 1 / 1.32 },
};

async function loadFonts() {
  const faces = Object.values(PLATE_FONTS).map((f) => new FontFace(f.family, `url("${f.url}") format("${f.format}")`, { weight: String(f.weight) }));
  for (const f of faces) document.fonts.add(f);
  await Promise.all(faces.map((f) => f.load()));
}

// Monochrome SVG icons, fitted like Drawable::drawWithin: the drawable bounds are the union of
// the path extents (not the viewBox), placed centred, only ever reduced.
const ICON_FILES = {
  chevronDown: "header_icon_chevron_down.svg",
  chevronRight: "header_icon_chevron_right.svg",
  flask: "header_icon_flask.svg",
};
const ICONS = {};

async function loadIcons() {
  const probe = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  probe.setAttribute("width", "0");
  probe.setAttribute("height", "0");
  probe.style.position = "absolute";
  document.documentElement.appendChild(probe);
  for (const [key, file] of Object.entries(ICON_FILES)) {
    const res = await fetch(`${ART}/gui_icons/${file}`);
    if (!res.ok) throw new Error(`topbar: ${file} ${res.status}`);
    const doc = new DOMParser().parseFromString(await res.text(), "image/svg+xml");
    const paths = [...doc.querySelectorAll("path")].map((p) => ({ d: p.getAttribute("d"), rule: p.getAttribute("fill-rule") || "nonzero" }));
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    for (const p of paths) {
      const n = document.createElementNS("http://www.w3.org/2000/svg", "path");
      n.setAttribute("d", p.d);
      g.appendChild(n);
    }
    probe.appendChild(g);
    const b = g.getBBox();
    probe.removeChild(g);
    ICONS[key] = { paths, box: [b.x, b.y, b.width, b.height] };
  }
  probe.remove();
}

await Promise.all([loadFonts(), loadIcons()]);

let measureCtx = null;
/** Advance width in editor px of `text` in a product font at JUCE height `h` (editor px). */
export function advance(text, font, h) {
  if (!measureCtx) measureCtx = document.createElement("canvas").getContext("2d");
  const size = 100;
  measureCtx.font = `${font.weight} ${size}px "${font.family}"`;
  return (measureCtx.measureText(text).width * h * font.emPerHeight) / size;
}

/**
 * juce::roundToInt: the double "magic number" trick, i.e. round half to EVEN (216.5 -> 216,
 * 23.5 -> 24). Geometry that lands on exact halves (centred 9 px icons, 7.25 px chevrons) rounds
 * the way the editor does only with this, not with Math.round.
 */
export function roundToInt(v) {
  const f = Math.floor(v);
  const d = v - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}
/** juce::Rectangle<float>::toNearestInt: each of x, y, w, h rounded on its own. */
export const toNearestInt = ([x, y, w, h]) => [roundToInt(x), roundToInt(y), roundToInt(w), roundToInt(h)];
const jround = roundToInt;
const svgNS = "http://www.w3.org/2000/svg";
function sv(tag, attrs, parent) {
  const n = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, typeof v === "number" ? String(+v.toFixed(4)) : v);
  if (parent) parent.appendChild(n);
  return n;
}

/** juce::Colour::withMultipliedSaturation(s).withMultipliedBrightness(b) on an sRGB triple. */
function hsbScale(c, sMul, bMul) {
  const [r, g, b] = c.map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const v = max;
  const s = max > 0 ? (max - min) / max : 0;
  let h = 0;
  if (max !== min) {
    if (max === r) h = ((g - b) / (max - min)) / 6;
    else if (max === g) h = (2 + (b - r) / (max - min)) / 6;
    else h = (4 + (r - g) / (max - min)) / 6;
    if (h < 0) h += 1;
  }
  const s2 = Math.min(1, s * sMul);
  const v2 = Math.min(1, v * bMul);
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v2 * (1 - s2);
  const q = v2 * (1 - f * s2);
  const t = v2 * (1 - (1 - f) * s2);
  const rgb = [[v2, t, p], [q, v2, p], [p, v2, t], [p, q, v2], [t, p, v2], [v2, p, q]][i % 6];
  return rgb.map((x) => Math.round(x * 255));
}

// Real component bounds at 638 x 386 (TopHeaderBar::resized, TopBarDrawer).
const B = {
  minus: [82, 12, 32, 32],
  plus: [118, 12, 32, 32],
  preset: [154, 12, 78, 32],
  presetLabel: [162, 11, 50, 32],
  logo: [248, 0, 128, 56],
  engine: [392, 12, 112, 32],
  engineLabel: [398, 12, 84, 32],
  trim: [512, 11, 112, 35],
};

/**
 * One top bar. opts: { parent, k (plate px per editor px), engineName ("Green"), placeholder
 * (true: the selector shows its text-when-nothing-selected, e.g. "New Engine" for a Create draft),
 * presetName (null: the "Preset" placeholder) }.
 */
export class TopBar {
  constructor({ parent, k, engineName = "Green", placeholder = false, presetName = null }) {
    this.k = k;
    const W = HEADER_EDITOR_W * k;
    const H = HEADER_EDITOR_H * k;
    this.el = el("div", { parent, cls: "cb-topbar", style: { position: "absolute", left: "0px", top: "0px", width: px(W), height: px(H), overflow: "hidden", background: BG } });
    const svg = sv("svg", { width: W, height: H, viewBox: `0 0 ${HEADER_EDITOR_W} ${HEADER_EDITOR_H}` });
    Object.assign(svg.style, { position: "absolute", left: "0px", top: "0px", overflow: "hidden" });
    this.el.appendChild(svg);
    this.svg = svg;

    // Surfaces, glyphs, chevrons (paintProceduralHeader order: delete, save, glyphs, preset).
    this._surface(B.minus, false);
    this._surface(B.plus, true);
    this._plusMinus(B.minus, false, false);
    this._plusMinus(B.plus, true, true);
    this._surface(B.preset, true);
    this._chevron(B.preset);
    this._wordmark();
    this._surface(B.engine, true);
    this._chevron(B.engine);
    this._trim();
    // TopHeaderBar::paint: bottom hairline over the bar.
    sv("rect", { x: 0, y: HEADER_EDITOR_H - 0.5, width: HEADER_EDITOR_W, height: 0.5, fill: rgba(BORDER, 0.78) }, svg);

    // Combo texts (HeaderLookAndFeel, under the drawer). A selected item is drawn by the combo's
    // label (drawLabel) inside the label's bounds. The text-when-nothing-selected ("Preset", a
    // Create draft's name) is drawn by drawComboBoxTextWhenNothingSelected into the COMBO's
    // graphics with the label's LOCAL bounds, so it starts at the combo's left edge, not the
    // label's (plus headerNothingSelectedTextXOffset: 3 for the preset menu, 0 for the engine).
    this._comboText(presetName == null ? B.preset : B.presetLabel, presetName ?? "Preset", presetName == null, presetName == null ? 3 : 0, B.presetLabel);
    this.engineText = this._comboText(placeholder ? B.engine : B.engineLabel, engineName, placeholder, 0, B.engineLabel);

    this._drawer();
  }

  // drawShellSurface(bounds, hover 0, pressed false, enabled, purple false)
  _surface([x, y, w, h], enabled) {
    const r = [x + 0.5, y + 0.5, w - 1, h - 1];
    const rad = 4;
    const fill = enabled ? SURFACE : hsbScale(SURFACE, 0.35, 0.75);
    sv("rect", { x: r[0], y: r[1] + 1, width: r[2], height: r[3], rx: rad, fill: "rgba(0,0,0,0.22)" }, this.svg);
    sv("rect", { x: r[0], y: r[1], width: r[2], height: r[3], rx: rad, fill: rgba(fill) }, this.svg);
    sv("rect", { x: r[0], y: r[1], width: r[2], height: r[3], rx: rad, fill: "none", stroke: rgba(BORDER, enabled ? 0.76 : 0.34), "stroke-width": 0.5 }, this.svg);
  }

  // drawPlusMinusGlyph: Graphics::drawLine is a butt-ended stroke of 1.12 px, arm 3.5.
  _plusMinus([x, y, w, h], plus, enabled) {
    const c = [x + w / 2, y + h / 2];
    const t = 1.12;
    const col = rgba(TEXT_SECONDARY, enabled ? 0.94 : 0.34);
    sv("rect", { x: c[0] - 3.5, y: c[1] - t / 2, width: 7, height: t, fill: col }, this.svg);
    if (plus) sv("rect", { x: c[0] - t / 2, y: c[1] - 3.5, width: t, height: 7, fill: col }, this.svg);
  }

  _icon(key, [x, y, w, h], colour, alpha) {
    const ic = ICONS[key];
    // drawMonochromeSvg snaps the target with toNearestInt (x, y, w, h rounded separately), then
    // fits the path extents inside (centred, only reduced).
    const t = toNearestInt([x, y, w, h]);
    const node = sv("svg", { x: t[0], y: t[1], width: t[2], height: t[3], viewBox: ic.box.join(" "), preserveAspectRatio: "xMidYMid meet", overflow: "visible" }, this.svg);
    for (const p of ic.paths) sv("path", { d: p.d, "fill-rule": p.rule, fill: colour, "fill-opacity": alpha }, node);
    return node;
  }

  // drawChevron: the down chevron in 9 x 9 centred in the right 22 px of the combo.
  _chevron([x, y, w, h]) {
    const zone = [x + w - 22, y, 22, h];
    const c = [zone[0] + zone[2] / 2, zone[1] + zone[3] / 2];
    this._icon("chevronDown", [c[0] - 4.5, c[1] - 4.5, 9, 9], rgba(TEXT_SECONDARY), 0.9);
  }

  // KAIZEN DSP wordmark in the logo button (drawn at 0.96, centred, only reduced).
  _wordmark() {
    const [x, y, w, h] = B.logo;
    const aspect = 940 / 180;
    const maxH = Math.min(36, Math.max(1, h - 18));
    const maxW = Math.max(1, w - 2);
    const cw = Math.min(maxW, maxH * aspect);
    const ch = cw / aspect;
    const k = this.k;
    el("img", {
      parent: this.el,
      attrs: { src: `${ART}/gui_icons/kaizen_wordmark_white.png`, alt: "", draggable: "false" },
      style: { position: "absolute", left: px((x + (w - cw) / 2) * k), top: px((y + (h - ch) / 2) * k), width: px(cw * k), height: px(ch * k), opacity: "0.96" },
    });
  }

  // Output section: TRIM (tracked 0.65 px, glyph by glyph), 24-segment meter at -inf, "0.00 dB".
  _trim() {
    const [x, y, w] = B.trim;
    const cond = PLATE_FONTS.cond;
    // Label: drawTrackedLeftText in (x, y, w, 12), each glyph centred in (gx, y, adv + 1, 12).
    let gx = x;
    for (const ch of "TRIM") {
      const a = advance(ch, cond, 12.5);
      const r = toNearestInt([gx, y, a + 1, 12]);
      this._text(ch, r, cond, 12.5, rgba(TEXT_SECONDARY), "center");
      gx += a + 0.65;
    }
    // Meter track and segments.
    const m = [x + 1, y + 14, w - 2, 6];
    sv("rect", { x: m[0], y: m[1] - 1, width: m[2], height: m[3] + 2, rx: 1.5, fill: rgba(BORDER, 0.34) }, this.svg);
    const segW = (m[2] - 23) / 24;
    for (let i = 0; i < 24; i++) sv("rect", { x: m[0] + i * (segW + 1), y: m[1], width: segW, height: m[3], rx: 0.7, fill: rgba(TEXT_SECONDARY, 0.32) }, this.svg);
    // Readout: drawFittedText in (x, y + 23, w, 11) expanded by 1 px vertically, centred.
    this.trimText = this._text("0.00 dB", [x, y + 22, w, 13], cond, 12.4, rgba(TEXT_PRIMARY, 0.86), "center");
  }

  /** The Output Trim readout in dB ("-2.30 dB"); the 16:9 film never calls it, so it stays "0.00 dB". */
  setTrim(db) {
    if (!this.trimText || db == null || !Number.isFinite(db)) return;
    const v = Math.abs(db) < 0.005 ? 0 : db;
    const text = `${v.toFixed(2)} dB`;
    if (this.trimText.textContent !== text) this.trimText.textContent = text;
  }

  /** A text run centred vertically on its ascent + descent box, like JUCE drawText. */
  _text(text, [x, y, w, h], font, juceH, colour, align) {
    const k = this.k;
    return el("div", {
      parent: this.el,
      text,
      // Longhands only: the `font` shorthand would reset line-height.
      style: {
        position: "absolute",
        left: px(x * k),
        top: px(y * k),
        width: px(w * k),
        height: px(h * k),
        fontFamily: `"${font.family}"`,
        fontWeight: String(font.weight),
        fontSize: px(juceH * font.emPerHeight * k),
        lineHeight: px(h * k),
        textAlign: align,
        whiteSpace: "pre",
        color: colour,
      },
    });
  }

  // Combo text: origin (x, y) of the label (selected) or of the combo (placeholder), the label's
  // size, border (0, 4, 0, 2), centred-left; the placeholder at half alpha with its x offset.
  _comboText([x, y], text, placeholder, dx, [, , w, h]) {
    const colour = rgba(TEXT_PRIMARY, placeholder ? 0.5 : 1);
    return this._text(text, [x + 4 + dx, y, w - 6, h], PLATE_FONTS.cond, 12.5, colour, "left");
  }

  setEngineName(name, placeholder = false) {
    const [x, y] = placeholder ? B.engine : B.engineLabel;
    const [, , w, h] = B.engineLabel;
    const k = this.k;
    this.engineText.textContent = name;
    this.engineText.style.color = rgba(TEXT_PRIMARY, placeholder ? 0.5 : 1);
    this.engineText.style.left = px((x + 4) * k);
    this.engineText.style.top = px(y * k);
    this.engineText.style.width = px((w - 6) * k);
    this.engineText.style.height = px(h * k);
  }

  // TopBarDrawer, collapsed (slide progress 0), no hover.
  _drawer() {
    const g = sv("g", {}, this.svg);
    const chevronZone = 18;
    const padStart = 10;
    const padEnd = 10;
    const wellSize = 22;
    const wellGap = 8;
    const expandedW = chevronZone + padStart + 4 * wellSize + 3 * wellGap + padEnd; // 150
    const collapsedW = chevronZone + padStart + wellSize + padEnd; // 60
    const imageX = -(expandedW - collapsedW);
    const surface = [imageX, 9, expandedW, 36];
    const rightRounded = ([x, y, w, h], r) => {
      const rr = Math.min(r, w / 2, h / 2);
      return `M${x} ${y}L${x + w - rr} ${y}Q${x + w} ${y} ${x + w} ${y + rr}L${x + w} ${y + h - rr}Q${x + w} ${y + h} ${x + w - rr} ${y + h}L${x} ${y + h}Z`;
    };
    const hair = 0.5;
    sv("path", { d: rightRounded([surface[0], surface[1] + 1.8 - 1.5, surface[2], surface[3] + 3], 10.8), fill: "rgba(0,0,0,0.24)" }, g);
    sv("path", { d: rightRounded(surface, 10), fill: BG }, g);
    sv("path", { d: rightRounded(surface, 10), fill: rgba(SURFACE, 0.72) }, g);
    sv("path", { d: rightRounded(surface, 10), fill: "none", stroke: "rgba(0,0,0,0.32)", "stroke-width": hair * 1.15 }, g);
    sv("path", { d: rightRounded([surface[0] + hair / 2, surface[1] + hair / 2, surface[2] - hair, surface[3] - hair], 12), fill: "none", stroke: rgba(BORDER, 0.72), "stroke-width": hair }, g);
    // Rail (alpha 0.92 when collapsed).
    const rail = [imageX + (padEnd - 2), 12, 4 * wellSize + 3 * wellGap + 4, 30];
    const rg = sv("g", { opacity: 0.92 }, g);
    sv("rect", { x: rail[0], y: rail[1] + 0.8, width: rail[2], height: rail[3], rx: 5, fill: "rgba(0,0,0,0.18)" }, rg);
    sv("rect", { x: rail[0], y: rail[1], width: rail[2], height: rail[3], rx: 5, fill: rgba(SURFACE) }, rg);
    sv("rect", { x: rail[0], y: rail[1], width: rail[2], height: rail[3], rx: 5, fill: "none", stroke: rgba(BORDER, 0.65), "stroke-width": hair }, rg);
    // Pinned Create well and icon (engine-builder beta is on in the release build).
    const cx = imageX + (expandedW - collapsedW) + padEnd + wellSize / 2;
    const cy = 27;
    const well = [cx - wellSize / 2, cy - wellSize / 2, wellSize, wellSize];
    sv("rect", { x: well[0] - 0.8, y: well[1] - 0.8 + 0.4, width: well[2] + 1.6, height: well[3] + 1.6, rx: 4, fill: "rgba(0,0,0,0.22)" }, g);
    sv("rect", { x: well[0], y: well[1], width: well[2], height: well[3], rx: 4, fill: rgba(SURFACE) }, g);
    sv("rect", { x: well[0] - 0.35, y: well[1] - 0.35, width: well[2] + 0.7, height: well[3] + 0.7, rx: 4, fill: "none", stroke: rgba(BORDER, 0.62), "stroke-width": hair }, g);
    const iconBox = [cx - 7.8, cy - 7.8, 15.6, 15.6];
    this._icon("flask", iconBox, "#fbfbfb", 0.85);
    // Chevron ">" (7.25 px, nudged 0.35 px left), #dddddd.
    const chx = imageX + (expandedW - chevronZone / 2);
    const chy = 9 + 18;
    this._icon("chevronRight", [chx - 7.25 / 2 - 0.35, chy - 7.25 / 2, 7.25, 7.25], "#dddddd", 1);
  }
}
