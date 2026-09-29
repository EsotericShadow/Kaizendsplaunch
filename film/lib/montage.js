// MONTAGE (v5): hard-cut plate macros on a list of hits (S02, S19, S22 and the TikTok).
//
//   const m = createMontage(layer, "green", [
//     { h: kick1, on: "rate", zoom: 2.0, at: [540, 1010] },
//     { h: kick2, on: "depth", zoom: 2.0, at: [540, 1010] }, ...], { push: [1.0, 1.03], punchAmp });
//   render(t): const k = m.render(t, demos.plateState(t)); m.plate.setGrade(demos.grade("green", t));
//
// Shot k is on screen from the frame of shots[k].h to the frame before shots[k + 1].h. Each shot
// pushes in over one beat (MACRO PUSH-IN, sine.inOut) and PUNCHes on the kicks inside it. The
// zoom is a plate transform (the plate has no canvas), anchored on the framed control. The plate
// has no top bar unless { header: true } (a macro frames the body).

import { createPlate } from "./plate.js";
import { getBeats } from "./beats.js";
import { punch, push, MOTION } from "./motion.js";

export class Montage {
  constructor(parent, engine, shots, { push: pushRange = [1.0, 1.03], pushBeats = 1, punchAmp = MOTION.punch.macro, punchSrc = "kick", plate = null, state = null, header = false, beats = null } = {}) {
    this.beats = beats || getBeats();
    this.shots = shots.map((s) => ({ ...s, t: typeof s.h === "number" ? s.h : s.h.t }));
    this.push = pushRange;
    this.pushBeats = pushBeats;
    this.punchAmp = punchAmp;
    this.punchSrc = punchSrc;
    const maxZoom = Math.max(...shots.map((s) => s.zoom)) * pushRange[1] * (1 + 2 * punchAmp);
    this.plate = plate || createPlate(engine, { parent, scale: maxZoom, hiRes: true, header, state });
  }

  /** Index of the shot on screen at t (-1 before the first). */
  index(t) {
    return this.beats.stepIndex(this.shots.map((s) => s.t), t);
  }

  /** Frame the shot on screen at t; state (optional) goes to plate.setState. Returns the index. */
  render(t, state = null) {
    const k = this.index(t);
    if (k < 0) return k;
    const s = this.shots[k];
    const b = this.beats;
    const t0 = b.onsetTime(s.t);
    const p = push(t, t0, t0 + b.beats(s.pushBeats ?? this.pushBeats), this.push[0], s.pushTo ?? this.push[1]);
    const next = this.shots[k + 1];
    const kicks = typeof this.punchSrc === "string" ? b.hitsIn(this.punchSrc, s.t - 0.02, next ? next.t - 0.02 : s.t + 10) : this.punchSrc;
    const pu = this.punchAmp > 0 ? punch(t, kicks, { amp: this.punchAmp, beats: b }) : 1;
    this.plate.focus({ on: s.on, zoom: s.zoom * p * pu, at: s.at });
    if (state) this.plate.setState(state);
    return k;
  }
}

export function createMontage(parent, engine, shots, opts) {
  return new Montage(parent, engine, shots, opts);
}
