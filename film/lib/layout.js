// Choroboros plate constants and art paths. Control geometry lives in plate.js (generated from
// the release-candidate editor layout by film/tools/rc_layout.py); see film/UI_FIDELITY.md.
// Art is served from outside the repo: /art/rc = the release-candidate Assets folder, /data/gui =
// per-frame slices and prepared plates (film/tools/prep_gui.py).

/** Plate width in px: the 638 editor px window at K = 1400 / 638. */
export const PLATE_W = 1400;
export const ART = "/art/rc";
export const ENGINES = ["green", "blue", "red", "purple", "black"];

// Value text colours: each factory engine's accent (CustomLookAndFeel, applyEngineVisual); the clean
// white Create draft's valueTextColour (CreateDocumentFactory).
export const READOUT_COLOR = {
  green: "#9dbd78",
  blue: "#7fb8ff",
  red: "#ff8d8b",
  purple: "#b88dd8",
  black: "#d4d4d4",
  white: "#303030",
};

export const GUI = "/data/gui"; // per-frame slices of the sheets and prepared plates
const pad3 = (n) => String(n).padStart(3, "0");

/** Engines with a prepared 2x backpanel (film/tools/prep_gui.py, /data/gui/plates2x). */
export const PLATES_2X = ["green", "blue", "red", "purple"];

/**
 * Art URLs for an engine (or "white" for the Create canvas). The backpanels are the 1400 x 725
 * bitmaps the product ships and draws (MIX/, BinaryData); plateOnEditor is the light-on bitmap at
 * the 638 x 330 the editor's lit overlay caches it at; plate2x holds the 2800 x 1450 close-up
 * plates prepared from the shipped ones (same colour and geometry, the 2800 px art's fine detail).
 * Thumbs come from the plugin art as shipped; filmstrip frames are per-frame slices of the sheets.
 */
export function artFor(engine) {
  const e = engine;
  if (e === "white") {
    return {
      plateOff: `${ART}/MIX/white_light_off_backpanel.png`,
      plateOn: `${ART}/MIX/white_light_on_backpanel.png`,
      plateOnEditor: `${GUI}/lit1x/white.png`,
      plate2x: null,
      knobFrame: (name, on, f) => `${GUI}/white/main/${pad3(f)}.png`,
      mixFrame: (f) => `${GUI}/white/mix/${pad3(f)}.png`,
      // CreateDocumentFactory leaves sliderThumbSprite at 0 for a clean white draft: the green thumb.
      thumb: `${ART}/green/green_slider_thumb.png`,
      // A clean white draft uses the shared factory switch (factorySwitchSpriteSheet default).
      switchFrame: (f) => `${GUI}/shared/switch_a/${pad3(f)}.png`,
    };
  }
  return {
    plateOff: `${ART}/MIX/${e}_light_off_backpanel.png`,
    plateOn: `${ART}/MIX/${e}_light_on_backpanel.png`,
    // The lit plate as the editor shows it: HQLitOverlay caches it at 638 x 330 (prep_gui.py).
    plateOnEditor: `${GUI}/lit1x/${e}.png`,
    plate2x: PLATES_2X.includes(e)
      ? { plateOff: `${GUI}/plates2x/${e}_light_off.png`, plateOn: `${GUI}/plates2x/${e}_light_on.png` }
      : null,
    knobFrame: (name, on, f) => `${GUI}/${e}/${name}_${on ? "on" : "off"}/${pad3(f)}.png`,
    mixFrame: (f) => `${GUI}/${e}/mix/${pad3(f)}.png`,
    thumb: e === "black" ? `${ART}/black/black__slider_thumb.png` : `${ART}/${e}/${e}_slider_thumb.png`,
    // The RC editor loads factorySwitchSpriteSheet(backgroundSet): one sheet per engine.
    switchFrame: (f) => `${GUI}/${e}/switch/${pad3(f)}.png`,
  };
}
