// S03 Tagline on the hero (TREATMENT section 2, ACT I). Bars 3-4, 3.648 to 6.891 (frames 218-412).
//
// CUT to the 3D hero: the centre of the desktop frames scaled so the frame height fills y 560 to
// 1540, graded to 60 % brightness, grain (kit layer). The scrub steps +6 source frames on each
// kick (easing out over 5 video frames) and creeps between. Floor offbeats: exposure +6 % for 3
// frames. The bar-4 run pushes in 1.00 -> 1.06 -> 1.12 -> 1.18 on 6.076, 6.486, 6.689 (SWEEP).
// PUNCH (plate, x 0.6 in the tom groove) on the kicks. Type: "Great sound" (120 px, baseline 400)
// holds; "doesn’t" STAMPs on the 5.270 kick (104 px, baseline 520).
//
// Hand-off to S04: the hero source frame at the S03 -> S04 cut is HERO_OUT (see render); S04's
// jump cut is +24 source frames from there. 97 frames exist (0-96): S04 should step +3 per kick.

const CREEP = 1.5; // source frames per second between kicks
export const HERO_BASE = 4; // source frame on the S03 cut

export default {
  id: "a03-tagline-hero",
  t0: 3.6485,
  t1: 6.8918,
  events: [],
  async build(ctx) {
    const { lib, beats: b, motion: M } = ctx;
    const { el, show, setStyle } = lib.util;

    const cut = b.hitNear("kick", 3.6485);
    const next = b.hitNear("kick", 6.8918); // S04
    const T0 = cut.tf;
    const T1 = next.tf;
    const kicks = b.hitsIn("kick", cut.t - 0.01, next.t - 0.01);
    const floors = [3.8528, 4.2698, 4.6857, 5.4759].map((x) => b.hitNear("floortom", x));
    const run = [b.hitNear("racktom", 6.0762), b.hitNear("kick", 6.4863), b.hitNear("floortom", 6.6886)];
    const stampHit = b.hitNear("kick", 5.2701);
    this.events.push(
      { t: cut.tm, kind: "cut", hit: "kick + rack 3.648" },
      ...kicks.map((h) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (scrub +6)` })),
      ...floors.map((h) => ({ t: h.tm, kind: "flash", hit: `floor tom ${h.tm} (exposure +6 %)` })),
      ...run.map((h) => ({ t: h.tm, kind: "sweep", hit: `${h.piece} ${h.tm} (push-in)` })),
      { t: stampHit.tm, kind: "stamp", hit: "kick 5.270 (doesn’t)" },
    );

    const L = ctx.layer("hero", 10);
    const hero = lib.createHero(L, { x: 0, y: 560, width: 1080, height: 980 });
    // Soft top and bottom edges so the picture sits in black under the type.
    el("div", { parent: L, style: { position: "absolute", left: "0px", top: "556px", width: "1080px", height: "170px", background: "linear-gradient(#050506, rgba(5,5,6,0))" } });
    el("div", { parent: L, style: { position: "absolute", left: "0px", top: "1380px", width: "1080px", height: "164px", background: "linear-gradient(rgba(5,5,6,0), #050506)" } });

    const TL = ctx.layer("type", 40);
    lib.type.headline({ text: "Great sound", size: 120, parent: TL, x: 72, baseline: 400 });
    const doesnt = lib.type.headline({ text: "doesn’t", size: 104, parent: TL, x: 72, baseline: 520 });
    setStyle(doesnt.el, "transformOrigin", "0% 80%");

    return {
      sequences: [hero.seq],
      render(t) {
        const on = t >= T0 && t < T1;
        show(L, on);
        show(TL, on);
        if (!on) return;
        const f = b.frameAt(t);
        const steps = M.sweep(t, kicks, { frames: 5, easeName: "power2.out" });
        const frame = Math.min(96, HERO_BASE + 6 * steps + CREEP * (t - T0));
        const push = 1 + 0.06 * M.sweep(t, run, { frames: 3 });
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate * M.MOTION.tomGroove });
        const exposure = floors.some((h) => f >= h.frame && f < h.frame + 3) ? 1.06 : 1;
        hero.draw(frame, { scale: push * pu, originX: 0.5, originY: 0.5, grade: { brightness: 0.6 * exposure, contrast: 1.05 } });
        const st = M.stamp(t, stampHit);
        setStyle(doesnt.el, "visibility", st.on ? "" : "hidden");
        setStyle(doesnt.el, "opacity", String(+st.opacity.toFixed(4)));
        setStyle(doesnt.el, "transform", st.scale === 1 ? "" : `scale(${+st.scale.toFixed(5)})`);
      },
    };
  },
};
