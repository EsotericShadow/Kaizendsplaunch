# Echolalia -- Visual Reconstruction Guide

## What It Is

Echolalia is a delay and reverb plugin by Kaizen DSP with six engines (Room, Plate, Tape Echo, Ping-Pong, Reverse, Diffuse). Its signature feature is "Evolution" -- echoes that transform as they return. The GUI is a web-based interface rendered in a native WebView, featuring 3D-rendered hardware knobs on a console faceplate, with a phosphor-amber glow aesthetic.

---

## Window Dimensions

- Scene (render canvas): **1760 x 894 px** (aspect ratio ~1.97:1)
- Default window: **880 x 447 px** (half-resolution, scales up on Retina)
- Rendered via WKWebView (Safari 15), Canvas-based 3D knob rendering

---

## Color Palette

### Interface Colors

| Element | Hex | Notes |
|---------|-----|-------|
| Background (native) | `#090b09` | Near-black with slight green |
| Root background | `#080b09` | Web root |
| Detail panel | `#10160f` | Slightly lighter green-black |
| Insert rack | `#0b100a` | Dark green-black |
| Time settings bg | `#0a100a` | Dark panel |

### Text Colors

| Element | Hex | Usage |
|---------|-----|-------|
| Primary text | `#bfbda5` | Warm light khaki |
| Muted/header text | `#878f7a` | Olive-gray |
| Labels | `#8e987f` | Sage gray |
| Panel headings | `#c4b994` | Warm gold-khaki |
| Button text | `#bfc5af` | Light sage |
| Output values | `#d1ba80` / `#bbab7d` | Gold readouts |
| Time settings text | `#dfcda4` | Warm cream-gold |

### Accent Colors

| Element | Hex | Usage |
|---------|-----|-------|
| Focus ring | `#d4b071` | Gold, primary accent |
| Input accent | `#bc995c` | Warm amber |
| Hover border | `#a8956b` | Muted gold |
| Evolution accent | `#bfa16b` / `#d0bd91` / `#e4cf9c` | Gold gradient stages |

### Border/Divider Colors

| Element | Hex |
|---------|-----|
| Button borders | `#36412f` |
| Panel border | `#444a34` |
| Audio controls border | `#303a2a` |
| Dividers | `#343a2b` |
| Engine selector border | `#474936` |
| Engine active bg | `#272a1d` |
| Engine active border | `#796c48` |
| Time settings border | `#655b41` |

### Button Colors

| State | Background | Text |
|-------|-----------|------|
| Default | `#131a14` | `#bfc5af` |

### Website Theme (for marketing reference)

| Token | Hex | Notes |
|-------|-----|-------|
| `--ink` | `#080706` | Page background |
| `--cream` | `#f4ecdc` | Primary text |
| `--cream-soft` | `#d8cebb` | Softer cream |
| `--muted` | `#a59d90` | Muted text |
| `--dim` | `#71695e` | Dim text |
| `--amber` | `#f0a04a` | Primary amber accent |
| `--amber-soft` | `#d8a066` | Softer amber |
| `--hot` | `#ffe6bf` | Hot/bright amber |

---

## Typography

### Plugin Interface Fonts

| Font | File | Usage |
|------|------|-------|
| **JetBrains Mono NL Thin** | 206 KB TTF | Header area, thin monospace |
| **JetBrains Mono ExtraBold** | 279 KB TTF | Header area, bold monospace |
| **IBM Plex Sans Condensed Regular** | 200 KB TTF | Console labels |
| **IBM Plex Sans Condensed Medium** | 202 KB TTF | Console labels (emphasized) |
| Georgia | System | Panel headings, 22 px |
| Arial, sans-serif | System | Root fallback |

### Website Fonts

| Font | Usage |
|------|-------|
| **Fraunces** (variable, serif) | Display/headline text |
| **Inter** (variable, sans-serif) | Body text |
| System monospace | Code/technical values |

---

## Component Layout

### Console Faceplate

The main interface is a console-style faceplate (`console-plate-repaired.png`) with hardware controls mounted on it. The detail panel overlays the right portion of the console.

- Detail panel inset: `top 13%, right 4%, bottom 4%` from edges

### Rotary Knobs (3D Canvas-Rendered)

Each knob is rendered from a spritesheet atlas:
- **96 frames** per knob, arranged in an **8 x 12 grid**
- **256 px per frame**
- Rotation step: **3.75 degrees** per frame
- Interaction: vertical drag (`cursor: ns-resize`)

| Knob Atlas | File | Size |
|------------|------|------|
| Main (delay time/amount) | `atlas-hardware-main.png` | 5.5 MB |
| Body | `atlas-hardware-body.png` | 4.6 MB |
| Decay | `atlas-hardware-decay.png` | 4.6 MB |
| Frequency | `atlas-hardware-freq.png` | 4.6 MB |
| Trim | `atlas-hardware-trim.png` | 4.0 MB |

### Engine Selector

- Rotary selector with handle texture (`engine-selector-handle.png`)
- Six positions: Room, Plate, Tape Echo, Ping-Pong, Reverse, Diffuse
- z-index 2 (overlaps other elements)

### Evolution Handle

- Circular drag handle
- Can drag horizontally or vertically depending on context
- Three stages: Clear, Transform, Dissolve

### Insert Rack

- Grid of bypass/amount/select slots
- Background: `#0b100a`
- Contains: Tone, Saturation, Stereo Width controls

### Audio Controls

- Flex row with channel modes (Mono, Stereo)
- Border: `#303a2a`

---

## Visual Elements to Recreate

### The Console

The primary visual is a hardware console faceplate with machined metal appearance. Key reference files:
- `console-plate-repaired.png` -- the faceplate overlay
- `console-reference.png` -- full console in context
- `reference.png` -- complete assembly reference
- `housing-refined.png` -- the enclosure/housing

### 3D Knobs

The knobs are 3D-rendered metallic controls with realistic lighting. They were generated in Atlas (Kaizen's material rendering studio) and exported as spritesheet atlases. Each atlas contains 96 rotation frames.

For video reconstruction:
- Use the atlas PNGs as frame references or animate from the grid
- PBR source maps available: `atlas-albedo.png`, `atlas-roughness.png`, `atlas-height.png`

### Phosphor Display

The signature visual is a phosphor-amber glow effect:
- See `phosphor-light-study.mp4` (looping hero video) and its poster frame
- The plugin's display shows delay traces with a warm amber phosphor look
- Echoes appear as glowing amber traces that decay and transform

### Console Labels

- `console-label-clean.png` -- high-resolution label overlay
- Typography is etched/printed onto the faceplate

---

## Motion / Video Assets

Already-produced video materials for reference:

| File | Description | Location |
|------|-------------|----------|
| `phosphor-light-study.mp4` | Looping phosphor glow (hero video, silent) | KaizenDelivery site assets |
| `time-sound-preview.mp4` | 44.1s demo, guitar through Tape Echo + Evolution, with audio | KaizenDelivery site assets |
| `Echolalia-Phosphor-Study*.mp4` | 7 phosphor study iterations (5.7-17 MB each) | Users-main/Downloads/ |

---

## Assets Included

```
assets/
  console/                   -- Console plate, housing, reference composites
  knob-atlases/              -- 3D knob spritesheets (96 frames, 8x12 grid, 256px/frame)
  textures/                  -- PBR maps (albedo, roughness, height), switch texture
  labels/                    -- Console label overlay
  branding/                  -- Kaizen wordmark (white)
  screenshots/               -- Desktop/mobile website previews, homepage screenshots
  engine-selector/           -- Engine selector handle texture
```

---

## Brand Identity

- Manufacturer: **Kaizen DSP** (brand of Kaizen Strategic AI Inc.)
- Product: **Echolalia**
- Tagline: "A little something to get lost in."
- Description: "Six delay and reverb engines, with echoes that change as they return. Shape the sound. Watch it glow."
- Six engines: Room, Plate, Tape Echo, Ping-Pong, Reverse, Diffuse
- Evolution stages: Clear, Transform, Dissolve
- Website: https://kaizendsp.com/echolalia
- Overall aesthetic: Dark, cinematic console hardware. Green-black base with phosphor amber accents. Machined metal faceplate with 3D-rendered knobs. The visual language is "cinematic light" -- warm amber/gold on dark surfaces, evoking vintage oscilloscope phosphor displays and high-end audio hardware.

### Design Philosophy (from internal brief)

"Dark stage, cinematic light, phosphor amber in place of Choroboros purple." The visual approach uses scroll-driven reveals and warm amber lighting against near-black backgrounds. The interface glows rather than shines.
