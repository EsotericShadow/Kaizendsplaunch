// STUB: T1 The totem, slot-snap into Red, the HQ flip (tau 0 to 1.622). Owner: Unit A. Frames 0 to 96 (0.0000 to 1.6167 s, composition time; master = t + 123.648).
// Spec: film/v5/TREATMENT.md section 7. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "t01-totem-red",
  t0: 0 / 60,
  t1: 97 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
