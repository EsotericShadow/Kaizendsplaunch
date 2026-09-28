// Builds a composition from scene modules: one paused master GSAP timeline, one render(t) that
// calls every scene, fonts, preloads and scope data. film/main/index.html and the gallery use it.
//
// Scene module contract (film/scenes/shotNN-name.js):
//   export default {
//     id: "shot07-green", t0: 16.0, t1: 20.0,
//     async build(ctx) {             // ctx: { stage, tl, cues, lib, layer, preload, id, t0, t1 }
//       const L = ctx.layer("plate", 20);        // absolutely positioned full-frame div, hidden
//       ctx.tl.to(node, {...}, 16.5);            // tweens go in at ABSOLUTE film times
//       return { render(t) { lib.util.show(L, t >= 16 && t < 20); ... } };   // may add sequences, preload, setup
//     },
//   };
// A scene owns only its layers and shows them for [t0, t1) plus any overlap it declares.

import { defineComposition, preloadImages } from "/__render/composition.js";
import { settleText, FONT_SPECS } from "./type.js";
import { loadScopeData } from "./scope.js";
import { relayoutReadouts } from "./plate.js";
import { el } from "./util.js";

export function makeStage(parent = document.body, { width = 1920, height = 1080, background = "#050506" } = {}) {
  return el("div", {
    parent,
    attrs: { id: "stage" },
    style: { position: "relative", width: `${width}px`, height: `${height}px`, overflow: "hidden", background },
  });
}

/** A full-frame layer for one scene, hidden until the scene shows it. */
export function makeLayer(stage, name, z = 0) {
  return el("div", {
    parent: stage,
    cls: "layer",
    attrs: { "data-layer": name },
    style: { position: "absolute", left: "0px", top: "0px", width: "100%", height: "100%", zIndex: String(z), visibility: "hidden", pointerEvents: "none" },
  });
}

/**
 * scenes: array of scene modules (default exports). lib: the namespace from film/lib/index.js.
 * Returns the composition object.
 */
export async function runScenes({ stage, scenes, cues, lib, duration, fps = 60, width = 1920, height = 1080, fonts = [] }) {
  if (!window.gsap) throw new Error("GSAP must be loaded with a classic <script> before the module");
  const tl = window.gsap.timeline({ paused: true });
  const renders = [];
  const sequences = [];
  const setups = [];
  const preloads = [];
  for (const scene of scenes) {
    const ctx = {
      stage,
      tl,
      cues,
      lib,
      id: scene.id,
      t0: scene.t0,
      t1: scene.t1,
      layer: (name, z = 0) => makeLayer(stage, `${scene.id}:${name}`, z),
      preload: (urls) => preloads.push(...[].concat(urls)),
    };
    const res = (await scene.build(ctx)) || {};
    if (res.render) renders.push({ id: scene.id, fn: res.render });
    if (res.sequences) sequences.push(...res.sequences);
    if (res.preload) preloads.push(...res.preload);
    if (res.setup) setups.push(res.setup);
  }
  // Keep the preloaded images referenced so their decoded pixels stay cached.
  const keep = [];
  return defineComposition({
    width,
    height,
    fps,
    duration,
    timeline: tl,
    fonts: [...FONT_SPECS, ...fonts],
    sequences,
    async setup() {
      // Fonts are loaded by now: place text on its baselines and re-measure readout slots.
      settleText();
      relayoutReadouts();
      await loadScopeData(cues);
      keep.push(...(await preloadImages([...new Set(preloads)])));
      for (const s of setups) await s();
    },
    render(t, info) {
      for (const r of renders) r.fn(t, info);
    },
  });
}
