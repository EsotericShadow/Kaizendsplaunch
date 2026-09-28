// Choroboros GUI plate rebuilt from the plugin's own bitmaps (visual-assets 3.4), for the five
// engines and the white Create canvas.
//
//   const p = createPlate("green", { parent, scale: 0.9, x: 96, y: 350 });
//   p.requireRender(cues, "R02", 16, 20);          // in build(): prepare the frames it will show
//   p.setState(cues.plateStateAt("R02", t));      // in render(t)
//   p.place({ x, y, scale, dx });                 // camera / drift, any time
//
// Values are display units (rate Hz, offset degrees, the rest percent) and map to filmstrip
// frames, thumb x and readout text exactly as the plugin does. Filmstrip frames are per-frame
// images (film/tools/prep_gui.py) shown by visibility; the plate is plain DOM, never a canvas, so
// it may be scaled by a CSS transform deterministically.

import { LAYOUT, PLATE_W, PLATE_H, PLUGIN_PX, READOUT_COLOR, READOUT_FX, artFor, controlRect } from "./layout.js";
import { pFromValue, knobFrameMain, knobFrameMix, knobFrameWhiteMix, thumbX, formatReadout, SWITCH_OFF, SWITCH_ON } from "./cues.js";
import { el, setStyle, px, clamp, rgba, TAU } from "./util.js";

const KNOBS = ["rate", "depth", "offset", "width"];
const READOUTS = ["rate", "depth", "offset", "width", "color", "mix"];
const SX = PLUGIN_PX; // plate px per plugin px, horizontal
const SY = 725 / 331; // vertical

// Readout text ------------------------------------------------------------------------------

let measureCtx = null;
function measure(ch, font) {
  if (!measureCtx) measureCtx = document.createElement("canvas").getContext("2d");
  measureCtx.font = font;
  return measureCtx.measureText(ch).width;
}

/**
 * Readout faces. "technology": the seven-segment Technology.ttf the brief specifies; letter and
 * space slots fitted to the real plugin captures (public/engines/<e>-on.png). "jetbrains": what
 * the September release-candidate editor draws (ProductTypography::valueTextFont maps the
 * "technology" id to JetBrains Mono SemiBold), with that code's slot factors.
 */
export const READOUT_FONTS = {
  technology: { family: "Technology", weight: 400, letter: 1.0, space: 0.75 },
  jetbrains: { family: '"JetBrains Mono"', weight: 600, letter: 1.3, space: 0.9 },
};

const isDigit = (c) => c >= "0" && c <= "9";

// Every readout, so the stage can lay them out again once the fonts have loaded (slot widths come
// from font metrics, and a plate may be given its first state in build(), before the load).
const allReadouts = new Set();
export function relayoutReadouts() {
  for (const r of allReadouts) {
    r.key = null;
    if (r.last != null) r.set(r.last);
  }
}

/**
 * One value readout, laid out like LabelWithContainer::paint: every character sits centred in its
 * own slot (digits share one slot width), the run is right-aligned to the inner box, and a digit
 * that changes flips over 60 ms (fade, vertical squash to 20%, shear), as the plugin draws it.
 */
class Readout {
  constructor(parent, box, color, fx, face = READOUT_FONTS.technology) {
    const [x, y, w, h, , fontPx] = box;
    this.fontPx = fontPx;
    this.face = face;
    this.font = `${face.weight} ${fontPx}px ${face.family}`;
    this.innerX = SX; // one plugin px border
    this.innerY = SY;
    this.innerW = w - 2 * SX;
    this.innerH = h - 2 * SY;
    this.node = el("div", { parent, cls: "cb-readout" });
    Object.assign(this.node.style, {
      position: "absolute",
      left: px(x),
      top: px(y),
      width: px(w),
      height: px(h),
      font: this.font,
      color,
      whiteSpace: "pre",
    });
    const s = fx.glowSpread * SX;
    const d = 0.7 * s;
    const c = rgba(color, fx.glowAlpha * 0.14);
    this.shadow = [
      [-s, 0], [s, 0], [0, -s], [0, s], [-d, -d], [d, -d], [-d, d], [d, d],
    ].map(([a, b]) => `${px(a)} ${px(b)} 0 ${c}`).join(", ");
    this.cells = [];
    this.last = null;
    allReadouts.add(this);
    // Clip margin of a flipping character: flip travel (0.25 px x 50%) + 2 px, plugin px.
    this.clipPad = (0.25 * 0.5 + 2) * SY;
    this.key = null;
  }

  _slot(ch, w, digitSlot, symbolMin, pad) {
    if (ch === " ") return symbolMin * this.face.space;
    if (isDigit(ch)) return Math.max(digitSlot, w * 1.05) + pad;
    // The plugin's rule for units and punctuation is measured * 1.3; for the Technology face the
    // letters (the "Hz") sit tighter in the real captures.
    const k = /[A-Za-z]/.test(ch) ? this.face.letter : 1.3;
    return Math.max(symbolMin, w * k) + pad;
  }

  // One cell per character: a clip box (used only while that character flips, as the plugin's
  // reduceClipRegion does) holding the incoming glyph and the outgoing one.
  _cell(i) {
    while (this.cells.length <= i) {
      const pad = this.clipPad;
      const box = el("div", { parent: this.node, style: { position: "absolute", top: px(this.innerY - pad), height: px(this.innerH + 2 * pad) } });
      const mk = () =>
        el("div", {
          parent: box,
          style: {
            position: "absolute",
            left: "0px",
            top: px(pad),
            height: px(this.innerH),
            lineHeight: px(this.innerH),
            textAlign: "center",
            textShadow: this.shadow,
          },
        });
      this.cells.push({ box, a: mk(), b: mk() });
    }
    return this.cells[i];
  }

  /** value: "45%" or { text, from, progress } (see Cues.readoutAt). */
  set(value) {
    this.last = value;
    const v = typeof value === "string" ? { text: value, from: value, progress: 1 } : value;
    const flipping = v.from !== v.text && v.progress < 1;
    const p = flipping ? clamp(v.progress) : 1;
    const key = flipping ? `${v.from}>${v.text}@${p.toFixed(4)}` : v.text;
    if (key === this.key) return;
    this.key = key;

    const text = v.text;
    // Map the old digits onto the new text from the right (setAnimatedValueText).
    let mapped = text.split("");
    const flipIdx = new Set();
    let dir = 0;
    if (flipping) {
      const fromD = [];
      const toD = [];
      for (let i = 0; i < v.from.length; i++) if (isDigit(v.from[i])) fromD.push(i);
      for (let i = 0; i < text.length; i++) if (isDigit(text[i])) toD.push(i);
      let fi = fromD.length - 1;
      for (let ti = toD.length - 1; ti >= 0; ti--) {
        const at = toD[ti];
        const fd = fi >= 0 ? v.from[fromD[fi]] : " ";
        mapped[at] = fd;
        if (fd !== text[at]) flipIdx.add(at);
        fi--;
      }
      const a = parseFloat(v.from);
      const b = parseFloat(text);
      if (Number.isFinite(a) && Number.isFinite(b)) dir = b > a ? 1 : b < a ? -1 : 0;
    }
    const old = mapped.join("");

    const fp = this.font;
    let digitSlot = 0;
    for (let d = 0; d <= 9; d++) digitSlot = Math.max(digitSlot, measure(String(d), fp));
    digitSlot = Math.max(digitSlot, this.innerH * 0.26);
    const symbolMin = Math.max(this.innerH * 0.16, digitSlot * 0.38);
    const pad = Math.max(0.8 * SX, this.innerH * 0.03);
    const widths = [];
    let total = 0;
    for (let i = 0; i < text.length; i++) {
      const w = Math.max(
        this._slot(text[i], measure(text[i], fp), digitSlot, symbolMin, pad),
        this._slot(old[i], measure(old[i], fp), digitSlot, symbolMin, pad),
      );
      widths.push(w);
      total += w;
    }

    let x = this.innerX + this.innerW - total;
    const setGlyph = (g, ch, w, alpha, transform, origin) => {
      if (g.__ch !== ch) {
        g.__ch = ch;
        g.textContent = ch;
      }
      setStyle(g, "display", "block");
      setStyle(g, "width", px(w));
      setStyle(g, "opacity", alpha >= 1 ? "" : String(+alpha.toFixed(4)));
      setStyle(g, "transform", transform || "");
      setStyle(g, "transformOrigin", origin || "");
    };
    const minScale = 0.2;
    const shearAmt = 0.3;
    for (let i = 0; i < text.length; i++) {
      const w = widths[i];
      const cell = this._cell(i);
      setStyle(cell.box, "display", "block");
      setStyle(cell.box, "left", px(x));
      setStyle(cell.box, "width", px(w));
      if (!flipIdx.has(i)) {
        setStyle(cell.box, "overflow", "visible");
        setGlyph(cell.a, text[i], w, 1);
        setStyle(cell.b, "display", "none");
      } else {
        setStyle(cell.box, "overflow", "hidden");
        const valueDown = dir < 0;
        // Label-space transform: scale about the pivot, then shear about the label origin
        // (JUCE applies the transform added last first). The glyph box sits at (x, innerY).
        const origin = `${px(-x)} ${px(-this.innerY)}`;
        const mk = (scale, pivotBottom, sign, travel) => {
          const pivot = pivotBottom ? this.innerY + this.innerH : this.innerY;
          const shear = (1 - scale) * shearAmt * sign;
          const f = pivot * (1 - scale) + travel;
          return `matrix(1, ${+shear.toFixed(5)}, 0, ${+scale.toFixed(5)}, 0, ${+f.toFixed(4)})`;
        };
        const outSign = valueDown ? -1 : 1;
        const travel = 0.25 * SY * 0.5; // flipTravelPx 0.25 x in/out 50%
        const outDir = valueDown ? -1 : 1;
        setGlyph(cell.b, old[i], w, 1 - p, mk(minScale + (1 - minScale) * (1 - p), !valueDown, outSign, outDir * travel * p), origin);
        setGlyph(cell.a, text[i], w, p, mk(minScale + (1 - minScale) * p, valueDown, -outSign, -outDir * travel * (1 - p)), origin);
      }
      x += w;
    }
    for (let k = text.length; k < this.cells.length; k++) setStyle(this.cells[k].box, "display", "none");
  }

  clear() {
    this.key = "";
    for (const c of this.cells) setStyle(c.box, "display", "none");
  }
}

// Frame stacks ---------------------------------------------------------------------------------

/**
 * One control drawn from per-frame images: an <img> per frame that the scenes declared, all
 * decoded before frame 0, shown by visibility. Nothing is loaded or decoded during the render, so
 * a seek to any time shows the right frame (never swap img.src per frame).
 */
class FrameStack {
  constructor(parent, urlOf, x, y, w, h, label) {
    this.urlOf = urlOf;
    this.label = label;
    this.node = el("div", { parent, style: { position: "absolute", left: px(x), top: px(y), width: px(w), height: px(h) } });
    this.imgs = new Map();
    this.cur = null;
    this.opacity = 1;
  }

  require(frames) {
    for (const f of frames) {
      if (this.imgs.has(f)) continue;
      const img = el("img", { parent: this.node, attrs: { src: this.urlOf(f), alt: "", draggable: "false" } });
      Object.assign(img.style, { position: "absolute", left: "0px", top: "0px", width: "100%", height: "100%", visibility: "hidden" });
      this.imgs.set(f, img);
    }
  }

  has(f) {
    return this.imgs.has(f);
  }

  show(f) {
    if (f === this.cur) return;
    if (f != null && !this.imgs.has(f)) {
      throw new Error(`plate: ${this.label} frame ${f} was not prepared; call plate.require()/requireRender() in build()`);
    }
    if (this.cur != null) this.imgs.get(this.cur).style.visibility = "hidden";
    this.cur = f;
    if (f != null) this.imgs.get(f).style.visibility = "";
  }

  setOpacity(a) {
    setStyle(this.node, "opacity", a >= 1 ? "" : String(+a.toFixed(4)));
    setStyle(this.node, "visibility", a > 0 ? "" : "hidden");
  }

  urls() {
    return [...this.imgs.keys()].map((f) => this.urlOf(f));
  }
}

// Plate ---------------------------------------------------------------------------------------

const range = (a, b) => {
  const out = [];
  for (let f = Math.min(a, b); f <= Math.max(a, b); f++) out.push(f);
  return out;
};

export class Plate {
  /**
   * engine: green | blue | red | purple | black | white (Create).
   * opts: { parent, scale, x, y (top-left) or cx, cy (centre), hiRes (2800 px plates; default when
   * scale > 1.05), thumb, readouts, readoutFont ("technology" | "jetbrains", see READOUT_FONTS),
   * state (initial state; its frames are prepared) }.
   */
  constructor(engine, { parent = null, scale = 1, x = 0, y = 0, cx = null, cy = null, hiRes = null, thumb = null, readouts = null, readoutFont = "technology", className = "", state = null } = {}) {
    if (!LAYOUT[engine]) throw new Error(`plate: unknown engine ${engine}`);
    this.engine = engine;
    this.L = LAYOUT[engine];
    this.white = engine === "white";
    this.art = artFor(engine, { hiRes: hiRes ?? scale > 1.05 });
    this.showThumb = thumb ?? !this.white;
    this.showReadouts = readouts ?? !this.white;

    this.el = el("div", { cls: `cb-plate cb-${engine} ${className}`.trim(), parent });
    Object.assign(this.el.style, { position: "absolute", left: "0px", top: "0px", transformOrigin: "0 0" });
    this.inner = el("div", { parent: this.el });
    Object.assign(this.inner.style, {
      position: "absolute",
      left: "0px",
      top: "0px",
      width: `${PLATE_W}px`,
      height: `${PLATE_H}px`,
      transformOrigin: "0 0",
    });
    const plateBg = (url) =>
      el("div", {
        parent: this.inner,
        style: {
          position: "absolute",
          left: "0px",
          top: "0px",
          width: `${PLATE_W}px`,
          height: `${PLATE_H}px`,
          backgroundImage: `url("${url}")`,
          backgroundSize: `${PLATE_W}px ${PLATE_H}px`,
          backgroundRepeat: "no-repeat",
        },
      });
    this.plateOff = plateBg(this.art.plateOff);
    this.plateOn = plateBg(this.art.plateOn);
    Object.assign(this.plateOn.style, { opacity: "0", visibility: "hidden" });

    // Knobs: the _off frames, with the _on frames over them for the HQ cross-fade.
    this.knobs = {};
    for (const k of KNOBS) {
      const [kx, ky, w, h] = this.L[k];
      const mk = (on) => new FrameStack(this.inner, (f) => this.art.knobFrame(k, on, f), kx - w / 2, ky - h / 2, w, h, `${engine} ${k}${on ? " on" : " off"}`);
      const off = mk(false);
      const on = this.white ? null : mk(true);
      this.knobs[k] = { off, on };
    }
    {
      const [mx, my, w, h] = this.L.mix;
      this.mix = new FrameStack(this.inner, (f) => this.art.mixFrame(f), mx - w / 2, my - h / 2, w, h, `${engine} mix`);
    }
    if (this.showThumb && this.art.thumb) {
      const [, , , , tw, th, ty] = this.L.slider;
      this.thumb = el("div", {
        parent: this.inner,
        style: {
          position: "absolute",
          top: px(ty - th / 2),
          width: px(tw),
          height: px(th),
          backgroundImage: `url("${this.art.thumb}")`,
          backgroundSize: "100% 100%",
          backgroundRepeat: "no-repeat",
        },
      });
      this.thumbW = tw;
    }
    {
      const [x0, y0, w, h] = this.L.hq;
      // Two stacks: the lever frame under the fractional position and the next one over it.
      this.sw = [0, 1].map((i) => new FrameStack(this.inner, (f) => this.art.switchFrame(f), x0, y0, w, h, `${engine} switch`));
    }
    this.readouts = {};
    if (this.showReadouts) {
      const color = READOUT_COLOR[engine];
      for (const r of READOUTS) {
        const fx = r === "mix" ? READOUT_FX.mix : r === "color" ? READOUT_FX.color : READOUT_FX.main;
        this.readouts[r] = new Readout(this.inner, this.L.values[r], color, fx, READOUT_FONTS[readoutFont]);
      }
    }
    this.cur = {};
    this.placement = { x: 0, y: 0, scale: 1, dx: 0, dy: 0 };
    this.place(cx != null ? { cx, cy, scale } : { x, y, scale });
    if (state) {
      this.require(state);
      this.setState(state);
    }
  }

  // Frames this state shows: { knobs: {rate: f,...}, mix: f, switch: [i0, i1], on, off }.
  _framesOf(state) {
    const out = { knobs: {}, mix: null, sw: [], on: false, off: false };
    for (const k of KNOBS) {
      if (state.frames && state.frames[k] != null) out.knobs[k] = state.frames[k];
      else if (state[k] != null) out.knobs[k] = this.white ? 50 : knobFrameMain(pFromValue(k, state[k]));
    }
    if (state.frames && state.frames.mix != null) out.mix = state.frames.mix;
    else if (state.mix != null) out.mix = this.white ? knobFrameWhiteMix(0.5) : knobFrameMix(pFromValue("mix", state.mix));
    let sf = state.switchFrame;
    if (sf == null && state.hq != null) sf = state.hq ? SWITCH_ON : SWITCH_OFF;
    if (sf == null && this.white) sf = SWITCH_ON;
    if (sf != null) {
      const f = clamp(sf, 0, 17);
      const i0 = Math.floor(f + 1e-6);
      out.sw = [i0, Math.min(17, i0 + 1)];
      out.frac = f - i0;
      out.lit = 1 - f / 17;
      out.on = out.lit > 1e-4;
      out.off = out.lit < 1 - 1e-4;
    }
    return out;
  }

  /**
   * Prepare the frames a state (or list of states) will show. Call in build(); setState throws on
   * a frame that was not prepared. States without a switch position prepare both HQ sheets.
   */
  require(states) {
    for (const s of [].concat(states)) {
      const fr = this._framesOf(s);
      const both = !fr.sw.length;
      for (const k of KNOBS) {
        if (fr.knobs[k] == null) continue;
        if (fr.off || both || this.white) this.knobs[k].off.require([fr.knobs[k]]);
        if ((fr.on || both) && this.knobs[k].on) this.knobs[k].on.require([fr.knobs[k]]);
      }
      if (fr.mix != null) this.mix.require([fr.mix]);
      if (fr.sw.length) {
        this.sw[0].require([fr.sw[0]]);
        if (fr.frac > 1e-4) this.sw[1].require([fr.sw[1]]);
      }
    }
    return this;
  }

  /** Prepare every frame between two knob frames (a gesture), for one control. */
  requireFrames(control, f0, f1, { on = true, off = true } = {}) {
    const fs = range(f0, f1);
    if (control === "mix") this.mix.require(fs);
    else if (control === "switch") {
      this.sw[0].require(fs);
      this.sw[1].require(fs);
    } else {
      if (off || this.white) this.knobs[control].off.require(fs);
      if (on && this.knobs[control].on) this.knobs[control].on.require(fs);
    }
    return this;
  }

  /**
   * Prepare everything a cue render shows over [t0, t1] (sampled per video frame), e.g.
   * plate.requireRender(cues, "R04", 24, 28) for the Red shot with its HQ flip.
   */
  requireRender(cues, renderId, t0, t1, fps = 60) {
    const n = Math.max(1, Math.round((t1 - t0) * fps));
    const states = [];
    for (let i = 0; i <= n; i++) states.push(cues.settingsAt(renderId, t0 + ((t1 - t0) * i) / n));
    return this.require(states);
  }

  /** The image URLs this plate draws (for preloading). */
  urls() {
    const u = [this.art.plateOff, this.art.plateOn];
    if (this.art.thumb && this.showThumb) u.push(this.art.thumb);
    for (const k of KNOBS) {
      u.push(...this.knobs[k].off.urls());
      if (this.knobs[k].on) u.push(...this.knobs[k].on.urls());
    }
    u.push(...this.mix.urls(), ...this.sw[0].urls(), ...this.sw[1].urls());
    return [...new Set(u)];
  }

  /**
   * Position on screen (relative to the parent): x/y is the plate's top-left, or give cx/cy for
   * its centre. dx/dy is an extra offset (G2 drift). Scale is a plain 2D transform: the plate has
   * no canvas inside, so it is seek-safe.
   */
  place({ x, y, cx, cy, scale, dx, dy } = {}) {
    const P = this.placement;
    if (scale != null) P.scale = scale;
    if (cx != null) P.x = cx - (PLATE_W * P.scale) / 2;
    else if (x != null) P.x = x;
    if (cy != null) P.y = cy - (PLATE_H * P.scale) / 2;
    else if (y != null) P.y = y;
    if (dx != null) P.dx = dx;
    if (dy != null) P.dy = dy;
    setStyle(this.el, "left", px(P.x));
    setStyle(this.el, "top", px(P.y));
    setStyle(this.el, "width", px(PLATE_W * P.scale));
    setStyle(this.el, "height", px(PLATE_H * P.scale));
    setStyle(this.el, "transform", P.dx || P.dy ? `translate(${px(P.dx)}, ${px(P.dy)})` : "");
    setStyle(this.inner, "transform", P.scale === 1 ? "" : `scale(${+P.scale.toFixed(6)})`);
    return this;
  }

  /** Plate px -> screen px in the parent's coordinates, with the current placement. */
  toScreen(pxX, pxY) {
    const P = this.placement;
    return [P.x + P.dx + pxX * P.scale, P.y + P.dy + pxY * P.scale];
  }

  /** A control's centre and size in screen px ({ cx, cy, size }), for rings and camera moves. */
  controlScreenRect(name) {
    const r = controlRect(this.engine, name, name === "color" || name === "thumb" ? this.cur.thumbX : null);
    const [cx, cy] = this.toScreen(r.cx, r.cy);
    return { cx, cy, size: r.size * this.placement.scale };
  }

  /**
   * state: { rate, depth, offset, width, color, mix } in display units (any subset),
   * hq (0/1) or switchFrame (0..17, float while the lever moves),
   * readouts: { rate: "0.60 Hz" | { text, from, progress }, ... } to override the text
   * (default: formatted from the values), frames: { rate: 47, mix: 78 } to force filmstrip frames.
   * Cues.plateStateAt(render, t) returns exactly this shape.
   */
  setState(state) {
    const c = this.cur;
    const fr = this._framesOf(state);
    if (fr.sw.length) {
      const key = `${fr.sw[0]}:${fr.frac.toFixed(4)}`;
      if (c.sw !== key) {
        c.sw = key;
        c.lit = fr.lit;
        this.sw[0].show(fr.sw[0]);
        const a = fr.frac > 1e-4 ? fr.frac : 0;
        this.sw[1].show(a > 0 ? fr.sw[1] : null);
        this.sw[1].setOpacity(a);
        // Lit plate follows the lever: 1 - frame / 17.
        setStyle(this.plateOn, "opacity", String(+fr.lit.toFixed(4)));
        setStyle(this.plateOn, "visibility", fr.lit > 1e-4 ? "" : "hidden");
      }
    }
    const lit = c.lit ?? 0;
    for (const k of KNOBS) {
      const f = fr.knobs[k];
      const kn = this.knobs[k];
      const onA = kn.on ? lit : 0;
      // _on over _off at the lever's opacity; _off fades out over the last fifth so the soft knob
      // shadow is not doubled once the lever is fully up.
      const offA = kn.on ? clamp((1 - lit) * 5) : 1;
      if (f != null) {
        if (offA > 0) kn.off.show(f);
        if (kn.on && onA > 0) kn.on.show(f);
      }
      kn.off.setOpacity(offA);
      if (kn.on) kn.on.setOpacity(onA);
    }
    if (fr.mix != null) this.mix.show(fr.mix);
    if (this.thumb && state.color != null) {
      const tx = thumbX(pFromValue("color", state.color));
      if (c.thumbX !== tx) {
        c.thumbX = tx;
        this.thumb.style.left = px(tx - this.thumbW / 2);
      }
    }
    if (this.showReadouts) {
      for (const r of READOUTS) {
        const o = state.readouts && state.readouts[r];
        if (o != null) this.readouts[r].set(o);
        else if (state[r] != null) this.readouts[r].set(formatReadout(r, state[r]));
      }
    }
    return this;
  }
}

/** createPlate("green", opts) or createPlate(stateWithEngine, opts) (prepares and shows that state). */
export function createPlate(engineOrState, opts = {}) {
  if (typeof engineOrState === "string") return new Plate(engineOrState, opts);
  return new Plate(engineOrState.engine, { ...opts, state: engineOrState });
}

/** G2 plate drift in px: A sin(2 pi cycles), A = 4 px x min(1, Depth / 30%). */
export function driftPx(settings, amp = 4) {
  return amp * Math.min(1, settings.depth / 30) * Math.sin(TAU * settings.cycles);
}
