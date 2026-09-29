// T4 The freeze and the Mix turn in the silence (TREATMENT section 7.2). tau 4.865 to 6.487,
// frames 291 to 388 (master 128.513 to 130.134). Demo T04: Green, Mix 0 % -> 40 % from 129.324 to
// 129.729 (bar 80, beats 3 to 4), in the stop-time silence; Trim follows Mix.
//
// kick + snare 128.513 (f291): FREEZE. CUT to the Green MIX macro, the main film's frame-0
//   composition (the knob about 600 px across, s 0.12, only the "0%" readout in colour, the 3 px
//   lavender ring at 1.12x the knob). All motion stops and the grain freezes (manifest). Only the
//   scope inset moves (the guitar alone, dry). Tag "GREEN · MIX 0%" (#7ee0a0).
// 129.324 (f340, beat 80.3, silence): THE MIX TURN. The knob turns 0 -> 40 % over one beat, the
//   colour floods with the knob (s = 0.12 + 0.88 mix / 40), the ring pulses, the readout rolls
//   "0%" -> "40%" (the plugin's own readout, about 120 px at this zoom), the scope's wet trace
//   blooms. "doesn’t sit still." (italic 110 px, lavender chorustype Green, baseline 420) STAMPs.
//   The tag STAMPs "GREEN · MIX 40%" as the knob lands, 129.729 (beat 80.4: a text event).
// crash + kick 129.932 (f377): the band slams back: FLASH Green (0.30), SHAKE 10 px, WHIP out to
//   the whole Green plate. It SMEARs out over 0.25 s centred on 130.134 into T5's Black.
// The knob sits at (540, 1000) and the scope inset (260 px) at (800, 580), not the main film's
// (540, 1180) and (770, 560): the tag at baseline 1470 and the line at 420 must clear both.

import { scrim, hit, cl, bigTag, frameDiv, renderWhip, smearAt, PlateSmear, ringSvg, checkSafe, applyStamp, COLOR, setStyle } from "./t00-common.js";
import { WHOLE } from "./t01-totem-red.js";

const KNOB_PX = 600;
const KNOB_AT = [540, 1000];
const KNOB_VISIBLE = 0.75; // the knob inside its mix-sheet frame (as S01)
const SCOPE = [800, 580, 260];

export default {
  id: "t04-freeze-mixturn",
  t0: 291 / 60,
  t1: 389 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show } = lib.util;

    const freeze = cl(b, 128.5133); // snare + kick
    const turn = b.beat(80, 3); // 129.324, the guitar alone
    const d = demos.demoById("T04");
    const g = d._g.find((x) => x.param === "mix");
    const g0 = b.comp(g.t0);
    const g1 = b.comp(g.t1);
    const slam = cl(b, 129.9324); // crash + kick
    const bar81 = b.bar(81);
    const T0 = freeze.tf;
    const T1 = b.onsetTime(bar81);
    this.t0 = T0;
    this.t1 = T1;
    this.events.push(
      { t: freeze.tm, kind: "cut", hit: "kick + snare 128.513 (FREEZE: the Green MIX macro)" },
      { t: b.master(turn), kind: "gesture", hit: "beat 80.3 129.324 (the Mix turn, 0 -> 40 %)" },
      { t: b.master(turn), kind: "stamp", hit: "beat 80.3 129.324 (doesn’t sit still.)" },
      { t: g.t1, kind: "stamp", hit: "beat 80.4 129.729 (tag STAMPs GREEN · MIX 40%)" },
      { t: slam.tm, kind: "flash", hit: "crash + kick 129.932 (Green 0.30)" },
      { t: slam.tm, kind: "whip", hit: "crash + kick 129.932 (to the whole plate)" },
    );
    lib.registerFlash({ t: slam.t, peak: 0.3, color: COLOR.fill.green, id: "T4-flash" });

    const PL = ctx.layer("plate", 10);
    const mg = frameDiv(PL);
    const plate = lib.createPlate("green", { parent: mg, scale: 1, hiRes: true, header: false });
    const zoom = KNOB_PX / plate.controlRect("mix").size;
    plate.require(demos.statesIn(T0, slam.t + 0.1, "T04", 240));
    frameDiv(mg, { background: `radial-gradient(circle at ${KNOB_AT[0]}px ${KNOB_AT[1]}px, rgba(5,5,6,0) 0px, rgba(5,5,6,0) 420px, rgba(5,5,6,0.62) 700px, rgba(5,5,6,0.92) 1000px)` });
    scrim(mg, { top: 1, to: 860 });
    const wg = frameDiv(PL);
    const whole = new PlateSmear(wg, lib, "green", { scale: WHOLE.scale });
    whole.require(demos.statesIn(slam.t - 0.1, bar81 + 0.15, "T04", 120));

    const RL = ctx.layer("ring", 12);
    const ring = ringSvg(RL, { color: COLOR.lavender, width: 3 });

    const SL = ctx.layer("scope", 14);
    const scope = lib.createScope(SL, { cx: SCOPE[0], cy: SCOPE[1], size: SCOPE[2], stem: "guitar", color: COLOR.hue.green, disc: "rgba(5,5,6,0.55)", labelSize: 14 });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const TL = ctx.layer("type", 41);
    const tag = bigTag(TL, "GREEN · MIX 0%", COLOR.hue.green);
    tag.style.transformOrigin = "0% 80%";
    // x 74: the wet copies swing 12 px left of the dry line and must stay inside x 60.
    const line = lib.type.headline({ text: "", accent: "doesn’t sit still.", size: 110, parent: TL, x: 74, baseline: 420 });
    line.el.style.transformOrigin = "0% 80%";
    const ct = lib.createChorusType(line.accent, { law: "SINE", engine: "green" });

    return {
      setup() {
        checkSafe([TL], "T4");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const plateOn = t >= T0 && t < bar81 + 0.125;
        show(PL, plateOn);
        show(RL, on);
        show(SL, on);
        show(FL, on);
        show(TL, on);
        if (!plateOn) return;
        const st = demos.plateState(t, "T04");
        const inWhole = renderWhip(M, t, slam, mg, wg, { dir: [1, 0] });
        // The macro: frozen (no punch, no shake) until the band slams back.
        const sh = M.shake(t, [slam], { amp: M.MOTION.shake.amp });
        plate.setState(st);
        plate.focus({ on: "mix", zoom, at: KNOB_AT, dx: sh.x, dy: sh.y });
        plate.setGrade({ ...demos.grade("green", t), keep: ["mix"] });
        if (b.frameAt(t) >= slam.frame - 2) {
          whole.setState(st);
          whole.setGrade(demos.grade("green", t));
          whole.place({ cx: WHOLE.cx, cy: WHOLE.cy, scale: WHOLE.scale * M.punch(t, [slam], { amp: M.MOTION.punch.plate }), dx: sh.x, dy: sh.y });
          const u = smearAt(t, bar81);
          whole.render(u ?? 0, u == null ? null : "out");
        }
        if (!on) return;

        // Ring: steady through the freeze, a pulse over the turn, gone with the whip.
        const r = plate.controlScreenRect("mix");
        let k = 1.12;
        if (t >= g0 && t < g1) k = 1.12 + 0.06 * Math.sin((Math.PI * (t - g0)) / (g1 - g0));
        ring.render({ cx: r.cx, cy: r.cy, d: r.size * KNOB_VISIBLE * k, alpha: inWhole ? 0 : 1 });

        scope.draw(t, { stem: "guitar", color: COLOR.hue.green, zoom: 1.6 });
        flash.render(t, M.flash(t, [slam], { peak: 0.3 }), COLOR.fill.green, lib.flash.flashMode("T4-flash"));

        // The tag holds "0%" through the turn (the plugin's readout rolls) and STAMPs "40%" as the
        // knob lands on beat 80.4.
        const landed = b.after(t, g1);
        const txt = landed ? "GREEN · MIX 40%" : "GREEN · MIX 0%";
        if (tag.textContent !== txt) tag.textContent = txt;
        if (landed) applyStamp(tag, M.stamp(t, g1));
        else {
          setStyle(tag, "transform", "");
          setStyle(tag, "opacity", "");
          setStyle(tag, "visibility", "");
        }
        applyStamp(line.el, M.stamp(t, turn));
        ct.render(t, demos.settingsAt(t));
        setStyle(TL, "transform", sh.x || sh.y ? `translate(${lib.util.px(sh.x / 5)}, ${lib.util.px(sh.y / 5)})` : "");
      },
    };
  },
};
