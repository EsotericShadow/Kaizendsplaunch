// Shot 2, 2.00-3.00: the MIX turn on the Green rebuild, HQ unlit, 2800 px plate at 2.0x with plate
// point (1100, 560) at screen centre. Ring on MIX from 2.15; MIX frames 149 -> 85 (0% -> 45%,
// sine.inOut on knob position) over 2.25-2.75; saturation follows the knob, 0.15 + 0.85 mix/45%.
const T0 = 2;
const T1 = 3;
const SCALE = 2;
const FOCUS = [1100, 560];

export default {
  id: "shot02-mix-turn",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { lib, cues } = ctx;
    const { util } = lib;
    const plateL = ctx.layer("plate", 10);
    const ringL = ctx.layer("ring", 20);
    const plate = lib.createPlate("green", { parent: plateL, scale: SCALE, x: 960 - FOCUS[0] * SCALE, y: 540 - FOCUS[1] * SCALE, hiRes: true });
    plate.requireRender(cues, "R01", T0, T1);
    const ring = lib.createRing(ringL);
    const gesture = cues.gesture("R01", "mix");
    return {
      render(t) {
        const on = t >= T0 && t < T1;
        util.show(plateL, on);
        util.show(ringL, on);
        if (!on) return;
        const s = cues.plateStateAt("R01", t);
        plate.setState(s);
        const sat = 0.15 + 0.85 * util.clamp(s.mix / 45);
        util.setStyle(plateL, "filter", sat >= 1 ? "" : `saturate(${+sat.toFixed(4)})`);
        ring.renderGesture(t, gesture, plate.controlScreenRect("mix"));
      },
    };
  },
};
