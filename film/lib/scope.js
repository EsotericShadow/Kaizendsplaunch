// The line (treatment G7): a canvas goniometer of the featured stem, drawn from the audio build's
// scope data. x = side (L-R)/2, y = mid (L+R)/2, so mono is a vertical line.
//
// Data: /data/scope/index.json and one int16 file per stem (<stem>.i16), aligned to film time.
// Frame f holds 400 (mid, side) pairs, already scaled by the one film gain (-12 dBFS -> 0.45 of
// the trace radius). When the data is missing the scope draws a PLACEHOLDER derived from the cue
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

// Component ------------------------------------------------------------------------------------

export class Scope {
  /**
   * parent: an untransformed layer. cx, cy: centre in the parent's px. size: circle diameter.
   * disc: backdrop fill or null. frame: 1 px circle outline (persists across the tour, never smears).
   */
  constructor(parent, { cx = 0, cy = 0, size = 160, disc = "rgba(5,5,6,0.6)", frame = true, frameColor = "rgba(246,244,239,0.14)", color = "#f6f4ef", stem = "gtr", radius = 0.46 } = {}) {
    this.size = size;
    this.color = color;
    this.stem = stem;
    this.radius = radius;
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

  /**
   * Draw the trace for film time t. opts: { stem, color, zoom, alpha, render } where render is a
   * cue render id used only by the placeholder when the stem's section map has none.
   */
  draw(t, { stem = this.stem, color = this.color, zoom = 1, alpha = 1, render = null } = {}) {
    const ctx = this.ctx;
    const W = this.canvas.width;
    const H = this.canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, W, H);
    if (alpha <= 0) return;
    const f = Math.round(t * FPS);
    const [r, g, b] = hexToRgb(color);
    const R = (this.radius * this.size * zoom) * this.dpr;
    const cx = W / 2;
    const cy = H / 2;
    ctx.globalCompositeOperation = "lighter";
    ctx.lineWidth = 1.5 * this.dpr;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    let placeholder = false;
    const trails = [[f - 2, 0.25], [f - 1, 0.5], [f, 1]];
    for (const [ff, k] of trails) {
      const { data, scale, placeholder: ph } = frameData(ff, stem, render);
      placeholder = placeholder || ph;
      ctx.strokeStyle = `rgba(${r},${g},${b},${+(0.35 * k * alpha).toFixed(4)})`;
      ctx.beginPath();
      const n = data.length / 2;
      for (let i = 0; i < n; i++) {
        const mid = clamp(data[2 * i] * scale, -1, 1);
        const side = clamp(data[2 * i + 1] * scale, -1, 1);
        const x = cx + side * R;
        const y = cy - mid * R;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    if (placeholder) {
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "rgba(255,90,90,0.9)";
      ctx.font = `600 ${Math.max(8, Math.round(this.size * 0.055)) * this.dpr}px "JetBrains Mono", monospace`;
      ctx.textAlign = "center";
      ctx.fillText("PLACEHOLDER", cx, H - this.size * 0.12 * this.dpr);
    }
  }
}

export function createScope(parent, opts) {
  return new Scope(parent, opts);
}
