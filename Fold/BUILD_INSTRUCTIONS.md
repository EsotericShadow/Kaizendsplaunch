# Fold -- Visual Reconstruction Guide

## What It Is

Fold is a spectral stereo shaper plugin by Kaizen DSP. It folds the stereo field across frequency -- pulling lows inward and opening highs outward, or reversing the balance with one continuous control. The GUI features a large central Fold knob, several smaller secondary knobs, and a spectral frequency display. The interface is rendered with a physically-based lighting system over machined metal textures.

---

## Window Dimensions

- Default window: **900 x 620 px**
- Minimum window: **720 x 520 px**
- Panel background canvas: **1800 x 1080 px** (2x supersample for Retina)
- Resizable within constraints

---

## Color Palette

### Platform Design Tokens (shared Kaizen DSP system)

| Token | Hex | Usage |
|-------|-----|-------|
| `shellBg` | `#111316` | Outermost background |
| `workspaceBg` | `#181B20` | Workspace area |
| `interactiveBg` | `#242931` | Interactive element backgrounds |
| `textPrimary` | `#F0F0F2` | Primary text |
| `textSecondary` | `#888890` | Secondary/muted text |
| `focusPurple` | `#9B76C7` | Focus indicators |
| `liveSignal` | `#5BC7C5` | Live signal indicators (teal) |
| `movement` | `#5FA8FF` | Movement category (blue) |
| `voice` | `#66C989` | Voice category (green) |
| `character` | `#F17770` | Character category (red) |
| `tone` | `#D5B25F` | Tone category (gold) |
| `output` | `#B8BDC5` | Output level (silver) |
| `blocker` | `#DC625F` | Blocker/error (red) |

### Fold-Specific Accent

- Product accent: `#E87868` (warm coral/salmon)

### Prototype Colors (visual reference for the earlier concept)

| Element | Hex | Notes |
|---------|-----|-------|
| Background | `#121417` | Dark charcoal |
| Panel | `#27292D` | Raised panel |
| Sub-panel | `#2C2E32` | Nested panels |
| Graph surface | `#040609` | Near-black for spectrum display |
| Text | `#E5DFD0` | Warm off-white |
| Muted text | `#A5A39C` | Gray-warm |
| Accent (gold) | `#E1BB73` | Primary accent, warm amber |
| Accent secondary (teal) | `#96D6E2` | Complementary accent |
| Accent tertiary | `#C5BCA6` | Neutral warm |
| Accent soft (dark teal) | `#4C726B` | Background accent |

### Waterfall Heatmap Gradient (spectrum display)

From coldest to hottest:
1. `RGB(1, 2, 4)` -- near black
2. `RGB(12, 24, 30)` -- dark teal
3. `RGB(50, 78, 84)` -- mid teal
4. `RGB(111, 136, 122)` -- sage green
5. `RGB(180, 151, 101)` -- warm amber
6. `RGB(147, 88, 48)` -- burnt copper

---

## Typography

| Font | Size | Weight | Usage |
|------|------|--------|-------|
| System default | 42 px | Bold | Titles |
| System default | 21 px | Bold | Hero/section headings |
| System default | 18 px | Bold | Value readouts |
| System default | 13 px | Plain | Body text |
| System default | 12 px | Bold | Labels |
| System default | 11 px | Plain | Captions |

Website fonts (for marketing reference): **Fraunces** (variable serif) and **Inter** (variable sans-serif).

---

## Component Layout

### Main Fold Knob

- Size: 256 x 256 px (filmstrip frame size)
- Filmstrip: 65 frames
- Central position, dominant visual element
- Bipolar control (center = neutral, CW = fold out, CCW = fold in)

### Secondary Knobs

All secondary knobs share the same filmstrip format:
- Size: 128 x 128 px (newer per-control filmstrips) or 256 x 256 px (generic)
- Filmstrip: 145 frames

| Knob | Parameter | Description |
|------|-----------|-------------|
| Body | Body resonance amount | Adds resonant body character |
| Freq | Body frequency | Center frequency of body resonance |
| Decay | Damping/decay | Controls decay envelope |
| Trim | Output trim | Output level adjustment |
| Amount | Flavour amount | Selected flavour intensity |

### Spectrum Display

- Left panel in two-panel layout
- Waterfall/spectrogram visualization
- Header height: 40 px
- Uses the teal-to-amber heatmap gradient listed above

### Layout Metrics

| Metric | Value |
|--------|-------|
| Padding | 28 px |
| Title height | 78 px |
| Control panel width | 360 px |
| Knob diameter (prototype) | 312 px |
| Panel corner radius | 18 px |
| Inner corner radius | 12 px |
| Button height | 36 px |

---

## Surface Treatment and Lighting

Fold uses a physically-based rendering approach for its panel:

### Layer Stack (composited bottom to top at 1800 x 1080)

1. **Olive machined base** -- warm olive/green-gray metallic base
2. **Stepped chassis and recesses** -- depth/shadow layer for panel geography
3. **Spectrum well lip** -- raised edge around the spectrum display area
4. **Center crease spill** -- light spill effect at the central divider
5. **Recessed fasteners** -- subtle screw/bolt details
6. **Edge wear** -- worn metal at edges for realism
7. **Brushed metal grain and broad reflection** -- directional grain texture

### PBR Texture Maps

- `fold_surface_albedo.png` -- base color
- `fold_surface_height.png` -- displacement/depth
- `fold_surface_roughness.png` -- surface roughness
- `fold_machined_roughness.png` -- machining pattern
- `fold_machined_roughness_fine.png` -- fine machining detail

### Directional Lighting

Each knob has multiple filmstrip layers:
- `*_base` -- diffuse appearance
- `*_light` -- center light response
- `*_light_left` -- left-angled light response
- `*_light_right` -- right-angled light response

These are composited at runtime for realistic directional lighting on the knobs.

---

## Visual Elements to Recreate

### The Panel

The background is a photorealistic machined metal panel with olive/green-gray coloring, brushed grain, and subtle wear. It is assembled from 7 compositing layers (see Layer Stack above). The designer should use the pre-composited `fold_panel_background.png` as the primary reference, with the individual layers available if they want to animate or adjust the lighting.

### The Knobs

3D-rendered metallic knobs with directional lighting. The main Fold knob is larger and has a distinct profile. Secondary knobs are smaller and uniform. Each has base + light layers for compositing.

### The Spectrum Display

A real-time waterfall/spectrogram using the teal-to-amber gradient. For video, this should be animated with audio-reactive motion showing frequency content flowing downward.

---

## Assets Included

```
assets/
  panel/                     -- Composited panel background + individual layers
  textures/                  -- PBR maps (albedo, height, roughness, machining)
  knob-filmstrips/           -- Main and secondary knob filmstrips with lighting layers
  light-response/            -- Panel light response maps (center, left, right)
  screenshots/               -- Compact and enlarged UI screenshots
  3d-geometry/               -- STL bezel files for 3D reference
```

---

## Brand Identity

- Manufacturer: **Kaizen DSP** (brand of Kaizen Strategic AI Inc.)
- Product: **Fold**
- Tagline: "Fold the stereo field."
- Description: "Pull the lows inward and open the highs outward -- or reverse the balance with one continuous control."
- Bundle ID: `com.kaizendsp.fold`
- Plugin code: `Fld1`
- Category: Fx Spectral
- Price: Free (macOS only at launch, October 1, 2026)
- Website: https://kaizendsp.com/fold
- Overall aesthetic: Machined metal hardware unit. Warm olive/green-gray tones with brushed grain textures. Physically-based lighting with directional response. Professional, tactile, high-end audio hardware feel.
