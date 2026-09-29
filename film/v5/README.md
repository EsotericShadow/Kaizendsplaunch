# v5: the portrait launch film and the TikTok

This folder builds the two portrait (1080 x 1920, 60 fps) films for Choroboros. `TREATMENT.md` is
the only spec, and `demos.json` is its machine-readable twin for the audio and the readouts. They
use the same renderer, components and rules as the 16:9 film (`film/README.md`). Nothing
proprietary lives here: art and generated data are served through URL mounts, and every output
goes to `/home/user/build/v5`.

**Time.** Every time is master time: seconds from the first sample of the master. Film time is
song time. The main film is master 0.000 to 91.216. The TikTok is master 123.648 to 138.648;
inside that composition t = master - 123.648 (the manifest's `offset`). The song is never cut,
looped, reordered or stretched.

**Frames.** Frame f is drawn at t = f / 60. An event keyed to a hit at h lands on the frame that
contains h, `floor(60 h)` (`beats.onsetFrame(h)`). The picture is never late and at most one frame
early.

## Layout

| Path | What it is |
|---|---|
| `TREATMENT.md`, `demos.json` | The spec and the demo sheet. `demos.json` holds the knobs, gestures, bypass spans and chip text for both films. |
| `grid.json`, `hits.json`, `sections.json`, `AUDIO_MAP.md` | The 148 BPM bar grid, the drum hits (per piece `[t, dB, ...]`, plus `fills`) and the song sections. |
| `main.html` | The main film: 91.216 s, 5 473 frames. Loads `scenes/manifest.json`. |
| `tiktok.html` | The TikTok: 15.000 s, 900 frames. Loads `tiktok/manifest.json`. |
| `boot.js` | Shared boot. Loads the manifest, `beats` (with the offset) and `demos`, adds the kit layers (grain, chip), and runs the scenes through `film/lib/stage.js`. |
| `scenes/` | Main-film scenes. Unit A: `a01` to `a12`. Unit B: `b13` to `b24`. `a00-common.js` holds Unit A helpers and is not a scene. |
| `tiktok/` | TikTok scenes `t01` to `t07` (Unit A). |
| `hero-readouts.js` | The 3D hero's readout windows per source frame, and `maskHeroReadouts()`, which defocuses them after each hero draw (S03, S04, S20). |
| `v5.sh` | Prep, stills, every-frame stills, preview, render and determinism commands. |
| `DESCRIPTION.md` | The post text for YouTube Shorts, Instagram Reels and TikTok, with the music credit, the legal line and the checks to make before posting. |

## Manifest

```json
{ "duration": 91.216, "fps": 60, "width": 1080, "height": 1920,
  "offset": 0,                     // master time of t = 0 (TikTok: 123.648)
  "film": "main",                  // films.<film> in demos.json
  "chip": { "mixUntil": 3.6485 },  // the persistent chip; false to hide it; "hidden": [[t0, t1], ...]
  "grain": { "opacity": 0.05, "frozen": [[0, 0.4], [24.0, 36.08], [84.7167, 91.3]] },
  "scenes": ["a01-still-mixturn.js", "..."] }
```

- Both manifests already list every scene file, in play order. Neither unit edits a manifest; each unit fills in its own files.
- The grain is frozen in the listed spans (composition time): the frame-0 still, the guitar-alone tour and the stop. In the TikTok it is frozen on frame 0, in the freeze and in the Buy hold.

## Commands

Run from the repo root. `WORKERS` defaults to 2, because 4 CPUs are shared. `V5_OUT` sets the
output folder (default `/home/user/build/v5`). The composition argument is `main` (default) or
`tiktok`.

```sh
film/v5/v5.sh prep                                # data dirs, gui/frames symlinks, scope link, available.json
film/v5/v5.sh stills hook 0,0.4,2.1 [main|tiktok] # PNG stills + contact sheets in $V5_OUT/stills/hook
film/v5/v5.sh frames sync 0.38 0.45               # a still at EVERY frame of [0.38, 0.45] (sync checks)
film/v5/v5.sh preview act1 0 13.4                 # half-size MP4 in $V5_OUT/out/act1.mp4
film/v5/v5.sh render choroboros-portrait-v5       # final MP4 (muxes $V5_OUT/master_v5.wav when present)
film/v5/v5.sh render choroboros-tiktok-v5 "" "" tiktok   # muxes $V5_OUT/tiktok_v5.wav when present
film/v5/v5.sh check 0,0.4,1.6167,13.3667,23.1,36.0667,84.7167,91.2    # determinism
```

- Sheet layout: `SHEET_PER`, `SHEET_COLS` and `SHEET_W` (thumbnail width, default 270).
- The safe-zone guides: open a composition with `?safe=1` (for example through the renderer's static server). Renders never show them.

**Data.**
- `prep` makes `$V5_OUT/data` (main) and `$V5_OUT/data-tiktok`, each served as `/data`.
- `gui` and `frames` link to the 16:9 film's prepared slices in `/home/user/build/film/data`. If they are missing, `film/film.sh gui` builds them.
- `scope` links to the audio build's `$V5_OUT/audio/scope` (or `scope-tiktok`) once its `index.json` exists. Override the source with `V5_SCOPE`.
- `available.json` records `gui`, `scope`, `scopeStems`, `frames`, `measured` and `meter`. The page reads it, so it never requests a missing file (a 404 fails a render).
- Until the audio build writes the scope data, scopes draw their labelled PLACEHOLDER.

## Scene contract

This is the 16:9 contract (`film/README.md`, "Adding a scene"), plus the v5 kit on `ctx`:

```js
export default {
  id: "a05-meet", t0: 608 / 60, t1: 802 / 60,
  events: [],                        // [{ t: master time, kind, hit }] for the QC; see below
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const cut = b.hitNear("kick", b.comp(10.135));      // name hits by master time
    this.events.push({ t: cut.tm, kind: "cut", hit: "kick + rack 10.135" });
    const L = ctx.layer("plate", 10);
    const plate = lib.createPlate("green", { parent: L, scale: 0.66 });
    plate.require(demos.statesIn(cut.tf, 802 / 60));      // every knob frame it will show
    return {
      render(t) {
        const on = t >= cut.tf && t < 802 / 60;
        lib.util.show(L, on);
        if (!on) return;
        plate.place({ cx: 540, cy: 980, scale: 0.66 * M.push(t, 10.135, 13.378, 1, 1.05) });
        plate.setState(demos.plateState(t));
        plate.setGrade(demos.grade("green", t));          // colour = sound
      },
    };
  },
};
```

**Rules**
- A scene shows its layers only in its own frame window. Windows are given in frames, from the treatment's frame column.
- Everything is a pure function of `t`: no `Math.random`, no wall clock, no state carried from the previous frame.
- Name every hit by its master time with `beats.hitNear()`. Never type a frame number for a hit.
- Canvases (scope, hero, clips) never sit inside a changing scale. Scale them in their draw call and move them with left/top.

**Layer z order**
- picture: 10 to 20;
- scope: 14;
- flash: 30 (under all type);
- type: 40;
- grain: 800 (kit);
- chip: 900 (kit);
- safe overlay: 9999 (debug only).

**`events`** lists every designed event in master time. `kind` is one of `cut`, `stamp`, `slam`, `whip`, `sweep`, `flash`, `click`, `gesture` or `text`. The QC (`qc.mjs`, Unit B) reads the lists from `window.__v5.events`. PUNCH is not an event.

## The kit (`film/lib`)

All kit modules are imported by `film/lib/index.js`. Scenes also get the loaded instances on
`ctx`.

### `beats.js`: the drum clock (`ctx.beats`)

`boot.js` calls `loadBeats({ offset })`. Every function takes and returns composition time. Hits
are `{ i, piece, t, tm (master), db, frame, tf (frame time), extra }`. Pieces are `kick`, `snare`,
`racktom`, `floortom`, `hihat`, `crash` and `cymbal`. The groups are `tom`, `drums` (kick, snare
and both toms) and `all`. An array of pieces also works.

| Call | Returns |
|---|---|
| `bar(n)`, `beat(n, k)` | Bar n downbeat; beat k (1-based, fractional: 2.5 is the "and" of 2) |
| `beats(n)`, `bars(n)`, `period`, `barLen` | Durations in seconds |
| `pos(t)`, `sectionAt(t)` | `{ bar, beat, phase }`; the `sections.json` entry |
| `master(t)`, `comp(tm)` | Time conversion (the offset) |
| `frameAt(t)`, `onsetFrame(h)`, `onsetTime(h)`, `since(t, h)`, `framesSince(t, h)`, `after(t, h)` | Frame-exact comparisons (use these, never `t >= h`) |
| `hitsIn(piece, t0, t1, { minDb })` | The hits in [t0, t1) |
| `hitNear(piece, x, tol)` | The hit nearest x: how scenes name a hit |
| `lastHit(piece, t, { minDb, within })`, `nextHit(piece, t)` | Frame-exact |
| `stepIndex(hitsOrTimes, t)` | Index of the current step (-1 before the first) |
| `env(piece, t, tau, { minDb, level, max, attack })` | Σ exp(-Δt/τ) over hits, peak 1 on the hit frame, clamped to 2 |
| `kick(t)`, `snare(t)`, `tom(t)`, `crash(t)` | `env` presets: τ 70, 90, 80 and 60 ms; snare ghosts under -20 dB ignored |
| `fills`, `fillAt(t)`, `fillsIn(t0, t1)` | The `hits.json` fills, each with its `hits` |

### `motion.js`: the primitives (TREATMENT 5.4)

Every primitive is `f(t, hits, opts)`, pure. `hits` is an array of hits or times, one hit, or a
piece name. `MOTION` holds the constants:
- punch τ 0.07 (amp: plate 0.03, macro 0.045, type 0.012);
- `tomGroove` 0.6;
- shake 10 px, 14 px on the first hit, type 2 px, τ 0.12;
- stamp 1.18 over 5 frames, then 1.02;
- whip 5 frames, 180 px, copies 50/30/18/10/6/3 %;
- sweep 3 frames;
- flash peak 0.30, white 0.45, `first` [0.45, 0.20, 0.06], `stop` [0.45, 0.15], τ 0.06;
- slam 160 px over 6 frames;
- inhale 0.97, then 0.95;
- click-stop 5 frames.

| Call | Use |
|---|---|
| `punch(t, "kick", { amp })` | The scale. Anchor it on the framed subject: `plate.focus({ on, zoom: z * punch, at })` |
| `shake(t, hits, { amp, salt })` | `{ x, y }`, hash noise of (hit, frame) |
| `stamp(t, h)` | `{ scale, opacity, on }` |
| `slam(t, h, { dir, dist })` | `{ x, y, on, done }`; follow it with a PUNCH |
| `whip(t, h, { dir })` | `{ active, cut, outX, outY, inX, inY, copies[] }`; 5 frames centred on the hit frame |
| `sweep(t, hits)` | The number of steps taken (fractional): multiply by the step size |
| `steps(t, hits, values)` | A click-stop value |
| `flash(t, hits, { peak })` or `flash(t, [h], { frames: MOTION.flash.first })` | The layer alpha |
| `push(t, t0, t1, a, b, ease)` | MACRO PUSH-IN or a dolly |
| `inhale(t, preHits, stopHit)` | The frame scale before a stop |
| `cut(t, cuts)`, `transform({ x, y, scale })`, `hash11()` | Helpers |

### `demos.js`: what is heard (`ctx.demos`)

This module reads `demos.json`, and reads `/data/scope/measured.json` when `available.json` says it
exists. Steps, gestures and HQ throws start on their hit's frame (the picture leads the sound by
less than one frame).

| Call | Returns |
|---|---|
| `stateAt(t)` | `{ engine, hq, core, knobs, trim, bypass, heard, chip, demoId, demo }` |
| `plateState(t, id?)` | The `plate.setState()` shape: values, the lever `switchFrame` (420 ms smootherstep) and readouts with the 60 ms digit flip |
| `statesIn(t0, t1, id?)` | Every state in a span, for `plate.require()` in `build()` |
| `grade(engine, t)` | `{ sat, bright }`: heard 1/1, not heard 0.35/0.75, bypass or Mix 0 0.12/0.9, and 0.12 + 0.88·mix/40 during a Mix move |
| `chipText(t)` | `● GUITAR · CHOROBOROS GREEN · LAGRANGE 3RD`, `○ GUITAR · BYPASS`, or the `MIX n%` form before `chip.mixUntil` |
| `cyclesAt(t)`, `settingsAt(t)` | The integrated LFO phase (the render's 3 s pre-roll included); the settings for chorustype and drift |
| `gestureAt(t)`, `bypassAt(t)`, `demoAt(t)`, `trimOf(demo)`, `levelMatched(id)` | "LEVEL MATCHED" appears only if `levelMatched` is true |

### The other kit modules

- **`portrait.js`**
  - `W`, `H`;
  - `SAFE` (TEXT x 60 to 940, y 220 to 1540; `ZONES`; `LEGAL`);
  - `COLOR` (`hue`, `fill`, `readout`, `family`);
  - `TYPE` and `MIN_SIZE`;
  - `createSafeOverlay(stage)`, shown only with `?safe=1`;
  - `unsafeText(root)`, for QC gate 3. It skips `[data-bleed]`.
- **`plate.js`**
  - `plate.setGrade({ sat, bright, keep })`: a CSS filter on the body and the top bar. The readouts keep their colour, or only the readouts named in `keep` do (S01 uses `keep: ["mix"]`).
- **`flash.js`**
  - `createFlash(layer)`, then `.render(t, alpha, color, mode)`. The flash is additive (plus-lighter).
  - `registerFlash({ t, peak, color, area, id })` in `build()`. `boot.js` runs `resolveFlashes()` in setup: a 4th qualifying flash in any 1 s window becomes an edge glow.
  - `flashMode(id)` tells the scene which.
- **`chip.js`**: the chip, a kit layer at x 72, baseline 256, mono 26 px, 70 % white, with the dot in the hue.
- **`montage.js`**
  - `createMontage(layer, engine, [{ h, on, zoom, at, pushTo? }], { push, punchAmp, header })`: hard-cut macros on hits, each with a push-in over one beat and a PUNCH on the kicks.
  - `.render(t, state)` returns the shot index. `.plate` is the plate.
- **`slices.js`**
  - `createSlice(layer, engine, { x, y, w, h, scale, centreY })`: a knob-row strip that uses the plate geometry and `plate.height`.
  - `knobRowCentre(engine)`.
- **Unit B's modules** (the agreed APIs are in their headers):
  - `endcard.js` and `abtoggle.js` are stubs that throw until Unit B delivers them.
  - Unit B adds them to `index.js`.

The 16:9 components are reused as they are: `plate.js` (`focus`, `hiRes`), `scope.js`,
`chorustype.js`, `smear.js`, `ring.js`, `type.js`, `grain.js`, `hero.js` and `clips.js`.

## The hook (built: S01 to S03, frames 0 to 412)

| File | Shot | What it does |
|---|---|---|
| `a01-still-mixturn.js` | S01, f0 to 120 | The dead still (Green MIX macro, element 600 px, at (540, 1180), s 0.12, only "0%" and the ring in colour, empty scope, "Great / sound" 180 px). On f24: white flash [0.45, 0.20, 0.06], 14 px shake (type 2 px), the five-hue burst, Mix click-stop 1. On f48, f72 and f97: click-stops 2 to 4, with a PUNCH and a ring pulse. The ring leaves over 0.3 s from f108. |
| `a02-montage.js` | S02, f121 to 217 | Four hard-cut 2.0x macros on the bar-2 kicks: RATE, DEPTH, OFFSET, WIDTH. Each pushes 1.00 to 1.03 over its beat, PUNCHes, and blinks its readout on the floor toms. |
| `a03-tagline-hero.js` | S03, f218 to 412 | The 3D hero, portrait crop y 560 to 1540 at 60 % brightness. The scrub steps +6 source frames per kick. Exposure +6 % on the floor offbeats. The bar-4 push-in run. "doesn’t" STAMPs on 5.270. |

**Checked**
- Stills at every frame from 0.38 to 0.45 s: frame 23 is still and frame 24 (0.400, containing 0.4048) carries the flash, the burst and the shake.
- A contact sheet every half beat from 0.405 to 6.891.
- `v5.sh check 0,0.4,1.6167,2.4167,3.2333,5.3`: deterministic.

**Deviations from the spec**
- The scope inset sits at (770, 560), not (770, 520). At 520 its rim touched the one-line "Great sound" of S02. S01 matches S02 for continuity.
- The S01 ring is 1.12x the visible knob (the mix-sheet frame has a 12.5 % border). At 1.12x the frame it cut through the "0%" readout.
- The S02 macros omit the top bar and rise out of black under the type.

**Hand-off to S04**
- The hero source frame at the S03/S04 cut is about 51 of 97 (`HERO_BASE` 4, +6 per kick, 1.5 per second creep).
- S04 jump-cuts +24 on 6.892, then its bar-5 kicks hard-cut to hero angles 8, 60 and 28 (creeping from each), so the 97 frames never run out.

## Build units (TREATMENT section 6)

Files are disjoint and the manifests are frozen. Replace a stub, keep its id and file name.

**Unit A**
- Main S04 to S12:
  - `a04-sit-still.js` (f413 to 607);
  - `a05-meet.js` (f608 to 801);
  - `a06-title.js` (f802 to 996);
  - `a07-lineup.js` (f997 to 1190);
  - `a08-five-voices.js` (f1191 to 1385, uses `slices.js`);
  - `a09-blue.js` (f1386 to 1580);
  - `a10-red.js` (f1581 to 1774);
  - `a11-purple.js` (f1775 to 1969);
  - `a12-black.js` (f1970 to 2163; ends with the 3 % pull-back).
- The TikTok:
  - `t01-totem-red.js` (τ f0 to 96);
  - `t02-blue.js` (f97 to 193);
  - `t03-purple.js` (f194 to 290);
  - `t04-freeze-mixturn.js` (f291 to 388);
  - `t05-black.js` (f389 to 485);
  - `t06-offer.js` (f486 to 680);
  - `t07-buy.js` (f681 to 899, uses Unit B's `endcard.js`, TikTok variant).
- Helpers go in `scenes/a00-common.js`, or in a `tiktok/t00-common.js` that is not listed in the manifest.

**Unit B**
- Main S13 to S24:
  - `b13-cores.js` (f2164 to 2358; owns the 36.080 seam, frame 2164);
  - `b14-create.js` (f2359 to 2747);
  - `b15-looks.js` (f2748 to 2942);
  - `b16-free.js` (f2943 to 3331);
  - `b17-trial.js` (f3332 to 3720);
  - `b18-ab.js` (f3721 to 4109, uses `abtoggle.js`);
  - `b19-settings.js` (f4110 to 4304, uses `montage.js`);
  - `b20-price.js` (f4305 to 4693);
  - `b21-family.js` (f4694 to 4985; bypass span, the family heard dry);
  - `b22-windup.js` (f4986 to 5082, `montage.js` with `pushTo` 1.05, `inhale()`);
  - `b23-stop.js` (f5083 to 5180);
  - `b24-endcard.js` (f5181 to 5472).
- Kit modules: `film/lib/endcard.js` (main and TikTok variants) and `film/lib/abtoggle.js`, both due by hour 3.
- The picture QC: `film/v5/qc.mjs`.

**Shared kit**
- Owned by the kit engineer. Ask before changing it: `beats.js`, `motion.js`, `portrait.js`, `demos.js`, `flash.js`, `chip.js`, `montage.js`, `slices.js`, `boot.js`, `v5.sh` and the manifests.
- `plate.setGrade` is the only change to a 16:9 component. It is additive, and `film/main` renders as before.

## Open points

- **Audio.**
  - The first scope, meter and `measured.json` pass from the audio build is linked, and the scopes draw real traces.
  - Every demo in it has `level_matched: false`, so no "LEVEL MATCHED" line shows.
  - `v5.sh` renders silent video until `master_v5.wav` and `tiktok_v5.wav` exist.
- **Hero readouts.** Closed. The 3D hero render bakes in its own readouts (1.00 Hz, 50 %), not the heard settings, so `hero-readouts.js` defocuses the six readout windows on every hero frame (S03, S04, S20) from a per-source-frame table (hand-measured on frames 0 and 96, tracked between them). No hero number can be read.
- **Chip.** During a click-stop the chip's MIX % can lead the plate readout's 60 ms digit flip by one frame.
