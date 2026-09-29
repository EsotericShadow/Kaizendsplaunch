// STUB: T2 Blue Offset (tau 1.622 to 3.244). Owner: Unit A. Frames 97 to 193 (1.6167 to 3.2333 s, composition time; master = t + 123.648).
// Spec: film/v5/TREATMENT.md section 7. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "t02-blue",
  t0: 97 / 60,
  t1: 194 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
