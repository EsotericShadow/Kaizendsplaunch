// Boots a v5 portrait composition from a manifest. film/v5/main.html and film/v5/tiktok.html
// call it; nothing else differs between the two films.
//
// Manifest (JSON):
//   { "duration": 91.216, "fps": 60, "width": 1080, "height": 1920,
//     "offset": 0,                  // master time of the composition's t = 0 (TikTok: 123.648)
//     "film": "main",               // which films.* block of demos.json this composition plays
//     "chip": { "mixUntil": 3.6485 },   // persistent chip; " · MIX n%" form before mixUntil (master s)
//     "grain": { "opacity": 0.05, "frozen": [[0, 0.4], ...] },   // persistent grain, frozen spans (comp s)
//     "scenes": ["a01-still-mixturn.js", ...] }   // modules next to the manifest, in play order
//
// Every scene gets the usual ctx (film/README.md) plus:
//   ctx.beats (film/lib/beats.js, loaded with the manifest's offset), ctx.demos (film/lib/demos.js),
//   ctx.motion, ctx.portrait, ctx.manifest.
// The chip (z 900) and the grain (z 800) are kit layers, owned by no scene. Flashes that scenes
// register with lib.registerFlash() go through the PSE limiter in setup.

import * as lib from "/film/lib/index.js";

export async function boot(manifestUrl) {
  const base = manifestUrl.slice(0, manifestUrl.lastIndexOf("/") + 1);
  const manifest = await (await fetch(manifestUrl)).json();
  const width = manifest.width || 1080;
  const height = manifest.height || 1920;
  const fps = manifest.fps || 60;
  const beats = await lib.loadBeats({ offset: manifest.offset || 0, fps });
  const demos = await lib.loadDemos({ film: manifest.film || "main", beats });
  if (manifest.chip && manifest.chip.mixUntil != null) demos.chipMixUntil = manifest.chip.mixUntil;
  const cues = manifest.cues ? await lib.loadCues(manifest.cues) : null;
  const kit = { beats, demos, motion: lib.motion, portrait: lib.portrait, manifest };
  const scenes = [];
  for (const file of manifest.scenes) {
    const mod = await import(`${base}${file}`);
    const scene = mod.default;
    // Wrap build() so every scene sees the v5 kit on ctx without changing lib/stage.js.
    scenes.push({ ...scene, build: (ctx) => scene.build(Object.assign(ctx, kit)) });
  }
  scenes.push(kitLayers(manifest, kit));
  const stage = lib.stage.makeStage(document.body, { width, height });
  lib.portrait.createSafeOverlay(stage);
  const comp = await lib.stage.runScenes({ stage, scenes, cues, lib, duration: manifest.duration, fps, width, height });
  window.__v5 = { manifest, beats, demos, lib, events: scenes.map((s) => ({ id: s.id, events: s.events || [] })) };
  return comp;
}

/** The persistent layers: grain (z 800) and the chip (z 900). */
function kitLayers(manifest, { demos }) {
  return {
    id: "kit",
    t0: 0,
    t1: manifest.duration,
    async build(ctx) {
      const { lib } = ctx;
      let grain = null;
      let gl = null;
      if (manifest.grain !== false) {
        const g = manifest.grain || {};
        gl = ctx.layer("grain", 800);
        grain = lib.createGrain(gl, { opacity: g.opacity ?? 0.05 });
        ctx.preload([lib.grain.GRAIN_URL]);
      }
      const frozen = (manifest.grain && manifest.grain.frozen) || [];
      let chip = null;
      let cl = null;
      if (manifest.chip !== false) {
        cl = ctx.layer("chip", 900);
        chip = lib.createChip(cl, demos);
      }
      const hideChip = (manifest.chip && manifest.chip.hidden) || [];
      return {
        setup() {
          const r = lib.resolveFlashes();
          if (r.demoted.length) console.log(`[v5] PSE: ${r.demoted.length} flash(es) demoted to edge glows`, JSON.stringify(r.demoted));
        },
        render(t) {
          if (grain) {
            lib.util.show(gl, true);
            const span = frozen.find(([a, b]) => t >= a && t < b);
            grain.render(t, { frozen: !!span, frozenFrame: span ? Math.round(span[0] * 60) : 0 });
          }
          if (chip) {
            const off = hideChip.some(([a, b]) => t >= a && t < b);
            lib.util.show(cl, !off);
            if (!off) chip.render(t);
          }
        },
      };
    },
  };
}
