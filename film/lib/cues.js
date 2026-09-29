// The cue sheet (film/cues.json) as functions of time.
//
// One file drives the audio automation and the picture. Gestures ease the knob POSITION p (0..1)
// with the named ease, and p maps to display units exactly as in the plugin (visual-assets 3.3).
// The audio generator samples the same curve, so a knob frame, a readout and the heard setting
// agree at every t.

import { clamp, lerp, ease, smootherstep } from "./util.js";

export const PARAMS = ["rate", "depth", "offset", "width", "color", "mix"];

// Position p (0..1) <-> display value. Rate in Hz, offset in degrees, the rest in percent.
export function valueFromP(param, p) {
  p = clamp(p);
  switch (param) {
    case "rate": return 0.005 + 19.995 * Math.pow(p, 4.35);
    case "offset": return 180 * p;
    case "width": return 200 * p;
    case "depth":
    case "color":
    case "mix": return 100 * p;
    default: throw new Error(`valueFromP: unknown param ${param}`);
  }
}

export function pFromValue(param, v) {
  switch (param) {
    case "rate": return clamp(Math.pow(Math.max(0, (v - 0.005) / 19.995), 1 / 4.35));
    case "offset": return clamp(v / 180);
    case "width": return clamp(v / 200);
    case "depth":
    case "color":
    case "mix": return clamp(v / 100);
    default: throw new Error(`pFromValue: unknown param ${param}`);
  }
}

// Filmstrip frames (visual-assets 3.2). The plugin snaps to the nearest frame.
export const knobFrameMain = (p) => Math.round(((14 + 332 * clamp(p)) / 360) * 99);
export const knobFrameMix = (p) => Math.round(155 - ((14 + 332 * clamp(p)) / 360) * 155);
/** White Create mix sheet: 100 frames, read in reverse like the other mix sheets. */
export const knobFrameWhiteMix = (p) => Math.round(99 - ((14 + 332 * clamp(p)) / 360) * 99);
/** COLOR thumb centre x on the 1400x725 plate. */
export const thumbX = (p) => 473.8 + 498.5 * clamp(p);

/**
 * Readout text in the plugin's formats (PluginEditor::updateValueLabel): Rate two decimals below
 * 1 Hz and one above; percentages and degrees truncate, after +1e-6 so 35% never prints 34%.
 */
export function formatReadout(param, v) {
  switch (param) {
    case "rate": return v < 1 ? `${v.toFixed(2)} Hz` : `${v.toFixed(1)} Hz`;
    case "offset": return `${Math.floor(v + 1e-6)}°`;
    case "depth":
    case "width":
    case "color":
    case "mix": return `${Math.floor(v + 1e-6)}%`;
    default: throw new Error(`formatReadout: unknown param ${param}`);
  }
}

// Plugin switch sheet: frame 0 = lever up = HQ on (LED lit); frame 17 = lever down = HQ off.
export const SWITCH_ON = 0;
export const SWITCH_OFF = 17;

export class Cues {
  constructor(json) {
    this.json = json;
    this.fps = json.fps;
    this.duration = json.duration;
    this.renders = json.renders;
    this.gestures = json.gestures || [];
    this.sections = json.sections || [];
    this.scope = json.scope || {};
    this._byRenderParam = new Map();
    for (const g of this.gestures) {
      const k = `${g.render}:${g.param}`;
      if (!this._byRenderParam.has(k)) this._byRenderParam.set(k, []);
      this._byRenderParam.get(k).push(g);
    }
    for (const list of this._byRenderParam.values()) list.sort((a, b) => a.t0 - b.t0);
    this._cycleCache = new Map();
  }

  render(id) {
    const r = this.renders[id];
    if (!r) throw new Error(`cues: no render ${id}`);
    return r;
  }

  gesturesFor(renderId, param) {
    return this._byRenderParam.get(`${renderId}:${param}`) || [];
  }

  /** The gesture (if any) of a render, by param. */
  gesture(renderId, param) {
    return this.gesturesFor(renderId, param)[0] || null;
  }

  /** Knob position p of a render's param at time t, with gesture eases applied to p. */
  pAt(renderId, param, t) {
    return pFromValue(param, this.valueAt(renderId, param, t));
  }

  /** Display value of a render's param at time t. */
  valueAt(renderId, param, t) {
    const r = this.render(renderId);
    if (param === "hq") return this.hqAt(renderId, t);
    let v = r.knobs[param];
    for (const g of this.gesturesFor(renderId, param)) {
      if (t < g.t0) break;
      if (t >= g.t1) {
        v = g.to;
        continue;
      }
      const u = (t - g.t0) / (g.t1 - g.t0);
      const p0 = pFromValue(param, g.from);
      const p1 = pFromValue(param, g.to);
      return valueFromP(param, lerp(p0, p1, ease(g.ease, u)));
    }
    return v;
  }

  /** HQ as heard: steps at the gesture's t0. */
  hqAt(renderId, t) {
    let hq = this.render(renderId).hq;
    for (const g of this.gesturesFor(renderId, "hq")) if (t >= g.t0) hq = g.to;
    return hq;
  }

  /**
   * HQ switch art frame (float, 0..17). The switch animates over the gesture window with the
   * plugin's smootherstep blend: 420 ms for off to on, as AnimatedToggleButton does.
   */
  switchFrameAt(renderId, t) {
    const r = this.render(renderId);
    let frame = r.hq ? SWITCH_ON : SWITCH_OFF;
    for (const g of this.gesturesFor(renderId, "hq")) {
      const f0 = g.from ? SWITCH_ON : SWITCH_OFF;
      const f1 = g.to ? SWITCH_ON : SWITCH_OFF;
      if (t < g.t0) break;
      if (t >= g.t1) {
        frame = f1;
        continue;
      }
      return lerp(f0, f1, smootherstep((t - g.t0) / (g.t1 - g.t0)));
    }
    return frame;
  }

  /**
   * LFO cycles of a render from film time 0 to t: the integral of Rate. Use it for anything that
   * moves "at R" (ChorusType, plate drift, hairlines) so a Rate gesture speeds the motion up
   * without a phase jump. sin(2*PI*cyclesAt(...)) replaces sin(2*PI*R*t).
   */
  cyclesAt(renderId, t) {
    const r = this.render(renderId);
    const gs = this.gesturesFor(renderId, "rate");
    // The render's LFO starts at the head of its pre-roll, before film time 0, at the initial Rate.
    const pre = r.knobs.rate * this.prerollOf(renderId);
    if (!gs.length) return pre + r.knobs.rate * t;
    let acc = pre;
    let tPrev = 0;
    let rate = r.knobs.rate;
    for (const g of gs) {
      if (t <= g.t0) return acc + rate * (t - tPrev);
      acc += rate * (g.t0 - tPrev);
      const tEnd = Math.min(t, g.t1);
      acc += this._integrateRate(renderId, g.t0, tEnd);
      if (t <= g.t1) return acc;
      tPrev = g.t1;
      rate = g.to;
    }
    return acc + rate * (t - tPrev);
  }

  /**
   * Seconds the render ran before film time 0: the render's own "preroll" (R05's swoosh sweep),
   * else the sheet's preroll_default, else 2.0 (treatment 8.4: every render uses --preroll 2).
   */
  prerollOf(renderId) {
    const r = this.render(renderId);
    return r.preroll ?? this.json.preroll_default ?? 2.0;
  }

  _integrateRate(renderId, a, b) {
    if (b <= a) return 0;
    // Composite Simpson with a fixed step count: deterministic and well below a pixel of error.
    const n = 512;
    const h = (b - a) / n;
    let s = this.valueAt(renderId, "rate", a) + this.valueAt(renderId, "rate", b);
    for (let i = 1; i < n; i++) s += (i % 2 ? 4 : 2) * this.valueAt(renderId, "rate", a + i * h);
    return (s * h) / 3;
  }

  /** Every heard setting of a render at t, in display units, plus HQ, switch art and LFO cycles. */
  settingsAt(renderId, t) {
    const r = this.render(renderId);
    const s = { render: renderId, engine: r.engine, stem: r.stem };
    for (const p of PARAMS) s[p] = this.valueAt(renderId, p, t);
    s.hq = this.hqAt(renderId, t);
    s.switchFrame = this.switchFrameAt(renderId, t);
    s.cycles = this.cyclesAt(renderId, t);
    return s;
  }

  /**
   * Readout of a render's param at t, with the plugin's 60 ms digit flip: { text, from, progress }.
   * The flip starts when the text last changed; that moment is found by bisection on the value
   * curve, so the result depends on t only.
   */
  readoutAt(renderId, param, t, flipSec = 0.06) {
    const fmt = (tt) => formatReadout(param, this.valueAt(renderId, param, tt));
    const text = fmt(t);
    const before = fmt(t - flipSec);
    if (before === text) return { text, from: text, progress: 1 };
    let lo = t - flipSec; // text differs here
    let hi = t; // text equals `text` here
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      if (fmt(mid) === text) hi = mid;
      else lo = mid;
    }
    return { text, from: fmt(lo), progress: clamp((t - hi) / flipSec) };
  }

  /** Every readout of a render at t (see readoutAt). */
  readoutsAt(renderId, t) {
    const out = {};
    for (const p of PARAMS) out[p] = this.readoutAt(renderId, p, t);
    return out;
  }

  /**
   * Plate state for a render at time t, ready for plate.setState(). Values in display units,
   * readouts with flips, switch art frame.
   */
  plateStateAt(renderId, t) {
    const s = this.settingsAt(renderId, t);
    return { ...s, readouts: this.readoutsAt(renderId, t) };
  }

  /**
   * Level-match footnotes as the audio build decided them (treatment 8.6): "LEVEL MATCHED" for
   * shots 2-3 and "SAME TAKE · LEVEL MATCHED" for the tour only when the log passed, otherwise the
   * fallback wording.
   */
  footnote(kind) {
    const r = (this.json.levelmatch && this.json.levelmatch.result) || {};
    if (kind === "opening") return r.footnote_shots_2_3 ?? (r.bars_1_4_pass ? "LEVEL MATCHED" : null);
    if (kind === "tour") return r.footnote_tour ?? (r.bars_9_18_pass ? "LEVEL MATCHED" : ""); // v4: each engine plays the next two bars of the song
    throw new Error(`cues.footnote: unknown kind ${kind}`);
  }

  /** A section by name (e.g. "fold"), with any clip_in / clip_out the audio build wrote. */
  section(name) {
    return this.sections.find((s) => s.name === name) || null;
  }

  sectionAt(t) {
    for (const s of this.sections) if (t >= s.t0 && t < s.t1) return s;
    return null;
  }

  /** The render heard on a stem at time t (from the section audio map), or null. */
  renderFor(stem, t) {
    const s = this.sectionAt(t);
    const id = s && s.audio ? s.audio[stem] : null;
    return id && this.renders[id] ? id : null;
  }

  /** Featured scope stem at time t (optionally for one engine on a multi-plate card). */
  featuredStemAt(t, engine = null) {
    for (const f of this.scope.featured || []) {
      if (t < f.t0 || t >= f.t1) continue;
      if (f.stem) return f.stem;
      if (f.stems && engine) return f.stems[engine] || null;
    }
    return null;
  }
}

export async function loadCues(url = "/film/cues.json") {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`cues: ${r.status} ${url}`);
  return new Cues(await r.json());
}
