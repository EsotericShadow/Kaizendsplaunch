// What the viewer hears on the guitar, frame by frame: film/v5/demos.json read as pure functions
// of composition time. The picture reads the same file as the audio build, so every readout,
// knob frame, chip and colour grade shows exactly what is heard.
//
//   const demos = await loadDemos({ film: "main", beats });     // boot.js does this: ctx.demos
//   demos.stateAt(t)      -> { engine, hq, core, knobs, trim, bypass, heard, chip, demoId, demo }
//   demos.plateState(t)   -> the plate.setState() shape, readouts with the plugin's 60 ms flip
//   demos.grade(engine,t) -> { sat, bright } for plate.setGrade (colour = sound)
//   demos.cyclesAt(t)     -> the integrated LFO phase (sin(2 pi cycles) for drift and chorustype)
//   demos.gestureAt(t)    -> { param, u, g } while a gesture runs, else null
//   demos.levelMatched(id)-> true only when measured.json says that demo passed
//
// Picture timing: a step or switch keyed to a hit starts on the hit's frame (beats.onsetTime), so
// the picture leads the sound by less than one frame and is never late.

import { clamp, lerp, smootherstep } from "./util.js";
import { formatReadout, PARAMS } from "./cues.js";

const EASE = {
  "sine-inout": (u) => -(Math.cos(Math.PI * clamp(u)) - 1) / 2,
  "sine.inOut": (u) => -(Math.cos(Math.PI * clamp(u)) - 1) / 2,
  linear: (u) => clamp(u),
};
const KEYMAP = { rate: "rate_hz", depth: "depth_pct", offset: "offset_deg", width: "width_pct", color: "color_pct", mix: "mix_pct" };
export const HQ_SWITCH_S = 0.42; // the lever's own animation (smootherstep), picture only
export const FLIP_S = 0.06; // the plugin's readout digit flip
/** Colour = sound grades (TREATMENT section 2). */
export const GRADE = { heard: { sat: 1, bright: 1 }, notHeard: { sat: 0.35, bright: 0.75 }, off: { sat: 0.12, bright: 0.9 } };

let current = null;
export function getDemos() {
  if (!current) throw new Error("demos: loadDemos() has not run");
  return current;
}

export async function loadDemos({ url = "/film/v5/demos.json", film = "main", beats, measuredUrl = "/data/scope/measured.json" } = {}) {
  const json = await (await fetch(url)).json();
  let measured = null;
  try {
    const a = await (await fetch("/data/available.json")).json();
    if (a.measured) measured = await (await fetch(measuredUrl)).json();
  } catch {
    measured = null;
  }
  current = new Demos(json, { film, beats, measured });
  return current;
}

export class Demos {
  constructor(json, { film = "main", beats, measured = null }) {
    this.json = json;
    this.film = json.films[film];
    if (!this.film) throw new Error(`demos: no film "${film}"`);
    this.beats = beats;
    this.offset = beats ? beats.offset : this.film.offset || 0;
    this.engines = json.engines;
    this.measured = measured;
    this.demos = this.film.demos.map((d) => ({ ...d, _g: (d.gestures || []).filter((g) => g.param !== "trim") }));
    this.bypassSpans = [...(this.film.bypass_spans || [])];
    this.chipMixUntil = -Infinity; // master time until which the chip ends with " · MIX n%"
  }

  _onset(tm) {
    // The picture time of a master-time event: the start of the frame that contains it.
    const b = this.beats;
    return b ? b.onsetTime(tm - this.offset) + this.offset : tm;
  }

  /** The demo playing at composition time t (null outside every demo). */
  demoAt(t) {
    const tm = t + this.offset;
    // A demo that runs to the film's end holds through the last frame (main: M13 ends at 91.216,
    // inside frame 5472, which starts at 91.200; the end card's last frame is the thumbnail).
    const end = (this.film.span && this.film.span[1]) ?? Infinity;
    for (const d of this.demos) if (tm >= this._onset(d.t0) && (tm < this._onset(d.t1) || d.t1 >= end - 1e-6)) return d;
    return null;
  }

  demoById(id) {
    return this.demos.find((d) => d.id === id || d.id.startsWith(id)) || null;
  }

  /** A knob's value (display units) in demo d at composition time t. */
  valueIn(d, param, t) {
    const tm = t + this.offset;
    let v = d.knobs_at_t0[KEYMAP[param]];
    for (const g of d._g) {
      if (g.param !== param) continue;
      if (g.steps) {
        const ramp = g.ramp_s ?? 0.09;
        for (const s of g.steps) {
          const s0 = this._onset(s.t);
          if (tm < s0) break;
          v = lerp(s.from, s.to, EASE["sine-inout"]((tm - s0) / ramp));
        }
      } else {
        const g0 = this._onset(g.t0);
        const g1 = g0 + (g.t1 - g.t0);
        if (tm >= g0) v = lerp(g.from, g.to, (EASE[g.shape] || EASE["sine-inout"])((tm - g0) / (g1 - g0)));
      }
    }
    return v;
  }

  /** The lever's art frame (0 = HQ on, 17 = off) in demo d at t: the hq switch animates 420 ms. */
  switchFrameIn(d, t) {
    const tm = t + this.offset;
    const off = (hq) => (hq ? 0 : 17);
    const sw = d.hq_switch;
    if (!sw) return off(d.hq);
    const s0 = this._onset(sw.t);
    if (tm < s0) return off(sw.from);
    const u = smootherstep((tm - s0) / HQ_SWITCH_S);
    return lerp(off(sw.from), off(sw.to), u);
  }

  hqIn(d, t) {
    const sw = d.hq_switch;
    if (!sw) return d.hq;
    return t + this.offset >= this._onset(sw.t) ? sw.to : sw.from;
  }

  bypassAt(t) {
    const tm = t + this.offset;
    const inSpan = (s) => tm >= this._onset(s.t0) && tm < this._onset(s.t1);
    if (this.bypassSpans.some(inSpan)) return true;
    const d = this.demoAt(t);
    if (!d) return true; // outside every demo: the untouched master
    return (d.bypass || []).some(inSpan);
  }

  /** Everything heard at t. */
  stateAt(t) {
    const d = this.demoAt(t);
    if (!d) return { engine: null, hq: 0, core: null, knobs: null, trim: 0, bypass: true, heard: null, chip: "○ GUITAR · BYPASS", demoId: null, demo: null };
    const knobs = {};
    for (const p of PARAMS) knobs[p] = this.valueIn(d, p, t);
    const hq = this.hqIn(d, t);
    const core = this.engines[d.engine].cores[hq] || d.core;
    const bypass = this.bypassAt(t);
    const heard = !bypass && knobs.mix > 0 ? d.engine : null;
    const trimG = this.trimOf(d, t);
    const followsMix = (d.gestures || []).some((g) => g.param === "trim" && g.shape === "follows-mix");
    const trim = bypass ? 0 : followsMix ? (trimG * knobs.mix) / 40 : trimG;
    return { engine: d.engine, hq, core, knobs, trim, bypass, heard, chip: this.chipText(t, { d, knobs, core, bypass }), demoId: d.id, demo: d };
  }

  /** measured.json's entry for a demo id (its "demos" map, or a flat map), or null. */
  _measuredOf(id) {
    const M = this.measured;
    if (!M) return null;
    return (M.demos && M.demos[id]) || M[id] || null;
  }

  /**
   * The trim in dB a demo uses at composition time t: measured.json when present (a demo split at
   * a bar line has trim_parts), else the estimate in demos.json.
   */
  trimOf(d, t = null) {
    const m = this._measuredOf(d.id);
    if (m && Array.isArray(m.trim_parts) && m.trim_parts.length) {
      const tm = t == null ? m.trim_parts[0].t0 : t + this.offset;
      const part = m.trim_parts.find((p) => tm >= p.t0 && tm < p.t1) || (tm < m.trim_parts[0].t0 ? m.trim_parts[0] : m.trim_parts[m.trim_parts.length - 1]);
      return part.trim_db;
    }
    if (m && m.trim_db != null) return m.trim_db;
    const s = String(d.trim_db || "");
    const est = s.match(/estimate\s*(-?\d+(\.\d+)?)/);
    return est ? parseFloat(est[1]) : typeof d.trim_db === "number" ? d.trim_db : 0;
  }

  /** Chip text: "● GUITAR · CHOROBOROS GREEN · LAGRANGE 3RD" / "○ GUITAR · BYPASS" / the MIX form. */
  chipText(t, { d = this.demoAt(t), knobs = null, core = null, bypass = null } = {}) {
    if (!d) return "○ GUITAR · BYPASS";
    bypass = bypass ?? this.bypassAt(t);
    if (bypass) return "○ GUITAR · BYPASS";
    const mix = knobs ? knobs.mix : this.valueIn(d, "mix", t);
    const eng = d.engine.toUpperCase();
    if (t + this.offset < this.chipMixUntil) return `${mix > 0 ? "●" : "○"} GUITAR · CHOROBOROS ${eng} · MIX ${formatReadout("mix", mix)}`;
    const c = (core || this.engines[d.engine].cores[this.hqIn(d, t)] || d.core).toUpperCase();
    return `${mix > 0 ? "●" : "○"} GUITAR · CHOROBOROS ${eng} · ${c}`;
  }

  /**
   * Colour = sound: the plate grade for a plate of `engine` on screen at t. Heard 1 / 1; on screen
   * but not heard 0.35 / 0.75; bypass or Mix 0 (for the demo's own engine) 0.12 / 0.9; during a Mix
   * move s = 0.12 + 0.88 x mix / 40.
   */
  grade(engine, t) {
    const d = this.demoAt(t);
    if (!d || this.bypassAt(t)) return { ...GRADE.off };
    if (engine !== d.engine) return { ...GRADE.notHeard };
    const mix = this.valueIn(d, "mix", t);
    const mixMoves = d._g.some((g) => g.param === "mix");
    if (mix <= 0) return { ...GRADE.off };
    if (mixMoves && mix < 40) {
      const u = clamp(mix / 40);
      return { sat: 0.12 + 0.88 * u, bright: 0.9 + 0.1 * u };
    }
    return { ...GRADE.heard };
  }

  /** Readout with the 60 ms digit flip ({ text, from, progress }), as cues.readoutAt. */
  readoutIn(d, param, t) {
    const fmt = (tt) => formatReadout(param, this.valueIn(d, param, tt));
    const text = fmt(t);
    if (fmt(t - FLIP_S) === text) return { text, from: text, progress: 1 };
    let lo = t - FLIP_S;
    let hi = t;
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      if (fmt(mid) === text) hi = mid;
      else lo = mid;
    }
    return { text, from: fmt(lo), progress: clamp((t - hi) / FLIP_S) };
  }

  /**
   * The plate.setState() shape at t for the demo playing then (or demo `id`, e.g. to show a plate
   * whose engine is not heard with its own values held at the demo's t0 state).
   */
  plateState(t, id = null) {
    const d = id ? this.demoById(id) : this.demoAt(t);
    if (!d) return null;
    const s = { engine: d.engine, switchFrame: this.switchFrameIn(d, t), readouts: {} };
    for (const p of PARAMS) {
      s[p] = this.valueIn(d, p, t);
      s.readouts[p] = this.readoutIn(d, p, t);
    }
    // The plugin's Output Trim (top bar readout): the measured trim, scaled by Mix where it follows Mix.
    const followsMix = (d.gestures || []).some((g) => g.param === "trim" && g.shape === "follows-mix");
    const trimG = this.trimOf(d, t);
    s.trim = followsMix ? (trimG * s.mix) / 40 : trimG;
    return s;
  }

  /** Every state a demo shows over [t0, t1] sampled at `fps` (for plate.require in build()). */
  statesIn(t0, t1, id = null, fps = 240) {
    const out = [];
    const n = Math.max(1, Math.ceil((t1 - t0) * fps));
    for (let i = 0; i <= n; i++) {
      const s = this.plateState(t0 + ((t1 - t0) * i) / n, id);
      if (s) out.push(s);
    }
    return out;
  }

  /** Integrated LFO phase at t (the render starts 3 s before the demo: the audio's pre-roll). */
  cyclesAt(t, id = null) {
    const d = id ? this.demoById(id) : this.demoAt(t);
    if (!d) return 0;
    const pre = 3.0;
    return d.knobs_at_t0.rate_hz * (t + this.offset - (d.t0 - pre));
  }

  /** The gesture running at t: { param, u (0..1), g } or null (click-steps count while ramping). */
  gestureAt(t) {
    const d = this.demoAt(t);
    if (!d) return null;
    const tm = t + this.offset;
    for (const g of d._g) {
      if (g.steps) {
        const ramp = g.ramp_s ?? 0.09;
        for (const s of g.steps) {
          const s0 = this._onset(s.t);
          if (tm >= s0 && tm < s0 + ramp) return { param: g.param, u: (tm - s0) / ramp, g, step: s };
        }
      } else {
        const g0 = this._onset(g.t0);
        const g1 = g0 + (g.t1 - g.t0);
        if (tm >= g0 && tm < g1) return { param: g.param, u: (tm - g0) / (g1 - g0), g };
      }
    }
    return null;
  }

  /** True only when measured.json exists and says the demo passed the level match. */
  levelMatched(id) {
    const m = this._measuredOf(id);
    return !!(m && (m.level_matched === true || m.pass === true || m.level_pass === true));
  }

  /** Settings for chorustype and drift: { rate, depth, offset, width, color, mix, cycles, engine }. */
  settingsAt(t) {
    const st = this.stateAt(t);
    if (!st.demo) return null;
    return { ...st.knobs, mix: st.bypass ? 0 : st.knobs.mix, cycles: this.cyclesAt(t), engine: st.engine, hq: st.hq };
  }
}
