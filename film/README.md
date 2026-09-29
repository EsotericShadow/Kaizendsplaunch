# Still Life: the picture

This folder holds the picture for "Still Life", the 86-second Choroboros launch film. The film is
an HTML composition that `tools/render.mjs` renders frame by frame in headless Chromium. The build
spec is `docs/brief/treatment.md`; timings, knob values and gestures come from `film/cues.json`,
the same file that drives the audio automation.

Nothing proprietary lives here. Plugin art, website art and generated data are served from
outside the repo through URL mounts, and every output (videos, stills, extracted frames) goes to
`/home/user/build/film/`.

## Layout

| Path | What it is |
|---|---|
| `main/index.html` | The film: 1920x1080, 60 fps, 86.0 s. Loads every scene listed in `scenes/manifest.json`. |
| `scenes/manifest.json` | Scene modules in play order. |
| `scenes/shotNN-name.js` | One module per shot (see "Adding a scene"). |
| `lib/` | Shared components. Scenes get them as `ctx.lib`. |
| `gallery/index.html` | An 8-second test composition that exercises every component. |
| `gallery/verify.html` | Legacy: plates in the state of the old plugin captures (superseded by `gallery/fidelity.html`). |
| `gallery/fidelity.html` | The UI-fidelity bench: plates in the states of the real editor renders, the owner's panel pose and four close-ups. |
| `UI_FIDELITY.md` | What the plate was checked against, the measured differences and how to repeat the checks. |
| `tools/prep_gui.py` | Slices the plugin's filmstrip sheets into one image per frame; prepares the 2x close-up plates and the editor-size lit plates. |
| `tools/rc_layout.py` | The editor's layout code as Python: the plate geometry table, and `--check` against component dumps. |
| `tools/fidelity_compare.py`, `tools/fidelity_offsets.py`, `tools/fidelity_panels.py` | Plate against editor renders (side by side, blend, diff, zooms), per-element registration, and plate against the owner's panels. |
| `tools/verify_plate.py` | Legacy: measures the plates against the old captures. |
| `tools/qc_picture.mjs`, `tools/qc_picture.py` | Picture QC (treatment 11, gates 5-9 and 11) into `qc-picture.json`. |
| `tools/sheet.py` | Contact sheets (12 stills each) for `film.sh stills`. |
| `qc-picture.json` | The latest picture QC report. |
| `film.sh` | Render, stills, preview, determinism and data-prep commands. |

## URL mounts

The renderer serves these prefixes. Code uses the prefixes, never file paths.

| Prefix | Folder | Used for |
|---|---|---|
| `/art/rc` | `/home/user/choroboros-rc/Assets` | Plates, slider thumbs, top-bar fonts, icons and wordmark from the September release candidate |
| `/art/site` | `/home/user/kaizendsp/public` | Hero frames, grain tile, VST logo, product stills |
| `/data` | `/home/user/build/film/data` | Generated data: `gui/` frames and prepared plates, `scope/`, `frames/` from product clips, `available.json` |
| `/` | the repo | `film/`, `cues.json` |
| `/__render/`, `/__node_modules/` | the runtime and npm packages | `composition.js`, GSAP, fontsource fonts |

`film.sh` passes the mounts on every command. It also writes `/data/available.json`, which tells
the page what generated data exists, so a missing folder never turns into a 404 (any 404 fails a
render).

## How a frame is made

`main/index.html` loads GSAP with a classic script, then a module that reads `cues.json` and the
manifest, imports each scene and calls `lib.stage.runScenes()`. That function builds one paused
GSAP timeline, calls every scene's `build(ctx)`, then calls `defineComposition()` from the runtime
with the fonts, image sequences and a `render(t)` that calls every scene's `render(t)` in manifest
order. Setup, which runs once before frame 0, places text on its baselines, loads the scope data
and decodes every image.

For each frame the renderer seeks the timeline to `t`, then calls `render(t)`. Each scene decides
from `t` alone what it shows. Nothing may depend on the previous frame, the wall clock or
`Math.random`.

## Adding a scene

Create `scenes/shot07-green.js` and add `"shot07-green.js"` to `scenes/manifest.json`:

```js
export default {
  id: "shot07-green",
  t0: 16.0,
  t1: 20.0,
  async build(ctx) {
    const { lib, cues } = ctx;
    const L = ctx.layer("plate", 20); // full-frame div, hidden until the scene shows it
    const plate = lib.createPlate("green", { parent: L, scale: 0.9, x: 96, y: 350 });
    plate.requireRender(cues, "R02", 16, 20); // prepare every filmstrip frame it will show
    const ring = lib.createRing(L);
    return {
      render(t) {
        const on = t >= 16 && t < 20;
        lib.util.show(L, on);
        if (!on) return;
        const s = cues.plateStateAt("R02", t);
        plate.place({ dx: lib.driftPx(s) });
        plate.setState(s);
        ring.renderGesture(t, cues.gesture("R02", "depth"), plate.controlScreenRect("depth"));
      },
    };
  },
};
```

`ctx` holds `stage`, `tl` (the master timeline), `cues`, `lib`, `id`, `t0`, `t1`,
`layer(name, z)` and `preload(urls)`. `build()` may return `sequences` (ImageSequence objects to
preload), `preload` (image URLs) and `setup` (an async function run before frame 0).

A scene owns only its own layers and hides them outside its window, plus any overlap it declares
(a smear, a fade). Cuts are hard unless the treatment says otherwise. GSAP tweens go into `ctx.tl`
at absolute film times. Anything that depends on the cue sheet is easier to write in `render(t)`.

Rules from the render pipeline (`docs/brief/render-pipeline.md` 7.1):

- Never put a canvas (the hero, the scope, clip footage) inside an element whose scale or 3D
  transform changes. Zoom inside the draw call instead. The GUI plate has no canvas, so it can be
  scaled with a transform.
- No `mask-image` on or around a canvas. Use a gradient overlay.
- No `<video>`, and never swap `img.src` during the render. Use `ImageSequence` and the plate's
  prepared frames.
- Hide things with `lib.util.show(node, false)`. It uses visibility, so a hidden layer hides
  everything inside it and canvases keep their size.

## Components

- `cues.js`: `loadCues()` returns a `Cues` object. `valueAt(render, param, t)` applies each
  gesture's ease to the knob position, then maps it to display units exactly as the audio build
  does. `settingsAt()` returns every heard setting plus the HQ switch art frame and `cycles`, the
  integrated LFO phase: use `sin(2π·cycles)` rather than `sin(2πRt)`, so a Rate gesture speeds up
  without a jump. `plateStateAt()` also adds readouts with the plugin's 60 ms digit flip.
  `footnote("opening" | "tour")` returns the level-match footnote text that the audio log allows.
  `formatReadout()`, the frame maps and `thumbX()` are exported for direct use.
- `plate.js` (+ `topbar.js`): the editor window rebuilt for green, blue, red, purple, black and the
  white Create canvas: the release top bar over the body, 1400 x 847.02 at scale 1 (638 x 386
  editor px x 1400 / 638; body 724.14 px high, `plate.height` / `HEADER_PX`). Values in display
  units map to knob frames, thumb position and readouts as in the editor. The switch uses each
  engine's own lever sheet. The lit plate (at the 638 x 330 the editor caches it at) and the `_on`
  knob frames blend with the lever (`1 - frame/17`), and the lever moves with the plugin's
  smootherstep. Readouts are JetBrains Mono SemiBold with the editor's character slots, glow,
  reflections and clipped digit flip. `plate.focus({ on: "rate", zoom: 2, at: [x, y] })` frames a
  close-up; above scale 1 the plate shows prepared 2x backpanels (pass `hiRes: true` to a plate
  built small that is pushed in later). Filmstrip frames are separate images that must be prepared
  in `build()` with `require()`, `requireFrames()` or `requireRender()`; `setState()` throws on a
  frame that was not prepared. See `UI_FIDELITY.md`.
- `chorustype.js`: the italic accent as a static dry layer plus wet copies in the engine hue, under
  the SINE, STEP, WOW and ORBIT laws (G3), with Black's ensemble layers.
- `scope.js`: the goniometer (G7), reading `/data/scope`. On top of the data's fixed gain it
  applies one fixed display gain for the whole film (`DISPLAY_GAIN`, with a radial tanh soft limit,
  so typical frames fill about 55-80% of the circle and nothing clips flat). It draws its own
  graticule (outline, M/S crosshair, L/R rim ticks, L / R / M / S labels) in the pro orientation
  (M up, L upper-left), a Catmull-Rom trace with an additive glow in the hue, and the 50%/25%
  persistence of the two previous frames. Mono stays on the vertical axis. Until the audio build
  writes the data, the scope draws a placeholder from the cue sheet and labels it PLACEHOLDER.
- `smear.js`: the engine-change smear (G4) as a `SmearGroup` of three copies.
- `ring.js`: the gesture ring (G6).
- `type.js`: brand tokens, baseline placement (`placeText`), eyebrow, headline with italic accent,
  pills, the typeset KAIZEN DSP lockup, the G3b offer hairline, site buttons and the end-card
  format row with the unmodified VST Compatible logo.
- `grain.js`, `hero.js`, `clips.js`: grain tile, the hero camera move with frame blending and
  grade, and product-clip frames as image sequences.

## Commands

Run from the repo root. `WORKERS` defaults to 2 because the machine is shared.

```sh
film/film.sh gui                             # slice the filmstrips into /data/gui (once, about 15 s)
film/film.sh frames                          # extract the Fold and Echolalia windows to /data/frames
film/film.sh gallery                         # stills of the component gallery
film/film.sh stills shot07 16.1,18.25,19.9   # stills of the film
film/film.sh preview tour 16 36              # half-size preview of a range
film/film.sh render final                    # full render, with the master audio if it exists
film/film.sh check 3.5,18.25,26.2 film/gallery/index.html   # determinism check
python3 film/tools/verify_plate.py /home/user/build/film/stills/verify
```

Picture QC, after any change to the scenes, cues or copy:

```sh
node film/tools/qc_picture.mjs scan          # layers and text blocks on every frame (about 2 min)
node film/tools/qc_picture.mjs gates         # readouts, knob frames, captions (gate 5), VST tile (gate 8)
film/film.sh check 0.25,2.6,20.1,26.2,41.5,50.1,63.3,72,80 > /home/user/build/film/logs/determinism.log
python3 film/tools/qc_picture.py             # gates 6, 7, 9, cuts and coverage; writes film/qc-picture.json
```

`film.sh prep` runs before every command. It slices the filmstrips if that has not been done yet
and rewrites `/data/available.json`. Direct `node tools/render.mjs` calls work too, with the three
`--mount` flags from `film.sh`.

## Checking the plates

`UI_FIDELITY.md` has the method, the results against renders of the real editor and the commands
(`gallery/fidelity.html` with `tools/fidelity_compare.py`, `fidelity_offsets.py` and
`fidelity_panels.py`). The older `gallery/verify.html` and `tools/verify_plate.py` measure against
captures of an older build and are kept only for reference.

## Open points

- The readouts use JetBrains Mono SemiBold, as the release-candidate editor draws them (the layout's
  "technology" font id maps to it; the editor never loads `Technology.ttf`). The remaining measured
  differences from the real editor, and what a 1.0.5 screenshot would settle, are listed in
  `UI_FIDELITY.md`.
