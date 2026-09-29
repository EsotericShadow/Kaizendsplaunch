// S18 The A/B (TREATMENT section 2, ACT VI). Bars 39-42, 62.026 to 68.513 (frames 3721-4109).
// This module also draws the A/B frame through the first bar of S19 (f4110 to 4194): the ON slam
// on 68.514 and the snare pulses up to the S19 cut on 69.931. Its type ends on f4109; S19 owns
// the type from f4110 and lists those events (b19-settings.js).
//
// Layout: zone T holds the headline and the A/B toggle (film/lib/abtoggle.js, 856 x 96 at x 72,
// y 560). Zone H: the scope, 580 px at (540, 980): the dry band as a 20 % white ghost, the heard
// guitar in Blue while Choroboros is on. Zone S: the Blue plate at 0.58 (x 134 to 946, y 1290 to
// 1781, the lower part under the platform UI, picture only).
// Each slam, on the hit frame (ON 62.027, BYPASS 63.447, ON 65.270, BYPASS 66.688, ON 68.514): the
// toggle slides (3 frames, power3.out); the plate saturation snaps (demos.grade); the wet trace
// appears or vanishes; the wet copies of "guitar." turn on or off; the chip changes (kit); FLASH
// in the new state's hue (Blue 0.30; bypass white 0.12); SHAKE 10 px (type 2 px).
// Between slams: PUNCH (plate) on the kicks; the snares pulse the toggle border +60 % for 6
// frames; the bar-40 fill (64.959, 65.068, 65.169) steps the toggle glow three times (SWEEP).
// Eyebrow: "LEVEL MATCHED · DRUMS UNTOUCHED" only when measured.json says M11 is level matched and
// the drums are untouched (QC-A4); otherwise "A/B ON THE GUITAR BUS".

import { hitAt, inF, ev, fitter, headLine, eyebrowLine, applyStamp, flashBank, vis } from "./b00-common.js";
import { S18_PLATE } from "./b17-trial.js";

const SCOPE = { cx: 540, cy: 980, size: 580 };

/** QC-A4 as the audio build reports it in measured.json (top level or on the M11 entry). */
function drumsUntouched(m, id) {
  if (!m) return false;
  const d = (m.demos && m.demos[id]) || {};
  const v = [m.drums_untouched, m.a4_pass, d.drums_untouched, d.a4_pass, m.qc && m.qc.A4 && m.qc.A4.pass].find((x) => x != null);
  return v === true;
}

export default {
  id: "b18-ab",
  t0: 3721 / 60,
  t1: 4110 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show, setStyle } = lib.util;
    const { COLOR } = P;
    const slams = [
      { h: hitAt(b, 62.0271), on: true },
      { h: hitAt(b, 63.4469), on: false },
      { h: hitAt(b, 65.2703), on: true },
      { h: hitAt(b, 66.688), on: false },
      { h: hitAt(b, 68.5138), on: true }, // S19's ON slam, drawn here
    ];
    const cut19 = hitAt(b, 69.9313); // S19 cuts to the whole plate here
    const F0 = slams[0].h.frame;
    const FT = slams[4].h.frame; // S18's type ends here (f4110)
    const F1 = cut19.frame;
    const fill = [64.959, 65.0678, 65.1695].map((x) => hitAt(b, x, { pieces: ["snare"] }));
    const snares = b.hitsIn("snare", slams[0].h.t, cut19.t - 0.01, { minDb: -20 }).filter((h) => !fill.includes(h));
    const kicks = b.hitsIn("kick", slams[0].h.t - 0.01, cut19.t - 0.01);
    slams.slice(0, 4).forEach((s) => {
      ev(this, b, s.h, "slam", `crash + kick ${s.h.tm} (${s.on ? "ON" : "BYPASS"} slam)`);
      ev(this, b, s.h, "flash", `crash + kick ${s.h.tm} (FLASH ${s.on ? "Blue" : "white"})`);
    });
    ev(this, b, slams[0].h, "stamp", "crash + kick 62.027 (headline, eyebrow)");
    snares.filter((h) => h.frame < FT).forEach((h) => ev(this, b, h, "sweep", `snare ${h.tm} (toggle border pulse)`));
    fill.forEach((h) => ev(this, b, h, "sweep", `snare ${h.tm} (fill: toggle glow step)`));

    const PL = ctx.layer("plate", 12);
    const plate = lib.createPlate("blue", { parent: PL, scale: S18_PLATE.scale, header: true, hiRes: false });
    plate.require(demos.statesIn(slams[0].h.t, cut19.t, "M11", 4));
    const W = plate.width * S18_PLATE.scale;
    const H = plate.height * S18_PLATE.scale;

    const SL = ctx.layer("scope", 14);
    const ghost = lib.createScope(SL, { cx: SCOPE.cx, cy: SCOPE.cy, size: SCOPE.size, stem: "dry", color: "#f6f4ef", disc: "rgba(5,5,6,0.55)", labelSize: 18 });
    const wet = lib.createScope(SL, { cx: SCOPE.cx, cy: SCOPE.cy, size: SCOPE.size, stem: "guitar", color: COLOR.hue.blue, disc: null, outline: null, graticule: false });

    const flashes = flashBank(ctx, lib, slams.map((s) => (s.on ? { h: s.h, color: COLOR.fill.blue, peak: 0.3 } : { h: s.h, color: "#ffffff", peak: 0.12 })));

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const ok = demos.levelMatched("M11-blue-ab") && drumsUntouched(demos.measured, "M11-blue-ab");
    const brow = eyebrowLine(TL, fit, ok ? "LEVEL MATCHED · DRUMS UNTOUCHED" : "A/B ON THE GUITAR BUS", { size: 28, baseline: 294 });
    // 12 px lower than the spec's 380 / 490: at 380 the caps of "A/B" touched the eyebrow.
    const h1 = headLine(TL, fit, { text: "A/B on the", size: 104, baseline: 392 });
    const h2 = headLine(TL, fit, { text: "", accent: "guitar.", size: 104, baseline: 500 });
    const ct = lib.createChorusType(h2.accent, { law: "SINE", engine: "blue" });
    const AL = ctx.layer("toggle", 42);
    const ab = lib.createABToggle(AL, { x: 72, y: 560, w: 856, h: 96, hue: COLOR.hue.blue });

    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [PL, SL, TL, AL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const f = b.frameAt(t);
        const k = slams.filter((s) => s.h.frame <= f).length - 1;
        const cur = slams[k];
        const bypass = demos.bypassAt(t);

        const sh = M.shake(t, slams.map((s) => s.h), { amp: M.MOTION.shake.amp });
        const ts = M.shake(t, slams.map((s) => s.h), { amp: M.MOTION.shake.type, salt: 5 });
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });

        plate.place({ cx: S18_PLATE.x + W / 2, cy: S18_PLATE.y + H / 2, scale: S18_PLATE.scale * pu, dx: sh.x, dy: sh.y });
        plate.setState(demos.plateState(t, "M11"));
        plate.setGrade(demos.grade("blue", t));

        ghost.moveTo(SCOPE.cx + sh.x, SCOPE.cy + sh.y);
        wet.moveTo(SCOPE.cx + sh.x, SCOPE.cy + sh.y);
        ghost.draw(t, { stem: "dry", color: "#f6f4ef", alpha: 0.2, gratAlpha: 5 });
        wet.draw(t, { stem: "guitar", color: COLOR.hue.blue, alpha: bypass ? 0 : 1 });

        // Toggle: slide on the slam, border pulse on the snares, glow steps on the fill.
        const pulse = snares.some((h) => f >= h.frame && f < h.frame + 6) ? 1 : 0;
        const fillSteps = M.sweep(t, fill);
        const glow = f < slams[2].h.frame ? fillSteps / 3 : Math.max(0, 1 - (f - slams[2].h.frame) / 12);
        ab.render(t, { on: !bypass, slamHit: cur.h, pulse, glow: fillSteps > 0 ? glow : 0 });
        setStyle(AL, "transform", ts.x || ts.y ? `translate(${ts.x.toFixed(3)}px, ${ts.y.toFixed(3)}px)` : "");

        // Type (to f4109).
        const typeOn = f < FT;
        show(TL, typeOn);
        if (typeOn) {
          const st = M.stamp(t, slams[0].h);
          for (const n of [brow, h1.el, h2.el]) applyStamp(n, st, { dx: ts.x, dy: ts.y });
          const s = demos.settingsAt(t);
          if (s) ct.render(t, s);
        }
      },
    };
  },
};
