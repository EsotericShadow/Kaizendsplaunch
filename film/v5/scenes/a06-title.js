// S06 Title slam (TREATMENT section 2, ACT II). Bars 9-10, 13.378 to 16.621 (frames 802 to 996).
//
// crash + kick 13.378 (f802): CUT back to the whole Green plate (0.66, as S05), FLASH Green (0.30),
// SHAKE 10 px (type 2 px, in S05's type layer), a SMEAR burst on the plate (the peak on the hit
// frame, clear in 0.125 s), and "Choroboros." lands as chorustype (150 px italic, lavender, Green
// wet copies at the heard settings), baseline 580. The dek STAMPs on the snare 13.780.
// Kicks PUNCH (plate). Snares spread the chorustype's wet copies +30 % and relax over 150 ms.
// The double kicks (14.190 + 14.390, 15.812 + 16.012) SWEEP the plate in, +1.5 % a step.
// crash + kick 14.796 (f887): FLASH Green (0.30).
// "Meet" and the eyebrow hold (owned by a05-meet.js to 16.621).

import { applyStamp, PlateSmear, checkSafe } from "./a00-common.js";

const PLATE = { cx: 540, cy: 700 + (847.02 * 0.66) / 2, scale: 0.66 };

export default {
  id: "a06-title",
  t0: 802 / 60,
  t1: 997 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, setStyle } = lib.util;
    const { COLOR } = ctx.portrait;

    const cut = b.hitNear("kick", 13.3783);
    const crash2 = b.hitNear("kick", 14.796);
    const dekHit = b.hitNear("snare", 13.7803);
    const next = b.hitNear("kick", 16.6215); // S07
    const T0 = cut.tf;
    const T1 = next.tf;
    this.t0 = T0;
    this.t1 = T1;
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    const snares = b.hitsIn("snare", cut.t - 0.01, next.t - 0.01);
    const doubles = [14.1895, 14.3904, 15.8119, 16.0123].map((x) => b.hitNear("kick", x));
    this.events.push(
      { t: cut.tm, kind: "cut", hit: "crash + kick 13.378 (Green plate)" },
      { t: cut.tm, kind: "flash", hit: "crash + kick 13.378 (Green 0.30)" },
      { t: cut.tm, kind: "stamp", hit: "crash + kick 13.378 (Choroboros.)" },
      { t: dekHit.tm, kind: "stamp", hit: "snare 13.780 (dek)" },
      ...snares.filter((h) => h !== dekHit).map((h) => ({ t: h.tm, kind: "sweep", hit: `snare ${h.tm} (wet copies spread)` })),
      ...doubles.map((h) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (plate push step)` })),
      { t: crash2.tm, kind: "flash", hit: "crash + kick 14.796 (Green 0.30)" },
    );
    lib.registerFlash({ t: cut.t, peak: 0.3, color: COLOR.fill.green, id: "S06-a" });
    lib.registerFlash({ t: crash2.t, peak: 0.3, color: COLOR.fill.green, id: "S06-b" });

    const L = ctx.layer("plate", 10);
    const plate = new PlateSmear(L, lib, "green", { scale: PLATE.scale });
    plate.require(demos.statesIn(T0, T1));

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const TL = ctx.layer("type", 40);
    const title = lib.type.headline({ text: "", accent: "Choroboros.", size: 150, parent: TL, x: 72, baseline: 580 });
    title.el.style.transformOrigin = "0% 80%";
    const ct = lib.createChorusType(title.accent, { law: "SINE", engine: "green" });
    const dek = lib.util.el("div", { parent: TL, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "72px 1330px" } });
    lib.type.body("A chorus and modulation plugin", { parent: dek, size: 44, weight: 500, color: COLOR.muted, x: 72, baseline: 1330 });
    lib.type.body("for macOS.", { parent: dek, size: 44, weight: 500, color: COLOR.muted, x: 72, baseline: 1386 });

    return {
      setup() {
        checkSafe([TL], "S06");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        for (const l of [L, FL, TL]) show(l, on);
        if (!on) return;
        const f = b.frameAt(t);

        // Plate: SHAKE on the slam, PUNCH on the kicks, the double-kick push steps, the burst.
        const sh = M.shake(t, [cut], { amp: M.MOTION.shake.amp });
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });
        const stepIn = 1 + 0.015 * M.sweep(t, doubles);
        plate.place({ cx: PLATE.cx, cy: PLATE.cy, scale: PLATE.scale * pu * stepIn, dx: sh.x, dy: sh.y });
        plate.setState(demos.plateState(t));
        plate.setGrade(demos.grade("green", t));
        const u = 0.5 + b.since(t, cut.t) / 0.25; // peak on the hit frame, clear after 0.125 s
        plate.render(u, u < 1 ? "burst" : null);

        // FLASH Green on the two crashes (the PSE limiter may turn one into an edge glow).
        const a1 = M.flash(t, [cut], { peak: 0.3 });
        const a2 = M.flash(t, [crash2], { peak: 0.3 });
        if (a2 > a1) flash.render(t, a2, COLOR.fill.green, lib.flash.flashMode("S06-b"));
        else flash.render(t, a1, COLOR.fill.green, lib.flash.flashMode("S06-a"));

        // Type: the title lands on the slam; the snares spread its wet copies +30 % (150 ms).
        const ts = M.shake(t, [cut], { amp: M.MOTION.shake.type, salt: 9 });
        const st = M.stamp(t, cut);
        applyStamp(title.el, st);
        if (st.scale === 1) setStyle(title.el, "transform", `translate(${lib.util.px(ts.x)}, ${lib.util.px(ts.y)})`);
        let spread = 0;
        for (const h of snares) {
          const df = (f - h.frame) / 60;
          if (df >= 0 && df < 0.15) spread = Math.max(spread, 1 - df / 0.15);
        }
        const s = demos.settingsAt(t);
        ct.render(t, { ...s, depth: s.depth * (1 + 0.3 * spread * spread) });
        applyStamp(dek, M.stamp(t, dekHit));
      },
    };
  },
};
