// Shot 17, 54.00-58.00: Trial. Four plates at 0.40 scale (560x290) in a 2x2 grid: Blue (a) (R03,
// Offset 90 by now) and Red (b) (R10) on top, Black (b) (R09, the Width gesture 100 -> 170% at
// 54.00-55.00) and the white Create canvas below. Each heard plate has a 200 px scope on its outer
// side (GTR, EP, PAD), with its label under the scope on the plate's bottom line; Create, which is
// not heard, has its label in the same place and no scope. The Width ring starts drawing at 53.90,
// so it is complete at the cut.

import { inFrames, fadeIn, setAlpha, sceneGrain, stageBox, hairlineY, plateLabel } from "./kit-late.js";

const T0 = 54.0;
const T1 = 58.0;
const SCALE = 0.4;
const PW = 1400 * SCALE;
const PH = 725 * SCALE;
const SCOPE = 200; // scope diameter
const SIDE = 28; // scope-to-plate gap
const MID = 56; // gap between the two plate columns
const X0 = (1920 - 2 * (SCOPE + SIDE + PW) - MID) / 2;
const COLS = [
  { x: X0 + SCOPE + SIDE, side: -1 }, // left column: scope on the left
  { x: X0 + SCOPE + SIDE + PW + MID, side: 1 }, // right column: scope on the right
];
const ROWS = [244, 578];
const HEAD_BASELINE = 168;
const SUB_BASELINE = 952;
const cell = (c, r) => ({ x: COLS[c].x, y: ROWS[r], side: COLS[c].side });
const PLATES = [
  { engine: "blue", render: "R03", ...cell(0, 0), label: "BLUE", stem: "gtr" },
  { engine: "red", render: "R10", ...cell(1, 0), label: "RED", stem: "ep" },
  { engine: "black", render: "R09", ...cell(0, 1), label: "BLACK", stem: "pad" },
  { engine: "white", render: null, ...cell(1, 1), label: "CREATE", stem: null },
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

    const items = PLATES.map((d) => {
      const plate = lib.createPlate(d.engine, { parent: plateL, scale: SCALE, x: d.x, y: d.y });
      if (d.render) plate.requireRender(cues, d.render, T0, T1);
      else plate.require(CREATE).setState(CREATE);
      const hue = d.engine === "white" ? type.C.fg : type.HUE[d.engine];
      // The outer column beside the plate: the scope, then the label on the plate's bottom line.
      const sx = d.side < 0 ? d.x - SIDE - SCOPE / 2 : d.x + PW + SIDE + SCOPE / 2;
      const label = plateLabel(d.label, { parent: typeL, hue, x: sx, baseline: d.y + PH - 2 });
      const scope = d.stem ? lib.createScope(scopeL, { cx: sx, cy: d.y + 122, size: SCOPE, disc: null, color: type.HUE[d.engine], stem: d.stem }) : null;
      return { ...d, plate, label, scope };
    });
    const black = items.find((i) => i.engine === "black");
    const ring = lib.createRing(ringL);
    const widthGesture = cues.gesture("R09", "width");

    const head = type.headline({ parent: typeL, text: "30-day free trial. ", accent: "No payment card.", size: 84, x: 960, baseline: HEAD_BASELINE, align: "center" });
    const sub = type.body("Unlocks Blue, Red, Black and Create.", { parent: typeL, size: 30, weight: 400, color: type.C.muted, x: 960, baseline: SUB_BASELINE, align: "center" });

    let hair = null;
    return {
      setup() {
        const b = stageBox(head.accent, stage);
        hair = type.offerHairline({
          parent: typeL,
          x: b.x,
          y: hairlineY(head.accent, HEAD_BASELINE),
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
