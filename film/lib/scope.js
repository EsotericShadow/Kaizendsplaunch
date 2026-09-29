// The line (treatment G7): a canvas goniometer of the featured stem, drawn from the audio build's
// scope data. x = side (L-R)/2, y = mid (L+R)/2, so mono is a vertical line.
//
// Data: /data/scope/index.json and one int16 file per stem (<stem>.i16), aligned to film time.
// Frame f holds 400 (mid, side) pairs, already scaled by the one film data gain (-12 dBFS -> 0.45
// of the trace radius). A fixed display gain with a tanh soft limit is applied at draw time (see
// DISPLAY_GAIN). When the data is missing the scope draws a PLACEHOLDER derived from the cue
// sheet, and says so on the canvas.
//
// The canvas must never sit inside an element with an animated transform (seek safety): place
// the scope with left/top only and zoom with draw(t, { zoom }).

import { el, TAU, clamp, hexToRgb, setStyle, px } from "./util.js";

const FPS = 60;
const SAMPLES_PER_FRAME = 800;
const SR = 48000;

export const scopeData = {
  status: "unloaded", // "real" | "placeholder"
  points: 400,
  frames: 0,
  stems: {}, // stem -> Int16Array
  cues: null,
  note: "",
};

/**
 * Load the scope data once (the stage calls this in setup). /data/available.json is written by
 * film/film.sh before every render and says whether /data/scope exists, so a missing folder never
 * produces a failing 404.
 */
export async function loadScopeData(cues) {
  scopeData.cues = cues;
  if (scopeData.status !== "unloaded") return scopeData;
  let avail = {};
  try {
    const r = await fetch("/data/available.json");
    if (r.ok) avail = await r.json();
  } catch {
    avail = {};
  }
  if (!avail.scope) {
    scopeData.status = "placeholder";
    scopeData.note = "no /data/scope index";
    return scopeData;
  }
  const idx = await (await fetch("/data/scope/index.json")).json();
  scopeData.points = idx.points_per_frame || idx.points || 400;
  let stems = idx.stems || idx.files || {};
  if (Array.isArray(stems)) stems = Object.fromEntries(stems.map((s) => (typeof s === "string" ? [s, {}] : [s.name || s.stem, s])));
  const wanted = avail.scopeStems || Object.keys(stems);
  await Promise.all(
    Object.entries(stems)
      .filter(([name]) => wanted.includes(name))
      .map(async ([name, info]) => {
        const file = (info && (info.file || info.path)) || `${name}.i16`;
        const r = await fetch(`/data/scope/${file}`);
        if (!r.ok) throw new Error(`scope ${r.status}: ${file}`);
        scopeData.stems[name] = new Int16Array(await r.arrayBuffer());
      }),
  );
  const any = Object.values(scopeData.stems)[0];
  scopeData.frames = any ? Math.floor(any.length / (2 * scopeData.points)) : 0;
  scopeData.status = Object.keys(scopeData.stems).length ? "real" : "placeholder";
  return scopeData;
}

// Placeholder signal ---------------------------------------------------------------------------

// The take's motif notes (M_D, M_Bm) for a plausible trace: eighth notes at 120 BPM.
const MOTIF = [146.83, 220.0, 277.18, 329.63, 369.99, 329.63, 277.18, 220.0, 123.47, 185.0, 220.0, 293.66, 329.63, 293.66, 220.0, 185.0];

function placeholderFrame(f, stem, renderHint) {
  const cues = scopeData.cues;
  const n = scopeData.points;
  const out = new Float32Array(n * 2);
  if (!cues) return out;
  const t = f / FPS;
  const render = renderHint || cues.renderFor(stem || "gtr", t);
  if (!render) return out;
  const s = cues.settingsAt(render, t);
  const mix = s.mix / 100;
  const D = s.depth / 100;
  const W = s.width / 100;
  const phi = (s.offset * Math.PI) / 180;
  const note = Math.floor(t / 0.25);
  const since = t - note * 0.25;
  const f0 = MOTIF[((note % MOTIF.length) + MOTIF.length) % MOTIF.length];
  const env = 0.55 * Math.exp(-since / 0.45) + 0.12;
  const lfoL = Math.sin(TAU * s.cycles);
  const lfoR = Math.sin(TAU * s.cycles + phi);
  const dL = 0.011 + D * 0.006 * lfoL;
  const dR = 0.011 + D * 0.006 * lfoR;
  const sig = (tt) => Math.sin(TAU * f0 * tt) + 0.35 * Math.sin(TAU * 2 * f0 * tt + 0.4) + 0.12 * Math.sin(TAU * 3 * f0 * tt + 1.1);
  for (let k = 0; k < n; k++) {
    const ts = t + (k * SAMPLES_PER_FRAME) / (n * SR);
    const dry = sig(ts);
    const L = dry * (1 - 0.5 * mix) + mix * sig(ts - dL);
    const R = dry * (1 - 0.5 * mix) + mix * sig(ts - dR);
    const mid = ((L + R) / 2) * env * 0.5;
    const side = ((L - R) / 2) * env * 0.5 * W;
    out[2 * k] = mid;
    out[2 * k + 1] = side;
  }
  return out;
}

function frameData(f, stem, renderHint) {
  const n = scopeData.points;
  const arr = scopeData.stems[stem];
  if (!arr) return { data: placeholderFrame(f, stem, renderHint), scale: 1, placeholder: true };
  if (f < 0 || f >= scopeData.frames) return { data: new Float32Array(n * 2), scale: 1, placeholder: false };
  return { data: arr.subarray(f * n * 2, (f + 1) * n * 2), scale: 1 / 32767, placeholder: false };
}

// Display ---------------------------------------------------------------------------------------

/**
 * One fixed DISPLAY gain for the whole film, applied at draw time on top of the data's own fixed
 * gain (-12 dBFS -> 0.45 of the trace radius), which was right for level but drew every trace as a
 * small squiggle. A gentle radial tanh soft limit follows, so a peak bends in towards the rim
 * instead of clipping flat: a point at trace radius r lands on KNEE * tanh(DISPLAY_GAIN * r / KNEE).
 * The limit is radial, so every angle (and the L, R and M axes) is kept, and a mono signal
 * (side = 0) stays exactly on the vertical axis. With the film's stems this puts typical frames at
 * about 55-80% of the circle.
 */
export const DISPLAY_GAIN = 3.0;
export const DISPLAY_KNEE = 1.0;

/** Display position of one (mid, side) point, in trace units (1 = this.radius of the size). */
export function displayPoint(mid, side) {
  const x = side * DISPLAY_GAIN;
  const y = mid * DISPLAY_GAIN;
  const r = Math.hypot(x, y);
  if (r < 1e-9) return [0, 0];
  const k = (DISPLAY_KNEE * Math.tanh(r / DISPLAY_KNEE)) / r;
  return [x * k, y * k];
}

// Component ------------------------------------------------------------------------------------

export class Scope {
  /**
   * parent: an untransformed layer. cx, cy: centre in the parent's px. size: circle diameter.
   * disc: backdrop fill or null. outline: 1 px circle colour or null. graticule: the faint M/S
   * crosshair, L/R rim ticks and the L / R / M / S labels (mono, 40% white). frame: the old CSS
   * outline (off; the canvas outline replaces it).
   *
   * Orientation follows the pro goniometer convention: M up, L on the upper-left diagonal, R on
   * the upper-right. With side = (L-R)/2 that puts +side to the LEFT (x = -side), so a signal in
   * the left channel only lies on the L axis. Mono (side = 0) is the vertical M axis either way.
   */
  constructor(parent, { cx = 0, cy = 0, size = 160, disc = "rgba(5,5,6,0.6)", frame = false, frameColor = "rgba(246,244,239,0.14)", outline = "rgba(246,244,239,0.2)", graticule = true, color = "#f6f4ef", stem = "gtr", radius = 0.46, labelSize = null, lineWidth = null } = {}) {
    this.size = size;
    this.color = color;
    this.stem = stem;
    this.radius = radius;
    this.outline = outline;
    this.graticule = graticule;
    this.labelSize = labelSize ?? (size >= 280 ? 16 : 14);
    // 1.5 px on the mini scopes, up to 2 px on the payoff (1080p px).
    this.lineWidth = lineWidth ?? 1.5 + 0.5 * clamp((size - 200) / 300);
    this.root = el("div", { parent, cls: "scope" });
    Object.assign(this.root.style, { position: "absolute", width: px(size), height: px(size), borderRadius: "50%" });
    if (disc) this.root.style.background = disc;
    if (frame) this.root.style.boxShadow = `inset 0 0 0 1px ${frameColor}`;
    this.canvas = el("canvas", { parent: this.root });
    Object.assign(this.canvas.style, { position: "absolute", left: "0px", top: "0px", width: px(size), height: px(size) });
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(size * dpr);
    this.canvas.height = Math.round(size * dpr);
    this.dpr = dpr;
    this.ctx = this.canvas.getContext("2d");
    this.moveTo(cx, cy);
  }

  /** Move by left/top (never by transform). */
  moveTo(cx, cy) {
    setStyle(this.root, "left", px(cx - this.size / 2));
    setStyle(this.root, "top", px(cy - this.size / 2));
  }

  /** Outline, crosshair, rim ticks and labels, at `a` opacity (source-over, under the trace). */
  _drawGraticule(a) {
    const ctx = this.ctx;
    const d = this.dpr;
    const W = this.canvas.width;
    const cx = W / 2;
    const cy = W / 2;
    const Rc = (this.size / 2) * d; // circle radius
    const lw = Math.max(1, Math.round(d));
    ctx.globalCompositeOperation = "source-over";
    ctx.lineCap = "butt";
    if (this.outline) {
      ctx.globalAlpha = a;
      ctx.strokeStyle = this.outline;
      ctx.lineWidth = lw;
      ctx.beginPath();
      ctx.arc(cx, cy, Rc - lw / 2, 0, TAU);
      ctx.stroke();
    }
    if (!this.graticule) {
      ctx.globalAlpha = 1;
      return;
    }
    const fs = this.labelSize * d;
    const inset = fs * 1.05; // label centres sit this far inside the rim
    const axisA = 0.11;
    // Crosshair: the M (vertical) and S (horizontal) axes, stopping short of their labels.
    ctx.globalAlpha = a;
    ctx.strokeStyle = `rgba(246,244,239,${axisA})`;
    ctx.lineWidth = lw;
    const gapEnd = Rc - inset - fs * 0.85;
    const x0 = Math.round(cx) + (lw % 2 ? 0.5 : 0);
    const y0 = Math.round(cy) + (lw % 2 ? 0.5 : 0);
    ctx.beginPath();
    ctx.moveTo(x0, cy + Rc - lw);
    ctx.lineTo(x0, cy - gapEnd);
    ctx.moveTo(cx - Rc + lw, y0);
    ctx.lineTo(cx + gapEnd, y0);
    ctx.stroke();
    // Short ticks on the rim for the L and R diagonals, and a small centre mark.
    const s2 = Math.SQRT1_2;
    ctx.beginPath();
    for (const sx of [-1, 1]) {
      const r0 = Rc - fs * 0.55;
      const r1 = Rc - lw;
      ctx.moveTo(cx + sx * r0 * s2, cy - r0 * s2);
      ctx.lineTo(cx + sx * r1 * s2, cy - r1 * s2);
    }
    ctx.stroke();
    // Labels: M at the top of the vertical axis, S at the end of the horizontal one, L and R on
    // the upper diagonals (mono, 40% white).
    ctx.font = `600 ${fs}px "JetBrains Mono", monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "rgba(246,244,239,0.4)";
    const rl = Rc - inset - fs * 0.35;
    const yNudge = fs * 0.04; // optical centring of caps on the middle baseline
    ctx.fillText("M", cx, cy - Rc + inset + yNudge);
    ctx.fillText("S", cx + Rc - inset, cy + yNudge);
    ctx.fillText("L", cx - rl * s2, cy - rl * s2 + yNudge);
    ctx.fillText("R", cx + rl * s2, cy - rl * s2 + yNudge);
    ctx.globalAlpha = 1;
  }

  /**
   * Draw the trace for film time t. opts: { stem, color, zoom, alpha, gratAlpha, render } where
   * render is a cue render id used only by the placeholder when the stem's section map has none,
   * and gratAlpha scales the graticule on top of alpha (the payoff fades it in round the dot).
   */
  draw(t, { stem = this.stem, color = this.color, zoom = 1, alpha = 1, gratAlpha = 1, render = null } = {}) {
    const ctx = this.ctx;
    const W = this.canvas.width;
    const H = this.canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, W, H);
    if (alpha <= 0) return;
    if (alpha * gratAlpha > 0) this._drawGraticule(clamp(alpha * gratAlpha));
    const f = Math.round(t * FPS);
    const [r, g, b] = hexToRgb(color);
    const R = (this.radius * this.size * zoom) * this.dpr;
    const cx = W / 2;
    const cy = H / 2;
    ctx.globalCompositeOperation = "lighter";
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    const core = this.lineWidth * this.dpr;
    let placeholder = false;
    // Phosphor persistence: the two previous frames at 50% and 25%.
    const trails = [[f - 2, 0.25], [f - 1, 0.5], [f, 1]];
    for (const [ff, k] of trails) {
      const { data, scale, placeholder: ph } = frameData(ff, stem, render);
      placeholder = placeholder || ph;
      const n = data.length / 2;
      const xs = new Float64Array(n);
      const ys = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        const [sx, my] = displayPoint(clamp(data[2 * i] * scale, -1, 1), clamp(data[2 * i + 1] * scale, -1, 1));
        xs[i] = cx - sx * R;
        ys[i] = cy - my * R;
      }
      // A Catmull-Rom curve through every point (as cubic Beziers): at the display gain the
      // straight segments between points showed as corners; the curve still passes through each
      // measured point.
      ctx.beginPath();
      ctx.moveTo(xs[0], ys[0]);
      for (let i = 0; i < n - 1; i++) {
        const i0 = i > 0 ? i - 1 : i;
        const i3 = i + 2 < n ? i + 2 : i + 1;
        ctx.bezierCurveTo(
          xs[i] + (xs[i + 1] - xs[i0]) / 6,
          ys[i] + (ys[i + 1] - ys[i0]) / 6,
          xs[i + 1] - (xs[i3] - xs[i]) / 6,
          ys[i + 1] - (ys[i3] - ys[i]) / 6,
          xs[i + 1],
          ys[i + 1],
        );
      }
      // Additive glow in the hue: a wide soft pass, then the thin core.
      ctx.strokeStyle = `rgba(${r},${g},${b},${+(0.06 * k * alpha).toFixed(4)})`;
      ctx.lineWidth = core * 4;
      ctx.stroke();
      ctx.strokeStyle = `rgba(${r},${g},${b},${+(0.12 * k * alpha).toFixed(4)})`;
      ctx.lineWidth = core * 2;
      ctx.stroke();
      ctx.strokeStyle = `rgba(${r},${g},${b},${+(0.78 * k * alpha).toFixed(4)})`;
      ctx.lineWidth = core;
      ctx.stroke();
    }
    if (placeholder) {
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "rgba(255,90,90,0.9)";
      ctx.font = `600 ${Math.max(8, Math.round(this.size * 0.055)) * this.dpr}px "JetBrains Mono", monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      ctx.fillText("PLACEHOLDER", cx, H - this.size * 0.12 * this.dpr);
    }
    ctx.globalCompositeOperation = "source-over";
  }
}

export function createScope(parent, opts) {
  return new Scope(parent, opts);
}
