# Kaizen DSP launch video

Source project for the Choroboros launch video (Kaizen DSP).

Work in progress. The composition, audio and render tooling will land here as they are built.

## Render tooling

Compositions are HTML pages that expose `window.__composition = { width, height, fps, duration, seek(t) }`.
`tools/render.mjs` captures them frame by frame in parallel headless Chromium processes and
encodes H.264 (High, yuv420p, BT.709, CRF 16, preset slow, AAC 320k, faststart).

```sh
npm install                 # pinned: playwright-core 1.56.1 (Chromium 1194), gsap, @fontsource/*
npm run demo:assets         # copy the demo image sequence into assets/ (gitignored)
node tools/render.mjs --comp tools/demo/index.html --out out/demo.mp4 [--preview] [--audio mix.wav]
node tools/stills.mjs --comp tools/demo/index.html --count 12     # QA stills + contact sheet
node tools/render.mjs --comp tools/demo/index.html --check-determinism count:10
node tools/test/run-tests.mjs                                      # end-to-end checks
node tools/render.mjs --help
```

Compositions import the runtime from `/__render/composition.js` (`defineComposition`,
`ImageSequence`, font and image helpers) and npm packages from `/__node_modules/`. Renders never
touch the network: fonts come from `@fontsource/*` or `tools/fetch-fonts.mjs`.

Needs Node 22, the Chromium 1194 builds under `/opt/pw-browsers` (or `CHROMIUM_PATH`), and an
ffmpeg with libx264 (`$FFMPEG`, the `imageio_ffmpeg` Python package, or `ffmpeg` on PATH).

Nothing proprietary belongs in this repo. Compositions that use plugin art live outside it and are
rendered with `--root` / `--mount`.
