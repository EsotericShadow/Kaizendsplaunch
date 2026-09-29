// T2 Blue (TREATMENT section 7.2). tau 1.622 to 3.244, frames 97 to 193 (master 125.270 to
// 126.892). Demo T02: Blue Cubic, Offset 0° -> 120° from the snare 125.675 to 126.080.
//
// 125.270 (f97, the empty downbeat): SMEAR (0.25 s, centred) from the whole Red plate to a
//   full-bleed Blue L-MACRO on OFFSET (the knob and its readout); tag "BLUE · CUBIC".
// kick 125.473 (f109): PUNCH and a push step.
// snare 125.675 (f121): "Offset." STAMPs (Fraunces italic 110 px, #79b8ff, baseline 1300); the RING
//   starts; the knob turns (demos.json) and the readout rolls large beside the caption (2.5x).
// kicks 126.081, 126.291 (f145, f157): two PUNCH steps back to the whole plate (1.35x, then the
//   whole plate at 0.77 with the scope inset, 340 px at (740, 760)).
// snares 126.487, 126.689 (f170, f182): WHIP to the WIDTH readout ("100%"), then WHIP back.
// The whole plate SMEARs out over 0.25 s centred on 126.892 into T3's Purple macro.

import { bottomScrim, hit, cl, bigTag, moveCaption, bigReadout, frameDiv, renderWhip, smearAt, PlateSmear, knobAnchor, checkSafe, applyStamp, COLOR, setStyle } from "./t00-common.js";
import { WHOLE } from "./t01-totem-red.js";

export default {
  id: "t02-blue",
  t0: 97 / 60,
  t1: 194 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, lerp, ease, clamp } = lib.util;

    const bar78 = b.bar(78);
    const bar79 = b.bar(79);
    const T0 = b.onsetTime(bar78);
    const T1 = b.onsetTime(bar79);
    this.t0 = T0;
    this.t1 = T1;
    const kStep = hit(b, "kick", 125.473);
    const sCap = cl(b, 125.6755); // snare + hat
    const back = [cl(b, 126.0778), cl(b, 126.2794)]; // hat + kick, twice (f145, f157)
    const wIn = hit(b, "snare", 126.4865);
    const wOut = hit(b, "snare", 126.6892);
    const d = demos.demoById("T02");
    const g0 = b.comp(d._g[0].t0);
    const g1 = b.comp(d._g[0].t1);
    this.events.push(
      { t: b.master(bar78), kind: "cut", hit: "bar 78.1 125.270 (smear to Blue OFFSET)" },
      { t: kStep.tm, kind: "sweep", hit: "kick 125.473 (punch + push step)" },
      { t: sCap.tm, kind: "stamp", hit: "snare 125.675 (Offset.)" },
      { t: sCap.tm, kind: "gesture", hit: "snare 125.675 (Offset 0 -> 120)" },
      ...back.map((h, i) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (step back ${i + 1})` })),
      { t: wIn.tm, kind: "whip", hit: "snare 126.487 (to WIDTH 100%)" },
      { t: wOut.tm, kind: "whip", hit: "snare 126.689 (back)" },
    );

    const PL = ctx.layer("plate", 10);
    const pg = frameDiv(PL);
    const plate = new PlateSmear(pg, lib, "blue", { scale: 2.0, hiRes: true, header: false });
    plate.require(demos.statesIn(T0 - 0.15, T1 + 0.15, "T02", 240));
    const OFF = knobAnchor(lib, "blue", "offset");
    const wg = frameDiv(PL);
    const wmac = lib.createPlate("blue", { parent: wg, scale: 3.0, hiRes: true, header: false });
    wmac.require(demos.plateState(wIn.t, "T02"));

    const SCL = ctx.layer("scope", 14);
    const scope = lib.createScope(SCL, { cx: 740, cy: 760, size: 340, stem: "guitar", color: COLOR.hue.blue, disc: "rgba(5,5,6,0.72)", labelSize: 14 });

    const RL = ctx.layer("ring", 16);
    const ring = lib.createRing(RL, { color: COLOR.lavender, width: 3, factor: 1.12 });

    const TL = ctx.layer("type", 41);
    bottomScrim(TL);
    const tag = bigTag(TL, "BLUE · CUBIC", COLOR.hue.blue);
    const cap = moveCaption(TL, "Offset.", COLOR.hue.blue);
    const big = bigReadout(TL, COLOR.readout.blue, { x: 470 });

    return {
      setup() {
        checkSafe([TL], "T2");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const plateOn = t >= bar78 - 0.125 && t < bar79 + 0.125;
        show(PL, plateOn);
        show(SCL, on && b.after(t, back[1].t));
        show(RL, on);
        show(TL, on);
        if (!plateOn) return;
        const st = demos.plateState(t, "T02");
        plate.setState(st);
        plate.setGrade(demos.grade("blue", t));

        // Framing: the macro (push step on 125.473, punch), then two steps back to the whole plate.
        const kicks = b.hitsIn("kick", T0 - 0.2, T1);
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.macro });
        const s1 = M.sweep(t, [kStep], { frames: 4 });
        const back1 = M.sweep(t, [back[0]], { frames: 4 });
        const back2 = M.sweep(t, [back[1]], { frames: 4 });
        const zMacro = 2.0 * (1 + 0.04 * s1);
        let z;
        let at;
        let on2;
        if (back2 > 0) {
          const u = ease("power2.out", clamp(back2));
          z = lerp(1.35, WHOLE.scale, u);
          on2 = [lerp(OFF[0], 700, u), lerp(OFF[1], lib.plate.BODY_PX_H / 2, u)];
          at = [540, lerp(1000, WHOLE.cy + (lib.plate.HEADER_PX * WHOLE.scale) / 2, u)];
        } else {
          z = lerp(zMacro, 1.35, ease("power2.out", clamp(back1)));
          on2 = OFF;
          at = [540, 1000];
        }
        plate.focus({ on: on2, zoom: z * pu, at });
        const u = t < bar78 + 0.125 ? smearAt(t, bar78) : smearAt(t, bar79);
        plate.render(u ?? 0, u == null ? null : t < bar78 + 0.125 ? "in" : "out");

        // The WIDTH readout whip (f168-f172) and back (f180-f184).
        const inW = b.after(t, wIn.t) && !b.after(t, wOut.t);
        if (b.frameAt(t) >= wIn.frame - 2 && b.frameAt(t) < wOut.frame + 3) {
          wmac.setState(st);
          wmac.setGrade(demos.grade("blue", t));
          wmac.focus({ on: "widthValue", zoom: 3.0, at: [540, 1000] });
          if (!inW) renderWhip(M, t, wOut, wg, pg, { dir: [-1, 0] });
          else renderWhip(M, t, wIn, pg, wg, { dir: [1, 0] });
        } else {
          setStyle(wg, "visibility", "hidden");
          setStyle(pg, "visibility", "");
          setStyle(pg, "transform", "");
          setStyle(pg, "filter", "");
        }
        if (!on) return;

        // Ring on the OFFSET knob while it turns (in 0.1 s before, out 0.3 s after).
        ring.render(t, { t0: g0, t1: g1, rect: inW ? null : plate.centre.controlScreenRect("offset") });
        scope.draw(t, { stem: "guitar", color: COLOR.hue.blue });
        const stc = M.stamp(t, sCap);
        applyStamp(cap, stc);
        setStyle(big.el, "visibility", stc.on ? "" : "hidden");
        if (stc.on) big.render(demos.readoutIn(demos.demoById("T02"), "offset", t));
      },
    };
  },
};
