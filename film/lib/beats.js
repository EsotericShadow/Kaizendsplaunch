// The v5 drum clock: the song's bar grid and drum hits as pure functions of time.
//
// Loads film/v5/grid.json and film/v5/hits.json once (setup). After that every call depends only
// on its arguments, so it is safe from render(t) in any seek order.
//
// TIME. Master time = seconds from the first sample of the owner's master (film time = song time).
// A composition can start later in the song (the TikTok): `offset` is the master time of the
// composition's t = 0. Every function here takes and returns COMPOSITION time; hit objects carry
// both (`t` composition, `tm` master).
//
// FRAMES. The renderer draws frame f at t = f / fps. A hit at time h lands on the frame that
// CONTAINS it, frame floor(h * fps): the picture is never later than the sound and at most one
// frame early. `onsetFrame(h)` and `onsetTime(h)` give that frame and its time; every envelope
// below starts at `onsetTime(h)`, so its peak is on the hit frame.

const EPS = 1e-6;

let current = null;

/** The Beats object loaded by the composition (also ctx.beats in every scene). */
export function getBeats() {
  if (!current) throw new Error("beats: loadBeats() has not run");
  return current;
}

export async function loadBeats({ grid = "/film/v5/grid.json", hits = "/film/v5/hits.json", sections = "/film/v5/sections.json", offset = 0, fps = 60 } = {}) {
  const get = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`beats: ${r.status} ${url}`);
    return r.json();
  };
  const [g, h, s] = await Promise.all([get(grid), get(hits), sections ? get(sections) : null]);
  current = new Beats(g, h, s, { offset, fps });
  return current;
}

/** Drum pieces in hits.json. "tom" = rack + floor; "drums" = kick, snare and both toms. */
export const PIECES = ["kick", "snare", "racktom", "floortom", "hihat", "crash", "cymbal"];
const GROUPS = {
  tom: ["racktom", "floortom"],
  toms: ["racktom", "floortom"],
  drums: ["kick", "snare", "racktom", "floortom"],
  shells: ["kick", "snare", "racktom", "floortom"],
  all: PIECES,
};

export class Beats {
  constructor(grid, hits, sections, { offset = 0, fps = 60 } = {}) {
    this.fps = fps;
    this.offset = offset;
    this.bpm = grid.bpm;
    this.period = grid.period_s; // one beat, s
    this.barLen = 4 * grid.period_s; // one bar, s
    this.t0m = grid.t0; // master time of bar 1 beat 1
    this.downbeatsM = grid.downbeats || null;
    this.sections = (sections && sections.sections) || [];
    // Hits: per piece, sorted by master time, each { i, piece, tm, t, db, frame, tf, extra }.
    this.pieces = {};
    for (const p of PIECES) {
      const rows = (hits[p] || []).slice().sort((a, b) => a[0] - b[0]);
      this.pieces[p] = rows.map((r, i) => this._hit(p, i, r));
    }
    this._merged = {};
    this.fills = (hits.fills || []).map((f, i) => ({
      i,
      ...f,
      startM: f.start,
      endM: f.end,
      start: f.start - offset,
      end: f.end - offset,
      hits: this.hitsIn("drums", f.start - offset - 0.002, f.end - offset + 0.002),
    }));
  }

  _hit(piece, i, row) {
    const [tm, db, ...extra] = row;
    const t = tm - this.offset;
    const frame = this.onsetFrame(t);
    return { i, piece, tm, t, db, frame, tf: frame / this.fps, extra };
  }

  // Time conversions ---------------------------------------------------------------------------
  /** Master time of composition time t. */
  master(t) {
    return t + this.offset;
  }
  /** Composition time of master time tm. */
  comp(tm) {
    return tm - this.offset;
  }
  /** The frame on screen at time t (the renderer's rounding of f / fps). */
  frameAt(t) {
    return Math.round(t * this.fps);
  }
  /** The frame that contains time h: where an event at h lands. */
  onsetFrame(h) {
    return Math.floor(h * this.fps + EPS);
  }
  /** Start time of the frame that contains h. */
  onsetTime(h) {
    return this.onsetFrame(h) / this.fps;
  }
  /** Quantize t to its frame time (use before comparing with onset times). */
  q(t) {
    return this.frameAt(t) / this.fps;
  }
  /** True from the frame containing h onwards. */
  after(t, h) {
    return this.frameAt(t) >= this.onsetFrame(h);
  }
  /** Seconds since the frame containing h began (negative before it). Frame-exact. */
  since(t, h) {
    return (this.frameAt(t) - this.onsetFrame(h)) / this.fps;
  }
  /** Whole frames since the frame containing h (negative before). */
  framesSince(t, h) {
    return this.frameAt(t) - this.onsetFrame(h);
  }

  // Grid -----------------------------------------------------------------------------------------
  /** Composition time of the downbeat of bar n (1-based; fractional n allowed). */
  bar(n) {
    return this.t0m + (n - 1) * this.barLen - this.offset;
  }
  /** Composition time of beat k (1-based, fractional allowed: 1.5 = the "and" of 1) of bar n. */
  beat(n, k = 1) {
    return this.bar(n) + (k - 1) * this.period;
  }
  /** Seconds in n beats (durations in the treatment are in beats). */
  beats(n) {
    return n * this.period;
  }
  /** Seconds in n bars. */
  bars(n) {
    return n * this.barLen;
  }
  /** Position at time t: { bar (1-based), beat (1-based, fractional), phase in the bar 0..1 }. */
  pos(t) {
    const x = (t + this.offset - this.t0m) / this.barLen;
    const bar = Math.floor(x) + 1;
    const phase = x - Math.floor(x);
    return { bar, beat: 1 + phase * 4, phase };
  }
  /** Section of the song at t (from sections.json), or null. */
  sectionAt(t) {
    const tm = t + this.offset;
    return this.sections.find((s) => tm >= s.start && tm < s.end) || null;
  }

  // Hits -----------------------------------------------------------------------------------------
  /** Sorted hit list for a piece, a group ("tom", "drums", "all") or an array of pieces. */
  list(piece) {
    if (Array.isArray(piece)) {
      const key = piece.slice().sort().join("+");
      if (!this._merged[key]) this._merged[key] = piece.flatMap((p) => this.list(p)).sort((a, b) => a.t - b.t || a.piece.localeCompare(b.piece));
      return this._merged[key];
    }
    if (GROUPS[piece]) return this.list(GROUPS[piece]);
    const l = this.pieces[piece];
    if (!l) throw new Error(`beats: unknown piece "${piece}"`);
    return l;
  }

  /** Hits with t0 <= t < t1 (composition time, by the hit's exact time). Option minDb. */
  hitsIn(piece, t0, t1, { minDb = -Infinity } = {}) {
    const l = this.list(piece);
    const out = [];
    for (let i = lowerBound(l, t0); i < l.length && l[i].t < t1; i++) if (l[i].db >= minDb) out.push(l[i]);
    return out;
  }

  /** The last hit whose frame has started by time t (frame-exact), or null. */
  lastHit(piece, t, { minDb = -Infinity, within = Infinity } = {}) {
    const l = this.list(piece);
    const f = this.frameAt(t);
    // Hits with frame <= f: every hit with t < (f + 1) / fps.
    let i = lowerBound(l, (f + 1) / this.fps - EPS) - 1;
    for (; i >= 0; i--) {
      const h = l[i];
      if (h.frame > f) continue;
      if ((f - h.frame) / this.fps > within) return null;
      if (h.db >= minDb) return h;
    }
    return null;
  }

  /** The first hit whose frame is after the frame at t, or null. */
  nextHit(piece, t, { minDb = -Infinity } = {}) {
    const l = this.list(piece);
    const f = this.frameAt(t);
    for (let i = lowerBound(l, f / this.fps - 1 / this.fps); i < l.length; i++) if (l[i].frame > f && l[i].db >= minDb) return l[i];
    return null;
  }

  /** The hit nearest to time x within tol seconds (for naming a hit by its approximate time). */
  hitNear(piece, x, tol = 0.03) {
    const l = this.list(piece);
    let best = null;
    for (let i = Math.max(0, lowerBound(l, x - tol)); i < l.length && l[i].t <= x + tol; i++) if (!best || Math.abs(l[i].t - x) < Math.abs(best.t - x)) best = l[i];
    return best;
  }

  /** Index of the hit in `hits` (an array of hits or times) that is current at t (-1 before the first). */
  stepIndex(hits, t) {
    const f = this.frameAt(t);
    let n = -1;
    for (let i = 0; i < hits.length; i++) {
      const h = hits[i];
      const hf = typeof h === "number" ? this.onsetFrame(h) : h.frame;
      if (hf <= f) n = i;
      else break;
    }
    return n;
  }

  // Envelopes -------------------------------------------------------------------------------------
  /**
   * Level weight of a hit: maps its own dB to lo..hi between floorDb and ceilDb (ghost notes are
   * smaller). With refDb = null every hit weighs 1.
   */
  weight(h, { floorDb = null, ceilDb = null, lo = 0.6, hi = 1.0 } = {}) {
    if (floorDb == null || ceilDb == null) return 1;
    const u = Math.min(1, Math.max(0, (h.db - floorDb) / (ceilDb - floorDb)));
    return lo + (hi - lo) * u;
  }

  /**
   * Decaying envelope: sum over hits h (frame started by t) of w(h) * exp(-(t - onsetTime(h)) / tau),
   * clamped to `max`. Peak 1 on the hit frame. Options: minDb, window (s, hits older than
   * window * tau are ignored; default 8 tau), level ({ floorDb, ceilDb, lo, hi } for weight()),
   * max (default 2), attack (frames of linear rise before the peak; default 0 = instant).
   */
  env(piece, t, tau, { minDb = -Infinity, window = 8, level = null, max = 2, attack = 0 } = {}) {
    const f = this.frameAt(t);
    const hits = this.hitsIn(piece, t - window * tau - 1 / this.fps, t + (attack + 1) / this.fps, { minDb });
    let s = 0;
    for (const h of hits) {
      const df = f - h.frame;
      let a;
      if (df < 0) {
        if (df < -attack) continue;
        a = attack > 0 ? 1 + df / (attack + 1) : 0;
      } else {
        a = Math.exp(-(df / this.fps) / tau);
      }
      s += a * (level ? this.weight(h, level) : 1);
    }
    return Math.min(max, s);
  }

  /** Kick punch envelope: 1 on the kick frame, 70 ms decay. */
  kick(t, tau = 0.07, opts = {}) {
    return this.env("kick", t, tau, opts);
  }
  /** Snare envelope: 1 on the snare frame, 90 ms decay. Ghost notes (below -20 dB) ignored. */
  snare(t, tau = 0.09, { minDb = -20, ...opts } = {}) {
    return this.env("snare", t, tau, { minDb, ...opts });
  }
  /** Tom envelope (rack + floor), 80 ms decay. */
  tom(t, tau = 0.08, opts = {}) {
    return this.env("tom", t, tau, opts);
  }
  /** Crash envelope: 1 on the frame of the hit the crash lands with, 60 ms decay. */
  crash(t, tau = 0.06, opts = {}) {
    return this.env("crash", t, tau, opts);
  }

  // Fills --------------------------------------------------------------------------------------------
  /** The fill in progress at t (frame-exact start, inclusive end), or null. */
  fillAt(t) {
    const f = this.frameAt(t);
    return this.fills.find((x) => f >= this.onsetFrame(x.start) && f <= this.onsetFrame(x.end)) || null;
  }
  /** Fills that start in [t0, t1). */
  fillsIn(t0, t1) {
    return this.fills.filter((x) => x.start >= t0 && x.start < t1);
  }
}

function lowerBound(list, t) {
  let lo = 0;
  let hi = list.length;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (list[m].t < t) lo = m + 1;
    else hi = m;
  }
  return lo;
}
