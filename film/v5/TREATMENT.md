# Choroboros v5: the portrait launch film and the TikTok. THE BUILD SPEC

Status: **FINAL**. This file is the only spec for the v5 build. Two picture engineers (Unit A, Unit B) and one audio engineer follow it exactly. Where it conflicts with the pitches in `/home/user/build/v5/concepts/`, this file wins. Its machine-readable twin for the audio and the knob readouts is `film/v5/demos.json`.

- Format: 1080 x 1920, 60 fps, both films.
- Time: every time is **master time**: seconds from the first sample of the owner's master (gapless 48 kHz decode, `/home/user/build/v5/master_src.wav`). Film time = song time. The song plays straight through from its first sample: never cut, looped, reordered or time-stretched.
- Grid: `film/v5/grid.json`. 148.000 BPM. Bar n starts at 0.4048 + (n - 1) x 1.621622 s. One beat = 0.405405 s = 24.32 frames.
- Hits: `film/v5/hits.json`. A hit-driven event lands on frame `floor(60 x h)` (`beats.onsetFrame(h)`), where h is the earliest attack in the cluster (a crash is keyed to the kick or snare it lands with). "Bar.beat" is 1-based; ".5" is the "and".

---

## 0. The verdict

### 0.1 Scores (1 to 10)

**Main film**

| Criterion | KINETIC | ENGINEER'S HANDS | Why |
|---|---|---|---|
| Stops the scroll in the first second | 9 | 8 | KINETIC: a still monument with an unfinished sentence, then a white hit and a five-hue type burst. HANDS: the product's own knob moves on the first kick, but frame 0 has no words. |
| Vitality (played by the drums) | 9 | 6 | KINETIC has a full grammar: punch, stamp, whip, flash, shake, sweep, colour = sound. HANDS' kick breath (0.6 % scale) is too polite for "where's the vitality". |
| Skill and technique | 7 | 9 | HANDS measured this song. Width 130-170 % drives the chorused guitar's L/R correlation negative, so Width stays at 100 %. It also has level matching shown on the plugin's own Trim, a bit-exact bypass, an A/B on the crashes and one move per engine. KINETIC's settings are unmeasured v4 values. |
| Honesty and claims | 8 | 9 | Both are clean. HANDS adds "drums untouched" as a null test and puts the level-match number on screen. KINETIC's colour = sound rule is honest, but its Width values fail mono. |
| Portrait craft and phone readability | 8 | 8 | Both are sized for a phone. KINETIC has the better full-bleed macros. HANDS has the better zone grid (type / hero / support). |
| Conversion | 8 | 8 | KINETIC: Buy on the loudest crash. HANDS: the price stamps on the crash pushes, and a clean end card over solo guitar. |
| Fidelity to the v4 film the owner liked | 6 | 9 | KINETIC moves the Mix turn to 13.4 s, puts the title before the tagline and the family before the price. HANDS keeps the owner's order: cold open, Mix turn, tagline, title, lineup, tour, cores, Create, looks, free, trial, price, products, payoff, end card. |
| Buildable in a day with the lib | 6 | 7 | KINETIC needs more new modules. |
| **Total** | **61** | **64** | |

**TikTok**

| Criterion | KINETIC (bar 77) | ENGINEER'S HANDS (bar 45) | Why |
|---|---|---|---|
| Stops the scroll | 8 | 9 | HANDS: a crash plus an A/B in the first second. KINETIC: a bold five-stripe poster with a challenge ("One riff. Five engines."), then a slam. |
| Vitality | 9 | 8 | KINETIC: 34 events on 34 hits, one engine per bar. |
| Skill and technique | 8 | 9 | HANDS: stepped moves on the crash pushes. KINETIC: a Mix turn in the stop-time silence (the purest demo moment in the song) and all five engines. |
| Honesty | 9 | 8 | Both clean. HANDS' 2 s end card is crowded. |
| Portrait craft | 9 | 7 | HANDS' frame 0 stacks a headline, a toggle, a scope, a smeared macro and a chip. |
| Conversion | 9 | 6 | KINETIC: the offer is seeded in tags, then Buy holds 3.65 s over solo guitar. HANDS: 2.03 s. |
| Buildable | 6 | 7 | |
| **Total** | **58** | **54** | |

### 0.2 Decision

- **Main film: THE ENGINEER'S HANDS is the skeleton.** It keeps the owner's v4 order and has the measured audio. It is fitted with KINETIC's motion system to fix its one weak score, vitality.
- **TikTok: KINETIC's bar-77 piece.** It uses new music the main film never plays, the stop-time freeze, and a long Buy. Its engine settings come from THE ENGINEER'S HANDS.
- **One shared kit** built on KINETIC's grammar: `film/lib/beats.js` and `film/lib/motion.js` are already written.

**Grafted from KINETIC into the main film:**
- the hit grammar (PUNCH, STAMP, WHIP, FLASH, SHAKE, SWEEP);
- **colour = sound**: a plate is saturated only while its engine is what you hear;
- the frame-0 unfinished sentence "Great / sound";
- the type burst on the first hit;
- the knob-by-knob Create assembly;
- the family cards heard **dry** (so nothing suggests you hear those products);
- the inhale before the stop;
- the PSE limiter.

**Grafted from THE ENGINEER'S HANDS into the TikTok:**
- Width 100 % everywhere, with the measured settings;
- the BP processing path;
- Purple's move is Color, not Rate (Orbit warbles a sustained guitar above about 0.3 Hz).

**Left out on purpose:**
- KINETIC's "Five voices" blitz (it muddles the A/B proof);
- HANDS' correlation-needle widget (too small to read on a phone).

---

## 1. Span, end point and ending

### Main film

- **Span:** 0.000 to 91.216. That is the first sample to the bar-57 downbeat: 5 473 frames (0 to 5472), bars 1 to 56.
- **Start:** frame 0 is the first sample. 0.000 to 0.405 is near silence, and it becomes the still (frames 0 to 23).
- **Climax:** the bar-53 full-band stop at **84.725** (snare 84.7251, kick 84.7296, the loudest crash in the song at 84.733). This is frame 5083. The band stops. The guitar plays on alone through Choroboros Green for four bars.
- **Ending treatment: fade.** An equal-power fade of the whole mix from 89.900 to 91.080, then digital silence to 91.216. The quiet cymbal pickup at 91.115 must be silent.
- **Last frame:** the picture holds the end card, with "Buy Choroboros", to the last frame (5472). No fade to black. The last frame is the thumbnail and the loop frame.

### TikTok

- **Span:** 123.648 to 138.648. That is bar 77 beat 1 to bar 86 beat 2: 15.000 s, 900 frames. It is one continuous stretch of the master.
- **Start:** a 1 ms fade-in. The first sample carries the crash + kick at 123.649.
- **Full-band stop:** at 135.000 (τ 11.352).
- **End:** a fade from 138.243 to 138.630, silence to 138.648. It loops into the crash at frame 0.

---

## 2. Main film timeline (master time)

### Picture rules for this section

- **Frame of an event:** `floor(60 x h)`.
- **Motion names** are defined in section 5.
- **Chip:** the persistent "now hearing" chip. It sits at x 72, baseline 256, JetBrains Mono 600, 26 px, 70 % white. Its text comes from `demos.json` at every frame:
  - on: `● GUITAR · CHOROBOROS <ENGINE> · <CORE>`, the dot in the engine hue;
  - bypass: `○ GUITAR · BYPASS`;
  - in S01 and S02 only, the text ends with ` · MIX n%`.
- **Colour = sound:** every plate body is filtered by `saturate(s) brightness(b)`:
  - s 1.0 and b 1.0 when its engine is what is heard;
  - s 0.35 and b 0.75 when it is on screen but not heard;
  - s 0.12 and b 0.9 when the chorus is bypassed or Mix is 0.
  - During a Mix move, s = 0.12 + 0.88 x mix / 40.
  - Frame-0 posters are the only exception, and they are listed below.
- **Layouts** (y ranges; text x 72 to 928 unless stated):
  - **L-MACRO:** a full-bleed plate close-up (`plate.focus`). Type sits in zone T (y 280 to 660) over a black scrim (72 % at y 0, down to 0 at y 720).
  - **L-TOUR:**
    - zone T: eyebrow baseline 300, headline baseline 420, BEST FOR line baseline 490;
    - zone H: the scope, 520 px across, centred at (540, 800);
    - zone S: the engine plate at scale 0.60 (840 x 508), x 120 to 960, y 1030 to 1538. During a gesture, zone S hard-cuts to a 2x macro of the moving control (clip box 1080 x 510 at y 1030) and cuts back.
    - "LEVEL MATCHED" (mono 26 px, 60 % white) sits at x 72, baseline 1000. It appears only if `measured.json` passes for that demo.
  - **L-CARD:** type-led, over a background plate or picture.

### ACT I: ATTENTION (bars 1 to 8, 0.000 to 13.378, intro tom groove; the guitar sits 1.4 dB under the drums)

| Shot | Time (frame) | Bar.beat | Hits that drive it | Picture and motion | Copy | Audio (demos.json) |
|---|---|---|---|---|---|---|
| **S01 Still + Mix turn** | 0.000 to 2.026 (0 to 120) | pre-roll, then 1.1 to 1.4 | **crash + kick + rack 0.407 (f24)**; kicks 0.811 (f48), 1.216 (f72), 1.622 (f97); floor toms 1.280, 1.412 (nothing: space); floor + rack 1.808 (ring out) | **Frames 0 to 23: a dead still** (grain frozen).<br>• The Green plate is L-MACRO on MIX: `plate.focus({ on: "mix", zoom })`, the knob about 600 px across, centred at (540, 1180), knob frame at 0 %. Saturation 0.12, except the MIX readout "0%" (`#9dbd78`, with its glow) and a 3 px lavender `#d0bdff` ring at 1.12x the knob diameter.<br>• An empty scope graticule, 300 px, centred at (770, 520).<br>**f24:**<br>• FLASH white, per-frame [0.45, 0.20, 0.06]; SHAKE 14 px (type 2 px).<br>• Colour floods: s 0.12 → 0.12 + 0.88 x mix / 40, following the knob.<br>• The type BURST: five copies of the headline in the five engine hues spray ±40 px sideways and snap back into the dry word over 10 frames (power3.out).<br>• Mix click-stop 1 (0 → 10 %, 90 ms, sine.inOut). The readout flips with the plugin's 60 ms digit flip. The scope trace blooms (real data).<br>**f48, f72, f97:** Mix click-stops 2, 3 and 4 (to 20, 30, 40 %). PUNCH (macro) on each kick. The ring pulses 1.12 → 1.18 → 1.12 over 8 frames on each step.<br>**f108:** the ring fades out over 0.3 s. | "Great" / "sound" (hook, Fraunces 600, 180 px, x 72, baselines 470 and 640). Chip `○ GUITAR · CHOROBOROS GREEN · MIX 0%`, then `●` with the live % | M01: Green, Mix 0 → 10 → 20 → 30 → 40 % on the four kicks; Trim follows |
| **S02 Set-up montage** (refrain 1) | 2.026 to 3.648 (121 to 217) | 2.1 to 2.4 | kicks 2.025 (f121), 2.433 (f145), 2.837 (f170), 3.243 (f194); floor toms 2.637, 3.445 | Four CUTs to 2.0x Green macros, one per kick: RATE "0.62 Hz", DEPTH "22%", OFFSET "90°", WIDTH "100%". Each pushes 1.00 → 1.03 over its beat (sine.inOut). PUNCH (macro) on the kick. On the floor toms the readout glow blinks +40 % for 3 frames. The scope inset holds at (770, 520). | "Great sound" drops to one line: Fraunces 600, 120 px, baseline 400 | M01 |
| **S03 Tagline on the hero** | 3.648 to 6.891 (218 to 412) | 3.1 to 4.4 | kick + rack 3.648 (CUT); kick 5.270 (STAMP); floor offbeats 3.853, 4.270, 4.686, 5.476; bar-4 run 6.076 (rack), 6.486 (kick + rack), 6.689 (floor) | CUT to the 3D hero (portrait crop: the centre of the desktop frames scaled so the frame height fills y 560 to 1540, graded to 60 %, grain).<br>• The scrub steps on each kick: +6 source frames, easing out over 5 video frames, then creeping.<br>• Floor offbeats: exposure +6 % for 3 frames.<br>• The bar-4 run is three push-ins: 1.00 → 1.06 → 1.12 → 1.18 on 6.076, 6.486 and 6.689 (SWEEP).<br>• PUNCH (plate) on the kicks. | "Great sound" (120 px, baseline 400) holds. "doesn’t" STAMPs on 5.270 (104 px, baseline 520). | M01 |
| **S04 "sit still."** | 6.891 to 10.135 (413 to 607) | 5.1 to 6.4 | kick + rack 6.892 (STAMP + a hero jump cut of +24 source frames); kicks of bars 5 and 6 | "*sit still.*" STAMPs on 6.892 as chorustype: Fraunces italic 400, 120 px, lavender, with Green wet copies at the heard settings (0.62 Hz, Depth 22 %, Mix 40 %).<br>• Bar 5: PUNCH (plate).<br>• **Bar 6 (8.513 to 10.135) is a designed hold:** nothing new appears, and PUNCH amplitude is x 0.6. This is the space before the title. | "Great sound" / "doesn’t" / "*sit still.*" (baselines 400, 520, 650) | M01 |
| **S05 Meet** | 10.135 to 13.378 (608 to 801) | 7.1 to 8.4 | kick + rack 10.135 (CUT); bar-8 fill: snare + floor + rack 12.767 (f766), kick + snare 12.973 (f778), floor 13.173 (f790) | CUT to the whole Green plate at scale 0.66 (924 x 559), centred at x 540, y 700 to 1259, lit. It pushes 1.00 → 1.05 across bars 7 and 8 (sine.inOut): tension.<br>**The fill:** three CUTs to 2x macros, each held to the next hit: Blue OFFSET knob (f766), Red HQ lever (f778), Purple COLOR thumb (f790). They are not heard, so they are graded s 0.35: a preview of the tour. | Eyebrow "FIRST RELEASE · KAIZEN DSP" (mono 30 px, `#b88cff`, baseline 300) and "Meet" (104 px, baseline 420), both STAMPed on 10.135 | M01 |

### ACT II: VITALITY (bars 9 to 14, 13.378 to 23.108, riff 1: full band, the guitar 6.6 dB over the drums)

| Shot | Time (frame) | Bar.beat | Hits | Picture and motion | Copy | Audio |
|---|---|---|---|---|---|---|
| **S06 Title slam** | 13.378 to 16.621 (802 to 996) | 9.1 to 10.4 | **crash + kick 13.378 (f802)**; snare 13.780 (f826); crash + kick 14.796 (f887); kicks; snares 15.402, 16.216, 16.418, 16.517 | CUT back to the whole Green plate (0.66) on f802. FLASH Green (0.30). SHAKE 10 px. A SMEAR burst (0.25 s) on the plate. "*Choroboros.*" lands on f802 as chorustype (150 px italic, lavender, Green wet copies). The dek STAMPs on f826. Kicks: PUNCH (plate). Snares: the chorustype's wet copies spread +30 % and relax over 150 ms. f887: FLASH Green (0.30). | "Meet" / "*Choroboros.*" (baselines 420 and 580). Dek "A chorus and modulation plugin / for macOS." (Inter 500, 44 px, `#a8a7a0`, baselines 1330 and 1386) | M01 (Green 40 %) |
| **S07 Lineup deck** | 16.621 to 19.864 (997 to 1190) | 11.1 to 12.4 | **crash + kick 16.622 (f997)**; snares 17.024 (f1021), 17.840 (f1070), 18.649 (f1118), 19.459 (f1167); snare pickups 19.662, 19.747 | CUT to black and the headline. Five plates slam onto a deck, scale 0.66, each 12 px lower and 8 px right of the one before: Green f997, Blue f1021, Red f1070, Purple f1118, Black f1167. Each drops from +40 px over 6 frames (expo.out) with a SMEAR burst in its own hue and a PUNCH. Colour = sound: Green s 1.0, the others s 0.35. The snare pickups (19.662, 19.747) push the deck 20 px, then 40 px (SWEEP). | "Five prebuilt" / "*engines.*" (104 px, baselines 420 and 530), STAMPed on f997 | M01 |
| **S08 The five voices** | 19.864 to 23.108 (1191 to 1385) | 13.1 to 14.4 | kick 19.856 / crash 19.928 (f1191); snares 20.270 (f1216), 21.081 (f1264), 21.892 (f1313), 22.703 (f1362), 22.900 (f1374); crash + kick 21.283 (f1276) | f1191: the deck fans into five knob-row strips (`slices.js`: the plate at scale 0.72, clipped to its knob row, 1008 x 200, 16 px gaps, y 560 to 1624; the last strip runs under the bottom UI, which is picture only). The fan takes 12 frames (expo.out). Each strip's tag brightens and the strip gets a PUNCH on its snare: Green f1216, Blue f1264, Red f1313, Purple f1362, Black f1374. f1276: FLASH Green (0.30) and all strips PUNCH. | Strip tags (mono 28 px, engine hue, top left of each strip): "GREEN · WARM", "BLUE · WIDE", "RED · VINTAGE", "PURPLE · EXPERIMENTAL", "BLACK · DENSE". The headline holds. | M01 |

### ACT III: SKILL, the tour (bars 15 to 22, 23.108 to 36.080; the band stops and the guitar plays alone)

**Stillness rule for 24.0 to 36.080:** there is no PUNCH, SHAKE or FLASH, and the grain is frozen. Only data moves: the scope, the readouts, the chorustype, and the TRIM meter in the top bar. The only other movement is the gesture.

Each engine gets 2 bars:
- **Bar A, beat 1:** a SMEAR, 0.5 s centred on the bar line.
- **Bar B:** the gesture runs from beat 1 to beat 3 (sine.inOut). The RING comes in 0.1 s before it and goes out 0.3 s after. Zone S cuts to the control macro on bar B beat 1 and cuts back on bar B beat 4.

| Shot | Time (frame) | Bars | Driver | Engine and move (audio = picture curve) | Picture | Copy |
|---|---|---|---|---|---|---|
| **S09 Blue** | 23.108 to 26.351 (1386 to 1580) | 15 to 16 | **The stop: kick + crash 23.108 (f1386)**, the last hit before the silence | M02: Blue Cubic, **Offset 0° → 120°, 24.729 to 25.540** (bar 16, beats 1 to 3) | f1386: the five strips collapse into the Blue strip, which opens into L-TOUR. FLASH Blue (0.30) and a SMEAR burst: the one flash of the act, because it is a real hit. Then stillness. The macro on OFFSET (2.0x) runs from f1483 to 25.945. The scope's two sides pull apart. | Eyebrow "CUBIC CORE"; "Blue. *Widens.*"; "BEST FOR  Clean width on vocals and buses"; caption "OFFSET 0° → 120°" (mono 32 px, `#79b8ff`, x 72, baseline 1000, instead of LEVEL MATCHED while the move runs) |
| **S10 Red** | 26.351 to 29.594 (1581 to 1774) | 17 to 18 | bar line 26.351 (SMEAR) | M03: Red, **HQ BBD → Tape at 27.972** (bar 18.1) | The lever throws on its own 18-frame sheet (the plugin's smootherstep, 420 ms), and the lit plate blends in by (1 - frame / 17). The macro on the lever (2.0x) runs from f1678 to 29.189. The chorustype on "Wavers." changes law, from STEP to WOW. | Eyebrow "BBD CORE", which becomes "TAPE CORE" at f1678; "Red. *Wavers.*"; "BEST FOR  BBD AND TAPE. VINTAGE INSTABILITY."; caption "HQ · BBD → TAPE" |
| **S11 Purple** | 29.594 to 32.837 (1775 to 1969) | 19 to 20 | bar line 29.594 | M04: Purple Orbit, **Color 10 % → 45 %, 31.216 to 32.026** | The macro on the COLOR slider (2.0x, crossing the portrait width) runs from f1872 to 32.432. The thumb glides and the scope's figure flattens. | Eyebrow "ORBIT CORE"; "Purple. *Orbits.*"; "BEST FOR  STRANGE TEXTURES, SOUND DESIGN, WEIRDNESS"; caption "COLOR 10% → 45%" |
| **S12 Black** | 32.837 to 36.080 (1970 to 2163) | 21 to 22 | bar line 32.837; the drums re-enter at 36.081 | M05: Black Linear Ensemble, **Depth 15 % → 30 %, 34.459 to 35.270** | The macro on DEPTH (at most 1.6x) runs from f2067 to 35.675. From 35.675 (bar 22.4) the frame pulls back 3 % (sine.in) into the drums. | Eyebrow "ENSEMBLE CORE"; "Black. *Multiplies.*"; "BEST FOR  Dense ensembles. Low CPU."; caption "DEPTH 15% → 30%" |

The headlines sit at 104 px, with the italic accent as chorustype at the heard engine's law. The BEST FOR lines use mono 26 px for "BEST FOR" and Inter 36 px for the text.

### ACT IV: DESIRE (bars 23 to 30, 36.080 to 49.053, tom groove 2). Heard: Black (M05) throughout, and the chip says so.

| Shot | Time (frame) | Bar.beat | Hits | Picture and motion | Copy |
|---|---|---|---|---|---|
| **S13 17 sound cores** | 36.080 to 39.324 (2164 to 2358) | 23.1 to 24.4 | kick + rack 36.081 (CUT, f2164); then 36.486, 36.887, 37.297, 37.502, 37.683, 37.926, 38.310, 38.517, 38.910 | CUT to black. A ring of 17 core glyphs (v4 cores art), 820 px across, centred at (540, 920). "17" sits in its centre: Fraunces 600, 260 px. The **ten prebuilt cores light one per hit** on the ten hits listed, in engine-hue pairs (green, green, blue, blue, red, red, purple, purple, black, black). Each light-up is 4 frames with a PUNCH (1.03) on the ring. The seven Create-only glyphs stay at 25 % white. Floor tom 39.133: the ring pulses. | Eyebrow "FIVE PREBUILT ENGINES · 17 SOUND CORES" (mono 30 px, baseline 300) and the headline "17 sound *cores.*" (104 px, baseline 420) STAMP on f2164. Dek: "The ten cores inside the prebuilt / engines, plus seven more." (Inter 40 px, baselines 1420 and 1470), on 36.887 |
| **S14 Create** | 39.324 to 45.810 (2359 to 2747) | 25.1 to 28.4 | kick + rack 39.324 (f2359); kicks 39.730, 40.135, 40.540; kick + floor 40.934; kick + rack 42.567 (f2554); kick + floor 44.171 (f2650); the other kicks | **f2359:**<br>• The seven Create-only glyphs flare white together.<br>• The ring collapses (8 frames, expo.in) into the **white Create canvas plate** at scale 0.72, centred at x 540, y 640 to 1250.<br>• The canvas **assembles on the kicks:** RATE drops in 40 px with a PUNCH on 39.324, DEPTH on 39.730, OFFSET on 40.135, WIDTH on 40.540. Readouts in `#303030`.<br>**f2554:** CUT to the real interface capture `/art/site/product/create/core-recipe.webp`, fitted to 936 px wide, centred at y 900. The white plate shrinks into zone S (scale 0.40, y 1250 to 1590, picture only).<br>**f2650:** CUT to `/art/site/product/create/review.webp`.<br>Kicks PUNCH the captures at 1.02. | "Build your own" / "engines" / "in *Create.*" (96 px, baselines 380, 480 and 580), STAMPed on f2359. On 40.934: "Choose one or two cores." / "Modify recipes. Pair them with artwork." (Inter 40 px, baselines 1380 and 1430). On 42.974: "Included with an active 30-day trial" / "or a paid licence." (mono 28 px, baselines 1470 and 1510), replacing the Inter lines |
| **S15 26 custom looks** | 45.810 to 49.053 (2748 to 2942) | 29.1 to 30.4 | bar 29: 45.811, 46.216, 46.418, 46.622, 46.832, 47.027; the bar-30 fill: 47.414 (f2844), 47.637 (f2858), 47.835, 48.042, 48.236, 48.446, 48.648 | **The wall:** a 4 x 7 grid of the 26 look thumbnails (`/art/site/themes/<id>-thumb.webp`), tiles 200 x 100, 16 px gaps, x 72 to 920, y 560 to 1356. It builds **one row per hit**: rows 1 to 6 on the six bar-29 hits, and row 7 (2 tiles) on f2844. On f2858 the wall collapses into one large look (`<id>-on.webp`, 880 x 440, centred at y 960: 18.7 % of the frame, under the PSE area limit). The look **swaps with a hard CUT and a PUNCH on each remaining fill hit**. The six looks are ordered by mean luminance, so neighbours differ by less than 10 %. The sound does not change. | "26 custom" / "*looks.*" (104 px, baselines 380 and 490). "A custom look changes what Choroboros" / "looks like, not how it sounds." (Inter 40 px, baselines 1420 and 1470, on a 60 % black band) |

### ACT V: THE OFFER (bars 31 to 38, 49.053 to 62.026, verse, backbeat)

| Shot | Time (frame) | Bar.beat | Hits | Picture and motion | Copy | Audio |
|---|---|---|---|---|---|---|
| **S16 Free** | 49.053 to 55.540 (2943 to 3331) | 31.1 to 34.4 | **crash + kick 49.054 (f2943)**; snares 49.459, 50.270; crash + kick 50.469; **crash + kick 52.296 (f3137)**; snares on 2 and 4; pickups 55.338, 55.417 | FLASH Green (0.30). The Green plate (scale 0.56, 784 x 474, x 148 to 932, y 600 to 1074) SLAMs down from the top, and the Purple plate (y 1090 to 1564) SLAMs up from the bottom. A SLAM is a 6-frame drop from ±160 px (power4.out) with a PUNCH on landing.<br>• Snares 49.459 and 50.270 STAMP "FREE" tags on Green, then Purple (mono 26 px on engine-hue pills, at each plate's top-left corner).<br>• f3137: FLASH Purple (0.30). Colour = sound swaps: Purple lit, Green dimmed.<br>• Kicks PUNCH (plate). The pickups 55.338 and 55.417 SWEEP both plates up and out (2 steps of 400 px). | "Green and Purple" / "are *free.*" (104 px, baselines 380 and 490) on f2943. "No card or licence key needed." (Inter 44 px, baseline 1500) on 50.469 | M06 Green (bars 31 to 32), M07 Purple (bars 33 to 34) |
| **S17 Trial** | 55.540 to 62.026 (3332 to 3720) | 35.1 to 38.4 | **crash + kick 55.540 (f3332)**; hat + kick 56.341; **crash + kick 56.958 (f3417)**; **crash + kick 58.784 (f3527)**; kick 60.405 (f3624); snares on 2 and 4; snare 61.621 | A 2 x 2 grid of plates at scale 0.30 (420 x 254), x 72 to 928, y 640 to 1164, gap 16: Blue and Red on top, Black and the white Create canvas below.<br>• The heard tile is at s 1.0 with a ring in its hue; the others are at 0.35.<br>• Blue from f3332, Red (lever at TAPE, lit) from f3417, Black from f3527. Each switch is a FLASH in the new hue (0.30) plus a STAMP of the tile.<br>• f3624: the Create tile STAMPs with a white ring. The chip still reads BLACK.<br>• Snares PUNCH the tile labels.<br>• 61.621: a WHIP up (dir [0, -1]) into S18. | "30-day free trial." / "*No payment card.*" (96 px, baselines 380 and 480) on f3332. "The trial unlocks Blue, Red," / "Black and Create." (Inter 44 px, baselines 1260 and 1314) on 56.341. "After the trial, Green and" / "Purple stay free." (Inter 40 px, muted, baselines 1380 and 1430) on 58.784. Tile labels BLUE / RED / BLACK / CREATE (mono 26 px, engine hue; CREATE in white) | M08 Blue, M09 Red Tape, M10 Black |

**Line-fit rule (all shots, both films):**
- Every scene measures each line it sets.
- If a line would pass x 928 at the size given here, the scene first lowers the size, never below the TYPE minimum (headline 96 px, body 40 px).
- If the line still does not fit, it breaks at the last space that fits.
- `qc.mjs` fails any text that leaves the safe rectangle.

### ACT VI: PROOF (bars 39 to 44, 62.026 to 71.756, riff 2, the loudest guitar)

| Shot | Time (frame) | Bar.beat | Hits | Picture and motion | Copy | Audio |
|---|---|---|---|---|---|---|
| **S18 The A/B** | 62.026 to 68.513 (3721 to 4109) | 39.1 to 42.4 | **ON crash + kick 62.027 (f3721); BYPASS crash + kick 63.447 (f3806); ON crash + kick 65.270 (f3916); BYPASS crash + kick 66.688 (f4001)**; snares on 2 and 4; bar-40 fill 64.959, 65.068, 65.169 | Layout:<br>• zone T: the headline and the **A/B toggle** (`abtoggle.js`), a film graphic that is not plugin UI. It is a segmented pill 856 x 96 at x 72, y 560 to 656, reading `BYPASS │ CHOROBOROS`, mono 40 px. The active segment is filled `#79b8ff` with text `#0b1420`; BYPASS active is a `#a8a7a0` outline.<br>• zone H: the scope, 580 px, centred at (540, 980).<br>• zone S: the Blue plate at scale 0.58 (812 x 491), x 134 to 946, y 1290 to 1781 (its lower part runs under the UI, picture only).<br>**Each slam, on the hit frame:**<br>• the toggle slides over 3 frames (power3.out);<br>• saturation snaps (ON 1.0, BYPASS 0.12);<br>• the scope's wet trace appears or vanishes (the dry trace remains as a 20 % white ghost);<br>• the chorustype wet copies on "guitar." turn on or off;<br>• the chip changes;<br>• FLASH in the new state's hue (Blue 0.30; bypass: a white 0.12);<br>• SHAKE 10 px.<br>Between slams: PUNCH (plate) on kicks, and snares pulse the toggle border +60 % for 6 frames. The fill steps the toggle glow 3 times (SWEEP). | "A/B on the" / "*guitar.*" (104 px, baselines 380 and 490). Eyebrow "LEVEL MATCHED · DRUMS UNTOUCHED" (mono 28 px, baseline 300). It appears only if QC-A4 and QC-A5 pass for M11; otherwise "A/B ON THE GUITAR BUS" | M11 Blue; bypass 63.447 to 65.270 and 66.688 to 68.514 |
| **S19 The settings** (refrain 2) | 68.513 to 71.756 (4110 to 4304) | 43.1 to 44.4 | **ON crash + kick 68.514 (f4110)**; crash + kick 69.931 (f4195); bar 44: kick 70.337 (f4220), snare 70.540, hat + kick 70.938, hat + kick 71.139, snare 71.352 | f4110: the ON slam. f4195: CUT to the whole Blue plate at scale 0.74 (bleeding past the margins, picture only), with a FLASH (Blue 0.30).<br>**Bar 44:** five hard CUTs to 2x Blue macros, one per hit (`montage.js`): RATE "1.23 Hz" (70.337), DEPTH "12%" (70.540), OFFSET "120°" (70.938), COLOR "45%" (71.139), MIX "40%" (71.352). Each pushes 1.00 → 1.03 with a PUNCH (macro). This rhymes with S02. | "Blue. *Widens.*" (104 px, baseline 420) with the eyebrow "CUBIC CORE" | M11 ON |

### ACT VII: BUY (bars 45 to 56, 71.756 to 91.216)

| Shot | Time (frame) | Bar.beat | Hits | Picture and motion | Copy | Audio |
|---|---|---|---|---|---|---|
| **S20 Price** | 71.756 to 78.243 (4305 to 4693) | 45.1 to 48.4 | **crash + kick 71.757 (f4305)**; crash + kick 72.364, 73.176; bar 46 (no crash); crash + kick 75.000, 75.608, 76.418; bar 48: crash + kick 76.823, 77.228, 77.634; snares 77.838, 78.041 | f4305: a SLAM to the 3D hero (portrait crop, full colour, 70 % brightness, y 560 to 1920) with FLASH Green (0.30) and SHAKE 10 px. "$49.99" SLAMs in. The term lines STAMP one per crash push:<br>• 72.364 "One-time purchase."<br>• 73.176 "No subscription."<br>• 75.000 "Lifetime updates."<br>• 75.608 "30-day money-back guarantee."<br>Every crash has a FLASH Green (0.30). **Bar 46 is a hold:** no new element; snares PUNCH the price at 1.012. 76.418: the hero scrub jumps +24 frames. **Bar 48:** three hard CUTs between hero angles (jumps in the hero sequence) on 76.823, 77.228 and 77.634. The flashes on 77.228 and 77.634 become edge glows (PSE). The snares 77.838 and 78.041 SWEEP the term stack up 60 px, twice. | "$49.99" (Fraunces 600, 190 px, baseline 520) / "*USD.*" (italic 400, 190 px, lavender, baseline 720). Terms: Inter 600, 48 px, baselines 860, 924, 988, 1052 | M12 Green |
| **S21 More from Kaizen DSP** | 78.243 to 83.107 (4694 to 4985) | 49.1 to 51.4 | **crash + kick 78.244 (f4694)**; crash + kick 78.850, 79.662; bar line 79.864 (f4791); kick 80.066; **crash + kick 81.486 (f4889)**; crash + kick 82.095, 82.904 | **Heard dry** (bypass), and the chip reads `○ GUITAR · BYPASS`.<br>• **Fold** (f4694): the Fold clip frames (`clips.js`), portrait-cropped in zone H. On the crashes at 78.850 and 79.662, CUT between two Fold crops. No flash (the Fold segment flash, if any, is `#64e28b` at 0.20).<br>• **Echolalia** (f4791, a hard CUT on the bar line): its clip frames in amber. The kick at 80.066 PUNCHes it (1.03).<br>• **Stovetop** (f4889): `/art/site/stovetop/stovetop-hero.jpg`, shown whole and never cropped (scaled to 900 px wide, centred at y 900). Crashes at 82.095 and 82.904: PUNCH 1.02 with a `#ff7a2e` edge glow. | Eyebrow "MORE FROM KAIZEN DSP" (mono 30 px, `#b88cff`, baseline 300) for all three. Fold: "Fold." (104 px, baseline 420); pill "FREE · COMING SOON" (mono 26 px, `#64e28b`); "A free spectral stereo shaper." (Inter 44 px, baseline 1420). Echolalia: "Echolalia." ; pill "DELAY + REVERB · COMING SOON" (`#f0a04a`); "Echoes that change *as they return.*" (Inter 44 px, accent `#d8a066`, two lines). Stovetop: "Stovetop." (Sedgwick Ave Display, 110 px, `#ff7a2e`); pill "IN DEVELOPMENT"; "Add a little something-something." (Inter 44 px) | the master (bypass span 78.244 to 83.310) |
| **S22 Wind-up** (refrain 3) | 83.107 to 84.725 (4986 to 5082) | 52.1 to 52.4 | **crash + kick 83.310 (f4998)**; snare 83.513; kick 83.715 (+ crash 83.763); kick 84.120 (+ crash 84.167); snare 84.324; kick 84.526 | Six hard CUTs to 2x Green macros, accelerating into the stop. Choroboros is back on at f4998 (the chip becomes ●, colour floods).<br>• RATE "0.62 Hz" (f4998), DEPTH "22%" (83.513), OFFSET "90°" (83.715), WIDTH "100%" (84.120), COLOR "35%" (84.324), MIX "40%" (84.526, with the ring on).<br>• Each macro pushes 1.00 → 1.05 (faster).<br>• FLASH Green (0.30) on f4998, 83.715 and 84.120. The PSE limiter allows 3 in this second.<br>• **The inhale:** on 84.324 and 84.526 the whole frame compresses to 0.97, then 0.95 (4 frames each, power2.out). | none | M13 Green |
| **S23 THE STOP: payoff** | **84.725 to 86.351 (5083 to 5180)** | 53.1 to 53.4 | **snare 84.7251 + kick 84.7296 + the loudest crash 84.733** (f5083); the crash rings to about 85.4 | f5083:<br>• the frame releases from 0.95 to 1.00 with a single 1.01 overshoot on the next frame;<br>• white FLASH [0.45, 0.15];<br>• a hard CUT to near-black stillness.<br>The scope, 760 px, centred at (540, 1060), shows the white dry ghost plus the Green wet trace: the only moving picture. The grain freezes. | "Great sound" / "doesn’t" / "*sit still.*" (Fraunces 600, 120 px, baselines 400, 530, 660). "sit still." is chorustype SINE Green at the heard 0.62 Hz | M13: the guitar alone through Green |
| **S24 End card + Buy** | 86.351 to 91.216 (5181 to 5472) | 54.1 to 56.4 | bar lines (guitar only): 86.351 (f5181), 87.162 (f5229), 87.972 (f5278) | **f5181:** HARD build of the name, the live Green plate and the **Buy button**, all together. **f5229:** the price line and the URL. **f5278:** the format row and the legal line. Bars 55 and 56 hold everything. The only movement is the plate readouts and TRIM meter (live), the chorustype, the scope inset and the Buy button's hairline (G3b, one cycle per bar at 0.62 Hz). The picture holds to f5472. | The end card, in the copy deck (section 4.3) | M13; fade 89.900 to 91.080 |

**Event density check:** from 0.407 to 23.108 and from 36.080 to 84.725, there is a designed event (cut, stamp, slam, whip, sweep step, flash, gesture start or click-stop) at least once every 2 beats. The only exceptions are the designed holds: bar 6, bar 46 and bar 53 onward. PUNCH does not count as an event.

---

## 3. DEMO SPEC (audio build)

`film/v5/demos.json` is authoritative: the knob values, gesture times, switch rules, level-match rules and output paths are all there. The picture reads the same file for readouts, so what you see is what you hear. Summary:

**Method (both films): the BP path.** `out = master - BP(nd) + choro_trim(BP(nd))`.
- `nd` = `/home/user/build/v5/stems/nondrums.wav`.
- BP = a zero-phase Butterworth band-pass, 120 Hz to 5.5 kHz (4th order per edge, `sosfiltfilt`).
- This replaces the guitar band inside the master. The drums, the low end and the air above 5.5 kHz stay the untouched master.
- In the guitar-alone windows nd = master, so the master itself is processed there without a path switch.
- **Fallback:** parallel wet-only (`demos.json` `method.fallback_parallel`), chosen per demo only if a null test fails. Log the choice.

Everything outside the demos, and every bypass span, is the untouched master, bit for bit.

**Renderer:** `/home/user/build/choro-render/build/choro-render`, called by path. Pass every knob explicitly, `--block 128`. Give each demo 3 s of real pre-roll input. Automation is sampled every 10 ms from the same curves the picture uses. Use `--trim` for the plug-in's Output Trim. Workers at most 2.

**Main film (display units: rate Hz, depth %, offset °, width %, color %, mix %)**

| Demo | Span (bars) | Engine / core, hq | Rate | Depth | Offset | Width | Color | Mix | Gesture / toggle | Switch in |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | 0.000 to 23.108 (1 to 14) | Green / Lagrange 3rd, 0 | 0.62 | 22 | 90 | 100 | 35 | **0 → 10 → 20 → 30 → 40** | Mix click-steps (90 ms, sine.inOut) on the kicks 0.4074, 0.8106, 1.2160, 1.6217 (1.1 to 1.4). Trim follows Mix. | start |
| M02 | 23.108 to 26.351 (15 to 16) | Blue / Cubic, 0 | 1.23 | 12 | **0 → 120** | 100 | 45 | 40 | Offset from 24.7291 to 25.5399 (16.1 to 16.3) | 20 ms, ends on the 23.108 stop hit |
| M03 | 26.351 to 29.594 (17 to 18) | Red / BBD → **Tape**, 0 → 1 | 0.62 | 30 | 90 | 100 | 30 | 40 | HQ step at 27.9723 (18.1) | 20 ms, centred on 26.3507 |
| M04 | 29.594 to 32.837 (19 to 20) | Purple / Orbit, 1 | 0.12 | 50 | 90 | 100 | **10 → 45** | 30 | Color from 31.2156 to 32.0264 (20.1 to 20.3) | 20 ms, centred on 29.594 |
| M05 | 32.837 to 49.054 (21 to 30) | Black / Linear Ensemble, 1 | 0.31 | **15 → 30** | 120 | 100 | 60 | 40 | Depth from 34.4588 to 35.2696 (22.1 to 22.3), then held as the bed | 20 ms, centred on 32.8372 |
| M06 | 49.054 to 52.296 (31 to 32) | Green / Lagrange 3rd, 0 | 0.62 | 22 | 90 | 100 | 35 | 40 | none | ends on the 49.054 crash |
| M07 | 52.296 to 55.540 (33 to 34) | Purple / Orbit, 1 | 0.12 | 50 | 90 | 100 | 45 | 30 | none | ends on the 52.296 crash |
| M08 | 55.540 to 56.958 (35) | Blue / Cubic, 0 | 1.23 | 12 | 120 | 100 | 45 | 40 | none | ends on the 55.540 crash |
| M09 | 56.958 to 58.784 (35.4.5 to 36) | Red / Tape, 1 | 0.62 | 30 | 90 | 100 | 30 | 40 | none | ends on the 56.958 crash |
| M10 | 58.784 to 62.027 (37 to 38) | Black / Linear Ensemble, 1 | 0.31 | 30 | 120 | 100 | 60 | 40 | none | ends on the 58.784 crash |
| M11 | 62.027 to 71.757 (39 to 44) | Blue / Cubic, 0 | 1.23 | 12 | 120 | 100 | 45 | 40 | **Bypass A/B:** BYPASS 63.447 to 65.270 and 66.688 to 68.514 (the master itself). Toggles are 10 ms equal-power, midpoint 5 ms before the hit | ends on the 62.027 crash |
| M12 | 71.757 to 78.244 (45 to 48) | Green / Lagrange 3rd, 0 | 0.62 | 22 | 90 | 100 | 35 | 40 | none | ends on the 71.757 crash |
| bypass | 78.244 to 83.310 (49 to 52.1.5) | the master | | | | | | | the family cards | 10 ms toggles on the 78.244 and 83.310 crashes |
| M13 | 83.310 to 91.216 (52 to 56) | Green / Lagrange 3rd, 0 | 0.62 | 22 | 90 | 100 | 35 | 40 | none; fade 89.900 to 91.080 | ends on the 83.310 crash |

**Level matching (per bar):**
- One Output Trim per demo, `-(LUFS(out) - LUFS(master))` over its ON span, rounded to 0.1 dB. The estimates are Green -2.4, Blue -2.0, Red -2.4, Purple -2.0 and Black -1.1 dB.
- Pass: every full ON bar within ±0.5 LU of the same master bar, and the demo within ±0.2 LU.
- If a bar fails, split the demo at that bar line and give each part its own trim.
- The top bar's TRIM readout shows the trim in use, so the viewer sees the engineer's gain compensation.
- No limiter on the song. A bar's true peak may exceed the master's by at most 0.1 dB; if it does, lower the trim.
- The results go to `measured.json`, which the picture reads to gate "LEVEL MATCHED".

**Mono:**
- The processed band's fold-down may lose at most 0.6 LU more than the dry band's.
- The processed band's L/R correlation stays above +0.1.
- If a demo fails, lower its Depth in 2 % steps, and update `demos.json` and the readouts together.

**TikTok demos:** see section 7 and `demos.json` (T01 to T06).

**Audio deliverables:**
- `/home/user/build/v5/master_v5.wav` (91.216 s) and `/home/user/build/v5/tiktok_v5.wav` (15.000 s), both 48 kHz, 24-bit stereo.
- Scope data in `/home/user/build/v5/audio/scope/` and `/home/user/build/v5/audio/scope-tiktok/`. Each holds `index.json`, `dry.i16` and `wet.i16` in the existing `scope.js` format, aligned to composition time, plus `meter.json` and `measured.json`. `v5.sh prep` links them to `/data/scope`.
- The build script lives in the repo as code only: `audio/film/v5_demos.py`. It reads `film/v5/demos.json` and writes no audio into the repo.

---

## 4. Copy deck (every on-screen word, exact)

Type (from `film/lib/portrait.js` TYPE):
- **Headlines:** Fraunces 600, letter-spacing -0.02 em, 104 px (never under 96). The italic accent is Fraunces italic 400 in lavender `#d0bdff`. Headlines end with a full stop.
- **Body:** Inter 500, 44 px (minimum 40), in `#a8a7a0` when muted.
- **Eyebrows:** JetBrains Mono 600, uppercase, tracking 0.3 em, 30 px, `#b88cff`.
- **Tags and chip:** mono 26 to 28 px.
- **Legal:** Inter 22 px.

Use the typographic apostrophe (’). Text stays inside x 60 to 940, y 220 to 1540, except the legal line (`data-bleed`, y 1552 to 1640, end cards only).

Reading budget: each block is on screen at least max(1.5 s, 0.25 s per word). Checked blocks that sit below 1.5 s:
- the fill macros: no words;
- the family cards: 1.6 s each, 3 to 6 words;
- the "*Choroboros.*" accent, which is part of a block on for 3.2 s.

### 4.1 Main film

| # | On | Off | Text (exact) | Style | Position | Claim check (brand-and-copy) |
|---|---|---|---|---|---|---|
| 1 | 0.000 | end | `○ GUITAR · CHOROBOROS GREEN · MIX 0%` (live; see the chip rule) | chip 26 px, 70 % white | x 72, baseline 256 | A true statement about this video's processing; the engine and core names come from the product |
| 2 | 0.000 | 2.026 | Great / sound | Fraunces 600, 180 px | 72, 470 / 640 | §5.1 primary tagline, unfinished on purpose |
| 3 | 2.026 | 10.135 | Great sound | 120 px | 72, 400 | §5.1 |
| 4 | 5.270 | 10.135 | doesn’t | 104 px | 72, 520 | §5.1 |
| 5 | 6.892 | 10.135 | *sit still.* | italic 120 px, chorustype | 72, 650 | §5.1 (accent on "sit still.") |
| 6 | 10.135 | 16.621 | FIRST RELEASE · KAIZEN DSP | eyebrow | 72, 300 | §5.2 "First release" |
| 7 | 10.135 | 16.621 | Meet | 104 px | 72, 420 | §5.2 "Meet *Choroboros.*" |
| 8 | 13.378 | 16.621 | *Choroboros.* | italic 150 px, chorustype | 72, 580 | §5.2 |
| 9 | 13.780 | 16.621 | A chorus and modulation plugin / for macOS. | Inter 44 px, muted | 72, 1330 / 1386 | §9.2 |
| 10 | 16.621 | 23.108 | Five prebuilt / *engines.* | 104 px | 72, 420 / 530 | §9.6 |
| 11 | 19.864 | 23.108 | GREEN · WARM / BLUE · WIDE / RED · VINTAGE / PURPLE · EXPERIMENTAL / BLACK · DENSE | tags, mono 28 px, engine hue | strip tops | §5.2 "Five distinct chorus voices: warm, wide, vintage, experimental, and dense." (trimmed, same meaning) |
| 12 | 23.108 | 26.351 | CUBIC CORE / Blue. *Widens.* / BEST FOR  Clean width on vocals and buses / OFFSET 0° → 120° | eyebrow / 104 / mono 26 + Inter 36 / mono 32 in hue | L-TOUR | §5.2 BEST FOR verbatim; core name from the product; the verb is v4-approved |
| 13 | 26.351 | 29.594 | BBD CORE (TAPE CORE from 27.972) / Red. *Wavers.* / BEST FOR  BBD AND TAPE. VINTAGE INSTABILITY. / HQ · BBD → TAPE | same | L-TOUR | §5.2 verbatim casing |
| 14 | 29.594 | 32.837 | ORBIT CORE / Purple. *Orbits.* / BEST FOR  STRANGE TEXTURES, SOUND DESIGN, WEIRDNESS / COLOR 10% → 45% | same | L-TOUR | §5.2 |
| 15 | 32.837 | 36.080 | ENSEMBLE CORE / Black. *Multiplies.* / BEST FOR  Dense ensembles. Low CPU. / DEPTH 15% → 30% | same | L-TOUR | §5.2 and §11 ("Low CPU" verbatim, no number) |
| 16 | 23.108 | 36.080 | LEVEL MATCHED (per demo, only if measured.json passes; hidden while a gesture caption shows) | mono 26 px, 60 % white | 72, 1000 | True by QC |
| 17 | 36.081 | 39.324 | FIVE PREBUILT ENGINES · 17 SOUND CORES (eyebrow) / 17 sound *cores.* (headline) | eyebrow / 104 px | 72, 300 / 420 | §9.7 safe form ("Five prebuilt engines. 17 sound cores."), on the same screen as line 19; never "17 engines" |
| 18 | 36.081 | 39.324 | 17 | Fraunces 600, 260 px | ring centre | §9.7, paired with line 17 on the same screen |
| 19 | 36.887 | 39.324 | The ten cores inside the prebuilt / engines, plus seven more. | Inter 40 px | 72, 1420 / 1470 | §9.8 verbatim |
| 20 | 39.324 | 45.810 | Build your own / engines / in *Create.* | 96 px | 72, 380 / 480 / 580 | §9.9 verbatim |
| 21 | 40.934 | 42.974 | Choose one or two cores. / Modify recipes. Pair them with artwork. | Inter 40 px | 72, 1380 / 1430 | §9.9 trimmed, same meaning |
| 22 | 42.974 | 45.810 | Included with an active 30-day trial / or a paid licence. | mono 28 px | 72, 1470 / 1510 | §5.3 verbatim; Create is never shown as free |
| 23 | 45.810 | 49.053 | 26 custom / *looks.* | 104 px | 72, 380 / 490 | §9.10 |
| 24 | 45.810 | 49.053 | A custom look changes what Choroboros / looks like, not how it sounds. | Inter 40 px on a 60 % black band | 72, 1420 / 1470 | §5.3 verbatim; forbidden §10.12 respected |
| 25 | 49.054 | 55.540 | Green and Purple / are *free.* | 104 px | 72, 380 / 490 | §9.13; never "Choroboros is free" |
| 26 | 49.459 / 50.270 | 55.540 | FREE (tags on Green, then Purple only) | mono 26 px on hue pills | plate corners | §9.13 |
| 27 | 50.469 | 55.540 | No card or licence key needed. | Inter 44 px | 72, 1500 | §9.13 verbatim |
| 28 | 55.540 | 62.026 | 30-day free trial. / *No payment card.* | 96 px | 72, 380 / 480 | §9.14 |
| 29 | 56.341 | 62.026 | The trial unlocks Blue, Red, / Black and Create. | Inter 44 px | 72, 1260 / 1314 | §9.15 verbatim |
| 30 | 58.784 | 62.026 | After the trial, Green and / Purple stay free. | Inter 40 px, muted | 72, 1380 / 1430 | §9.16, first clause |
| 31 | 55.540 | 62.026 | BLUE / RED / BLACK / CREATE | mono 26 px | tile labels | §9.15 |
| 32 | 62.026 | 68.513 | A/B on the / *guitar.* | 104 px | 72, 380 / 490 | A description of the video |
| 33 | 62.026 | 68.513 | LEVEL MATCHED · DRUMS UNTOUCHED (fallback: A/B ON THE GUITAR BUS) | eyebrow | 72, 300 | True by QC-A4 and QC-A5, or the fallback is used |
| 34 | 62.026 | 68.513 | BYPASS │ CHOROBOROS | mono 40 px pill | y 560 to 656 | UI label of this video |
| 35 | 68.513 | 71.756 | CUBIC CORE / Blue. *Widens.* | eyebrow / 104 px | 72, 300 / 420 | as line 12 |
| 36 | 71.757 | 78.243 | $49.99 / *USD.* | 190 px | 72, 520 / 720 | §9.17, exact, never rounded |
| 37 | 72.364 / 73.176 / 75.000 / 75.608 | 78.243 | One-time purchase. / No subscription. / Lifetime updates. / 30-day money-back guarantee. | Inter 600, 48 px | 72, 860 / 924 / 988 / 1052 | §9.17 verbatim; not "updates forever" |
| 38 | 78.244 | 83.107 | MORE FROM KAIZEN DSP | eyebrow | 72, 300 | §9.28 |
| 39 | 78.244 | 79.864 | Fold. / FREE · COMING SOON / A free spectral stereo shaper. | 104 px / pill mono 26 px `#64e28b` / Inter 44 px | 72, 420 / pill y 460 to 510 / 1420 | §9.25; no date, no formats |
| 40 | 79.864 | 81.486 | Echolalia. / DELAY + REVERB · COMING SOON / Echoes that change / *as they return.* | 104 / pill `#f0a04a` / Inter 44 px | same; body 1420 / 1470 | §9.26; no price, no formats |
| 41 | 81.486 | 83.107 | Stovetop. / IN DEVELOPMENT / Add a little something-something. | Sedgwick Ave Display 110 px `#ff7a2e` / pill / Inter 44 px | same | §9.27; no price, no date |
| 42 | 84.725 | 86.351 | Great sound / doesn’t / *sit still.* | 120 px, chorustype | 72, 400 / 530 / 660 | §5.1 |

The engine verbs ("Widens.", "Wavers.", "Orbits.", "Multiplies.") are the v4-approved headlines. "Sways." (Green) is not used: Green's lesson is the Mix turn.

### 4.2 Forbidden-list scan (applies to both films)

All of these are absent:
- Windows or Linux;
- DAW names or logos;
- sample rates or minimum OS;
- version strings;
- the dev panel, beta toolbar or feedback items (the top bar is the release bar);
- "17 engines";
- rounded prices, discounts or urgency;
- "updates forever";
- testimonials, outlet logos or download counts;
- AI wording;
- "lush", "shimmer", "ethereal", "cosmic" or "spacetime";
- hardware lineage;
- any person's name;
- the track title.

VST appears only in the format row, next to the unmodified VST Compatible logo. AU, AAX and macOS appear as text only.

### 4.3 Main end card (built at 86.351, 87.162 and 87.972; held to 91.216)

| Element | Text | Style | Box |
|---|---|---|---|
| Name | *Choroboros.* | Fraunces italic 400, 150 px, `#f6f4ef`, chorustype SINE Green (live) | x 72, baseline 440 |
| Status | Available now for macOS. | Inter 500, 44 px, muted | 72, baseline 505 |
| Plate | the live Green plate, lit, at M13 values (0.62 Hz, 22 %, 90°, 100 %, COLOR 35 %, MIX 40 %, TRIM = measured) | scale 0.50 (700 x 424) | x 72 to 772, y 548 to 972 |
| Scope | the guitar band, live | 170 px canvas | centre (855, 760) |
| **Buy** | **Buy Choroboros →** | Cream `#f5f2ea` button, text `#171817`, Inter 600 56 px, radius 20 px, lucide ArrowRight | **x 72 to 928, y 1000 to 1140**. It is the largest and brightest object on the card |
| Secondary | Start your 30-day free trial | Outline button, Inter 500 36 px, 1 px border `rgba(255,255,255,0.32)`. Flag `TRIAL_CTA`, default on; the lead confirms the site's trial switch before release, otherwise it is off | x 72 to 620, y 1160 to 1222 |
| Offer | $49.99 USD · Green and Purple free | Inter 500, 40 px, `#f6f4ef` | 72, baseline 1290 (from 87.162) |
| URL | kaizendsp.com/choroboros | Inter 600, 44 px, underline `#b88cff` | 72, baseline 1350 (from 87.162) |
| Format row | [VST Compatible logo, with TM, unmodified] VST®3 · AU · AAX · [AppWindow] Standalone · [Monitor] macOS | five tiles 160 x 100, gap 16, labels mono 24 px | x 72 to 936, y 1392 to 1492 (from 87.972) |
| Legal | VST is a trademark of Steinberg Media Technologies GmbH, registered in Europe and other countries. AAX is a trademark of Avid Technology, Inc. macOS and Audio Units are trademarks of Apple Inc. | Inter 22 px, 50 % white, `data-bleed` | y 1552 to 1640 (from 87.972) |

The VST tile appears by a hard cut only. It is never scaled, blurred, flashed, tinted or cropped, and no layer draws over it.

### 4.4 Video descriptions (never on screen)

**Main film:**

> Choroboros: a chorus and modulation plugin for macOS. VST3, AU, AAX and standalone. Green and Purple are free. 30-day free trial, no payment card. $49.99 USD, one-time purchase. https://kaizendsp.com/choroboros?utm_source=<platform>&utm_medium=video&utm_campaign=choroboros_launch
> Music: Green Alderson (guitar), Flavio Monopoli (drums). Choroboros processing on the guitar was added by Kaizen DSP for this video.
> VST is a trademark of Steinberg Media Technologies GmbH, registered in Europe and other countries. AAX is a trademark of Avid Technology, Inc. macOS and Audio Units are trademarks of Apple Inc.

**TikTok post text:**

> One riff, five engines, on the guitar. Choroboros for macOS: Green and Purple free, 30-day free trial, $49.99 USD. kaizendsp.com/choroboros
> Music: Green Alderson (guitar), Flavio Monopoli (drums). Choroboros processing on the guitar added by Kaizen DSP. VST is a trademark of Steinberg Media Technologies GmbH, registered in Europe and other countries.

The names are spelled exactly and never appear on screen. "Guitar, Green Alderson" is written that way so "Green" cannot be read as the engine. The credit line implies no use or endorsement.

---

## 5. Vertical kit spec

The kit already exists in part: `film/lib/beats.js`, `film/lib/motion.js`, `film/lib/portrait.js` and `film/v5/boot.js`. This spec adopts their API and constants. The changes marked **KIT CHANGE** are required.

### 5.1 Frame, safe zones, grid (`portrait.js`)

- **Frame:** W 1080, H 1920, 60 fps.
- **Text-safe rectangle:** x 60 to 940, y 220 to 1540. The left text edge is x 72.
- **Platform zones:** top 0 to 220, bottom 1540 to 1920, right rail x 940 to 1080. Pictures may run under all three; text, prices, buttons and gesture subjects may not.
- **Vertical zones:**
  - chip: 232 to 262;
  - T (type): 280 to 660;
  - H (hero): 560 to 1240;
  - S (support): 1240 to 1540.
- **Legal small print:** y 1552 to 1640, end cards only, marked `data-bleed`.

### 5.2 Type scale and minimums

Set by `portrait.js` TYPE (px at 1080 wide, where 1 px = 0.36 pt on a phone):

| Style | Size | Minimum |
|---|---|---|
| hook | 180 | |
| title | 150 | |
| price | 190 | |
| headline | 104 | 96 |
| body | 44 | 40 |
| eyebrow | 30 | 28 |
| tag | 28 | 26 |
| chip | 26 | 24 |
| legal | 22 | |

A 104 px headline line holds about 15 characters. Use the line breaks given in the copy deck.

### 5.3 Colour tokens (`portrait.js` COLOR)

**Neutrals:**
- background `#050506`, surface `#0c0d10`;
- text `#f6f4ef`, muted `#a8a7a0`;
- brand purple `#b88cff`, lavender accent `#d0bdff`;
- Buy button `#f5f2ea` with text `#171817`.

**Engines:**

| Engine | Fill (solid, pills, flashes) | Glow (labels, scope, wet copies) | Readout (the product's own) |
|---|---|---|---|
| Green | `#64e28b` | `#7ee0a0` | `#9dbd78` |
| Blue | `#63b3ff` | `#79b8ff` | `#7fb8ff` |
| Red | `#ff776d` | `#ff8a80` | `#ff8d8b` |
| Purple | `#b88cff` | `#c9b1ff` | `#b88dd8` |
| Black | `#9ca3af` | `#9aa0a6` | `#d4d4d4` |

The white Create canvas readouts are `#303030`.

**Family** (each only in its own card): Fold `#64e28b`; Echolalia `#f0a04a` on `#080706`; Stovetop `#ff7a2e` on `#151517`.

### 5.4 Motion primitives (`motion.js`; beat = 0.405405 s = 24.32 frames)

| Primitive | Trigger | Exact behaviour | Duration |
|---|---|---|---|
| PUNCH | kick | `punch(t, "kick", { amp })`: scale 1 + amp x Σ exp(-Δt / 0.07 s), at most 1 + 2 amp. The anchor is the framed subject. amp: plate 0.03, macro 0.045, type 0.012. In the tom grooves (bars 1 to 8 and 23 to 30) amp x 0.6. Off from 24.0 to 36.080 and after 84.725. | decay τ 0.17 beat |
| STAMP | snare or a named hit | `stamp(t, h)`: scale 1.18 → 1.00 over 5 frames (power3.out), 1.02 on frame 5, 1.00 after; opacity 0 → 1 over 2 frames | 0.25 beat |
| SLAM | a crash or bar-line entrance | a translate from ±160 px to 0 over 6 frames (power4.out), then PUNCH (plate) | 0.25 beat |
| WHIP | a snare pickup or tom run | `whip(t, h, { dir })`: 5 frames centred on the hit frame. The outgoing layer moves 180 px (power2.in), the incoming arrives from -dir (power2.out), with a 6-copy stack blur (50/30/18/10/6/3 %). The cut shows on the hit frame. No CSS blur on canvases. | 0.2 beat |
| FLASH | crash | `flash(t, hits, { peak })`: an additive full-frame layer in the heard engine's fill hue, drawn under all type, buttons and the VST tile. Crash peak **0.30** and τ 0.06 s. First hit (0.407): white, frames [0.45, 0.20, 0.06]. The stop (84.725): white, [0.45, 0.15]. Bypass slam: white 0.12. **KIT CHANGE:** set `MOTION.flash.peak = 0.30` and `MOTION.flash.white = 0.45`. | τ 0.15 beat |
| SHAKE | crash (and the first hit) | `shake(t, hits, { amp })`: 10 px (14 px on the first hit), τ 0.12 s, hash noise; type at most 2 px | τ 0.3 beat |
| SWEEP | fills and pickups | `sweep(t, hits)`: one step per hit, 3 frames each (power2.out) | 0.12 beat per step |
| CLICK-STOP | a named hit (a knob step) | `steps(t, hits, values, { frames: 5 })`: a 90 ms knob step (sine.inOut on knob position); the audio uses the same step | 0.22 beat |
| GESTURE | a bar beat (a continuous knob move) | from beat 1 to beat 3 of a bar, sine.inOut on knob position, read from `demos.json`. RING in 0.1 s before and out 0.3 s after | 2 beats |
| MACRO PUSH-IN | a cut to a macro | `push(t, h, h + 1 beat, 1.00, 1.03)`, sine.inOut; 1.05 in the S22 wind-up | 1 beat |
| SMEAR | an engine change | `smear.js` SmearGroup. A 0.25 s burst centred on the hit in full-band sections; 0.5 s centred on the bar line in the guitar-alone tour. Three copies at ±48 px x sin(πu) | 0.6 or 1.2 beat |
| INHALE | the two hits before the stop | a frame scale of 0.97, then 0.95 (4 frames each, power2.out), released at the stop with a 1.01 overshoot | |
| HOLD | stops and designed holds | no hit-driven motion, grain frozen; only data moves | |
| COLOUR = SOUND | `demos.json` | the plate body filter (section 2). **KIT CHANGE:** add `plate.setGrade({ sat, bright })` as a CSS filter on the plate body, which contains no canvas | per frame |

**Photosensitivity (PSE) limiter, `flash.js`, Unit A:**
- At setup, scan every scheduled flash: at most 3 flashes above 10 % luminance change over more than 25 % of the frame in any rolling 1 s. A 4th flash in the window is automatically turned into a 3 px edge glow in the hue.
- Fills never flash; they cut.
- The looks swap stays at 18.7 % of the frame.

### 5.5 How scenes read time and hits

- `boot.js` loads `beats` with the manifest `offset`: 0 for the main film, 123.648 for the TikTok. Scenes use `ctx.beats` and `ctx.motion`, never raw JSON.
- Name hits by their master time from this file: `ctx.beats.hitNear("kick", ctx.beats.comp(71.757))`. Use `beats.bar(n)` and `beats.beat(n, k)` for bar lines.
- Everything is a pure function of `t`: no `Math.random`, no wall clock, no state from the previous frame.
- Canvases (the scope, the hero, clips) never sit inside a changing transform; they scale inside their draw call.
- **Knob values, engine, core, bypass state, chip text, heard or not heard, and the LFO phase (for chorustype and drift)** come from `film/lib/demos.js` (Unit A, new).
  - It loads `/film/v5/demos.json` and `/data/scope/measured.json`.
  - API: `stateAt(t)` returns `{ engine, hq, core, knobs, trim, bypass, heard, chip, demoId }`; `cyclesAt(t)` returns the integrated LFO phase; `gestureAt(t)` returns `{ param, u } | null`; `levelMatched(id)`.
  - It adapts to `plate.setState` and to `chorustype`.
- **Every scene exports `events: [{ t, kind, hit }]`** in master time, with kind one of `cut`, `stamp`, `slam`, `whip`, `sweep`, `flash`, `click`, `gesture`, `text`. The QC scripts read these lists.

---

## 6. Build units

Files are disjoint. Scene files live in `film/v5/scenes/` (main) and `film/v5/tiktok/` (TikTok).
- Main manifest: `film/v5/scenes/manifest.json`, duration **91.216**.
- TikTok manifest: `film/v5/tiktok/manifest.json`, duration 15.000, offset 123.648.

**Kit (owned by Unit A, which already started it):**
- `beats.js`, `motion.js` (with the flash KIT CHANGE) and `portrait.js`;
- new: `demos.js`, `flash.js` (PSE), `slices.js` (knob-row strips using `plate.height`, never `725 x SCALE`), `montage.js` (hard-cut macros on a hit list: S02, S19, S22 and the TikTok), `chip.js`;
- `plate.setGrade`.

Unit A delivers `demos.js`, `slices.js` and `montage.js` first (hour 2), because Unit B needs them.

**Unit A:**
- main shots **S01 to S12** (0.000 to 36.080), files `film/v5/scenes/a01-still-mixturn.js` to `a12-black.js`;
- **the TikTok**, all shots, `film/v5/tiktok/t01-*.js` onward, reusing Unit B's `endcard.js` (TikTok variant).

**Unit B:**
- main shots **S13 to S24** (36.080 to 91.216), files `film/v5/scenes/b13-cores.js` to `b24-endcard.js`;
- kit modules `endcard.js` (main and TikTok variants, format row, Buy button) and `abtoggle.js`, delivered by hour 3;
- the picture QC script `film/v5/qc.mjs`.

**Seams:**
- 36.080 is a hard CUT on the drum re-entry. Unit B owns frame 2164. Unit A's S12 ends on frame 2163 with the 3 % pull-back.
- 84.725 is inside Unit B.
- The chip and the grain are persistent layers in the kit, not in any scene.

**Audio engineer:**
- `audio/film/v5_demos.py`: renders, the BP assembly, crossfades, trims, null, mono and loudness logs, scope, meter and `measured.json`, both WAVs;
- the audio QC (QC-A);
- delivers a first pass with estimated trims by hour 3 so the picture gets real scope data.

**Lead:** merges, runs `film/v5/v5.sh check`, renders previews, then the finals with `WORKERS=2`, and commits.

---

## 7. THE TIKTOK SPEC (its own 1080 x 1920 composition; τ = master - 123.648)

**The stretch:** 123.648 to 138.648 (bar 77.1 to bar 86.2), uncut. Why this stretch:
- the first sample is the crash + kick of the riff-3 drop;
- riff 3's guitar sits 7.1 dB over the drums;
- bar 80 is a stop-time bar: one hit at 128.513, then 1.4 s of solo guitar;
- the full-band stop at 135.000 leaves 3.65 s of solo guitar for Buy;
- the end loops into the crash.

**Rules:**
- Every frame is full-bleed.
- A designed event lands at least once per beat until τ 11.352, except the designed 2-beat freeze at τ 4.865 to 5.676.
- It reads with the sound off: the tags say what changes.

### 7.1 Frame 0: THE TOTEM (a poster; the one colour = sound exception)

- **Top block, on black:**
  - eyebrow "CHOROBOROS" (mono 30 px, `#b88cff`, baseline 290);
  - "One riff." (Fraunces 600, 128 px, baseline 430);
  - "*Five engines.*" (Fraunces italic 400, 128 px, lavender, baseline 560).
- **Below:** five knob-row strips, edge to edge, 1080 x 220 each, from y 600 to 1700, in the order Green, Blue, **Red**, Purple, Black. Each is its plate at scale 0.77, clipped to the knob row, **all in full colour**. Red (heard from the first sample) is at +15 % exposure with a 3 px `#ff776d` rim.
  - Tags at each strip's top left (mono 30 px, engine hue): GREEN, BLUE, RED, PURPLE, BLACK, at baselines 636, 856, 1076, 1296 and 1516.
  - Below 1700: a black gradient and grain.
- The impact starts on frame 1, so frame 0 stays clean as a thumbnail.

### 7.2 Shot list on the hits (frame = floor(60 τ))

| τ (frame) | Master | Bar.beat | Hit | Picture | Copy | Audio (demos.json) |
|---|---|---|---|---|---|---|
| 0.000 (0) | 123.649 | 77.1 | crash + kick | The totem | as 7.1 | T01 Red, BBD |
| 0.017 to 0.167 (1 to 10) | | | | **SLOT-SNAP:** the Red strip expands from 220 px to the full 1920 px (power4.out). The other strips are pushed off-frame and desaturate as they go. SHAKE 14 px. A black scrim fades in behind the headline. | | |
| 0.183 (11) | | | | Full-bleed Red L-MACRO on RATE and DEPTH ("0.62 Hz", "30%") | Tag "RED · BBD" (mono 56 px, `#ff8a80`, baseline 1470). The headline shrinks to 86 px (baselines 330 and 420) | |
| 0.405 (24) | 124.053 | 77.2 | snare + hat | CUT to the HQ lever macro (2.0x) at BBD | pill "BBD · TAPE" at BBD (Inter 600, 34 px, y 1340 to 1420) | |
| 0.808 (48) | 124.456 | 77.3 | kick + hat | CUT to the scope (860 px, centred at (540, 1000), Red trace) over the plate at 20 %. PUNCH | | |
| 0.999 (59) | 124.647 | 77.3.5 | kick + hat | PUNCH on the scope | | |
| **1.217 (73)** | **124.865** | **77.4** | **snare + hat** | CUT back to the lever. **The lever FLIPS** (18 frames, smootherstep); the lit plate blends in; the pill slides to TAPE | Tag "RED · TAPE" | **hq 0 → 1 at 124.865** |
| 1.419 (85) | 125.067 | 77.4.5 | crash + kick | FLASH Red (0.30). WHIP out to the whole lit Red plate (scale 0.77, full width) | | |
| 1.622 (97) | 125.270 | 78.1 | (empty downbeat) | SMEAR (0.25 s) to a **full-bleed Blue** L-MACRO on OFFSET | Tag "BLUE · CUBIC" | T02 Blue, Offset 0° |
| 1.825 (109) | 125.473 | 78.1.5 | kick | PUNCH | | |
| 2.027 (121) | 125.675 | 78.2 | snare + hat | STAMP the caption; the RING starts; the readout rolls large (2.5x) | "*Offset.*" (Fraunces italic 110 px, `#79b8ff`, x 72, baseline 1300) | **Offset 0 → 120°, 125.675 to 126.080** |
| 2.430, 2.631 (145, 157) | 126.078, 126.279 | 78.3, 78.3.5 | kick + hat, twice | Two PUNCH steps back to the whole plate, with the scope inset (340 px, centred at (740, 760)) | | |
| 2.839, 3.041 (170, 182) | 126.487, 126.689 | 78.4, 78.4.5 | snare, snare | WHIP to the WIDTH readout ("100%"), then WHIP back | | |
| 3.244 (194) | 126.892 | 79.1 | crash + kick | SMEAR to a **full-bleed Purple** L-MACRO on the COLOR slider. FLASH Purple (0.30) | Tag "PURPLE · ORBIT" | T03 Purple, Color 10 % |
| 3.649 (218) | 127.297 | 79.2 | snare | STAMP the caption; RING; the thumb glides | "*Color.*" (110 px, `#c9b1ff`, baseline 1300) | **Color 10 → 45 %, 127.297 to 128.108** |
| 4.056, 4.237 (243, 254) | 127.704, 127.885 | 79.3, 79.3.5 | kick, kick + hat | PUNCH, PUNCH; the readout rolls large | | |
| 4.462 (267) | 128.110 | 79.4 | snare + hat | WHIP out to the whole Purple plate | | |
| **4.865 (291)** | **128.513** | **80.1** | **kick + snare (stop-time)** | **FREEZE.** CUT to the Green MIX macro: the main film's frame-0 composition, at s 0.12, "0%". All motion stops and the grain freezes. Only the scope inset moves (dry guitar). | Tag "GREEN · MIX 0%" (`#7ee0a0`) | T04 Green, Mix 0 %: the dry guitar alone |
| **5.676 (340)** | **129.324** | **80.3** | (silence, guitar only) | **THE MIX TURN IN THE SILENCE.** The knob turns 0 → 40 % over one beat. The colour floods with the knob. RING. The readout rolls "0%" → "40%" at 2.5x. The scope's wet trace blooms. | "*doesn’t sit still.*" (italic 110 px, lavender chorustype Green, baseline 420) STAMPs on 5.676. The tag becomes "GREEN · MIX 40%" | **Mix 0 → 40 %, 129.324 to 129.729** |
| 6.284 (377) | 129.932 | 80.4.5 | crash + kick | The band slams back: FLASH Green (0.30), SHAKE 10 px, WHIP out to the whole Green plate | | |
| 6.487 (389) | 130.134 | 81.1 | (empty downbeat) | SMEAR to the **full-bleed Black** plate at 1.2x | Tag "BLACK · ENSEMBLE" | T05 Black, Color 20 % |
| 6.690 (401) | 130.338 | 81.1.5 | kick | PUNCH | | |
| 6.892 (413) | 130.540 | 81.2 | snare + hat | CUT to the COLOR slider (1.3x); RING | "*Color.*" (110 px, `#9aa0a6`) | **Color 20 → 60 %, 130.540 to 130.945** |
| 7.295, 7.496 (437, 449) | 130.943, 131.144 | 81.3, 81.3.5 | kick + hat, twice | PUNCH, PUNCH | | |
| 7.703 (462) | 131.351 | 81.4 | snare | WHIP out | | |
| 7.906 (474) | 131.554 | 81.4.5 | crash + kick | FLASH (white 0.20) | | |
| 8.108 (486) | 131.756 | 82.1 | (empty downbeat) | **THE TOTEM RETURNS** (the five strips below the headline). Colour = sound now: Green lit, the others at 0.35 | "Green and Purple" / "are *free.*" (104 px, baselines 330 and 440) replaces the headline | T06 Green, Mix 40 % |
| 8.311 (498) | 131.959 | 82.1.5 | kick | PUNCH | | |
| 8.514 (510) | 132.162 | 82.2 | snare + hat | STAMP "FREE" tags on the Green and Purple strips | "FREE" (mono 28 px on hue pills) | |
| 8.916, 9.118 (534, 547) | 132.564, 132.766 | 82.3, 82.3.5 | kick + hat, twice | PUNCH | | |
| 9.325 (559) | 132.973 | 82.4 | snare + hat | STAMP "30-DAY TRIAL" tags on Blue, Red and Black, and the sub-line | "30-day free trial." / "No payment card." (Inter 44 px, baselines 1440 and 1494) | |
| 9.728 (583) | 133.376 | 83.1 | kick + snare | CUT: "$49.99" SLAMs in (Fraunces 600, 200 px, baseline 640) with "*USD.*" (italic 200 px, lavender, baseline 840), over the Green plate at 40 % | | |
| 9.933 (595) | 133.581 | 83.1.5 | crash + kick | FLASH Green (0.30) | | |
| 10.339 (620) | 133.987 | 83.2.5 | kick | STAMP | "One-time purchase." (Inter 600, 48 px, baseline 960) | |
| 10.541 (632) | 134.189 | 83.3 | snare + hat | The format row appears by a hard CUT, with the VST logo unmodified | format row, y 1392 to 1492 | |
| 10.744 (644) | 134.392 | 83.3.5 | crash + kick | FLASH (0.30, under the row) | | |
| 10.947, 11.149 (656, 668) | 134.594 (beat), 134.797 | 83.4, 83.4.5 | kick 134.797 | INHALE: 0.97, then 0.95 | | |
| **11.352 (681)** | **135.000** | **84.1** | **kick + snare: the stop** | **BUY.** The TikTok end card SLAMs in, releasing from 0.95 to 1.00 with a 1-frame 1.01 overshoot. White FLASH [0.40, 0.12] under the button. Then STILL. | End card (7.4) | The band stops. Green on the solo guitar |
| 11.352 to 15.000 (681 to 899) | 135.000 to 138.648 | 84 to 86.2 | (guitar alone) | HOLD. Only the scope inset, the plate readouts and the chorustype move. | | fade 138.243 → 138.630 |

### 7.3 The TikTok demo (demos.json T01 to T06, same BP method, Width 100 %)

| Demo | Span | Engine / core (hq) | Rate | Depth | Offset | Width | Color | Mix | Move |
|---|---|---|---|---|---|---|---|---|---|
| T01 | 123.648 to 125.270 | Red, BBD → Tape (0 → 1) | 0.62 | 30 | 90 | 100 | 30 | 40 | hq step at 124.865 (77.4, snare) |
| T02 | 125.270 to 126.891 | Blue, Cubic (0) | 1.23 | 12 | **0 → 120** | 100 | 45 | 40 | 125.675 to 126.080 (78.2 to 78.3) |
| T03 | 126.891 to 128.513 | Purple, Orbit (1) | 0.12 | 50 | 90 | 100 | **10 → 45** | 30 | 127.297 to 128.108 (79.2 to 79.4) |
| T04 | 128.513 to 130.134 | Green, Lagrange 3rd (0) | 0.62 | 22 | 90 | 100 | 35 | **0 → 40** | 129.324 to 129.729 (80.3 to 80.4), in the silence; Trim follows Mix |
| T05 | 130.134 to 131.756 | Black, Linear Ensemble (1) | 0.31 | 30 | 120 | 100 | **20 → 60** | 40 | 130.540 to 130.945 (81.2 to 81.3) |
| T06 | 131.756 to 138.648 | Green, Lagrange 3rd (0) | 0.62 | 22 | 90 | 100 | 35 | 40 | none |

Switch rules are as in the main film. Each demo gets at least 3 s of real pre-roll, so the chorus is warm on sample 1. The level-match and mono rules are the same (per bar; 2-bar demos are judged per bar and per demo).

### 7.4 TikTok end card (τ 11.352 to 15.000)

| Element | Text | Style | Box |
|---|---|---|---|
| Lockup | KAIZEN DSP | the typeset lockup, 48 px | x 72, baseline 290 |
| Name | *Choroboros.* | Fraunces italic 150 px, chorustype Green, live | baseline 440 |
| Plate | Green, lit, T06 values | scale 0.60 (840 x 508) | x 72 to 912, y 470 to 978 |
| Scope | live | 170 px | centre (855, 560), over the plate's top right |
| **Buy** | **Buy Choroboros →** | the same button as the main film (856 x 140, cream, Inter 600 56 px) | x 72 to 928, y 1000 to 1140 |
| Offer | $49.99 USD one-time purchase / Green and Purple free · 30-day free trial | Inter 500, 36 px | baselines 1196 and 1242 |
| URL | kaizendsp.com/choroboros | Inter 600, 44 px | baseline 1300 |
| Format row | as the main film | tiles 160 x 100 | y 1330 to 1430 |
| Platform | Available now for macOS. | Inter 500, 36 px, muted | baseline 1490 |
| Legal | the trademark line of 4.3 | 22 px, `data-bleed` | y 1552 to 1640 |

---

## 8. QC gates (all must pass before the final render)

**Picture: `film/v5/qc.mjs` (Unit B), run on both compositions.**

1. **Never boring.** Take the scene `events` lists and measure the gaps between consecutive events:
   - main film, high-energy spans (0.407 to 23.108 and 36.080 to 84.725, excluding the designed holds of bar 6 and bar 46): the maximum gap is ≤ 2 beats (0.811 s);
   - guitar-alone tour: ≤ 2 bars;
   - TikTok, τ 0 to 11.352: the maximum gap is ≤ 1 beat (0.405 s), except the freeze τ 4.865 to 5.676.
   Report the longest gap per section.
2. **Sync.** Every event's frame equals `floor(60 x h)` of its hit, within ±1 frame (target 0). Check the stills at every frame of the hook (frames 0 to 130), the stop (5075 to 5095) and the TikTok's first second, with `v5.sh frames`. A/V offset after muxing: a click-and-flash test within 5 ms, with the AAC priming and edit list verified.
3. **Readability.**
   - `portrait.unsafeText()` returns nothing on 24 stills (every shot).
   - Every text node is at or above its TYPE minimum.
   - Every copy block meets the reading budget (section 4).
   - Body text contrast is at least 4.5:1 against its local background, measured on the stills.
4. **Claims.**
   - The on-screen strings equal the copy deck exactly (extracted from the DOM on each shot's still).
   - The forbidden-list scan (section 4.2) finds nothing.
   - Every frame with "VST" also shows the VST tile, and the tile's pixels are hash-identical to the source logo at that size.
   - No person's name and no track title appear.
5. **Colour = sound.** The plate saturation on stills matches `demos.stateAt(t)`: no plate is lit while its engine is not heard (the frame-0 posters excepted).
6. **Determinism.** `v5.sh check` on 12 times per film, including frames 0, 24, 97, 802, 1386, 2164, 3721, 5083 and 5472, and TikTok frames 0, 73, 291, 340 and 681. Two browsers, three seek orders, identical hashes.
7. **PSE.** The flash scan: no more than 3 qualifying flashes in any 1 s. The looks swap stays at or under 25 % area.

**Audio: `audio/film/v5_demos.py` (the audio engineer). The report goes to `/home/user/build/v5/audio/report.json`.**

- **A1. The song is uncut.**
  - `master_v5.wav` is exactly 4 378 368 samples and `tiktok_v5.wav` exactly 720 000.
  - Cross-correlation against the master gives lag 0 (±0 samples) in every bar.
  - Outside the demos and in every bypass span, out equals the master bit for bit, except the final fade and the TikTok's 1 ms fade-in and final fade.
  - The TikTok equals master[123.648 : 138.648] under the same rule.
- **A2. Null.** Mix-0 renders equal their input to below -100 dBFS.
- **A3. Band.** `out - master` above 6.5 kHz is below -90 dBFS.
- **A4. Drums untouched.** The envelope correlation of `out - master` with the fitted drums is below 0.05.
- **A5. Level.** The per-bar ±0.5 LU and per-demo ±0.2 LU rule, with true peak no higher than the master's + 0.1 dB per bar.
- **A6. Mono.** The section 3 rule.
- **A7. Encoded check.** Decode the final MP4s and re-run A1 by correlation (≥ 0.999 per bar), with duration exact to the frame.

**Deliverables** (`v5.sh render`, H.264 High, CRF 16, 1080 x 1920, 60 fps, AAC 320k 48 kHz, faststart):
- `/home/user/build/v5/out/choroboros-portrait-v5.mp4`
- `/home/user/build/v5/out/choroboros-tiktok-v5.mp4`

---

## Amendment after the final review

- QC-A5 true peak: the per-bar rule "at most the master's true peak + 0.1 dB" is replaced by a
  -1 dBTP ceiling on the output, with the peak control acting only on the Choroboros change. The
  "LEVEL MATCHED" lines state loudness, and loudness passes everywhere (every full bar within
  0.5 LU, every demo within 0.2 LU, measured.json), so S18 keeps "LEVEL MATCHED · DRUMS UNTOUCHED".
- QC-A6 mono: a wide stereo chorus loses up to about 1 LU more than the dry guitar when summed to
  mono in some demos. Lowering Depth does not fix it without removing the effect, so the settings
  stay as heard.
- The 3D hero plates carry readouts that match the heard settings (film/v5/hero-readouts.js).

## Appendix: bar grid (bar n beat 1; frame = floor(60 t))

| Bar | Beat 1 | Frame | Bar | Beat 1 | Frame | Bar | Beat 1 | Frame |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.405 | 24 | 20 | 31.216 | 1872 | 39 | 62.026 | 3721 |
| 2 | 2.026 | 121 | 21 | 32.837 | 1970 | 40 | 63.648 | 3818 |
| 3 | 3.648 | 218 | 22 | 34.459 | 2067 | 41 | 65.270 | 3916 |
| 4 | 5.270 | 316 | 23 | 36.080 | 2164 | 42 | 66.891 | 4013 |
| 5 | 6.891 | 413 | 24 | 37.702 | 2262 | 43 | 68.513 | 4110 |
| 6 | 8.513 | 510 | 25 | 39.324 | 2359 | 44 | 70.134 | 4208 |
| 7 | 10.135 | 608 | 26 | 40.945 | 2456 | 45 | 71.756 | 4305 |
| 8 | 11.756 | 705 | 27 | 42.567 | 2554 | 46 | 73.378 | 4402 |
| 9 | 13.378 | 802 | 28 | 44.189 | 2651 | 47 | 74.999 | 4499 |
| 10 | 14.999 | 899 | 29 | 45.810 | 2748 | 48 | 76.621 | 4597 |
| 11 | 16.621 | 997 | 30 | 47.432 | 2845 | 49 | 78.243 | 4694 |
| 12 | 18.243 | 1094 | 31 | 49.053 | 2943 | 50 | 79.864 | 4791 |
| 13 | 19.864 | 1191 | 32 | 50.675 | 3040 | 51 | 81.486 | 4889 |
| 14 | 21.486 | 1289 | 33 | 52.297 | 3137 | 52 | 83.107 | 4986 |
| 15 | 23.108 | 1386 | 34 | 53.918 | 3235 | 53 | 84.729 | 5083 |
| 16 | 24.729 | 1483 | 35 | 55.540 | 3332 | 54 | 86.351 | 5181 |
| 17 | 26.351 | 1581 | 36 | 57.162 | 3429 | 55 | 87.972 | 5278 |
| 18 | 27.972 | 1678 | 37 | 58.783 | 3526 | 56 | 89.594 | 5375 |
| 19 | 29.594 | 1775 | 38 | 60.405 | 3624 | 57 | 91.216 | end |

TikTok bars (τ = master - 123.648):

| Bar | Master | τ | Frame |
|---|---|---|---|
| 77 | 123.648 | 0.000 | 0 |
| 78 | 125.270 | 1.622 | 97 |
| 79 | 126.891 | 3.243 | 194 |
| 80 | 128.513 | 4.865 | 291 |
| 81 | 130.134 | 6.486 | 389 |
| 82 | 131.756 | 8.108 | 486 |
| 83 | 133.378 | 9.730 | 583 |
| 84 | 134.999 | 11.351 | 681 |
| 85 | 136.621 | 12.973 | 778 |
| 86 | 138.243 | 14.595 | 875 |
