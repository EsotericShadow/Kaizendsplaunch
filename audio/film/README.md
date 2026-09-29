# audio/film: the "Still Life" soundtrack build

This code builds the soundtrack of the Choroboros launch film. It produces:

- the 86.0 s main film;
- the 28.0 s vertical cutdown;
- the scope (goniometer) data the picture reads;
- the QC logs.

Everything is generated from code; nothing is recorded by hand. The musical decisions and the bar-by-bar arc are in [PRODUCTION_NOTES.md](PRODUCTION_NOTES.md).

## Run

```sh
audio/film/run_all.sh                  # everything: main film, then the vertical
audio/film/run_all.sh --no-sweep       # reuse the Purple pre-roll already in cues.json
audio/film/run_all.sh --no-vertical    # main film only
python3 audio/film/mix.py --film vertical   # any single step, for either cut
```

**Requirements:**

- the packages in `audio/requirements.txt` (numpy, scipy, soundfile, imageio-ffmpeg, and numba, strongly recommended);
- the local `choro-render` CLI.

**Renderer path:** `common.CHORO` finds the renderer at `/home/user/build/choro-render/build/choro-render`, or at `$CHORO_RENDER` if that is set. **The binary and the plugin source are referenced by path only.** They are never copied into, committed to or shared from this repository.

The build uses at most 2 processes. Renders run with `--jobs 2`.

## Pipeline

| Step | Module | What it does |
|---|---|---|
| 1 | `compose.py` | Writes the score (one 2-bar hook, the harmony map, grooves, bass, pad, EP, arp, lead, pluck, bells, FX) and renders the dry mono stems, the tour loops and `score.json`. |
| 2 | `render_dsp.py` | Renders R01-R12 and R09ref through `choro-render`. Every knob is explicit; the flags are `--block 128 --tail 3 --meta`. Automation follows the eased knob position every 10 ms. It sweeps the Purple pre-roll, checks every meta file, and copies the metas to `audio/logs/render-meta/`. |
| 3 | `levelmatch.py` | Matches loudness per bar (BS.1770-4, tolerance 0.3 LU). Gesture bars ramp on the gesture ease, and a mid-bar gesture gets its own pre-gesture gain. Writes `audio/logs/level-match.json` and the `levelmatch.result` block in `film/cues.json`. |
| 4 | `clips.py` | Cuts the Fold, Echolalia (with a pitch-bend check) and Stovetop (with downbeat detection) excerpts at -18 LUFS. Writes the clip fields in `film/cues.json` and `audio/logs/clips.json`. |
| 5 | `mix.py` | Does the section edit (`edit.py`), then the mix and the master. The honesty zones get gain only. Everywhere else there are FDN plate and hall sends (modulation off), delay throws, tape, drum-bus parallel compression, kick sidechain and glue. A low shelf (80 Hz, -3 dB; -3.5 dB in the vertical) on the drum and bass buses keeps the sub in check. Under the product clips the music bed is muted (bass and kick only under Fold and Echolalia, nothing under Stovetop). The master chain is master gain, a true-peak limiter at -1.1 dBTP with at most 1 dB of gain reduction, the fade and the hard silences. |
| 6 | `scope.py` | Writes int16 (mid, side) data, 400 points per frame, one film gain (-12 dBFS maps to 0.45), for each featured stem and the mix. |
| 7 | `qc.py` | Runs treatment 11 items 1-4 and 10, the honesty-zone proofs, the mono fold, the digital silences, the join click scan, the P-block identity and the stem-sum check. Writes `audio/logs/qc.json` and `audio/logs/arc.json`. |
| 8 | `vertical.py` | Builds the vertical arrangement and writes `film/cues-vertical.json`. It then runs steps 2, 3, 5, 6 and 7 with `--film vertical`. |

**Support modules:**

- `common.py`: paths, the `Film` main/vertical switch, timing, I/O and loudness helpers.
- `instruments.py`: the film instruments, built on `audio/synth`. They are dry and mono, with no internal modulation.
- `edit.py`: the section edit and the joins.
- `analyze.py`: spectrogram PNGs and objective numbers, written to `<build>/png/`.

## Outputs

Heavy outputs go under `/home/user/build/film/` and are not committed.

| Path | Contents |
|---|---|
| `audio/stems/` | dry mono stems |
| `audio/renders/` | Choroboros renders and metas |
| `audio/edit/` | section-edited stems |
| `audio/mix/` | the stems as heard (`stem_*.wav`, which sum to the master), the float `mix.wav`, `mix_info.json` and the gain curves |
| `audio/master.wav` | the main master, 48 kHz 24-bit |
| `audio/vertical/` | the same structure for the vertical cut |
| `audio/vertical-master.wav` | the vertical master |
| `data/scope/` and `data/scope-vertical/` | `<stem>.i16` files plus `index.json` (5160 and 1680 frames) |

**In the repository:**

- `audio/logs/`:
  - `level-match*.json`, `qc*.json`, `arc*.json`, `clips.json`, `render-log*.json`;
  - `render-meta/R*.json`, with `*-vertical.json` for the vertical renders.
- `film/cues.json`: fields are added only (pre-roll, swoosh time, level-match result, clip fields); no timing changes.
- `film/cues-vertical.json`.
