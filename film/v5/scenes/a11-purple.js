// STUB: S11 Purple (tour). Owner: Unit A. Frames 1775 to 1969 (29.5833 to 32.8333 s, master time).
// Spec: film/v5/TREATMENT.md section 2. Replace this stub; keep the id and the file name (the
// manifest already lists it, so neither unit edits the manifest). See film/v5/README.md for the
// scene contract, the kit (ctx.beats, ctx.demos, ctx.motion, lib.*) and the events list.

export default {
  id: "a11-purple",
  t0: 1775 / 60,
  t1: 1970 / 60,
  stub: true,
  events: [], // [{ t: master time of the hit, kind: "cut" | "stamp" | "slam" | "whip" | "sweep" | "flash" | "click" | "gesture" | "text", hit: "kick 12.345" }]
  async build(ctx) {
    return { render() {} };
  },
};
