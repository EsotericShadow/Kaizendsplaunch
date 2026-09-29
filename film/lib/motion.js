// The v5 motion primitives: every hit-driven move of the portrait film as a pure function of t.
//
// Each primitive takes the composition time t and the hits (or times) that drive it, and returns
// numbers (scale, offsets, opacity). Scenes apply them with transforms on non-canvas layers (a
// canvas never sits inside a changing scale: scale inside its draw call instead).
//
// Onsets are frame-exact (see beats.js): an event at time h peaks on frame floor(h * fps).
// Durations are given in FRAMES (at 60 fps) or BEATS (beats.beats(n) seconds), as the treatment
// states them. Nothing reads the previous frame, the wall clock or Math.random.

import { getBeats } from "./beats.js";
import { clamp, lerp, ease, EASES } from "./util.js";

// Extra eases the treatment uses (gsap formulas).
EASES["power3.out"] = (u) => 1 - Math.pow(1 - u, 4);
EASES["power3.in"] = (u) => u * u * u * u;
EASES["power4.out"] = (u) => 1 - Math.pow(1 - u, 5);
EASES["expo.in"] = (u) => (u <= 0 ? 0 : Math.pow(2, 10 * u - 10));
EASES["expo.inOut"] = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u < 0.5 ? Math.pow(2, 20 * u - 10) / 2 : (2 - Math.pow(2, -20 * u + 10)) / 2);
EASES["back.out"] = (u) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2);
};

/** The default motion constants. Scenes pass overrides; the treatment's values live here. */
export const MOTION = {
  fps: 60,
  punch: { tau: 0.07, plate: 0.03, macro: 0.045, type: 0.012 },
  shake: { tau: 0.12, amp: 10, first: 14, type: 2 },
  stamp: { from: 1.18, frames: 5, overshoot: 1.02, fadeFrames: 2, ease: "power3.out" },
  whip: { frames: 5, dist: 180, copies: [0.5, 0.3, 0.18, 0.1, 0.06, 0.03] },
  sweep: { frames: 3, ease: "power2.out" },
  flash: { peak: 0.3, tau: 0.06, white: 0.45, first: [0.45, 0.2, 0.06], stop: [0.45, 0.15] },
  slam: { dist: 160, frames: 6, ease: "power4.out" },
  inhale: { scales: [0.97, 0.95], frames: 4, ease: "power2.out", overshoot: 1.01 },
  clickStop: { frames: 5, ease: "sine.inOut" },
  tomGroove: 0.6, // PUNCH amp factor in the tom grooves (bars 1-8 and 23-30)
  push: { ease: "sine.inOut" },
};

const B = (beats) => beats || getBeats();
const hitsOf = (beats, src, t, span) => {
  if (Array.isArray(src)) return src;
  if (typeof src === "string") return beats.hitsIn(src, t - span, t + 1 / beats.fps);
  return [src];
};
const frameOfHit = (beats, h) => (typeof h === "number" ? beats.onsetFrame(h) : h.frame);

/**
 * PUNCH: a scale jump on each hit that decays exponentially.
 * src: a piece name ("kick"), an array of hits / times, or one hit / time.
 * Returns the scale, 1 + amp * env, never above 1 + 2 * amp.
 */
export function punch(t, src = "kick", { amp = MOTION.punch.macro, tau = MOTION.punch.tau, minDb = -Infinity, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  let e = 0;
  for (const h of hitsOf(b, src, t, 8 * tau)) {
    if (typeof h !== "number" && h.db < minDb) continue;
    const df = f - frameOfHit(b, h);
    if (df >= 0) e += Math.exp(-df / b.fps / tau);
  }
  return 1 + amp * Math.min(2, e);
}

/** Integer hash to [-1, 1]. */
export function hash11(a, b = 0, salt = 0) {
  let n = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(salt | 0, 2246822519)) >>> 0;
  n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
  return (((n ^ (n >>> 16)) >>> 0) / 4294967296) * 2 - 1;
}

/**
 * SHAKE: a decaying jitter after each hit. The direction is hash noise of (hit index, frame), so
 * it is the same on every render. Returns { x, y } in px.
 */
export function shake(t, src = "crash", { amp = MOTION.shake.amp, tau = MOTION.shake.tau, salt = 0, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  let x = 0;
  let y = 0;
  const hits = hitsOf(b, src, t, 8 * tau);
  hits.forEach((h, k) => {
    const hf = frameOfHit(b, h);
    const df = f - hf;
    if (df < 0) return;
    const a = (typeof h === "object" && h.amp != null ? h.amp : amp) * Math.exp(-df / b.fps / tau);
    const id = typeof h === "number" ? hf : h.i * 7 + hf;
    x += a * hash11(id, f, salt + 1);
    y += a * hash11(id, f, salt + 2);
  });
  return { x, y };
}

/**
 * STAMP: an element lands big and settles. Scale from `from` to 1 over `frames` (power3.out),
 * `overshoot` on the next frame, 1 after. Opacity 0 -> 1 over fadeFrames. Before h: hidden.
 * Returns { scale, opacity, on }.
 */
export function stamp(t, h, { from = MOTION.stamp.from, frames = MOTION.stamp.frames, overshoot = MOTION.stamp.overshoot, fadeFrames = MOTION.stamp.fadeFrames, easeName = MOTION.stamp.ease, beats = null } = {}) {
  const b = B(beats);
  const df = b.frameAt(t) - frameOfHit(b, h);
  if (df < 0) return { scale: from, opacity: 0, on: false };
  let scale;
  if (df < frames) scale = lerp(from, 1, ease(easeName, df / frames));
  else if (df === frames) scale = overshoot;
  else scale = 1;
  const opacity = fadeFrames > 0 ? clamp((df + 1) / fadeFrames) : 1;
  return { scale, opacity, on: true };
}

/**
 * WHIP: a fast directional move between two shots, centred on h (the cut lands on the hit frame).
 * Over `frames` frames the outgoing layer moves `dist` px along dir and the incoming arrives from
 * -dir. Returns { active, u (0..1), cut (true from the hit frame: show the incoming shot),
 * outX, outY, inX, inY, copies: [{ dx, dy, alpha }] } for a copy-stack blur (no CSS blur on
 * canvases). dir: [1, 0] = right.
 */
export function whip(t, h, { frames = MOTION.whip.frames, dist = MOTION.whip.dist, dir = [1, 0], copies = MOTION.whip.copies, beats = null } = {}) {
  const b = B(beats);
  const hf = frameOfHit(b, h);
  const half = Math.floor(frames / 2);
  const df = b.frameAt(t) - (hf - half);
  const cut = b.frameAt(t) >= hf;
  if (df < 0 || df >= frames) return { active: false, u: df < 0 ? 0 : 1, cut, outX: 0, outY: 0, inX: 0, inY: 0, copies: [] };
  const u = (df + 1) / frames;
  const m = Math.sin(Math.PI * u); // blur amount, peaks mid-whip
  const outU = ease("power2.in", clamp(u * 2));
  const inU = ease("power2.out", clamp(u * 2 - 1));
  const outX = dir[0] * dist * outU;
  const outY = dir[1] * dist * outU;
  const inX = -dir[0] * dist * (1 - inU);
  const inY = -dir[1] * dist * (1 - inU);
  const step = (dist / copies.length) * 0.5 * m;
  const cs = copies.map((a, k) => ({ dx: -dir[0] * step * (k + 1), dy: -dir[1] * step * (k + 1), alpha: a * m }));
  return { active: true, u, cut, outX, outY, inX, inY, copies: cs };
}

/**
 * SWEEP / SEQUENCE: one step per hit, each easing out over `frames`. Returns the (fractional)
 * number of steps taken by t: multiply by the step size for a position, or floor it for an index.
 */
export function sweep(t, hits, { frames = MOTION.sweep.frames, easeName = MOTION.sweep.ease, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  let s = 0;
  for (const h of hits) {
    const df = f - frameOfHit(b, h);
    if (df < 0) break;
    s += df >= frames ? 1 : ease(easeName, (df + 1) / frames);
  }
  return s;
}

/**
 * FLASH: a full-frame additive layer. Either a decay (peak * exp(-dt / tau)) summed over hits and
 * clamped to peak, or explicit per-frame values (frames: [0.6, 0.25, 0.08]) after one hit.
 * Returns the layer opacity.
 */
export function flash(t, src = "crash", { peak = MOTION.flash.peak, tau = MOTION.flash.tau, frames = null, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  const hits = hitsOf(b, src, t, 8 * tau + (frames ? frames.length / b.fps : 0));
  let a = 0;
  for (const h of hits) {
    const df = f - frameOfHit(b, h);
    if (df < 0) continue;
    if (frames) a = Math.max(a, df < frames.length ? frames[df] : 0);
    else a += peak * Math.exp(-df / b.fps / tau);
  }
  return Math.min(frames ? 1 : peak, a);
}

/**
 * PUSH: a macro push-in (or any slow camera move) from t0 to t1: returns the eased value from a
 * to b (holds a before, b after). Times are exact (quantized to frames by the caller's t).
 */
export function push(t, t0, t1, a = 1, bVal = 1.03, easeName = MOTION.push.ease) {
  if (t <= t0) return a;
  if (t >= t1) return bVal;
  return lerp(a, bVal, ease(easeName, (t - t0) / (t1 - t0)));
}

/**
 * CUT: the index of the shot on screen at t, for a list of cut hits/times (shot k starts on the
 * frame of cuts[k]; -1 before the first).
 */
export function cut(t, cuts, { beats = null } = {}) {
  return B(beats).stepIndex(cuts, t);
}

/**
 * STEP: a stepped value that moves on each hit (a click-stop knob turn): values[k] is reached
 * `frames` frames after hit k (eased), values[0] before the first hit. Returns the value.
 */
export function steps(t, hits, values, { frames = MOTION.clickStop.frames, easeName = MOTION.clickStop.ease, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  let v = values[0];
  for (let k = 0; k < hits.length && k + 1 < values.length; k++) {
    const df = f - frameOfHit(b, hits[k]);
    if (df < 0) break;
    v = df >= frames ? values[k + 1] : lerp(values[k], values[k + 1], ease(easeName, df / frames));
  }
  return v;
}

/**
 * SLAM: an entrance from `dist` px away along dir to 0 over `frames` (power4.out), starting on the
 * hit frame. Returns { x, y, on, done }; follow it with a punch(t, [h], { amp: MOTION.punch.plate }).
 */
export function slam(t, h, { dist = MOTION.slam.dist, frames = MOTION.slam.frames, dir = [0, 1], easeName = MOTION.slam.ease, beats = null } = {}) {
  const b = B(beats);
  const df = b.frameAt(t) - frameOfHit(b, h);
  if (df < 0) return { x: dir[0] * dist, y: dir[1] * dist, on: false, done: false };
  const k = df >= frames ? 0 : 1 - ease(easeName, df / frames);
  return { x: dir[0] * dist * k, y: dir[1] * dist * k, on: true, done: df >= frames };
}

/**
 * INHALE: the frame scale before a stop. On each of the pre-hits the scale eases to the next value
 * of `scales` over `frames` (power2.out); on the stop hit it releases to 1 with a one-frame
 * `overshoot`. Returns the scale.
 */
export function inhale(t, preHits, stopHit, { scales = MOTION.inhale.scales, frames = MOTION.inhale.frames, easeName = MOTION.inhale.ease, overshoot = MOTION.inhale.overshoot, beats = null } = {}) {
  const b = B(beats);
  const f = b.frameAt(t);
  const fs = frameOfHit(b, stopHit);
  if (f >= fs) return f === fs ? overshoot : 1;
  let s = 1;
  preHits.forEach((h, k) => {
    const df = f - frameOfHit(b, h);
    if (df < 0) return;
    const from = k === 0 ? 1 : scales[k - 1];
    s = df >= frames ? scales[k] : lerp(from, scales[k], ease(easeName, df / frames));
  });
  return s;
}

/** CSS transform string for a layer: translate then scale about its transform origin. */
export function transform({ x = 0, y = 0, scale = 1, rotate = 0 } = {}) {
  const r = (v) => Math.round(v * 1000) / 1000;
  let s = `translate(${r(x)}px, ${r(y)}px)`;
  if (scale !== 1) s += ` scale(${Math.round(scale * 1e5) / 1e5})`;
  if (rotate) s += ` rotate(${r(rotate)}deg)`;
  return s;
}
