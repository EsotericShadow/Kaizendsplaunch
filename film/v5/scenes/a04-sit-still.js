// S04 "sit still." (TREATMENT section 2, ACT I). Bars 5-6, 6.891 to 10.135 (frames 413 to 607).
//
// kick + rack 6.892: "sit still." STAMPs as chorustype (Fraunces italic 400, 120 px, lavender,
// Green wet copies at the heard settings) and the hero JUMP-CUTS +24 source frames.
// Bar 5: the scrub steps +3 source frames on each kick (S03's grammar at half the step, so the 97
// frames last), PUNCH (plate, x 0.6 in the tom groove).
// Bar 6 (8.513 to 10.135) is a designed HOLD: nothing new appears, the scrub only creeps and the
// PUNCH amplitude is x 0.6 again. The space before the title.
// Type: "Great sound" / "doesn’t" / "sit still." at baselines 400, 520, 650.

import { HERO_BASE } from "./a03-tagline-hero.js";
import { applyStamp, checkSafe } from "./a00-common.js";

const CREEP = 1.5; // source frames per second (as S03)
const JUMP = 24; // the jump cut on 6.892
const STEP = 3; // source frames per bar-5 kick

export default {
  id: "a04-sit-still",
  t0: 413 / 60,
  t1: 608 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { el, show } = lib.util;

    const cut3 = b.hitNear("kick", 3.6485); // S03's cut: the scrub starts there
    const cut = b.hitNear("kick", 6.8918); // kick + rack, f413
    const next = b.hitNear("kick", 10.135); // S05
    const T0 = cut.tf;
    const T1 = next.tf;
    this.t0 = T0;
    this.t1 = T1;
    const bar6 = b.bar(6);
    // Where S03 left the scrub (its formula at its last frame): HERO_BASE + 6 per kick + creep.
    const k3 = b.hitsIn("kick", cut3.t - 0.01, cut.t - 0.01);
    const heroOut = HERO_BASE + 6 * k3.length + CREEP * (T0 - cut3.tf);
    const k5 = b.hitsIn("kick", cut.t + 0.01, bar6 - 0.01); // 7.297, 7.703, 8.110
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    this.events.push(
      { t: cut.tm, kind: "stamp", hit: "kick + rack 6.892 (sit still.)" },
      { t: cut.tm, kind: "cut", hit: "kick + rack 6.892 (hero jump +24)" },
      ...k5.map((h) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (scrub +3)` })),
    );

    const L = ctx.layer("hero", 10);
    const hero = lib.createHero(L, { x: 0, y: 560, width: 1080, height: 980 });
    el("div", { parent: L, style: { position: "absolute", left: "0px", top: "556px", width: "1080px", height: "220px", background: "linear-gradient(#050506 20%, rgba(5,5,6,0))" } });
    el("div", { parent: L, style: { position: "absolute", left: "0px", top: "1380px", width: "1080px", height: "164px", background: "linear-gradient(rgba(5,5,6,0), #050506)" } });

    const TL = ctx.layer("type", 40);
    lib.type.headline({ text: "Great sound", size: 120, parent: TL, x: 72, baseline: 400 });
    lib.type.headline({ text: "doesn’t", size: 104, parent: TL, x: 72, baseline: 520 });
    // x 74: the wet copies swing 13 px left of the dry word and must stay inside x 60.
    const sit = lib.type.headline({ text: "", accent: "sit still.", size: 120, parent: TL, x: 74, baseline: 650 });
    sit.el.style.transformOrigin = "0% 80%";
    const ct = lib.createChorusType(sit.accent, { law: "SINE", engine: "green" });

    return {
      sequences: [hero.seq],
      setup() {
        checkSafe([TL], "S04");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        show(L, on);
        show(TL, on);
        if (!on) return;
        const steps = M.sweep(t, k5, { frames: 5, easeName: "power2.out" });
        const frame = Math.min(96, heroOut + JUMP + STEP * steps + CREEP * (t - T0));
        const hold = b.after(t, bar6) ? 0.6 : 1; // bar 6: the designed hold
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate * M.MOTION.tomGroove * hold });
        hero.draw(frame, { scale: pu, originX: 0.5, originY: 0.5, grade: { brightness: 0.6, contrast: 1.05 } });
        applyStamp(sit.el, M.stamp(t, cut));
        ct.render(t, demos.settingsAt(t));
      },
    };
  },
};
