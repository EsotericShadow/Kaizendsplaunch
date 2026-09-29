// S07 Lineup deck (TREATMENT section 2, ACT II). Bars 11-12, 16.621 to 19.864 (frames 997 to 1190).
//
// crash + kick 16.622: CUT to black and the headline "Five prebuilt" / "engines." (104 px,
// baselines 420 and 530, STAMPed; "engines." is chorustype at the heard Green). Five plates SLAM
// onto a deck, scale 0.66, each 12 px lower and 8 px right of the one before: Green (16.622), Blue
// (snare 17.024), Red (snare 17.840), Purple (snare 18.649), Black (snare 19.459). Each drops from
// 40 px above over 6 frames (expo.out) with a SMEAR burst in its own hue and a PUNCH.
// Colour = sound: Green s 1.0, the others s 0.35.
// Each plate PUNCHes on its own landing; the deck PUNCHes (half the plate amount) on the kicks.
// The double kicks (17.433 + 17.634, 19.054 + 19.256) step the deck in, +1 % a step (S06's
// grammar). The snare pickups (19.662, 19.747) SWEEP the deck up 20 px, then 40 px.
// The headline holds through S08 (copy deck line 10: to 23.108); this scene owns it.

import { applyStamp, PlateSmear, checkSafe } from "./a00-common.js";

export const DECK = { x: 62, y: 650, dx: 8, dy: 12, scale: 0.66 };
export const ENGINES = ["green", "blue", "red", "purple", "black"];
export const DEMO_OF = { green: null, blue: "M02", red: "M03", purple: "M04", black: "M05" };
export const PICKUP_STEP = 20;

export default {
  id: "a07-lineup",
  t0: 997 / 60,
  t1: 1191 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, setStyle, el } = lib.util;

    const cut = b.hitNear("kick", 16.6215);
    const lands = [cut, ...[17.0238, 17.8396, 18.6486, 19.4593].map((x) => b.hitNear("snare", x))];
    const doubles = [17.4332, 17.6339, 19.0542, 19.2559].map((x) => b.hitNear("kick", x));
    const pickups = [19.6616, 19.7466].map((x) => b.hitNear("snare", x));
    const next = b.hitNear("kick", 19.8563); // S08: the fan
    const typeEnd = b.hitNear("kick", 23.1083); // S09
    const T0 = cut.tf;
    const T1 = next.tf;
    this.t0 = T0;
    this.t1 = T1;
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    this.events.push(
      { t: cut.tm, kind: "cut", hit: "crash + kick 16.622 (black, headline)" },
      { t: cut.tm, kind: "stamp", hit: "crash + kick 16.622 (Five prebuilt engines.)" },
      ...lands.map((h, i) => ({ t: h.tm, kind: "slam", hit: `${h.piece} ${h.tm} (${ENGINES[i]} plate)` })),
      ...doubles.map((h) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (deck step)` })),
      ...pickups.map((h) => ({ t: h.tm, kind: "sweep", hit: `snare pickup ${h.tm} (deck up)` })),
    );

    const L = ctx.layer("deck", 10);
    const deck = el("div", { parent: L, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "540px 930px" } });
    const plates = ENGINES.map((eng) => {
      const p = new PlateSmear(deck, lib, eng, { scale: DECK.scale });
      p.require(DEMO_OF[eng] ? demos.plateState(T0, DEMO_OF[eng]) : demos.statesIn(T0, T1));
      if (DEMO_OF[eng]) p.setState(demos.plateState(T0, DEMO_OF[eng]));
      return p;
    });

    const TL = ctx.layer("type", 40);
    const head = el("div", { parent: TL, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "72px 450px" } });
    lib.type.headline({ text: "Five prebuilt", size: 104, parent: head, x: 72, baseline: 420 });
    const acc = lib.type.headline({ text: "", accent: "engines.", size: 104, parent: head, x: 72, baseline: 530 });
    const ct = lib.createChorusType(acc.accent, { law: "SINE", engine: "green" });

    return {
      setup() {
        checkSafe([TL], "S07");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const typeOn = t >= T0 && t < typeEnd.tf;
        show(L, on);
        show(TL, typeOn);
        if (typeOn) {
          applyStamp(head, M.stamp(t, cut));
          ct.render(t, demos.settingsAt(t));
        }
        if (!on) return;
        const step = (1 + 0.01 * M.sweep(t, doubles)) * M.punch(t, kicks.filter((k) => k !== cut), { amp: M.MOTION.punch.plate * 0.5 });
        const up = PICKUP_STEP * M.sweep(t, pickups);
        setStyle(deck, "transform", `translate(0px, ${lib.util.px(-up)}) scale(${+step.toFixed(5)})`);
        plates.forEach((p, i) => {
          const h = lands[i];
          const landed = b.after(t, h.t);
          p.show(landed);
          if (!landed) return;
          const sl = M.slam(t, h, { dist: 40, frames: 6, dir: [0, -1], easeName: "expo.out" });
          const pu = M.punch(t, [h], { amp: M.MOTION.punch.plate });
          const x = DECK.x + i * DECK.dx;
          const y = DECK.y + i * DECK.dy + sl.y;
          const w = 1400 * DECK.scale;
          const hgt = 847.02 * DECK.scale;
          p.place({ cx: x + w / 2, cy: y + hgt / 2, scale: DECK.scale * pu });
          if (!DEMO_OF[ENGINES[i]]) p.setState(demos.plateState(t));
          p.setGrade(demos.grade(ENGINES[i], t));
          const u = 0.5 + b.since(t, h.t) / 0.25;
          p.render(u, u < 1 ? "burst" : null);
        });
      },
    };
  },
};
