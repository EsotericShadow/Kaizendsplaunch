# Audio map (v5)

This is the map of the owner's song that the portrait film, the TikTok and the Choroboros demos are cut against. Every time in this folder is **master time**: seconds from the first sample of the master mp3, decoded gapless at 48 kHz (the LAME encoder delay of 576 samples and the decoder delay of 529 are removed). The song plays straight through from its first sample, so master time = film time.

| File | What it holds |
|---|---|
| `grid.json` | Tempo, 4/4 bars 1-104, all 416 beats and 104 downbeats, the tempo curve, the fit, and the validation |
| `hits.json` | Drum hits `[t, dB]` per piece (kick, snare, rack tom, floor tom, hi-hat, crash, other cymbal), plus fills |
| `sections.json` | 17 sections, a per-bar table (loudness, drums vs non-drum, hits, 16th-note groove), guitar-alone windows, the first-3 s events, TikTok candidates |

The scripts are in `audio/forensics/` (run in order `s1_decode.py` … `s6_map.py`). Audio outputs go to `/home/user/build/v5`: `master_src.wav`, `stems/*.wav` (aligned drums, `nondrums.wav`, `other.wav`) and `work/` (intermediate files, `other_report.json`). No audio goes into the repo.

## Key facts

- **Tempo: 148.000 BPM, constant, from the first hit to the last.** The fit gives 148.0001 ± 0.0005 BPM (period 0.405405 s). Kick and snare attacks sit a median of 0.68 ms off the grid (90 % within 3.1 ms). The local tempo in 8 s windows reads 147.96 to 148.11 BPM (147.70 only in the sparse 88-96 s window, which spans a drum break with 11 hits), and the grid phase stays within about ±4 ms across all four drum breaks. The drums are a click-locked, edited take. The lead's preliminary "147.0 to 148.8 BPM wander" is not in the music; it was measurement noise.
- **Bars:** 4/4, 104 bars. Bar 1 starts at **t0 = 0.4048 s** on the first hit of the song (crash + kick + rack tom). Bar n starts at `0.4048 + (n - 1) × 1.621622 s`. Bar 104 ends at 169.053 s, which is the last sample of the file. There is no pickup: before 0.405 s there is only silence and a faint swell at -65 to -54 dBFS.
- **Drum stems:** all seven share one session timeline. The kit is aligned at `master_t = stem_t - 2.837833 s` (136 216 samples) at speed 1.000000 (every stem's slope is under 0.2 ppm, and every stem agrees within 1.8 samples).
- **The second mp3 is not time-locked to the master.** It holds the non-drum part (guitar plus the low bass that only plays with the drums), in a different mix and on a different timeline. Its offset wanders from -435 ms to -654 ms in steps (details in section 3). It cannot be subtracted from the master cleanly. **Use the master's own non-drum part instead** (`stems/nondrums.wav` = master minus the fitted drums). It is sample-locked, and fitted drums + non-drum part = master exactly.
- **The old 152.02 BPM grid is wrong.** It fails every test below at chance level, as does any constant 152 BPM grid.

## 1. Reference decode (`s1_decode.py`)

ffmpeg decodes the master gapless, honouring the LAME tag: delay 576 + decoder 529 = 1105 samples trimmed at the start, 507 at the end. The result is 7 455 284 samples at 44.1 kHz = 169.0541 s, and libsndfile decodes the same samples to within 4e-6. The 44.1 → 48 kHz step is a linear-phase polyphase FIR (160/147, Kaiser, 35 529 taps, pass band to 20.5 kHz, about -120 dB from 22.05 kHz) whose group delay is removed exactly. An impulse test puts 44.1 kHz sample 14 700 at 48 kHz sample 16 000.000 (centroid). The first sample of `master_src.wav` is t = 0.

## 2. Stem alignment (`s2_align.py`)

The method is band-limited GCC-PHAT against the master in 6 s windows across the song (27 windows, 24 for the toms, placed where they play), with a sub-sample peak and a straight-line fit of lag against time.

| Stem | Lag (samples) | Slope (ppm) | Fit rms (samples) | Windows used |
|---|---|---|---|---|
| Kick | 136 215.3 | -0.02 | 0.19 | 25/27 |
| Snare | 136 215.7 | -0.06 | 0.25 | 25/27 |
| Hi-hat | 136 215.9 | 0.00 | 0.02 | 26/27 |
| Rack tom | 136 214.2 | -0.02 | 0.32 | 20/24 |
| Floor tom | 136 214.7 | -0.16 | 0.56 | 16/24 |
| OH left (vs master L) | 136 216.1 | 0.00 | 0.06 | 26/27 |
| OH right (vs master R) | 136 216.1 | -0.01 | 0.04 | 27/27 |

All seven stems start their first non-zero sample within one sample of each other, so they are shifted by one common lag, 136 216 samples. That keeps the kit's own inter-mic timing intact.

## 3. The second mp3: what it is, and what to do instead (`s3_other.py`)

**Contents.** It is 48 kHz stereo, 169.44 s long, and 3.5 dB quieter than the master in RMS. The octave-band levels, measured at its local offset, show:

| Window | Master 8-16 kHz | Second mp3 8-16 kHz | Master 20-60 Hz | Second mp3 20-60 Hz | Drum stems 20-60 Hz |
|---|---|---|---|---|---|
| 55-60 s (crash every bar) | -46.5 | -80.4 | -36.8 | -43.2 | -51.4 |
| 17-22 s (riff 1) | -48.1 | -54.1 | -37.5 | -41.3 | -51.7 |
| 30.5-35.5 s (no drums) | -100.7 | -91.1 | -70.1 | -69.6 | (silent) |

So it has no cymbals or hats (34 dB less top octave than the master under a crash-every-bar passage). It carries the guitar, and a 20-60 Hz part (a bass) that plays only when the drums play and that the drum stems do not explain. Between 60 Hz and 2 kHz it sits about 2 to 3 dB under the master's non-drum part, and it is narrower (L/R correlation 0.71 against 0.56).

**Timing.** A GCC-PHAT lag curve against the drum-free master (2 s windows every 0.5 s, 90 confident windows) gives `other_t = master_t + lag`. The lag is about -435 ms at 12 s and -654 ms at 167 s. It is a staircase, not a line: flat plateaus (-454.5 ms from 30 to 38 s, -468.0 ms from 45 to 55 s, -486 ms around 62 s, -482 ms from 67 to 75 s) with jumps of 3 to 35 ms between them, sometimes moving back (for example -486 → -482 ms). A straight-line fit leaves ±46 ms.

A whole-song tempo comb (onset strength against a 146.5 to 150 BPM sweep, 16th-note harmonic) shows the difference:

- **Master:** sharp at 148.005 BPM (half-width 0.105 BPM).
- **Master's non-drum part:** 148.005 BPM.
- **Second mp3:** smeared, peaking at 148.34 BPM (half-width 0.36 BPM).

The master (guitar included) is on the 148 BPM grid. The second mp3 is the same performance on a different, region-edited timeline, most likely an earlier or unedited version of the non-drum tracks. The lead's "+0.44 s" was one point on this curve.

**Model test.** The test fits the master as the drum stems plus the second mp3, with a complex gain per stem per 11.7 Hz bin, refit every 3 s. The residual is relative to the master; a true stem of this master would take it far below -20 dB.

| Model | Residual (whole song) |
|---|---|
| Drums only | -1.6 dB |
| Drums + second mp3, best constant lag | -3.0 dB |
| Drums + second mp3, warped through the lag curve | -3.9 dB |

Its best 2 s block is -13.4 dB (32 to 34 s, guitar alone, where the lag is flattest). Typical drum sections sit at -2 to -6 dB. The per-band and per-2 s values are in `/home/user/build/v5/other_report.json`.

**Verdict.** "Replace the guitar bus inside the master" (master + choro(other) - fitted(other)) is **not clean**. Subtracting the fit would leave most of the dry guitar in place, and the timing errors would comb and flam. `stems/other.wav` is written (warped through the lag curve) for listening only; it is not sample-locked.

**Use instead:**

1. **In the guitar-alone windows, process the master itself** (bars 15-22, 53-56, 69-72, 84-87; see section 6). There the master is the guitar: the drum stems are digital silence or a decaying crash. Choroboros on the whole master is 100 % clean there, Mix sweeps included.
2. **Everywhere else, process the master's own non-drum part:** `out = drums_fit + choro(nondrums)`. Because `drums_fit + nondrums = master` exactly, Mix at 0 returns the master (given a transparent dry path). `nondrums` still holds some drum residue: the linear fit removes only about 6-7 dB of the processed cymbals (8-16 kHz, measured in a crash-every-bar passage). The guitar has almost nothing above about 6 kHz (the guitar-alone windows read -62 dB at 4-8 kHz and -100 dB at 8-16 kHz, against -37 dB at 500 Hz-1 kHz). So feed Choroboros a low band of `nondrums` (crossover near 5-6 kHz) and pass the top band dry: `out = master - lowband(nondrums) + choro(lowband(nondrums))`. This choruses the guitar without smearing the cymbals.
3. **A parallel wet path** (master + g × wet-only output of Choroboros fed by `nondrums`) is the most forgiving alternative, because nothing is subtracted.

## 4. Beat grid (`s4_grid.py`)

**Method.** The kick and snare attacks (s5, below) are each assigned to the nearest 16th note, and (t0, period) are solved by iterated least squares, dropping attacks more than 30 ms off: 434 of 435 were used. Nothing forces a constant tempo, and two checks allow drift:

- **8 s windows:** the same fit in every 8 s window gives a local BPM and phase (`grid.json → tempo_curve_8s`).
- **Independent tracker:** a dynamic-programming beat tracker (log-interval penalty, ±12 % beat-to-beat freedom) runs on all drum hits plus the guitar's onset strength. All 411 of its beats land on a grid beat: median 1.8 ms off, maximum 29 ms (inside fills), none on the wrong beat.

**Bars.** The 4-beat phase is chosen to put loud snares on 2 and 4 and crashes on 1. Phase 0 (bar 1 = the first hit) scores 80.5, against 49.0 for the half-bar phase and -70 to -74 for the others.

**Validation** (the same code for every grid):

| Test | This grid | Old grid 152.02 BPM | Old grid, best shift (-9 ms) | Best constant 152 BPM | DP live-tempo grid |
|---|---|---|---|---|---|
| Loud snares on beat 2 or 4 | **73.6 %** | 8.2 % | 8.2 % | 7.3 % | 73.6 % |
| Loud snares off every beat (> 35 ms) | **6.4 %** | 80.9 % | 80.9 % | 85.5 % | 6.4 % |
| Per-bar kick/snare mean offset from the 8th grid, median | **0.7 ms** | 45.0 ms | 46.8 ms | 53.1 ms | 1.0 ms |
| Bars whose mean offset is within 10 ms | **100 %** | 11.8 % | 11.8 % | 4.8 % | 98.8 % |
| Held-out hits (hi-hat, toms, overhead rise times of crashes and cymbals; 408), median distance to the 16th grid | **6.3 ms** | 25.1 ms | 25.2 ms | 25.4 ms | 5.2 ms |
| Held-out hits within ±10 ms (chance ≈ 20 %) | **61 %** | 20.3 % | 19.6 % | 17.9 % | 72.1 % |

The 20 % of loud snares on 1 or 3 come from the passages where the snare plays every beat (the build, bars 74-76, and the drive, bars 88-95). The held-out set uses the overheads' own rise times, which lead the kick by about 10 ms, so its errors are an upper bound. The per-bar phase coherence R (not in the table) is high even for the 152 grids (about 0.93), because one bar is too short to reveal a 2.7 % tempo error. The per-bar offset is the discriminating measure.

## 5. Hit map (`s5_hits.py`)

No stem is gated, and every close mic hears the whole kit. Hits are found as HF-rise onsets clustered across mics. A hit is kept only when its own mic beats the bleed the other mics predict. The rules sit in the gaps of mic-against-mic scatter plots:

| Piece | Rule |
|---|---|
| Kick | Kick-mic 40-100 Hz onset > -29 dB, with a beater click |
| Snare | 150-400 Hz > -28 dB, with a crack |
| Rack tom | 90-170 Hz > -24 dB and 4 dB above the kick and snare bleed |
| Floor tom | 45-90 Hz > -34 dB, 6 dB above the kick and rack bleed, and its own stick crack present |
| Crash | An overhead peak at -34 dBFS or louder that stays within 10 dB for ≥ 160 ms (snare, tom and hat bleed drops 10 dB in < 120 ms) |

Measured pitches: kick about 65 Hz, floor tom 55-70 Hz, rack tom 105-130 Hz (with a glide), snare about 285 Hz.

| Piece | Hits | Median distance to the 16th grid | Confidence |
|---|---|---|---|
| Kick | 277 | 0.7 ms | High |
| Snare | 158 | 0.8 ms | High |
| Rack tom | 108 | 5.6 ms | Good |
| Floor tom | 108 | 2.5 ms | Moderate: its mic rings in sympathy; a few weak intro hits between 16ths (1.28, 1.99 s) may be resonance |
| Hi-hat | 91 | 3.5 ms | Only clear, separate hat strokes (18 of them open); hats under snare hits are not listed |
| Crash | 57 | 1.1 ms | High |
| Other cymbal | 44 | 1.4 ms | Moderate |

A crash's `t` is the kick, snare or tom attack it lands with; its own 6-16 kHz rise starts about 10 ms earlier and is kept as `overhead_rise_s`. The loudest crash in the song is the bar-53 stop, at 84.733 s.

**Fills** (`hits.json → fills`):

| Bar | Time (s) | Fill |
|---|---|---|
| 8 | 12.767-12.980 | Snare + toms into riff 1 |
| 30 | 47.414-48.649 | Whole-bar snare + floor tom into the verse |
| 40 | 64.959-65.170 | Snare 16ths |
| 67-68 | 107.819-110.270 | Two-bar snare/floor-tom build into the stop |
| 76 | 123.440-123.542 | Snare 16th pickup into the drop |
| 96 | 155.878-156.287 | Toms |
| 103 | 166.115-166.520 | Floor tom into the last crash |

## 6. Section map (`s6_map.py`)

The boundaries are read off the per-bar table in `sections.json`, where the groove signature changes, the drums stop, or the loudness steps. The figures are computed.

- **LUFS:** BS.1770 K-weighted mean over the section.
- **LUFS per bar:** the range of the per-bar values.
- **Gtr - drums:** the per-bar median of non-drum loudness minus fitted-drum loudness.

| # | Section | Bars | Start (s) | End (s) | LUFS | LUFS per bar | Drums | Drum hits/bar | Gtr - drums (dB) | Gtr onsets/bar | Crashes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Intro: tom groove | 1-8 | 0.405 | 13.378 | -12.9 | -13.8 to -12.3 | in | 10.6 | -1.4 | 8.9 | 1 |
| 2 | Riff 1: full band, backbeat | 9-14 | 13.378 | 23.108 | -8.8 | -9.7 to -8.4 | in | 8.3 | 6.6 | 17.2 | 5 |
| 3 | Stop, then guitar alone (long) | 15-22 | 23.108 | 36.080 | -17.6 | -19.6 to -15.8 | out after the downbeat hit | 0.4 | 26.1 | 5.6 | 1 |
| 4 | Tom groove 2 | 23-30 | 36.080 | 49.053 | -13.1 | -13.9 to -12.6 | in | 10.4 | -1.6 | 7.9 | 0 |
| 5 | Verse: backbeat, sparser guitar | 31-38 | 49.053 | 62.026 | -10.4 | -11.3 to -9.2 | in | 8.1 | 3.6 | 10.8 | 7 |
| 6 | Riff 2: loudest, busiest guitar | 39-44 | 62.026 | 71.756 | -8.7 | -9.5 to -8.3 | in | 8.5 | 6.5 | 14.7 | 6 |
| 7 | Accent section: crash pushes | 45-52 | 71.756 | 84.729 | -8.8 | -9.4 to -8.2 | in | 9.0 | 5.3 | 17.5 | 18 |
| 8 | Stop, then guitar alone | 53-56 | 84.729 | 91.216 | -16.7 | -18.2 to -14.8 | out after the downbeat hit | 0.8 | 23.2 | 5.8 | 1 |
| 9 | Tom groove 3, guitar rising | 57-66 | 91.216 | 107.432 | -11.6 | -13.5 to -10.2 | in | 9.5 | 2.0 | 9.3 | 0 |
| 10 | Snare and floor-tom build | 67-68 | 107.432 | 110.675 | -10.2 | -10.4 to -10.0 | in | 15.0 | 5.5 | 13.0 | 0 |
| 11 | Stop, breakdown: quietest guitar alone | 69-72 | 110.675 | 117.161 | -20.3 | -23.1 to -16.9 | out after the downbeat hit | 0.5 | 28.6 | 10.2 | 1 |
| 12 | Build: hi-hat, then snare on every beat | 73-76 | 117.161 | 123.648 | -16.4 | -19.4 to -14.0 | in | 11.5 | 0.3 | 13.5 | 0 |
| 13 | Riff 3, with a stop-time bar | 77-83 | 123.648 | 134.999 | -9.2 | -13.6 to -8.4 | in | 8.9 | 7.1 | 15.0 | 7 |
| 14 | Stop, then guitar alone | 84-87 | 134.999 | 141.486 | -18.6 | -21.5 to -16.8 | out after the downbeat hit | 0.5 | 28.2 | 5.5 | 0 |
| 15 | Drive: snare on every beat | 88-95 | 141.486 | 154.459 | -9.8 | -11.0 to -9.0 | in | 7.8 | 5.2 | 14.6 | 8 |
| 16 | Outro: tom groove | 96-103 | 154.459 | 167.432 | -13.0 | -13.2 to -12.7 | in | 11.0 | -0.1 | 7.9 | 2 |
| 17 | Ring-out | 104 | 167.432 | 169.053 | -20.1 | -20.1 | out | 0.0 | 21.7 | 0.0 | 0 |

**Grooves:**

- **Tom groove:** kick on every beat, rack tom on most beats, floor tom on the off-beats, no snare.
- **Backbeat:** snare on 2 and 4; kick on 1 (or its "and"), on 3 and the "and" of 3, and on the "and" of 4 into the next bar; a crash on 1 of every other bar; a 16th-note snare pickup ends the even bars.
- **Accent section:** crash + kick on 1, the "and" of 2 and the "and" of 4 in every other bar.
- **Drive:** snare on every beat.

**Stops** (a single hit on the downbeat, then the drums are silent):

| Bar | Time (s) | Hit |
|---|---|---|
| 15 | 23.108 | Kick, hat, crash |
| 53 | 84.729 | Kick, snare, crash; the loudest crash |
| 69 | 110.675 | Kick, crash |
| 84 | 134.999 | Kick, snare |

Bar 80 (128.510) is a stop-time bar: a hit on 1, silence, then a crash on the "and" of 4 at 129.932.

**Big entries** (crash + kick on the downbeat after a change):

| Time (s) | Bar | Note |
|---|---|---|
| 0.405 | 1 | Out of silence |
| 13.378 | 9 | |
| 49.053 | 31 | |
| 62.026 | 39 | |
| 71.756 | 45 | |
| 123.648 | 77 | Drop after the build |
| 141.486 | 88 | +14 dB over the second before |
| 166.622 | 103 | Last crash |

**Guitar alone or sustained.** The master is the guitar in these windows, and its momentary loudness holds steady at -17 to -20 LUFS. The guitar keeps playing and does not die away.

| Bars | Time (s) | Note |
|---|---|---|
| 15-22 | 23.108-36.080 | Crash ring until about 24.0; drum stems digital silence 29.6-34.5 |
| 53-56 | 84.729-91.216 | Crash ring until about 85.4 |
| 69-72 | 110.675-117.161 | The quietest part |
| 84-87 | 134.999-141.486 | |
| 104 | 166.622-169.053 | The last crash and the guitar decay (-14 → -26 LUFS) |

## 7. Recommendations

### Hook in the first 3 s

The song is silent until **0.405 s**, then hits with crash + kick + rack tom: the master peaks at -3.0 dBFS within 10 ms, and the 400 ms loudness jumps from silence to -12 LUFS. Put frame 0 on black or a still, and make the first cut on 0.405 s.

After that the pulse is the kick (with the rack tom on most beats) on the quarter notes: 0.810, 1.216, 1.622, 2.025, 2.433, 2.837 s. Floor-tom off-beats fall at 1.808 (bar 1, beat 4.5) and 2.637 (bar 2, beat 2.5). Those quarter notes are the cut points for a fast opening montage. The full list is in `sections.json → first_3s_events`.

### TikTok: one continuous 15 s stretch, starting on a bar line

Ranked by musical arc. Loudness and contrast are computed in `sections.json → tiktok_15s_candidates`.

1. **Bar 45, 71.756-86.756 s.** Starts on crash + kick inside the loudest stretch (first second -8.2 LUFS). Then 13 s of crash pushes: 18 crashes in 8 bars, the densest set of visual accents in the song. At 12.97 s the whole band stops on the song's loudest crash (bar 53, 84.729), leaving 2 s of ring and solo guitar for the Buy card: hook, vitality, drive, release.
2. **Bar 88, 141.486-156.486 s.** The biggest entry: crash + kick + snare, +14.3 dB over the second before it. Snare on every beat and a crash every two bars; the tom-groove outro arrives at 13 s for the Buy card.
3. **Bar 77, 123.648-138.648 s.** The drop after the build (crash + kick). Stop-time bar 80 at 4.9 s is a built-in freeze frame, bar 83 is all pushes, and the full stop at 134.999 (11.35 s in) leaves the guitar alone for the close. A variant starts one bar earlier at **122.027** (bar 76): 1.6 s of rising snare, then the drop. It gives a stronger build but a softer first frame.
4. **Bar 1, 0.405-15.405 s.** The song's own opening hit out of silence (+57 dB contrast), the tom groove, then riff 1 lands at 13.378 (13 s in).
5. **Bar 39, 62.026-77.026 s.** Riff 2, the loudest and busiest guitar, constant energy (-8.7 LUFS over 15 s) with no release inside.
6. **Bar 9, 13.378-28.378 s.** Riff 1, then the stop at 23.108 (9.7 s in) and 5 s of guitar alone.

### Where Choroboros on the guitar is most audible and most musical

1. **Bars 15-22, 23.108-36.080 s (best).** 13 s of guitar alone after the crash dies (about 24.0 s), steady, 5.6 guitar onsets per bar (chordal, sustained), no drums. Process the master itself here. The window divides evenly for an engine tour: 8 bars of 1.622 s, for example 2 bars (3.24 s) per engine for four engines, switching on the downbeats listed in `grid.json`.
2. **Bars 53-56, 84.729-91.216 s.** Guitar alone after the bar-53 stop. This is the natural place for the payoff and the end card.
3. **Riff 1, 13.378-23.108, and riff 2, 62.026-71.756.** The guitar leads the drums by 6.5 dB. This is the place for a dramatic Mix turn, processing `nondrums` as in section 3 so the drums stay dry.
4. **Tom grooves (bars 1-8, 23-30).** The guitar is level with the drums (-1.4 dB). A chorus is audible, but it shares space with the toms. Use it for subtler moments.
5. **Beyond 95 s:** bars 69-72 (110.675-117.161, the quietest guitar) and bars 84-87 (134.999-141.486).

### End points for a 55-95 s film that starts at the first sample

| End (s) | Film length | Where | Musical reason |
|---|---|---|---|
| **86.35** (fade from about 85.1) | 86.35 s | The bar-53 stop, 84.729, with its crash ring | The only full-band stop between 55 and 95 s. It closes the 22-bar block of verse, riff 2 and accents (bars 31-52) on the loudest crash in the song, and the crash has decayed into the guitar by about 85.4 s. **Best.** |
| **91.216** (fade over bar 56, 89.59-91.22) | 91.2 s | Just before the tom groove re-enters on bar 57 | Completes the guitar's 4-bar solo answer after the stop. A calm end card over solo guitar; cut exactly before 91.216. |
| 72.3 to 72.5 (0.5-0.7 s after the hit, short fade) | about 72.4 s | "Button" on the bar-45 crash, 71.756 | The end of riff 2 on a crash downbeat. The band keeps playing, so it needs the fade; less natural. |
| 62.6 to 62.8 | about 62.7 s | "Button" on the bar-39 crash, 62.026 | The end of the verse; same caveat. |

The first stop (bar 15, 23.108) is too early for a 55 s film. The song's own ending (the last crash at 166.622, ring-out to 169.053) is the most final-sounding end, but it lies beyond 95 s.

## 8. Reproduce

```
python3 audio/forensics/s1_decode.py   # master_src.wav, master_src.json
python3 audio/forensics/s2_align.py    # stems/*.wav (drums), align.json
python3 audio/forensics/s5_hits.py     # work/hits_raw.npy (hits and envelopes)
python3 audio/forensics/s3_other.py    # stems/nondrums.wav, stems/other.wav, other_report.json
python3 audio/forensics/s6_map.py      # runs the grid (s4_grid.py) and writes film/v5/*.json
```

The inputs are the owner's files in the upload folder (found by their stem suffix; `SONG_UPLOADS` overrides the folder). Outputs go to `/home/user/build/v5` (`V5_OUT` overrides) and `film/v5`.
