// STUB: S20 Price. Owner: Unit B. Frames 4305 to 4693 (71.7500 to 78.2333 s, master time).
// Spec: film/v5/TREATMENT.md section 2. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "b20-price",
  t0: 4305 / 60,
  t1: 4694 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
