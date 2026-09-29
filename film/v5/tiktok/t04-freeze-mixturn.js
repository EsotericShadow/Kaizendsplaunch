// STUB: T4 FREEZE and the Mix turn in the silence (tau 4.865 to 6.487). Owner: Unit A. Frames 291 to 388 (4.8500 to 6.4833 s, composition time; master = t + 123.648).
// Spec: film/v5/TREATMENT.md section 7. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "t04-freeze-mixturn",
  t0: 291 / 60,
  t1: 389 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
