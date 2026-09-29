// STUB: S18 The A/B. Owner: Unit B. Frames 3721 to 4109 (62.0167 to 68.5000 s, master time).
// Spec: film/v5/TREATMENT.md section 2. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "b18-ab",
  t0: 3721 / 60,
  t1: 4110 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
