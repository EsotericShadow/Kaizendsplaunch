// STUB: T6 The totem returns: free, trial, $49.99, format row, inhale (tau 8.108 to 11.352). Owner: Unit A. Frames 486 to 680 (8.1000 to 11.3500 s, composition time; master = t + 123.648).
// Spec: film/v5/TREATMENT.md section 7. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "t06-offer",
  t0: 486 / 60,
  t1: 681 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
