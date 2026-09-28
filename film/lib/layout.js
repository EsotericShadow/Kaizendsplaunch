// Choroboros GUI geometry on the 1400x725 plate, and the art paths of the release-candidate
// source (served at /art/rc). Positions come from the editor layout (defaults_factory_mac.json run
// through the editor's scaling, see docs/brief/visual-assets.md 3.3): knobs are
// [centre x, centre y, w, h]; value boxes are [x, y, w, h, text right edge, font px].

export const PLATE_W = 1400;
export const PLATE_H = 725;
export const ART = "/art/rc";

/** Plugin pixels per plate pixel: the editor designs in 700x363 and scales by 638/700. */
export const PLUGIN_PX = 1400 / 638;

export const ENGINES = ["green", "blue", "red", "purple", "black"];

const G = {
  rate: [216.1, 303.4, 269.9, 269.4],
  depth: [508.0, 303.4, 269.9, 269.4],
  offset: [940.3, 303.4, 269.9, 269.4],
  width: [1223.4, 303.4, 269.9, 269.4],
  mix: [1232.1, 605.6, 120.7, 120.5],
  slider: [399.4, 481.9, 647.3, 135.8, 68.0, 135.8, 549.8],
  hq: [570.5, 113.9, 291.8, 291.3],
  values: {
    rate: [79.0, 429.3, 190.9, 65.7, 267.7, 29.9],
    depth: [366.5, 427.1, 190.9, 65.7, 555.2, 29.9],
    offset: [790.0, 429.3, 190.9, 65.7, 978.7, 29.9],
    width: [1086.2, 429.3, 190.9, 65.7, 1274.9, 29.9],
    color: [636.4, 602.3, 129.5, 50.4, 763.6, 29.9],
    mix: [1156.4, 665.9, 109.7, 30.7, 1263.9, 22.0],
  },
};

export const LAYOUT = {
  green: G,
  blue: {
    rate: [212.9, 289.1, 245.8, 245.3],
    depth: [500.3, 289.1, 245.8, 245.3],
    offset: [937.0, 289.1, 245.8, 245.3],
    width: [1226.6, 289.1, 245.8, 245.3],
    mix: [1229.9, 603.4, 116.3, 116.1],
    slider: [399.4, 481.9, 647.3, 135.8, 68.0, 135.8, 549.8],
    hq: [570.5, 113.9, 291.8, 291.3],
    values: {
      rate: [85.6, 422.7, 190.9, 65.7, 274.3, 29.9],
      depth: [364.3, 422.7, 190.9, 65.7, 553.0, 29.9],
      offset: [794.4, 424.9, 190.9, 65.7, 983.1, 29.9],
      width: [1084.0, 422.7, 190.9, 65.7, 1272.7, 29.9],
      color: [638.6, 598.0, 129.5, 50.4, 765.8, 29.9],
      mix: [1156.4, 661.5, 109.7, 30.7, 1263.9, 22.0],
    },
  },
  red: {
    rate: [212.9, 300.1, 272.1, 271.6],
    depth: [500.3, 300.1, 272.1, 271.6],
    offset: [937.0, 300.1, 272.1, 271.6],
    width: [1226.6, 300.1, 272.1, 271.6],
    mix: [1229.9, 603.4, 116.3, 116.1],
    slider: [399.4, 479.7, 647.3, 144.6, 72.4, 144.6, 552.0],
    hq: [568.3, 107.3, 291.8, 291.3],
    values: {
      rate: [85.6, 422.7, 190.9, 65.7, 274.3, 29.9],
      depth: [364.3, 422.7, 190.9, 65.7, 553.0, 29.9],
      offset: [794.4, 424.9, 190.9, 65.7, 983.1, 29.9],
      width: [1084.0, 422.7, 190.9, 65.7, 1272.7, 29.9],
      color: [638.6, 598.0, 129.5, 50.4, 765.8, 29.9],
      mix: [1156.4, 661.5, 109.7, 30.7, 1263.9, 22.0],
    },
  },
  purple: {
    rate: [216.1, 299.0, 300.6, 300.1],
    depth: [505.8, 299.0, 300.6, 300.1],
    offset: [940.3, 299.0, 300.6, 300.1],
    width: [1227.7, 299.0, 300.6, 300.1],
    mix: [1231.0, 606.7, 122.9, 122.7],
    slider: [399.4, 466.5, 647.3, 148.9, 74.6, 148.9, 541.0],
    hq: [570.5, 113.9, 291.8, 291.3],
    values: {
      rate: [83.4, 429.3, 190.9, 65.7, 272.1, 29.9],
      depth: [366.5, 427.1, 190.9, 65.7, 555.2, 29.9],
      offset: [787.8, 429.3, 190.9, 65.7, 976.5, 29.9],
      width: [1086.2, 429.3, 190.9, 65.7, 1274.9, 29.9],
      color: [638.6, 600.2, 129.5, 50.4, 765.8, 29.9],
      mix: [1154.2, 665.9, 109.7, 30.7, 1261.8, 22.0],
    },
  },
  black: {
    rate: [213.9, 299.0, 261.1, 260.6],
    depth: [501.4, 299.0, 261.1, 260.6],
    offset: [938.1, 299.0, 261.1, 260.6],
    width: [1227.7, 299.0, 261.1, 260.6],
    mix: [1229.9, 603.4, 116.3, 116.1],
    slider: [399.4, 484.1, 647.3, 133.6, 66.9, 133.6, 550.9],
    hq: [570.5, 113.9, 291.8, 291.3],
    values: {
      rate: [81.2, 427.1, 190.9, 65.7, 269.9, 29.9],
      depth: [362.1, 427.1, 190.9, 65.7, 550.8, 29.9],
      offset: [792.2, 429.3, 190.9, 65.7, 980.9, 29.9],
      width: [1086.2, 427.1, 190.9, 65.7, 1274.9, 29.9],
      color: [638.6, 600.2, 129.5, 50.4, 765.8, 29.9],
      mix: [1147.6, 661.5, 109.7, 30.7, 1255.2, 22.0],
    },
  },
  // Create's clean white canvas. Its windows are empty in the film; knobs, mix and switch sit on
  // the default grid (checked by eye against the white plate's printed labels and windows).
  white: {
    ...G,
    mix: [1232.1, 596.4, 120.7, 120.5],
  },
};

// Readout colours (the plugin's valueTextColour per factory engine).
export const READOUT_COLOR = {
  green: "#9dbd78",
  blue: "#7fb8ff",
  red: "#ff8d8b",
  purple: "#b88dd8",
  black: "#d4d4d4",
  white: "#303030",
};

// Readout FX from the layout defaults (plugin px): glow alpha and spread per value box.
export const READOUT_FX = {
  main: { glowAlpha: 0.4, glowSpread: 3.5 },
  color: { glowAlpha: 0.39, glowSpread: 3.48 },
  mix: { glowAlpha: 0.26, glowSpread: 0.07 },
};

// Filmstrip sheets (visual-assets 3.2). Each frame cell is drawn whole into the control's box.
export const SHEETS = {
  main: { size: 3132, frame: 300, offset: 12, step: 312, cols: 10, frames: 100 },
  mix: { size: 7552, frame: 512, offset: 64, step: 576, cols: 13, frames: 156 },
  whiteMix: { size: 1632, frame: 150, offset: 12, step: 162, cols: 10, frames: 100 },
  switch: { size: 2560, frame: 512, offset: 0, step: 512, cols: 5, frames: 18 },
};

export const GUI = "/data/gui"; // per-frame slices of the sheets (film/tools/prep_gui.py)
const pad3 = (n) => String(n).padStart(3, "0");

/**
 * Art URLs for an engine (or "white" for the Create canvas). Plates, thumbs and the font come from
 * the plugin art as shipped; filmstrip frames come from the per-frame slices of the same sheets.
 */
export function artFor(engine, { hiRes = false } = {}) {
  const e = engine;
  if (e === "white") {
    return {
      plateOff: `${ART}/MIX/white_light_off_backpanel.png`,
      plateOn: `${ART}/MIX/white_light_on_backpanel.png`,
      knobFrame: (name, on, f) => `${GUI}/white/main/${pad3(f)}.png`,
      mixFrame: (f) => `${GUI}/white/mix/${pad3(f)}.png`,
      thumb: null,
      // A clean white draft uses the shared factory switch (factorySwitchSpriteSheet default).
      switchFrame: (f) => `${GUI}/shared/switch_a/${pad3(f)}.png`,
    };
  }
  // 2800x1450 plates exist for every engine but black (black's copy is a legacy 1024 px plate).
  const big = hiRes && e !== "black";
  return {
    plateOff: big ? `${ART}/${e}/${e}_light_off_backpanel.png` : `${ART}/MIX/${e}_light_off_backpanel.png`,
    plateOn: big ? `${ART}/${e}/${e}_light_on_backpanel.png` : `${ART}/MIX/${e}_light_on_backpanel.png`,
    knobFrame: (name, on, f) => `${GUI}/${e}/${name}_${on ? "on" : "off"}/${pad3(f)}.png`,
    mixFrame: (f) => `${GUI}/${e}/mix/${pad3(f)}.png`,
    thumb: e === "black" ? `${ART}/black/black__slider_thumb.png` : `${ART}/${e}/${e}_slider_thumb.png`,
    // The RC editor loads factorySwitchSpriteSheet(backgroundSet): one sheet per engine.
    switchFrame: (f) => `${GUI}/${e}/switch/${pad3(f)}.png`,
  };
}

/**
 * Control rectangles for gesture rings and camera moves, in plate px: { cx, cy, size }.
 * The HQ size covers the lever's whole travel (ball up to ball down) around its pivot.
 */
export function controlRect(engine, name, thumbCx = null) {
  const L = LAYOUT[engine];
  if (name === "color" || name === "thumb") {
    const [, , , , tw, th, ty] = L.slider;
    return { cx: thumbCx ?? 473.8, cy: ty, size: Math.max(tw, th) };
  }
  if (name === "hq") {
    const [x, y, w, h] = L.hq;
    const k = w / 512;
    // Lever travel spans cell y 87..365 around the bezel at the cell centre.
    return { cx: x + w / 2, cy: y + 226 * k, size: 278 * k };
  }
  const [cx, cy, w] = L[name];
  return { cx, cy, size: w };
}
