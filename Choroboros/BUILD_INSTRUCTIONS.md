# Choroboros -- Visual Reconstruction Guide

## What It Is

Choroboros is a multi-engine stereo chorus plugin by Kaizen DSP. It has five selectable "engines" (Green, Blue, Red, Purple, Black), each with a unique color theme that re-skins the entire interface. The GUI features four large rotary knobs, a horizontal color slider, a smaller mix knob, and an animated HQ toggle switch -- all rendered over a richly textured backpanel background.

---

## Window Dimensions

- Design-space canvas: **700 x 363 px**
- UI scale factor: **0.91** (applied to all coordinates)
- Rendered window size: approximately **637 x 330 px**

All positions below are in the 700 x 363 design space. Multiply every value by 0.91 for final pixel coordinates.

---

## Color Palette

### Engine Accent Colors

| Engine | Accent Hex | Description |
|--------|-----------|-------------|
| Green | `#9dbd78` | Sage/olive green |
| Blue | `#7fb8ff` | Light sky blue |
| Red | `#ff8d8b` | Salmon/coral red |
| Purple | `#b88dd8` | Lavender purple |
| Black | `#d4d4d4` | Light gray |

### UI Chrome Colors

| Element | Hex | Notes |
|---------|-----|-------|
| Background fill | `#202020` | Base behind the backpanel |
| Panel base | `#121417` | Blended 12% toward accent |
| Panel outline | Accent at 82% alpha | Subtle glow border |
| Button background | `#4a4a4a` | Top utility buttons |
| Button ON background | `#5a5a5a` | Active state |
| Button text | `#d3d3d3` | Light gray |
| Popup background | `#1c1c1c` | Engine selector dropdown |
| Popup text | `#ffffff` | White |
| Popup highlight | `#3a3a3a` | Selected item |

### Toggle Switch Colors

| State | Gradient | Notes |
|-------|----------|-------|
| ON outer | `#4a6b5a` to `#2a3b32` | Green-tinted |
| OFF outer | `#606060` to `#404040` | Neutral gray |
| ON inner | `#2a4a3a` at 90% alpha | |
| OFF inner | `#1a1a1a` at 80% alpha | |
| ON indicator | `#9dbd78` to `#6b8d5a` | Green accent |
| OFF indicator | `#808080` to `#505050` | Gray |

### About Dialog Colors

| Element | Hex |
|---------|-----|
| Accent | `#9dbd78` |
| Body text | `#e8ecf1` |
| Muted text | `#9aa5b3` |

---

## Typography

| Font | File | Usage | Size (design px) |
|------|------|-------|-------------------|
| **Technology** | `Technology.ttf` (97 KB) | Knob value readouts | 15 |
| **Retroica** | `Retroica.ttf` (30 KB) | UI labels, buttons | 12.25 (labels), 10 (buttons) |
| **choroboros** | `choroboros.ttf` (164 KB) | Logo / branding font | 33 (about title) |
| **JetBrains Mono ExtraBold** | titles/ folder | Titles | Varies |
| **JetBrains Mono NL Thin** | labels/ folder | Labels | Varies |
| **JetBrains Mono NL ExtraLight** | tooltips/ folder | Tooltips | Varies |

### Font Sizes (design-space, multiply by 0.91 for rendered)

- Knob value labels: 15 px
- Color slider value: 15 px
- Mix value: 11 px
- UI labels (RATE, DEPTH, etc.): 12.25 px
- Top buttons: 10 px
- Engine selector: 10 px
- About dialog title: 33 px
- About dialog body: 14 px

---

## Component Layout

All in 700 x 363 design space (multiply by 0.91 for pixels).

### Four Main Rotary Knobs (128 x 128 px each, top Y = 78)

| Knob | Center X | Parameter |
|------|----------|-----------|
| Rate | 102 | LFO rate |
| Depth | 251 | Chorus depth |
| Offset | 466 | Phase offset |
| Width | 607 | Stereo width |

Knob spritesheets: 156 frames each, full 360-degree sweep.

### Color Slider (horizontal linear)

- Track: X 235 to X 485, Y 268
- Thumb height: 18 px
- Each engine has its own slider thumb PNG

### Mix Knob (58 x 58 px)

- Center X: 612, Top Y: 251
- Separate spritesheet, 156 frames

### HQ Toggle Switch (45 x 45 px)

- Center: X 350, Y 152
- Spritesheet: 18 frames, 5 columns, 512 px per frame
- Animation duration: 185 ms

### Value Labels (95 x 33 px, top Y = 201)

- Positioned under each knob with slight X offsets
- Flip animation: 140 ms duration, 0.30 px travel
- Glow effect: 4% alpha, 0.65 px spread

### Engine Selector

- Position: X 20, Y 335, W 80, H 14
- Dropdown with 5 engine options

### Top Buttons (45 x 10 px each)

- About, Help, Feedback -- aligned right, gap 5, margin 10 from right edge, Y = 5

---

## Visual Elements to Recreate

### Backpanel Background

Each engine has TWO background images (light-off and light-on for the HQ switch glow). These are full-size rendered textures that fill the entire window. See `assets/backpanels/`.

### Knob Rendering

Knobs use filmstrip/spritesheet animation. Each frame is one rotation position. The motion designer should:
1. Use the spritesheet PNGs as texture references
2. Note that some engines have per-parameter knobs (Green, Red) while others share a single knob style (Blue, Purple, Black)

### Switch Animation

The factory switches have 25-frame animated sequences for on/off transitions, available as both individual frames and spritesheets. Five color variants (green, red, blue, purple, black).

---

## Animation Parameters

| Animation | Duration | Notes |
|-----------|----------|-------|
| Value label flip | 140 ms | Vertical travel 0.30 px, shear 32%, min scale 35% |
| HQ switch toggle | 185 ms | 18 frames |
| Knob visual response | 100-150 ms | Rate/Width/Mix: 100 ms, Depth: 150 ms |
| Glow alpha | 4% | Spread 0.65 px |
| Top reflection | 2% alpha | Offset Y -0.80 px, shear 6% |
| Bottom reflection | 3% alpha | Offset Y 1.10 px, shear -8% |

---

## Assets Included

```
assets/
  backpanels/          -- Per-engine background images (light on/off variants)
  knob-spritesheets/   -- Rotary knob filmstrips (156 frames each)
  slider-thumbs/       -- Per-engine horizontal slider thumb PNGs
  switch-panels/       -- Static switch on/off images (5 colors)
  switch-spritesheets/ -- Animated switch spritesheets (25 frames, 5 colors)
  fonts/               -- Technology.ttf, Retroica.ttf, choroboros.ttf + JetBrains family
  icons/               -- lock.svg, unlock.svg, kaizen_logo.png
  screenshots/         -- Complete interface screenshots and theme overviews
```

---

## Brand Identity

- Manufacturer: **Kaizen DSP** (brand of Kaizen Strategic AI Inc.)
- Product: **Choroboros**
- Tagline: Multi-engine stereo chorus
- Logo font: `choroboros.ttf` (custom)
- Overall aesthetic: Dark, moody, hardware-inspired with per-engine color theming. Textured metallic backpanels with subtle lighting effects. Clean, minimal typography with glowing value readouts.
