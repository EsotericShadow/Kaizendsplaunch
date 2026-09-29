# Still Life: production notes

These notes describe the soundtrack of the Choroboros launch film "Still Life": the 86.0 s main film and the 28.0 s vertical cutdown.

They record the owner's production pass. Where that pass conflicts with treatment 3.3 and 8.5, the pass wins.

The picture is unchanged:

- Every section time, silence, impact, gesture time and Choroboros render setting is unchanged from `film/cues.json`.
- The only picture-side change is the video description line (section 9 below).

All numbers below come from the logs that the pipeline writes: `audio/logs/arc*.json`, `qc*.json` and `level-match*.json`. Rerun `audio/film/run_all.sh` to reproduce them.

## 1. The rules

### A. Honesty zones are strict

The honesty zones are 0.00-8.00 and 16.00-36.00 in the main film, and 0.00-14.00 in the vertical.

Inside a zone, the featured guitar is its Choroboros render, section-edited, times one scalar gain curve, and nothing else:

- no send, reverb, delay, saturation, EQ, glue or limiting after the plugin;
- the plate, hall and delay returns are exactly zero;
- every other music stem is exactly zero.

The backing in the zones (drums, bass, the treatment's FX) is produced: tape, parallel compression, a mono room. It carries no modulation and is mono.

In the main tour, the drums and bass are pasted from one steady-state render. They are sample-identical in all five passes. Pass 5 (Black) stops at 35.50 as the treatment says, so it is compared up to 35.49.

The only sounds in the zones besides the guitar and backing are the treatment's mono FX:

- the reverse-guitar swell into 8.00;
- the four noise swishes under the chorus smears at 20, 24, 28 and 32;
- the reverse crash into 16.00.

QC proves all of this sample by sample. See `honesty_zones` in `qc.json` and `qc-vertical.json`.

### B. Everywhere else, it is produced like a record

- **Sends:** a plate (RT60 1.6 s) and a hall (2.6 s). Both are 8-line FDNs with pre-delay and damping, and their modulation is off.
- **Delay throws:** a tempo-synced ping-pong delay (0.75 / 1.0 beat) opens only at phrase ends.
- **Saturation:** tape on the drum bus, the bass, the EP and the pad.
- **Drums:** parallel compression on the drum bus.
- **Room:** a mono room on the backing.
- **Sidechain:** the kick ducks the pad and arp by 3.5 dB in the offer.
- **Glue:** 2:1, 20 ms attack, 160 ms release. Its threshold is solved for a 2.5 dB mean gain reduction across the offer peak (50-62), and it is looser elsewhere.

**The only chorus or modulation effect in the film is Choroboros.** No synth has vibrato, unison, detune or PWM. No reverb is modulated. The EP has its tremolo and detune off. The pad has its LFO and unison off.

### C. One hook

The take is a spacious 2-bar hook. It plays five notes a bar on the cells 1, 1&, 2&, 3&, 4, with let-ring on 2& and 4 so the chorus has room to be heard.

| Figure | Chord | Notes |
|---|---|---|
| T1 | Dmaj9 | D3 . A3 . . F#4 . . C#4 E4 |
| T3 | Bm11 | B2 . F#3 . . E4 . . A3 D4 (A3) |
| T4 | A7sus4 to A7 | A2 . E3 . . D4 . . G3 C#4 |

The velocity shape is 100 / 72 / 92 / 66 / 86 (60 on the pickup). The take seed is 1954.

- In T1, the top line falls F#4 to E4.
- In T3, E4 resolves to D4: sus4 to b3, played as a pull-off.
- In T4, D4 resolves to C#4 on beat 4, the dominant before a drop.

Where the hook is heard:

| Time | How the hook is heard |
|---|---|
| 0.00 | Dry, at Mix 0%. |
| Tour | Through all five engines, as block P (T1 then T3, rendered once and pasted sample-identical at 16, 20, 24, 28 and 32). |
| 50.00 and 58.00 | Block P again, at the offer peak. The lead answers it at 58: A5 F#5 E5, then D5 C#5 A4. |
| 70.00 | Alone at the payoff, with **the same notes, velocities and seed as the opening**. |

Between these points the guitar plays variations of the same cell over G and A (M_G, M_A, M_A7).

### D. Tension and release

- **Before the title (8.00):** A7sus4 to A7 in bar 4, with the suspension resolving at 7.50. A reverse guitar swell and a riser lead into 8.00; the tonic is withheld until the impact.
- **Before the tour (16.00), the price card (58.00) and the final chord (78.00):** A7sus4 to A7 again.
- **The breakdown (36-46):** floats on Gmaj9#11 and Bm11 with a bell cascade (bar 19). Bar 21 is nearly empty (4 onsets) before the guitar returns at 42.
- **The build (46-49.85):**
  - G/A over an A pedal;
  - the bass pulses the A pedal in 8ths;
  - A7sus4 to A7;
  - the pad low-pass opens from 700 Hz to 9 kHz;
  - the arp moves from dotted 8ths to 16ths while its filter opens from 700 Hz to 6.3 kHz;
  - a snare roll, a riser (-32 to -18 dBFS) and a reverse crash.

  It is then cut to digital silence for 150 ms.
- **The drop (50.00):** Dmaj9 with the impact, a downlifter, crash, the full groove B, block P, pad, arp, bass and octave double. It is the loudest section of the film: it averages -11.5 LUFS against -11.9 for the price card, and its second bar (bar 27, -11.4 LUFS) is the loudest bar. The build bar before it is -12.4 LUFS.
- **The coda (62-69.5):** hovers on G and A under the three field clips; the tonic is withheld.
- **The payoff (70.00):** the hook alone, after 0.5 s of digital silence.
- **The final Dmaj9 (78.00):** the deepest release. It is a six-string strum with the pad, a D2 bass, a soft kick and crash, and the hall. The mix then thins to pad, bass and hall.
- **82.00:** a single F#4 over near-silence, with a delay throw, and a fade from 84.50.

### E and F. Arrangement and layering

| Element | What it is |
|---|---|
| Drums | Round-robin layered kick (body + sub tail + click) and layered snare (body + clap + noise tail), each hit re-synthesised. Closed hats, open-hat lifts on 4&, ghost notes, rim, a shaker in the offer, crashes on the drop downbeats. |
| Grooves | Groove A is half-time (title, lineup, tour). Groove B is full (offer). Fills: small, roll, full, a flam, a 16th pickup. Swing is 54% on the 16ths, and the hits are humanised with fixed seeds. |
| Bass | Layered: a clean sub sine plus a high-passed, tube-saturated mid layer that reads on phone speakers. Chromatic pickups (C#2 to B1, F#2 to G1, G#2 to A1) and an A pedal in the build. |
| Guitar extras | An octave double outside the zones (dry, then sent to the plate and hall). Attack pitch drift (2 + 4v cents, settling in 60 ms) and fret-hand squeaks before the shifts. These are string physics, not effects. |
| Pad | Juno-style pad plus a choir "aah" layer at -7 dB (formants, no vibrato, no unison). |
| EP | EP plus a quiet FM bell layer at -17 dB. |
| Arp | Analog-style pluck arp (saw + pulse through a ladder filter) in the title and lineup, from 40 in the create section, in the build and in the offer, with its filter swept. |
| FX | Risers, two impacts, downlifters after them, reverse crashes into 16, 49.85, 58 and 78, a reverse-guitar swell into 42, and the four smear swishes. |

## 2. What is processed where (main film)

| Span | Featured stem(s) through Choroboros | After the plugin | Backing |
|---|---|---|---|
| 0.00-8.00 | gtr R01 (dry, then the Mix turn) | gain only | FX (riser, reverse swell), mono, no modulation |
| 8.00-16.00 | gtr R01 | plate, hall, delay throws, glue | groove A, bass, arp, octave double, impact, downlifter |
| 16.00-36.00 | gtr R02-R06 (the tour) | gain only | drums + bass pasted sample-identical per pass, mono room; smear swishes |
| 36.00-46.00 | pad R07; gtr R01 from 42 | sends, glue | bells, arp, choir, bass, sparse kick and rim |
| 46.00-49.85 | pad R07, gtr R01 | sends, throws, glue | build: pedal, filter sweeps, roll, riser |
| 50.00-62.00 | gtr R01/R03, pad R08/R09, EP R10, lead R11, pluck R12 | sends, throws, sidechain, glue (mean gain reduction 2-3 dB), limiter up to 0.85 dB | groove B, bass, arp, crashes |
| 62.00-69.50 | pad R07, clips (-18 LUFS; bed ducked 6 dB) | sends, glue | quiet drums and bass |
| 70.00-86.00 | gtr R01, pad R07 | plate and hall (the payoff guitar is heard with the room around it) | end card and final chord |

The level-match gain for the featured stems is logged per bar in `audio/logs/level-match.json`. Every checked bar passes with a residual of at most 0.013 LU (vertical: 0.015 LU).

## 3. Loudness and dynamics

| Measure | Main | Vertical |
|---|---|---|
| Integrated | -14.4 LUFS | -14.4 LUFS |
| True peak | -1.1 dBTP | -1.1 dBTP |
| Limiter maximum gain reduction | 0.85 dB (none in the honesty zones) | 0.84 dB |
| LRA (ffmpeg) | 6.1 LU | 5.9 LU |
| Mono-fold drop, whole film | 1.01 LU | 0.96 LU |
| Mono-fold drop, worst section | 1.91 LU (payoff: the guitar is Choroboros Green at width 130%) | 1.74 LU |

The arc is quiet, then open, then dense:

- the opening is around -18.5 LUFS per bar;
- the tour is about -14;
- the breakdown is about -18.4;
- the drop (bars 26-27) is the loudest section;
- the coda is about -17;
- the payoff is -17 to -16;
- the final chord is -14.7, then the tail falls to -30.

## 4. Bar-by-bar arc, main film (86.0 s, 120 BPM, 2.000 s bars)

Column notes:

- **LUFS:** BS.1770 loudness of each 2 s bar of the master.
- **Short-term:** the 3 s loudness at the bar end.
- **Crest:** sample peak over RMS.
- **Onsets:** the number of onsets detected in the master.
- **Mono-fold drop:** the loudness lost when L and R are summed.
- **Stems:** as heard in the final mix.

| Bar | Time (s) | Section | Harmony | Audible stems (RMS > -42 dBFS) | LUFS (bar) | Short-term at bar end | Crest dB | Onsets | Mono-fold drop LU |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | 0.00 | cold-open | Dmaj9 | gtr | -18.4 | -18.4 | 12.8 | 5 | 0.00 |
| 2 | 2.00 | mix-turn/tagline | Dmaj9 | gtr | -18.4 | -18.4 | 13.8 | 5 | 1.00 |
| 3 | 4.00 | tagline | Bm11 | gtr | -17.5 | -17.6 | 13.5 | 5 | 1.67 |
| 4 | 6.00 | tagline | A7sus4 > A7 | gtr fx | -15.3 | -15.9 | 14.8 | 3 | 1.03 |
| 5 | 8.00 | title | Dmaj9 | gtr arp bass drums fx plate hall delay | -13.2 | -13.0 | 13.2 | 11 | 1.09 |
| 6 | 10.00 | title | Bm11 | gtr arp bass drums fx plate delay | -13.2 | -13.4 | 14.1 | 10 | 1.02 |
| 7 | 12.00 | lineup | Gmaj9#11 | gtr gtr_oct arp bass drums plate hall delay | -14.5 | -14.3 | 12.9 | 9 | 0.90 |
| 8 | 14.00 | lineup | A7sus4 > A7 | gtr gtr_oct arp bass drums hall | -14.7 | -14.7 | 14.1 | 6 | 0.73 |
| 9 | 16.00 | green | Dmaj9 | gtr bass drums | -14.2 | -14.4 | 13.9 | 13 | 0.86 |
| 10 | 18.00 | green | Bm11 | gtr bass drums | -13.5 | -13.7 | 13.8 | 14 | 0.96 |
| 11 | 20.00 | blue | Dmaj9 | gtr bass drums | -14.1 | -13.9 | 13.3 | 12 | 0.00 |
| 12 | 22.00 | blue | Bm11 | gtr bass drums | -13.5 | -13.8 | 13.4 | 14 | 0.92 |
| 13 | 24.00 | red | Dmaj9 | gtr bass drums | -14.2 | -13.9 | 13.5 | 11 | 1.01 |
| 14 | 26.00 | red | Bm11 | gtr bass drums | -13.6 | -13.8 | 13.0 | 13 | 0.90 |
| 15 | 28.00 | purple | Dmaj9 | gtr bass drums | -14.1 | -13.9 | 13.4 | 12 | 0.25 |
| 16 | 30.00 | purple | Bm11 | gtr bass drums | -13.6 | -13.8 | 13.4 | 14 | 0.35 |
| 17 | 32.00 | black | Dmaj9 | gtr bass drums | -14.1 | -13.8 | 14.1 | 13 | 1.33 |
| 18 | 34.00 | black | Bm11 | gtr bass drums | -13.9 | -14.0 | 13.6 | 11 | 1.44 |
| 19 | 36.00 | cores | Gmaj9#11 | pad bells bass hall | -18.4 | -17.2 | 11.6 | 6 | 1.85 |
| 20 | 38.00 | cores | Gmaj9#11 | pad bass drums hall | -18.3 | -18.0 | 12.1 | 9 | 1.83 |
| 21 | 40.00 | create | Bm11 | pad arp bass drums hall | -18.3 | -18.4 | 13.4 | 4 | 1.83 |
| 22 | 42.00 | create | Gmaj9#11 | gtr gtr_oct pad arp bass drums hall | -15.6 | -16.1 | 13.9 | 11 | 1.81 |
| 23 | 44.00 | create | A6sus2 | gtr gtr_oct pad arp bass drums plate hall delay | -15.2 | -15.4 | 13.2 | 4 | 1.31 |
| 24 | 46.00 | looks | G/A | gtr gtr_oct pad arp bass drums hall | -15.6 | -15.7 | 13.0 | 4 | 1.57 |
| 25 | 48.00 | looks | A7sus4 > A7 | gtr gtr_oct pad arp bass drums fx plate hall delay | -12.4 | -13.2 | 13.2 | 8 | 0.66 |
| 26 | 50.00 | free | Dmaj9 | gtr gtr_oct pad arp bass drums fx plate hall delay | -11.8 | -11.7 | 12.3 | 12 | 0.65 |
| 27 | 52.00 | free | Bm11 | gtr gtr_oct pad arp bass drums plate hall delay | -11.4 | -11.5 | 12.2 | 13 | 0.61 |
| 28 | 54.00 | trial | Gmaj9#11 | gtr gtr_oct ep pad arp bass drums plate hall delay | -13.2 | -12.5 | 13.3 | 10 | 1.16 |
| 29 | 56.00 | trial | A7sus4 > A7 | gtr gtr_oct ep pad arp bass drums plate hall delay | -13.0 | -13.1 | 14.3 | 10 | 1.52 |
| 30 | 58.00 | price | Dmaj9 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -12.2 | -12.4 | 12.2 | 12 | 1.46 |
| 31 | 60.00 | price | Bm11 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -11.8 | -11.8 | 12.7 | 11 | 1.36 |
| 32 | 62.00 | fold | Gmaj9#11 | pad bass drums clips plate hall delay | -17.2 | -14.6 | 13.9 | 11 | 0.70 |
| 33 | 64.00 | fold/echolalia | A6sus2 | pad bass drums clips hall | -15.8 | -15.8 | 12.6 | 10 | 0.95 |
| 34 | 66.00 | echolalia/stovetop | Gmaj9#11 | pad bass drums clips | -17.3 | -16.9 | 13.7 | 13 | 0.71 |
| 35 | 68.00 | stovetop | A6sus2 | pad bass drums clips | -17.9 | -17.0 | 13.4 | 13 | 0.34 |
| 36 | 70.00 | payoff | Dmaj9 | gtr | -17.1 | -17.4 | 14.6 | 5 | 2.08 |
| 37 | 72.00 | payoff | Bm11 | gtr plate | -15.8 | -16.1 | 14.1 | 5 | 1.81 |
| 38 | 74.00 | endcard | Gmaj9#11 | gtr gtr_oct pad bass plate hall | -14.6 | -14.6 | 14.3 | 8 | 1.71 |
| 39 | 76.00 | endcard | A7sus4 > A7 | gtr gtr_oct pad bass plate hall | -14.9 | -15.1 | 13.7 | 5 | 1.45 |
| 40 | 78.00 | hold | Dmaj9 | gtr pad bass drums plate hall | -14.7 | -14.4 | 15.7 | 3 | 1.82 |
| 41 | 80.00 | hold | Dmaj9 | pad bass hall | -20.0 | -19.1 | 12.6 | 0 | 1.82 |
| 42 | 82.00 | hold | Dmaj9 | gtr | -29.6 | -26.5 | 18.9 | 0 | 1.44 |
| 43 | 84.00 | hold | - |  | -68.6 | -54.5 | 17.4 | 0 | 0.33 |

## 5. Vertical cutdown (28.0 s, 14 bars)

The vertical has its own arrangement. It uses the same instruments, the same take, the same seeds and the same Choroboros settings, with the gesture times shifted; it is not an edit of the main mix.

The honesty zone is 0.00-14.00: the Mix turn and the five engine blocks. The drop is at 14.00 and is the loudest point (bars 8-9, -11.2 LUFS). The dominant (A7sus4 to A7 in bar 12) sets up the final Dmaj9 strum at 24.00.

| Bar | Time (s) | Section | Harmony | Audible stems (RMS > -42 dBFS) | LUFS (bar) | Short-term at bar end | Crest dB | Onsets | Mono-fold drop LU |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | 0.00 | mix-turn | Dmaj9 | gtr | -20.4 | -20.4 | 14.9 | 5 | 0.48 |
| 2 | 2.00 | title | Bm11 | gtr bass drums fx | -16.1 | -16.8 | 13.9 | 16 | 0.71 |
| 3 | 4.00 | green | Dmaj9 | gtr bass drums fx | -17.2 | -17.1 | 13.2 | 11 | 0.83 |
| 4 | 6.00 | blue | Bm11 | gtr bass drums | -16.9 | -17.2 | 12.8 | 10 | 0.47 |
| 5 | 8.00 | red | Dmaj9 | gtr bass drums | -17.4 | -17.2 | 15.1 | 8 | 0.88 |
| 6 | 10.00 | purple | Bm11 | gtr bass drums | -16.8 | -17.1 | 12.9 | 11 | 0.32 |
| 7 | 12.00 | black | Dmaj9 | gtr bass drums fx | -15.9 | -16.2 | 12.5 | 14 | 0.96 |
| 8 | 14.00 | free | Gmaj9#11 | gtr gtr_oct pad arp bass drums plate hall delay | -11.2 | -12.0 | 11.8 | 14 | 0.67 |
| 9 | 16.00 | free/trial | A7sus4 > A7 | gtr gtr_oct ep pad arp bass drums plate hall delay | -11.2 | -11.2 | 12.0 | 13 | 0.89 |
| 10 | 18.00 | trial | Gmaj9#11 | gtr gtr_oct ep pad arp bass drums plate hall delay | -11.8 | -11.9 | 12.5 | 12 | 1.36 |
| 11 | 20.00 | price | Dmaj9 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -12.3 | -12.3 | 13.4 | 14 | 1.08 |
| 12 | 22.00 | endcard | A7sus4 > A7 | gtr pad bass drums hall delay | -17.5 | -15.0 | 13.7 | 4 | 1.96 |
| 13 | 24.00 | endcard | Dmaj9 | gtr pad bass drums plate hall delay | -14.8 | -14.9 | 15.5 | 3 | 1.64 |
| 14 | 26.00 | endcard | Dmaj9 | pad bass hall | -22.6 | -20.6 | 13.9 | 0 | 1.59 |

## 6. Choroboros renders, Purple pre-roll and clips

**Renders.** R01-R12 and R09ref were rendered with `--block 128 --tail 3 --meta`, with every knob written explicitly. Gestures are automated on the eased knob position (sine.inOut), sampled every 10 ms. The binary is called by path (`/home/user/build/choro-render/build/choro-render`) and is never copied into the repo. The metas are in `audio/logs/render-meta/`.

**Purple (Orbit) pre-roll.** Candidates were swept from 0.00 to 8.25 s in 0.25 s steps.

| Cut | Pre-roll | Swoosh peak | Window |
|---|---|---|---|
| Main | 7.75 s | 29.18 | 28.75-29.50, with no other swoosh before 30.00 |
| Vertical | 6.50 s | 10.54 | 10.25-10.85 |

**Clips.** Each clip is at -18 LUFS, and the bed (pad, bass, drums) is ducked 6 dB under it.

| Clip | Source window (s) | Placed at | Gain |
|---|---|---|---|
| Fold | 1.00-3.25 | 62.25 | -0.64 dB |
| Echolalia | 9.50-11.75 | 64.75 | -1.12 dB |
| Stovetop | 3.005-5.505 | 67.00 | -2.55 dB |

The Stovetop window starts 40 ms before the detected kick downbeat at 3.045.

## 7. How the honesty rules are verified (`qc.json` gate `honesty_zones`)

- The featured guitar in the zones equals the Choroboros edit times the logged scalar gain curve. The maximum relative error is below 1e-5, and L and R are identical to the render.
- The limiter gain is exactly 1 inside the zones. Zone trims keep peaks under the ceiling instead.
- The plate, hall and delay returns and every other music stem (octave double, pad, EP, lead, pluck, arp, bells, clips) are exactly 0.0 inside the zones.
- The backing (drums + bass) has a correlation of 1 (mono) in the zones.
- In the main tour, the drums + bass of passes 2, 3 and 4 are bit-identical to pass 1. Pass 5 is bit-identical until it stops at 35.50.
- Block P (the hook through the tour) is bit-identical at all seven paste points in the dry guitar stem.

## 8. Arc summary

| Moment | Main | Vertical |
|---|---|---|
| Quiet opening (bar 1) | -18.4 LUFS, 5 onsets | -20.4 LUFS, 5 onsets |
| Loudest bar | bar 27 (drop), -11.4 | bars 8-9 (drop), -11.2 |
| Deepest release | 78.00 Dmaj9, crest 15.7 dB, 3 onsets | 24.00 Dmaj9, crest 15.5 dB, 3 onsets |
| Tail | the F#4 at 82.00 at -29.6, then the fade | pad, bass and hall at -22.6, then the fade |

## 9. Video description line

> All music is original. Every chorus and modulation effect you hear is Choroboros. Engine demos start from a mono, dry source and are level matched.

This line is already in `docs/brief/treatment.md` (the video description). Nothing else on screen changes.

## 10. Known weaknesses (honest)

- **Nobody has listened to this.** The synthesis and mix were judged by meters, spectrograms and the arc, not by ears. A listening pass on monitors and a phone is still needed.
- **The tour is louder than treatment 8.5 asks.** It sits at about -14 LUFS per bar, not about -15. With -14 LUFS integrated, at most 1 dB of limiting and a density-limited offer peak, the quiet sections cannot all sit lower without breaking the integrated target. The drop leads the tour by about 2.3 LU and the price card by 0.4 LU. More dynamic contrast would need more limiting or a quieter integrated target.
- **The offer peak is pinned by density.** The drop is louder than the price card by only 0.4 LU on average. The glue works 2-3 dB in the offer.
- **Mono fold.** The payoff loses 1.9-2.1 LU when summed to mono. That is the product: Green at width 130% on a solo guitar.
- **Echolalia down-bend.** The window 9.50-11.75 holds the rising glides (9.5-11.0) but ends on a falling bend (11.25-11.75).
- **Stovetop key clash.** The Stovetop clip is in its own key and tempo (80 BPM) against the G/A bed. The bed is ducked 6 dB but the clash is audible.
- **The low end still leans on the sub.** The 63 Hz octave band is about 6 dB above 125 Hz. Phone speakers get the saturated mid layer of the bass, but the balance may want 1-2 dB less sub after listening.
- **Click-scan maxima are drum hits, not clicks.** The worst values are +4.0 dB (main, at 58.00) and +4.7 dB (vertical, at 4.00). They are downbeat pluck and drum transients landing on section joins; the vertical's tour joins read +0.3 to +4.7 dB because its groove is sparser. At every join, the featured guitar's own high-frequency level is at least 5.6 dB under its surroundings.
