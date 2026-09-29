// S05 Meet (TREATMENT section 2, ACT I). Bars 7-8, 10.135 to 13.378 (frames 608 to 801).
//
// kick + rack 10.135: CUT to the whole Green plate at scale 0.66 (924 x 559), centred at x 540,
// y 700 to 1259, lit (colour = sound: Green is heard). It pushes 1.00 -> 1.05 across bars 7 and 8
// (sine.inOut): tension. Kicks PUNCH (plate, x 0.6 in the tom groove).
// The rack-tom accents (10.548, 10.950, 11.553, 12.164) flash the four knob readouts left to right
// (+70 % for 4 frames): S02's readout blink, walking the knob row, one designed event per 2 beats.
// The bar-8 fill: three CUTs to 2x macros, each held to the next hit: Blue OFFSET (snare + floor +
// rack 12.767), Red HQ lever (kick + snare 12.973), Purple COLOR thumb (floor 13.173). Not heard, so
// graded s 0.35 (a preview of the tour), each pushing 1.00 -> 1.03 while it holds.
// Type: the eyebrow "FIRST RELEASE · KAIZEN DSP" (mono 30 px, #b88cff, baseline 300) and "Meet"
// (104 px, baseline 420), both STAMPed on 10.135. This scene owns them to 16.621 (copy deck lines 6
// and 7: they hold through S06), with S06's 2 px type shake on the 13.378 crash.

import { applyStamp, scrim, checkSafe } from "./a00-common.js";

const PLATE = { cx: 540, cy: 700 + (847.02 * 0.66) / 2, scale: 0.66 };
const MACRO_AT = [540, 1010];

export default {
  id: "a05-meet",
  t0: 608 / 60,
  t1: 802 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { el, show, setStyle } = lib.util;
    const { COLOR } = ctx.portrait;

    const cut = b.hitNear("kick", 10.135);
    const next = b.hitNear("kick", 13.3783); // S06
    const typeEnd = b.hitNear("kick", 16.6215); // S07: eyebrow and "Meet" leave
    const T0 = cut.tf;
    const T1 = next.tf;
    this.t0 = T0;
    this.t1 = T1;
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    const racks = [10.5478, 10.9502, 11.5535, 12.1637].map((x) => b.hitNear("racktom", x));
    const fill = [b.hitNear("snare", 12.7668), b.hitNear("kick", 12.9735), b.hitNear("floortom", 13.1732)];
    this.events.push(
      { t: cut.tm, kind: "cut", hit: "kick + rack 10.135 (Green plate)" },
      { t: cut.tm, kind: "stamp", hit: "kick + rack 10.135 (eyebrow, Meet)" },
      ...racks.map((h, i) => ({ t: h.tm, kind: "sweep", hit: `rack ${h.tm} (readout ${["rate", "depth", "offset", "width"][i]})` })),
      { t: fill[0].tm, kind: "cut", hit: "snare + floor + rack 12.767 (Blue OFFSET macro)" },
      { t: fill[1].tm, kind: "cut", hit: "kick + snare 12.973 (Red HQ macro)" },
      { t: fill[2].tm, kind: "cut", hit: "floor 13.173 (Purple COLOR macro)" },
    );

    // The whole Green plate.
    const L = ctx.layer("plate", 10);
    const plate = lib.createPlate("green", { parent: L, scale: PLATE.scale });
    plate.require(demos.statesIn(T0, T1));
    const READ = ["rate", "depth", "offset", "width"];

    // The fill macros (not heard: s 0.35).
    const ML = ctx.layer("macros", 11);
    const macros = [
      { engine: "blue", id: "M02", on: "offset", h: fill[0], until: fill[1] },
      { engine: "red", id: "M03", on: "hq", h: fill[1], until: fill[2] },
      { engine: "purple", id: "M04", on: "color", h: fill[2], until: next, at: [540, 1180] },
    ].map((m) => {
      const box = el("div", { parent: ML, style: { position: "absolute", inset: "0", background: "#050506" } });
      const p = lib.createPlate(m.engine, { parent: box, scale: 2.06, hiRes: true, header: false });
      const st = demos.plateState(m.h.t, m.id);
      p.require(st);
      p.setState(st);
      return { ...m, box, plate: p };
    });
    scrim(ML, { top: 0.85, to: 760 });

    const TL = ctx.layer("type", 40);
    const eb = lib.type.eyebrow("FIRST RELEASE · KAIZEN DSP", { parent: TL, size: 30, color: COLOR.purple, x: 72, baseline: 300 });
    const meet = lib.type.headline({ text: "Meet", size: 104, parent: TL, x: 72, baseline: 420 });
    const block = el("div", { parent: TL, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "72px 420px" } });
    block.appendChild(eb);
    block.appendChild(meet.el);
    const crash = b.hitNear("kick", 13.3783);

    return {
      setup() {
        checkSafe([TL], "S05");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const typeOn = t >= T0 && t < typeEnd.tf;
        show(L, on);
        show(ML, on);
        show(TL, typeOn);
        if (typeOn) {
          const st = M.stamp(t, cut);
          applyStamp(block, st);
          const sh = M.shake(t, [crash], { amp: M.MOTION.shake.type, salt: 9 });
          if (st.scale === 1) setStyle(block, "transform", sh.x || sh.y ? `translate(${lib.util.px(sh.x)}, ${lib.util.px(sh.y)})` : "");
        }
        if (!on) return;

        // The fill macros take over the frame from 12.767.
        const k = b.stepIndex(macros.map((m) => m.h), t);
        macros.forEach((m, i) => setStyle(m.box, "visibility", i === k ? "" : "hidden"));
        if (k >= 0) {
          const m = macros[k];
          const z = 2.0 * M.push(t, m.h.tf, m.until.tf, 1.0, 1.03);
          m.plate.focus({ on: m.on, zoom: z, at: m.at || MACRO_AT });
          m.plate.setGrade(demos.grade(m.engine, t));
          return;
        }

        const push = M.push(t, T0, next.tf, 1.0, 1.05);
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate * M.MOTION.tomGroove });
        plate.place({ cx: PLATE.cx, cy: PLATE.cy, scale: PLATE.scale * push * pu });
        plate.setState(demos.plateState(t));
        plate.setGrade(demos.grade("green", t));
        // Readout walk on the rack accents: +70 % for 4 frames.
        const f = b.frameAt(t);
        racks.forEach((h, i) => {
          const blink = f >= h.frame && f < h.frame + 4;
          setStyle(plate.readouts[READ[i]].node, "filter", blink ? "brightness(1.7)" : "");
        });
      },
    };
  },
};
