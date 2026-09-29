# Still Life: production notes

These notes describe the soundtrack of the Choroboros launch film "Still Life": the 86.0 s main film and the 28.0 s vertical cutdown.

They record the owner's production pass and the mix revision that followed it. Where they conflict with treatment 3.3 and 8.5 (and, for the bed under the product clips, with treatment 5 shots 19-21 and 7.5), the owner's direction wins.

The mix revision changed four things, all in the mix plans (`mix.py`, and `vertical.py` for the vertical); the stems, renders, level match and clips are unchanged:

- **The clips stand alone.** The music bed is muted under the product clips (section 6).
- **Less sub.** A low shelf on the drum and bass buses takes the 63 Hz octave band 2 dB down against 125 Hz, in both cuts (section 1B).
- **The drop is the biggest moment on every measure.** The drop's impact is back on top of the build, and the build, the title and the final strum now sit under the drop in 400 ms (momentary) loudness too, not only per section, bar and 3 s window (section 1D).
- **The ending lands.** The final Dmaj9 at 78.00 sits 2.2-2.5 LU above the end-card bars, with its level in the whole chord rather than in the first pick transient, and the lone F#4 at 82.00 is 11 LU above the tail (section 1D).

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

The backing in the zones (drums, bass, the treatment's FX) is produced: tape, parallel compression, a mono room, the sub shelf. It carries no modulation and is mono.

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
- **Sub:** a low shelf (80 Hz, -3 dB, Q 0.8) on the drum bus, before its transient shave (whose ceiling is unchanged), and at the end of the bass bus. The 63 Hz octave band of the master now sits 4.3 dB above 125 Hz (it was 6.3 dB). The vertical's groove carries more sub, so its shelf is 0.5 dB deeper (-3.5 dB) and takes it the same 2 dB down: 5.0 dB (it was 7.0 dB). The shelf is linear and runs on the tour loops too, so the pasted backing stays sample-identical.

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

- **Before the title (8.00):** A7sus4 to A7 in bar 4, with the suspension resolving at 7.50. A reverse guitar swell and a riser lead into 8.00 (both 1.5 dB lower since the mix revision, gain only); the tonic is withheld until the impact.
- **Before the tour (16.00), the price card (58.00) and the final chord (78.00):** A7sus4 to A7 again.
- **The breakdown (36-46):** floats on Gmaj9#11 and Bm11 with a bell cascade (bar 19). Bar 21 is nearly empty (4 onsets) before the guitar returns at 42.
- **The build (46-49.85):**
  - G/A over an A pedal;
  - the bass pulses the A pedal in 8ths;
  - A7sus4 to A7;
  - the pad low-pass opens from 700 Hz to 9 kHz;
  - the arp moves from dotted 8ths to 16ths while its filter opens from 700 Hz to 6.3 kHz;
  - a snare roll, a riser (-32 to -18 dBFS) and a reverse crash.

  It is then cut to digital silence for 150 ms. The build crests under the drop, not level with it: bar 25 is -13.1 LUFS (it was -12.4), with the riser 5 dB and the arp 1 dB down on their faders, and its last 400 ms read -11.6 LUFS momentary (it was -10.7, as loud as the drop's loudest window).
- **The drop (50.00):** Dmaj9 with the impact, a downlifter, crash, the full groove B, block P, pad, arp, bass and octave double. It is the biggest moment of the film on every measure:
  - section: -11.3 LUFS against -12.1 for the price card;
  - bar: bar 27 (-11.2) and bar 26 (-11.4) are the two loudest bars;
  - 3 s short-term: the loudest window of the film (-11.2) starts on the downbeat at 50.00;
  - 400 ms momentary: the loudest window of the film is 52.00 (-10.5), and the downbeat at 50.00 reads -10.6, against -10.85 for the title impact at 8.00, -11.0 for the final strum at 78.00 and -11.6 for the end of the build.

  The impact now lands on top of the build. The FX are absolute-level stems, so the drop zone's peak trim (8.5 dB under its design level) had also pulled the impact down, to 11 dB under the title's impact and under the riser before it (fx-stem peaks -18.6 against -7.6 and -15.8 dBFS). The FX fader is +10 dB over 50-54, so the impact peaks at -8.5 dBFS against -7.1 for the title's and -17.8 for the riser tail. Its sub sweep (55 to 32 Hz) is the same thump as the title's. The pad (+3.5 dB), arp (+2 dB) and bass (+1 dB) carry more of the drop and the guitar sits 0.5 dB lower, so the drop keeps its density with less sub.
- **The coda (62-69.5):** the three field clips stand alone. The bed is muted under them: under Fold and Echolalia only the bass whole note (G1, then A1 and G1) and the soft kick remain; under Stovetop there is nothing until the digital silence at 69.50.
- **The payoff (70.00):** the hook alone, after 0.5 s of digital silence.
- **The final Dmaj9 (78.00):** the deepest release, where the Buy Choroboros button pulses. It is a six-string strum with the pad, a D2 bass, a kick and crash, and more hall on the strum. The strum's attack sits 4 dB down and the ringing chord rides back up over 0.8 s, while the pad blooms in under it (-4 dB to -0.5 dB over 78-79). The whole chord gets the level instead of the first pick transient, and the attack stays under the drop: 78.00-78.40 reads -11.0 LUFS momentary (before this revision: -9.6, the loudest 400 ms of the film). The bar is -12.8 LUFS against -15.0 and -15.3 for the two end-card bars before it (before: -14.7 against -14.6 and -14.9). Its crest is 13.4 dB (it was 15.7), and it needs no limiting. Over 78-80 the pad reads -15.8 LUFS, the bass -19.5, the strum -19.9, the drums -26.1 and the hall -31.6. The pad and bass then ride down over 79-81, so the mix thins to pad, bass and hall.
- **82.00:** a single F#4 over near-silence, with a delay throw, and a fade from 84.50. The note is 6.5 dB up on its own fader: its first 400 ms (82.00-82.40) read -19.0 LUFS against -30.0 for the tail just before it (81.40-81.90; before this revision: -24.1 against -29.8).

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
| 50.00-62.00 | gtr R01/R03, pad R08/R09, EP R10, lead R11, pluck R12 | sends, throws, sidechain, glue (mean gain reduction 2.3-2.7 dB), limiter up to 0.85 dB | groove B, bass, arp, crashes, impact, downlifter |
| 62.00-69.50 | clips alone (-18 LUFS); pad R07 only until 62.25 | none under the clips: every music stem and return is muted with 60 ms fades ending on the clip start | bass whole note and soft kick (ducked 6 dB) under Fold and Echolalia; nothing under Stovetop |
| 70.00-86.00 | gtr R01, pad R07 | plate and hall (the payoff guitar is heard with the room around it) | end card and final chord |

The level-match gain for the featured stems is logged per bar in `audio/logs/level-match.json`. Every checked bar passes with a residual of at most 0.013 LU (vertical: 0.015 LU).

## 3. Loudness and dynamics

| Measure | Main | Vertical |
|---|---|---|
| Integrated | -14.4 LUFS | -14.4 LUFS |
| True peak | -1.1 dBTP | -1.1 dBTP |
| Limiter maximum gain reduction | 0.85 dB (none in the honesty zones) | 0.84 dB |
| LRA (ffmpeg) | 5.4 LU | 6.1 LU |
| Mono-fold drop, whole film | 1.10 LU | 1.04 LU |
| Mono-fold drop, worst section | 1.97 LU (cores: the pad through Green (b) and the hall; the payoff is 1.91) | 1.87 LU (end card) |
| 63 Hz octave band above 125 Hz | 4.3 dB (was 6.3) | 5.0 dB (was 7.0) |
| Loudest 400 ms (momentary) | 52.00, the drop (-10.5 LUFS) | 14.00, the drop (-10.3 LUFS) |

The arc is quiet, then open, then dense:

- the opening is around -17.2 LUFS per bar;
- the title is -13.2 and -13.4, the lineup -14.8 and -15.1;
- the tour is -14.1 to -14.8;
- the breakdown is about -17.1;
- the build rises from -15.3 to -13.1;
- the drop (bars 26-27, -11.4 and -11.2) is the loudest section, bar, 3 s window and 400 ms window;
- the coda is the clips at -18 LUFS each, alone or over bass and kick;
- the payoff is -16.7 to -15.3;
- the end card is -15.0 and -15.3, the final chord -12.8, then the tail falls to -24.4 (the F#4) and -65.

Taking 2 dB out of the sub costs loudness in the kick- and bass-heavy sections. The drop, trial, title and tour are held by their peaks (the limiter may only take 0.85 dB), so at -14.4 LUFS integrated the master gain rises and the quiet sections come up with it. Against the drop section (-11.3 LUFS), the opening and the breakdown are 5.7-5.9 LU down (before the revision: 6.7-6.9) and the tour 2.7-3.5 LU down (before: 1.9-2.6). The ffmpeg LRA is 5.4 LU (it was 6.1).

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
| 1 | 0.00 | cold-open | Dmaj9 | gtr | -17.2 | -17.2 | 12.8 | 5 | 0.00 |
| 2 | 2.00 | mix-turn/tagline | Dmaj9 | gtr | -17.1 | -17.1 | 13.8 | 5 | 1.00 |
| 3 | 4.00 | tagline | Bm11 | gtr | -16.2 | -16.3 | 13.5 | 5 | 1.67 |
| 4 | 6.00 | tagline | A7sus4 > A7 | gtr fx | -15.0 | -15.3 | 15.0 | 4 | 1.32 |
| 5 | 8.00 | title | Dmaj9 | gtr arp bass drums fx plate hall delay | -13.2 | -13.1 | 13.3 | 9 | 1.15 |
| 6 | 10.00 | title | Bm11 | gtr arp bass drums fx plate hall delay | -13.4 | -13.6 | 14.6 | 10 | 1.12 |
| 7 | 12.00 | lineup | Gmaj9#11 | gtr gtr_oct arp bass drums plate hall delay | -14.8 | -14.6 | 13.4 | 9 | 0.99 |
| 8 | 14.00 | lineup | A7sus4 > A7 | gtr gtr_oct arp bass drums hall | -15.1 | -15.1 | 14.8 | 5 | 0.83 |
| 9 | 16.00 | green | Dmaj9 | gtr bass drums | -14.8 | -14.9 | 14.3 | 12 | 0.98 |
| 10 | 18.00 | green | Bm11 | gtr bass drums | -14.1 | -14.2 | 14.8 | 13 | 1.08 |
| 11 | 20.00 | blue | Dmaj9 | gtr bass drums | -14.7 | -14.4 | 14.0 | 12 | 0.00 |
| 12 | 22.00 | blue | Bm11 | gtr bass drums | -14.1 | -14.3 | 14.2 | 15 | 1.04 |
| 13 | 24.00 | red | Dmaj9 | gtr bass drums | -14.8 | -14.4 | 14.4 | 11 | 1.16 |
| 14 | 26.00 | red | Bm11 | gtr bass drums | -14.1 | -14.4 | 13.6 | 13 | 1.02 |
| 15 | 28.00 | purple | Dmaj9 | gtr bass drums | -14.7 | -14.4 | 14.2 | 13 | 0.28 |
| 16 | 30.00 | purple | Bm11 | gtr bass drums | -14.1 | -14.3 | 13.7 | 13 | 0.40 |
| 17 | 32.00 | black | Dmaj9 | gtr bass drums | -14.7 | -14.3 | 14.9 | 12 | 1.53 |
| 18 | 34.00 | black | Bm11 | gtr bass drums | -14.4 | -14.6 | 14.2 | 10 | 1.64 |
| 19 | 36.00 | cores | Gmaj9#11 | pad bells bass hall | -17.1 | -16.7 | 11.7 | 9 | 2.03 |
| 20 | 38.00 | cores | Gmaj9#11 | pad bass drums hall | -17.0 | -16.7 | 12.9 | 14 | 1.99 |
| 21 | 40.00 | create | Bm11 | pad arp bass drums hall | -17.1 | -17.1 | 13.2 | 5 | 1.97 |
| 22 | 42.00 | create | Gmaj9#11 | gtr gtr_oct pad arp bass drums plate hall delay | -14.3 | -14.8 | 13.6 | 14 | 1.91 |
| 23 | 44.00 | create | A6sus2 | gtr gtr_oct pad arp bass drums plate hall delay | -13.9 | -14.0 | 13.2 | 6 | 1.36 |
| 24 | 46.00 | looks | G/A | gtr gtr_oct pad arp bass drums plate hall | -15.3 | -15.1 | 13.2 | 7 | 1.62 |
| 25 | 48.00 | looks | A7sus4 > A7 | gtr gtr_oct pad arp bass drums fx plate hall delay | -13.1 | -13.7 | 12.9 | 8 | 0.90 |
| 26 | 50.00 | free | Dmaj9 | gtr gtr_oct pad arp bass drums fx hall delay | -11.4 | -11.8 | 11.7 | 13 | 0.60 |
| 27 | 52.00 | free | Bm11 | gtr gtr_oct pad arp bass drums plate hall delay | -11.2 | -11.3 | 12.3 | 14 | 0.60 |
| 28 | 54.00 | trial | Gmaj9#11 | gtr gtr_oct ep pad arp bass drums plate hall delay | -12.7 | -12.1 | 13.3 | 13 | 1.19 |
| 29 | 56.00 | trial | A7sus4 > A7 | gtr gtr_oct ep pad arp bass drums plate hall delay | -12.4 | -12.6 | 13.9 | 11 | 1.59 |
| 30 | 58.00 | price | Dmaj9 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -12.3 | -12.4 | 12.3 | 12 | 1.49 |
| 31 | 60.00 | price | Bm11 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -12.0 | -12.0 | 12.8 | 11 | 1.39 |
| 32 | 62.00 | fold | Gmaj9#11, then bass G1 under the clip | pad bass drums clips plate hall delay | -18.1 | -14.8 | 15.7 | 12 | 0.36 |
| 33 | 64.00 | fold/echolalia | bass A1 | bass drums clips | -16.4 | -16.4 | 12.8 | 10 | 0.73 |
| 34 | 66.00 | echolalia/stovetop | bass G1 to 67.00 | bass drums clips | -18.1 | -17.5 | 13.4 | 14 | 0.51 |
| 35 | 68.00 | stovetop | - (the clip alone) | clips | -18.9 | -18.2 | 10.3 | 9 | 0.11 |
| 36 | 70.00 | payoff | Dmaj9 | gtr | -16.7 | -17.1 | 14.6 | 5 | 2.08 |
| 37 | 72.00 | payoff | Bm11 | gtr plate | -15.3 | -15.7 | 14.1 | 5 | 1.81 |
| 38 | 74.00 | endcard | Gmaj9#11 | gtr gtr_oct pad bass plate | -15.0 | -14.8 | 14.5 | 11 | 1.74 |
| 39 | 76.00 | endcard | A7sus4 > A7 | gtr gtr_oct pad bass plate | -15.3 | -15.6 | 13.8 | 5 | 1.48 |
| 40 | 78.00 | hold | Dmaj9 | gtr pad bass drums hall | -12.8 | -13.4 | 13.4 | 3 | 1.63 |
| 41 | 80.00 | hold | Dmaj9 | pad bass hall | -20.1 | -16.7 | 13.8 | 1 | 1.77 |
| 42 | 82.00 | hold | Dmaj9 | gtr delay | -24.4 | -23.9 | 18.3 | 0 | 1.40 |
| 43 | 84.00 | hold | - |  | -65.6 | -49.5 | 17.4 | 0 | 0.25 |

## 5. Vertical cutdown (28.0 s, 14 bars)

The vertical has its own arrangement. It uses the same instruments, the same take, the same seeds and the same Choroboros settings, with the gesture times shifted; it is not an edit of the main mix.

The honesty zone is 0.00-14.00: the Mix turn and the five engine blocks. The drop is at 14.00 and is the loudest point on every measure (bars 8-9, -11.3 and -11.2 LUFS; the loudest 3 s window starts at 14.00, -11.1; the loudest 400 ms is the drop downbeat, -10.3). The vertical has no product clips; of this revision it takes the sub shelf (0.5 dB deeper, section 1B) and the final-chord shaping. The dominant (A7sus4 to A7 in bar 12) sets up the final Dmaj9 strum at 24.00. The strum's attack sits 5 dB down and rides back up over 1 s while the pad blooms under it: its first 400 ms read -11.0 LUFS (with the sub shelf alone they read -9.1, 1.2 LU over the drop), and the bar is -14.3 (before the revision: -14.8), 2.9 LU over bar 12.

| Bar | Time (s) | Section | Harmony | Audible stems (RMS > -42 dBFS) | LUFS (bar) | Short-term at bar end | Crest dB | Onsets | Mono-fold drop LU |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | 0.00 | mix-turn | Dmaj9 | gtr | -19.9 | -19.9 | 14.9 | 5 | 0.48 |
| 2 | 2.00 | title | Bm11 | gtr bass drums fx | -16.2 | -16.8 | 14.1 | 17 | 0.81 |
| 3 | 4.00 | green | Dmaj9 | gtr bass drums fx | -17.4 | -17.2 | 13.5 | 10 | 0.98 |
| 4 | 6.00 | blue | Bm11 | gtr bass drums | -17.1 | -17.4 | 13.8 | 10 | 0.55 |
| 5 | 8.00 | red | Dmaj9 | gtr bass drums | -17.5 | -17.2 | 15.3 | 8 | 0.99 |
| 6 | 10.00 | purple | Bm11 | gtr bass drums | -17.0 | -17.3 | 13.8 | 9 | 0.37 |
| 7 | 12.00 | black | Dmaj9 | gtr bass drums fx | -16.1 | -16.3 | 13.5 | 15 | 1.12 |
| 8 | 14.00 | free | Gmaj9#11 | gtr gtr_oct pad arp bass drums plate hall delay | -11.3 | -12.1 | 12.4 | 13 | 0.73 |
| 9 | 16.00 | free/trial | A7sus4 > A7 | gtr gtr_oct ep pad arp bass drums plate hall delay | -11.2 | -11.2 | 12.4 | 14 | 0.96 |
| 10 | 18.00 | trial | Gmaj9#11 | gtr gtr_oct ep pad arp bass drums plate hall delay | -11.7 | -11.7 | 12.6 | 13 | 1.44 |
| 11 | 20.00 | price | Dmaj9 | gtr gtr_oct lead ep pad pluck arp bass drums plate hall delay | -12.1 | -12.1 | 13.6 | 13 | 1.12 |
| 12 | 22.00 | endcard | A7sus4 > A7 | gtr pad arp bass drums hall delay | -17.2 | -14.7 | 14.0 | 4 | 2.02 |
| 13 | 24.00 | endcard | Dmaj9 | gtr pad bass drums plate hall delay | -14.3 | -14.8 | 14.5 | 6 | 1.88 |
| 14 | 26.00 | endcard | Dmaj9 | pad bass hall | -19.3 | -17.6 | 14.7 | 0 | 2.35 |

## 6. Choroboros renders, Purple pre-roll and clips

**Renders.** R01-R12 and R09ref were rendered with `--block 128 --tail 3 --meta`, with every knob written explicitly. Gestures are automated on the eased knob position (sine.inOut), sampled every 10 ms. The binary is called by path (`/home/user/build/choro-render/build/choro-render`) and is never copied into the repo. The metas are in `audio/logs/render-meta/`.

**Purple (Orbit) pre-roll.** Candidates were swept from 0.00 to 8.25 s in 0.25 s steps.

| Cut | Pre-roll | Swoosh peak | Window |
|---|---|---|---|
| Main | 7.75 s | 29.18 | 28.75-29.50, with no other swoosh before 30.00 |
| Vertical | 6.50 s | 10.54 | 10.25-10.85 |

**Clips.** Each clip is at -18 LUFS and stands alone. Every music stem and every return is muted under it with a 60 ms raised-cosine fade that ends on the clip start. Under Fold and Echolalia only the bass whole note and the soft kick remain, still ducked 6 dB; under Stovetop nothing remains until the digital silence at 69.50. The pad and returns do not come back in the 0.25 s between Fold and Echolalia.

The bed was cut back because it clashed. The measure is the chroma of the bed against the clip (`clip_bed` in `qc.json`): "semitone" is the clip's energy a minor second or major seventh from the bed's; a flat chroma would read 0.167 semitone and 0.083 unison.

| Clip | Bed before (ducked 6 dB) | Bed now |
|---|---|---|
| Fold (G major) | pad, bass, drums, delay, plate, hall at -22.6 LUFS: semitone 0.209, unison 0.083. The pad (0.233) and the delay echoes of the price card (0.286) clashed. | bass G1 then A1, soft kick, at -27.1 LUFS: semitone 0.154, unison 0.140 |
| Echolalia (C major / A minor) | -23.1 LUFS: semitone 0.194, unison 0.089; the pad read 0.252 | bass A1 then G1, soft kick, at -26.1 LUFS: semitone 0.155, unison 0.107 |
| Stovetop (own key, 80 BPM) | -23.4 LUFS: semitone 0.145, tritone 0.164 | nothing (exact zero) |

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
| Quiet opening (bar 1) | -17.3 LUFS, 5 onsets | -20.0 LUFS, 5 onsets |
| Loudest bar | bar 27 (drop), -11.2 | bars 8-9 (drop), -11.3 and -11.2 |
| Loudest 3 s window | from 50.00 (drop), -11.2 | from 14.00 (drop), -11.1 |
| Loudest 400 ms window | 52.00 (drop), -10.5; the drop downbeat 50.00 is -10.6 | 14.00 (drop), -10.3 |
| Deepest release | 78.00 Dmaj9, -12.8 LUFS bar, 2.2-2.5 LU over the end card, crest 13.4 dB, attack -11.0 LUFS momentary | 24.00 Dmaj9, -14.3 LUFS bar, 2.9 LU over bar 12, crest 14.5 dB, attack -11.0 LUFS momentary |
| Tail | the F#4 at 82.00, -19.0 LUFS over its first 400 ms and -24.4 for the bar, then the fade | pad, bass and hall at -19.3, then the fade |

## 9. Video description line

> All music is original. Every chorus and modulation effect you hear is Choroboros. Engine demos start from a mono, dry source and are level matched.

This line is already in `docs/brief/treatment.md` (the video description). Nothing else on screen changes.

## 10. Known weaknesses (honest)

- **Nobody has listened to this.** The synthesis and mix were judged by meters, spectrograms and the arc, not by ears. A listening pass on monitors and a phone is still needed.
- **The arc is flatter than before the sub shelf.** The sub carried loudness in the peak-bound sections (tour, title, drop, trial). With -14.4 LUFS integrated and at most 1 dB of limiting, the master gain rose about 2.3 dB and the quiet sections came up about 1 LU against the drop. The opening and breakdown are now 5.7-5.9 LU under the drop section (they were 6.7-6.9); the tour is 2.7-3.5 LU under (it was 1.9-2.6, closer to treatment 8.5's -15 per bar). More contrast would need more limiting, a quieter integrated target, or less sub reduction.
- **The offer peak is pinned by density.** The drop is louder than the price card by 0.8 LU on average; bar 31 is 0.5 LU under bar 26. The glue works 2.3-2.7 dB in the offer.
- **The drop's lead over the title and the final chord is small in 400 ms windows.** The drop's loudest momentary window (-10.5 LUFS) is 0.35 LU over the title impact (-10.85) and 0.5 LU over the final strum (-11.0). The drop zone is held by its own peaks (the limiter works 0.8 dB at 52.02) and by the 1 dB limiting cap, so a bigger lead has to come from pulling the title or the final chord down, not from pushing the drop up.
- **Mono fold.** The payoff loses 1.9 LU when summed to mono and the cores section 2.0 LU. That is the product: Green at width 130% on a solo guitar, and the Green pad through the hall. With less mono sub under them, most sections read 0.05-0.2 LU more than before.
- **Echolalia down-bend.** The window 9.50-11.75 holds the rising glides (9.5-11.0) but ends on a falling bend (11.25-11.75).
- **Click-scan maxima are drum hits, not clicks.** The worst values are +3.8 dB (main, at 58.00) and +5.1 dB (vertical, at 4.00). They are downbeat pluck and drum transients landing on section joins; the vertical's tour joins read +0.6 to +5.1 dB because its groove is sparser. At every join, the featured guitar's own high-frequency level is at least 5.6 dB under its surroundings (the closest are 74.00 and 28.00). The mute edges under the clips (62.19-62.25, 64.69-64.75, 66.94-67.00) read -4.6 dB or lower. The final-chord rides start on the strum: 78.00 reads +1.4 dB, the same as before the ride (the kick, crash and strum onset), and 24.00 in the vertical -1.1 dB.
