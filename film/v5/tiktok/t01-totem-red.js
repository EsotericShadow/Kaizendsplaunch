// T1 The totem, the slot-snap into Red, the HQ flip (TREATMENT section 7.1 and 7.2). tau 0 to
// 1.622, frames 0 to 96 (master 123.648 to 125.270). Demo T01: Red, BBD -> Tape on the snare 124.865.
//
// f0 THE TOTEM (a poster; the one colour = sound exception): on black, the eyebrow "CHOROBOROS"
//   (mono 30 px, #b88cff, baseline 290), "One riff." (Fraunces 600, 128 px, baseline 430) and
//   "Five engines." (italic 400, 128 px, lavender, baseline 560). Below, five knob-row strips edge
//   to edge (1080 x 220, y 600 to 1700: Green, Blue, Red, Purple, Black, each its plate at 0.77, all
//   in full colour); Red (heard from the first sample) at +15 % exposure with a 3 px #ff776d rim.
//   Tags (mono 30 px, engine hue) at baselines 636, 856, 1076, 1296, 1516. Nothing moves on f0.
// f1-f10 SLOT-SNAP (power4.out): the Red strip expands to the full 1920 px, the others are pushed
//   off-frame and desaturate as they go, SHAKE 14 px, a black scrim fades in behind the headline.
// f11 full-bleed Red L-MACRO on RATE and DEPTH ("0.62 Hz", "30%"); tag "RED · BBD" (mono 56 px,
//   #ff8a80, baseline 1470); the headline shrinks to 86 px (baselines 330 and 420).
// snare 124.055 (f24): CUT to the HQ lever macro (2.0x) at BBD; the pill "BBD · TAPE" (Inter 600
//   34 px, y 1322 to 1402: 18 px above the spec box so it clears the tag below) at BBD.
// kick 124.460 (f48): CUT to the scope (860 px at (540, 1000), Red trace) over the plate at 20 %,
//   PUNCH. kick 124.661 (f60): PUNCH and a zoom step on the scope.
// snare 124.865 (f73): CUT back to the lever, which FLIPS (18 frames, smootherstep; the lit plate
//   blends in); the pill slides to TAPE; tag "RED · TAPE".
// crash + kick 125.067 (f85): FLASH Red (0.30); WHIP out to the whole lit Red plate (0.77).
// The whole plate SMEARs out over 0.25 s centred on 125.270 into T2's Blue macro.
// This scene also owns the TikTok headline block, shown f0-f290 and again f389-f485.

import { bottomScrim, hit, cl, bigTag, frameDiv, renderWhip, smearAt, PlateSmear, knobAnchor, checkSafe, applyStamp, COLOR, el, setStyle, px, clamp } from "./t00-common.js";

export const ENGINES = ["green", "blue", "red", "purple", "black"];
export const TOTEM = { y0: 600, h: 220, scale: 0.77 };
export const WHOLE = { cx: 540, cy: 900, scale: 0.77 }; // the whole plate, full width
const SNAP = 10;
const SHRINK = 6;

export default {
  id: "t01-totem-red",
  t0: 0,
  t1: 97 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, lerp, ease } = lib.util;

    const first = hit(b, "kick", 123.6488);
    const hLever = cl(b, 124.0526); // snare + hat
    const hScope = cl(b, 124.4561); // kick + hat
    const hScope2 = cl(b, 124.6472); // hat + kick (f59)
    const hFlip = cl(b, 124.8649); // snare + hat
    const hWhip = cl(b, 125.0674); // crash + kick
    const bar78 = b.bar(78);
    const T1 = b.onsetTime(bar78);
    this.t1 = T1;
    const F_MACRO = 11;
    const smearEnd = bar78 + 0.125;
    const headOff = [291 / 60, 389 / 60]; // the freeze and the Mix turn own the frame (T4)
    const headEnd = 486 / 60; // T6's headline replaces this one
    this.events.push(
      { t: first.tm, kind: "slam", hit: "crash + kick 123.649 (the totem; the slot-snap from f1)" },
      { t: hLever.tm, kind: "cut", hit: "snare 124.055 (HQ lever macro, pill)" },
      { t: hScope.tm, kind: "cut", hit: "kick 124.460 (the scope)" },
      { t: hScope2.tm, kind: "sweep", hit: "hat + kick 124.647 (scope punch + zoom step)" },
      { t: hFlip.tm, kind: "cut", hit: "snare 124.865 (lever macro, the flip)" },
      { t: hFlip.tm, kind: "gesture", hit: "snare 124.865 (HQ BBD -> TAPE)" },
      { t: hWhip.tm, kind: "flash", hit: "crash + kick 125.067 (Red 0.30)" },
      { t: hWhip.tm, kind: "whip", hit: "crash + kick 125.067 (to the whole plate)" },
    );
    lib.registerFlash({ t: hWhip.t, peak: 0.3, color: COLOR.fill.red, id: "T1-flash" });

    // The totem strips (the Red one snaps open; hi-res for its growth).
    const SL = ctx.layer("totem", 10);
    const strips = ENGINES.map((eng, i) => {
      const s = lib.createSlice(SL, eng, { x: 0, y: TOTEM.y0 + i * TOTEM.h, w: 1080, h: TOTEM.h, scale: TOTEM.scale, hiRes: eng === "red" });
      const st = eng === "red" ? demos.plateState(0) : demos.plateState(0, { green: "T06", blue: "T02", purple: "T03", black: "T05" }[eng]);
      s.plate.require(st);
      s.plate.setState(st);
      // A solid pad (not a shadow) so the tag never prints over the plate's RATE engraving.
      const tag = el("div", { parent: s.el, text: eng.toUpperCase(), style: { font: `600 30px "JetBrains Mono", monospace`, letterSpacing: "0.12em", color: COLOR.hue[eng], padding: "3px 10px", margin: "-3px 0px 0px -10px", background: "rgba(5,5,6,0.78)", borderRadius: "6px" } });
      lib.type.placeText(tag, { x: 72, baseline: 36 });
      return { s, tag, eng };
    });
    const rim = el("div", { parent: strips[2].s.el, style: { position: "absolute", inset: "0", border: `3px solid ${COLOR.fill.red}`, boxSizing: "border-box" } });
    frameDiv(SL, { top: "1690px", height: "230px", background: "linear-gradient(rgba(5,5,6,0), #050506 60%)" });

    // The Red macro (RATE + DEPTH, then the lever), hi-res.
    const ML = ctx.layer("macro", 11);
    const mg = frameDiv(ML, { background: "#050506" });
    const macro = lib.createPlate("red", { parent: mg, scale: 2.0, hiRes: true, header: false });
    macro.require(demos.statesIn(0, T1 + 0.2, null, 240));
    const rd = [knobAnchor(lib, "red", "rate"), knobAnchor(lib, "red", "depth")];
    const RATE_DEPTH = [(rd[0][0] + rd[1][0]) / 2, (rd[0][1] + rd[1][1]) / 2];

    // The whole plate (the scope's 20 % backdrop, the whip target, the smear out).
    const WL = ctx.layer("whole", 12);
    const wg = frameDiv(WL);
    const whole = new PlateSmear(wg, lib, "red", { scale: WHOLE.scale });
    whole.require(demos.statesIn(0, smearEnd + 0.05, "T01", 120));

    const SCL = ctx.layer("scope", 14);
    const scope = lib.createScope(SCL, { cx: 540, cy: 1000, size: 860, stem: "guitar", color: COLOR.hue.red, disc: null, labelSize: 22 });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    // The headline block and its scrim (owned here for the whole TikTok, see headOff).
    const HL = ctx.layer("headline", 40);
    const scr = frameDiv(HL, { height: "700px", background: "linear-gradient(rgba(5,5,6,0.92) 55%, rgba(5,5,6,0))" });
    const head = frameDiv(HL, { transformOrigin: "72px 125.3px" });
    const brow = lib.type.eyebrow("CHOROBOROS", { parent: head, size: 30, color: COLOR.purple, x: 72, baseline: 290 });
    lib.type.headline({ text: "One riff.", size: 128, parent: head, x: 72, baseline: 430 });
    lib.type.headline({ text: "", accent: "Five engines.", size: 128, parent: head, x: 72, baseline: 560 });

    // Tags and the BBD · TAPE pill.
    const TL = ctx.layer("tags", 41);
    bottomScrim(TL);
    const tagBBD = bigTag(TL, "RED · BBD", COLOR.hue.red);
    const tagTAPE = bigTag(TL, "RED · TAPE", COLOR.hue.red);
    const pill = frameDiv(TL);
    const PX = 72;
    const PW = 520;
    const box = el("div", { parent: pill, style: { position: "absolute", left: px(PX), top: "1322px", width: px(PW), height: "80px", boxSizing: "border-box", border: "2px solid rgba(246,244,239,0.45)", borderRadius: "40px", overflow: "hidden", background: "rgba(5,5,6,0.7)" } });
    const knob = el("div", { parent: box, style: { position: "absolute", top: "0px", left: "0px", width: px(PW / 2), height: "76px", borderRadius: "38px", background: COLOR.fill.red } });
    const segs = ["BBD", "TAPE"].map((txt, i) =>
      el("div", { parent: box, text: txt, style: { position: "absolute", top: "0px", left: px((i * PW) / 2), width: px(PW / 2 - 2), height: "76px", display: "flex", alignItems: "center", justifyContent: "center", font: `600 34px "Inter", sans-serif`, letterSpacing: "0.06em" } }),
    );
    el("div", { parent: box, text: "·", style: { position: "absolute", top: "0px", left: px(PW / 2 - 20), width: "40px", height: "76px", display: "flex", alignItems: "center", justifyContent: "center", font: `600 34px "Inter", sans-serif`, color: "rgba(246,244,239,0.6)" } });

    return {
      setup() {
        checkSafe([HL, TL], "T1");
      },
      render(t) {
        const f = b.frameAt(t);
        const on = t < T1;
        const headOn = (t < headOff[0] || (t >= headOff[1] && t < headEnd));
        show(HL, headOn);
        show(SL, on && f <= SNAP);
        show(ML, on && f >= F_MACRO && f < hWhip.frame + 3);
        show(WL, t < smearEnd && (b.after(t, hScope.t) && f < hLever.frame + 1000));
        show(SCL, on && b.after(t, hScope.t) && !b.after(t, hFlip.t));
        show(FL, on);
        show(TL, on && f >= F_MACRO);

        // Headline: shrinks to 86 px from f11 (the eyebrow leaves); the scrim fades in over the snap.
        if (headOn) {
          const k = clamp((f - F_MACRO + 1) / SHRINK);
          const s = f < F_MACRO ? 1 : lerp(1, 86 / 128, ease("power3.out", k));
          setStyle(head, "transform", s === 1 ? "" : `scale(${+s.toFixed(5)})`);
          setStyle(brow, "visibility", f < F_MACRO ? "" : "hidden");
          const sa = t >= headOff[1] ? 1 : clamp(f / SNAP);
          setStyle(scr, "opacity", String(+sa.toFixed(4)));
        }
        if (!on && t >= smearEnd) return;

        // f0-f10: the totem, then the slot-snap.
        if (f <= SNAP) {
          const u = f === 0 ? 0 : ease("power4.out", f / SNAP);
          const sh = f === 0 ? { x: 0, y: 0 } : M.shake(t, [1 / 60], { amp: M.MOTION.shake.first });
          strips.forEach(({ s, tag, eng }, i) => {
            const y0 = TOTEM.y0 + i * TOTEM.h;
            if (eng === "red") {
              s.place({ x: 0, y: lerp(y0, 0, u), w: 1080, h: lerp(TOTEM.h, 1920, u), scale: lerp(TOTEM.scale, 1.5, u), dx: sh.x, dy: sh.y });
              s.plate.setGrade({ sat: 1, bright: lerp(1.15, 1, u) });
              setStyle(rim, "opacity", String(+(1 - u).toFixed(4)));
              s.plate.setState(demos.plateState(t));
            } else {
              const dy = i < 2 ? -u * (y0 + TOTEM.h) : u * (1920 - y0);
              s.place({ y: y0 + dy });
              s.plate.setGrade({ sat: lerp(1, 0.12, u), bright: 1 });
            }
            setStyle(tag, "opacity", String(+(1 - u).toFixed(4)));
          });
        }

        // The Red macro: RATE + DEPTH (f11), the lever (f24, and again from the flip).
        const inScope = b.after(t, hScope.t) && !b.after(t, hFlip.t);
        if (f >= F_MACRO && f < hWhip.frame + 3 && !inScope) {
          const st = demos.plateState(t);
          macro.setState(st);
          macro.setGrade(demos.grade("red", t));
          if (!b.after(t, hLever.t)) macro.focus({ on: RATE_DEPTH, zoom: 1.9, at: [540, 1000] });
          else macro.focus({ on: "hq", zoom: 2.0 * M.punch(t, [hLever, hFlip], { amp: M.MOTION.punch.macro }), at: [540, 1000] });
        }
        setStyle(mg, "visibility", inScope ? "hidden" : "");

        // The scope shot: the plate at 20 % behind an 860 px scope; PUNCH + a zoom step on f60.
        if (inScope) {
          whole.place({ cx: WHOLE.cx, cy: 1000, scale: WHOLE.scale });
          whole.setState(demos.plateState(t, "T01"));
          whole.setGrade(demos.grade("red", t));
          whole.render(0, null);
          setStyle(wg, "opacity", "0.2");
          const z = M.punch(t, [hScope, hScope2], { amp: 0.06 }) * (1 + 0.12 * M.sweep(t, [hScope2]));
          scope.draw(t, { stem: "guitar", color: COLOR.hue.red, zoom: z });
        } else if (b.after(t, hFlip.t)) {
          // The whip (f83-f87) from the lever macro to the whole lit plate, then the smear out.
          setStyle(wg, "opacity", "");
          const cutIn = renderWhip(M, t, hWhip, mg, wg, { dir: [-1, 0] });
          if (cutIn || f >= hWhip.frame - 2) {
            whole.place({ cx: WHOLE.cx, cy: WHOLE.cy, scale: WHOLE.scale * M.punch(t, [hWhip], { amp: M.MOTION.punch.plate }) });
            whole.setState(demos.plateState(t, "T01"));
            whole.setGrade(demos.grade("red", t));
            const u = smearAt(t, bar78);
            whole.render(u ?? 0, u != null ? "out" : null);
          }
        }

        // Tags, the pill, the flash.
        if (on) {
          const flipped = b.after(t, hFlip.t);
          setStyle(tagBBD, "visibility", !flipped ? "" : "hidden");
          setStyle(tagTAPE, "visibility", flipped ? "" : "hidden");
          const pillOn = b.after(t, hLever.t) && !b.after(t, hWhip.t) && !inScope;
          setStyle(pill, "visibility", pillOn ? "" : "hidden");
          if (pillOn) {
            applyStamp(box, M.stamp(t, hLever));
            const k = flipped ? ease("power3.out", clamp((f - hFlip.frame + 1) / 6)) : 0;
            setStyle(knob, "left", px((k * PW) / 2 - (k > 0 ? 2 * k : 0)));
            segs.forEach((sEl, i) => setStyle(sEl, "color", (i === 1 ? k >= 0.5 : k < 0.5) ? "#150807" : "rgba(246,244,239,0.7)"));
          }
          flash.render(t, M.flash(t, [hWhip], { peak: 0.3 }), COLOR.fill.red, lib.flash.flashMode("T1-flash"));
        }
      },
    };
  },
};
