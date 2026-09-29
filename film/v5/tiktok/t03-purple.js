// STUB: T3 Purple Color (tau 3.244 to 4.865). Owner: Unit A. Frames 194 to 290 (3.2333 to 4.8500 s, composition time; master = t + 123.648).
// Spec: film/v5/TREATMENT.md section 7. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "t03-purple",
  t0: 194 / 60,
  t1: 291 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
