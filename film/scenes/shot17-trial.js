// Shot 17, 54.00-58.00: Trial. Four plates at 0.30 scale at x 60, 520, 980, 1440, y 400: Blue (a)
// (R03, Offset 90 by now), Red (b) (R10), Black (b) (R09, the Width gesture 100 -> 170% at
// 54.00-55.00) and the white Create canvas. Mini scopes under Blue, Red and Black read GTR, EP and
// PAD. The Width ring starts drawing at 53.90, so it is complete at the cut.

import { inFrames, fadeIn, setAlpha, sceneGrain, stageBox, hairlineY, plateLabel } from "./kit-late.js";

const T0 = 54.0;
const T1 = 58.0;
const SCALE = 0.3;
const Y = 400;
const PLATES = [
  { engine: "blue", render: "R03", x: 60, label: "BLUE", stem: "gtr" },
  { engine: "red", render: "R10", x: 520, label: "RED", stem: "ep" },
  { engine: "black", render: "R09", x: 980, label: "BLACK", stem: "pad" },
  { engine: "white", render: null, x: 1440, label: "CREATE", stem: null },
];
// Create tile (treatment 8.3): white main knob frame 50 on all four, white mix at 12 o'clock,
// switch lit, readout windows empty, no thumb.
const CREATE = { engine: "white", rate: 1, depth: 50, offset: 90, width: 100, mix: 50, switchFrame: 0 };

export default {
  id: "shot17-trial",
  t0: T0,
  t1: T1,
  async build(ctx) {
    const { lib, cues, stage } = ctx;
    const { type, util } = lib;
    const { show } = util;

    const plateL = ctx.layer("plates", 20);
    const ringL = ctx.layer("ring", 25);
    const scopeL = ctx.layer("scopes", 30);
    const typeL = ctx.layer("type", 40);
    const { layer: grainL, grain } = sceneGrain(ctx, lib);
    const layers = [plateL, ringL, scopeL, typeL, grainL];

    const W = 1400 * SCALE;
    const items = PLATES.map((d) => {
      const cx = d.x + W / 2;
      const plate = lib.createPlate(d.engine, { parent: plateL, scale: SCALE, x: d.x, y: Y });
      if (d.render) plate.requireRender(cues, d.render, T0, T1);
      else plate.require(CREATE).setState(CREATE);
      const hue = d.engine === "white" ? type.C.fg : type.HUE[d.engine];
      const label = plateLabel(d.label, { parent: typeL, hue, x: cx, baseline: 660 });
      const scope = d.stem ? lib.createScope(scopeL, { cx, cy: 750, size: 120, disc: null, color: type.HUE[d.engine], stem: d.stem }) : null;
      return { ...d, plate, label, scope };
    });
    const black = items.find((i) => i.engine === "black");
    const ring = lib.createRing(ringL);
    const widthGesture = cues.gesture("R09", "width");

    const head = type.headline({ parent: typeL, text: "30-day free trial. ", accent: "No payment card.", size: 84, x: 960, baseline: 210, align: "center" });
    const sub = type.body("Unlocks Blue, Red, Black and Create.", { parent: typeL, size: 30, weight: 400, color: type.C.muted, x: 960, baseline: 900, align: "center" });

    let hair = null;
    return {
      setup() {
        const b = stageBox(head.accent, stage);
        hair = type.offerHairline({
          parent: typeL,
          x: b.x,
          y: hairlineY(head.accent, 210),
          width: b.w,
          strands: [{ engine: "blue" }, { engine: "red" }, { engine: "black" }],
        });
      },
      render(t) {
        const on = inFrames(t, T0, T1);
        for (const L of layers) show(L, on);
        if (!on) return;
        for (const it of items) {
          if (!it.render) continue;
          const s = cues.plateStateAt(it.render, t);
          it.plate.place({ dx: lib.driftPx(s) });
          it.plate.setState(s);
          it.scope.draw(t, { stem: it.stem, render: it.render });
        }
        ring.renderGesture(t, widthGesture, black.plate.controlScreenRect("width"));
        setAlpha(head.el, 1);
        setAlpha(sub, fadeIn(t, 54.75));
        hair.render(t, [cues.cyclesAt("R03", t), cues.cyclesAt("R10", t), cues.cyclesAt("R09", t)]);
        grain.render(t);
      },
    };
  },
};
