// T6 The offer (TREATMENT section 7.2). tau 8.108 to 11.352, frames 486 to 680 (master 131.756 to
// 135.000). Demo T06: Green (heard to the end).
//
// 131.756 (f486, the empty downbeat): THE TOTEM RETURNS, five strips below the headline, colour =
//   sound now (Green lit, the others s 0.35). "Green and Purple" / "are free." (104 px, baselines
//   330 and 440) replaces the headline (STAMP).
// kicks (131.960, 132.564, 132.766): PUNCH and a push step.
// snare 132.162 (f510): STAMP "FREE" pills (mono 28 px on the hue) on the Green and Purple strips.
// snare 132.973 (f559): STAMP "30-DAY TRIAL" tags (hue outline) on Blue, Red and Black, and the
//   sub-line "30-day free trial." / "No payment card." (Inter 44 px, baselines 1440 and 1494, on a
//   78 % black band).
// snare + kick 133.376 (f583): CUT: "$49.99" SLAMs in (Fraunces 600, 200 px, baseline 640) over the
//   whole Green plate at 40 %. "USD." (italic 200 px, lavender, baseline 840) STAMPs on the next
//   beat, 133.784 (the spec lands it with the price; one beat later there is an event every beat).
// crash + kick 133.581 (f595): FLASH Green (0.30).
// kick 133.987 (f620): STAMP "One-time purchase." (Inter 600, 48 px, baseline 960).
// snare 134.189 (f632): the format row appears by a hard CUT (y 1392 to 1492), in a layer above
//   the grain; the VST Compatible logo is never scaled, flashed or covered.
// crash + kick 134.392 (f644): FLASH Green (0.30, under the row).
// beat 83.4 (134.594) and kick 134.797: the INHALE, 0.97 then 0.95 (everything but the row).
// T7's end card releases it on the stop, 135.000.

import { fitNodes } from "../scenes/a00-common.js";
import { cl, frameDiv, PlateSmear, checkSafe, applyStamp, bodyLine, COLOR, el, setStyle, px } from "./t00-common.js";
import { ENGINES, TOTEM, WHOLE } from "./t01-totem-red.js";

export default {
  id: "t06-offer",
  t0: 486 / 60,
  t1: 681 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show } = lib.util;

    const bar82 = b.bar(82);
    const T0 = b.onsetTime(bar82);
    const stop = cl(b, 134.9998);
    const T1 = stop.tf;
    this.t0 = T0;
    this.t1 = T1;
    const steps = [cl(b, 131.9595), cl(b, 132.5643), cl(b, 132.7659)];
    const sFree = cl(b, 132.162);
    const sTrial = cl(b, 132.9728);
    const price = cl(b, 133.3758);
    const f1 = cl(b, 133.581);
    const usd = b.beat(83, 2);
    const once = cl(b, 133.9866);
    const row = cl(b, 134.189);
    const f2 = cl(b, 134.3919);
    const inh = [b.beat(83, 4), cl(b, 134.7974)];
    const kicks = b.hitsIn("kick", T0 - 0.01, T1);
    this.events.push(
      { t: b.master(bar82), kind: "cut", hit: "bar 82.1 131.756 (the totem returns)" },
      { t: b.master(bar82), kind: "stamp", hit: "bar 82.1 (Green and Purple are free.)" },
      ...steps.map((h) => ({ t: h.tm, kind: "sweep", hit: `${h.piece} ${h.tm} (punch + push step)` })),
      { t: sFree.tm, kind: "stamp", hit: "snare 132.162 (FREE pills)" },
      { t: sTrial.tm, kind: "stamp", hit: "snare 132.973 (30-DAY TRIAL tags, sub-line)" },
      { t: price.tm, kind: "slam", hit: "snare + kick 133.376 ($49.99)" },
      { t: f1.tm, kind: "flash", hit: "crash + kick 133.581 (Green 0.30)" },
      { t: b.master(usd), kind: "stamp", hit: "beat 83.2 133.784 (USD.)" },
      { t: once.tm, kind: "stamp", hit: "kick 133.987 (One-time purchase.)" },
      { t: row.tm, kind: "cut", hit: "snare 134.189 (format row)" },
      { t: f2.tm, kind: "flash", hit: "crash + kick 134.392 (Green 0.30, under the row)" },
      { t: b.master(inh[0]), kind: "sweep", hit: "beat 83.4 134.594 (inhale 0.97)" },
      { t: inh[1].tm, kind: "sweep", hit: "kick 134.797 (inhale 0.95)" },
    );
    lib.registerFlash({ t: f1.t, peak: 0.3, color: COLOR.fill.green, id: "T6-a" });
    lib.registerFlash({ t: f2.t, peak: 0.3, color: COLOR.fill.green, id: "T6-b" });

    // The totem again (colour = sound).
    const SL = ctx.layer("totem", 10);
    const sg = frameDiv(SL, { transformOrigin: "540px 1150px" });
    // The strip tags sit in an unscaled group so the kick PUNCH never pushes them out of the safe
    // rectangle.
    const tagsL = frameDiv(SL);
    const strips = ENGINES.map((eng, i) => {
      const y = TOTEM.y0 + i * TOTEM.h;
      const s = lib.createSlice(sg, eng, { x: 0, y, w: 1080, h: TOTEM.h, scale: TOTEM.scale });
      const st = eng === "green" ? null : demos.plateState(T0, { blue: "T02", red: "T01", purple: "T03", black: "T05" }[eng]);
      if (st) {
        s.plate.require(st);
        s.plate.setState(st);
      } else s.plate.require(demos.statesIn(T0, price.t, null, 30));
      const tg = frameDiv(tagsL, { top: px(y), height: px(TOTEM.h) });
      const name = el("div", { parent: tg, text: eng.toUpperCase(), style: { font: `600 30px "JetBrains Mono", monospace`, letterSpacing: "0.12em", color: COLOR.hue[eng], textShadow: "0 0 10px rgba(5,5,6,0.95), 0 0 3px rgba(5,5,6,0.95)" } });
      lib.type.placeText(name, { x: 72, baseline: 36 });
      const free = eng === "green" || eng === "purple";
      const tag = el("div", {
        parent: tg,
        text: free ? "FREE" : "30-DAY TRIAL",
        style: {
          position: "absolute",
          top: "6px",
          left: "0px",
          height: "38px",
          lineHeight: "38px",
          padding: "0px 12px",
          borderRadius: "6px",
          boxSizing: "border-box",
          font: `600 28px "JetBrains Mono", monospace`,
          letterSpacing: "0.12em",
          color: free ? "#0b0b0c" : COLOR.hue[eng],
          background: free ? COLOR.fill[eng] : "rgba(5,5,6,0.8)",
          border: free ? "none" : `2px solid ${COLOR.hue[eng]}`,
          transformOrigin: "0% 50%",
        },
      });
      return { s, name, tag, eng, free };
    });
    const band = frameDiv(SL, { top: "1392px", height: "124px", background: "rgba(5,5,6,0.8)" });
    const subA = bodyLine(band, "30-day free trial.", { baseline: 1440 - 1392, size: 44, color: COLOR.fg });
    bodyLine(band, "No payment card.", { baseline: 1494 - 1392, size: 44, color: COLOR.fg });
    void subA;

    // The price over the whole Green plate at 40 %.
    const WL = ctx.layer("price-plate", 11);
    const wg = frameDiv(WL, { opacity: "0.4" });
    const whole = new PlateSmear(wg, lib, "green", { scale: WHOLE.scale });
    whole.require(demos.statesIn(price.t, T1, null, 30));

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const HL = ctx.layer("type", 40);
    const head = frameDiv(HL, { transformOrigin: "72px 400px" });
    const gp = lib.type.headline({ text: "Green and Purple", size: 104, parent: head, x: 72, baseline: 330 });
    const free = lib.type.headline({ text: "are ", accent: "free.", size: 104, parent: head, x: 72, baseline: 440 });
    const ct = lib.createChorusType(free.accent, { law: "SINE", engine: "green" });
    const pr = frameDiv(HL);
    const p1 = lib.type.headline({ text: "$49.99", size: 200, parent: pr, x: 72, baseline: 640 });
    const usdN = lib.type.headline({ text: "", accent: "USD.", size: 200, parent: pr, x: 72, baseline: 840 });
    usdN.el.style.transformOrigin = "0% 80%";
    const onceN = bodyLine(pr, "One-time purchase.", { baseline: 960, size: 48, weight: 600, color: COLOR.fg });
    onceN.style.transformOrigin = "0% 80%";

    // The format row: above the grain (z 850, under the kit chip's 900), never scaled or covered.
    const TOP = ctx.layer("formats", 850);
    const rowN = lib.endcard.formatRowPortrait({ parent: TOP, x0: 72, y: 1392 });
    ctx.preload([lib.endcard.VST_URL]);

    const inhaled = [SL, WL, HL];
    return {
      setup() {
        // The pills sit after each strip's name.
        for (const st of strips) setStyle(st.tag, "left", px(st.name.offsetLeft + st.name.offsetWidth + 18));
        // Line-fit rule: "Green and Purple" passes x 928 at 104 px; it drops toward 96 px (the
        // headline minimum) and warns if it still does not fit.
        fitNodes([{ node: gp.el, min: 96 }], { label: "T6" });
        checkSafe([HL], "T6");
      },
      render(t) {
        const on = t >= T0 && t < T1;
        const priced = b.after(t, price.t);
        show(SL, on && !priced);
        show(WL, on && priced);
        show(FL, on);
        show(HL, on);
        show(TOP, on && b.after(t, row.t));
        if (!on) return;
        const f = b.frameAt(t);
        // The inhale (0.97, 0.95): every layer here but the format row.
        const inS = M.inhale(t, inh, stop);
        for (const l of inhaled) setStyle(l, "transform", inS === 1 ? "" : `scale(${+inS.toFixed(5)})`);
        for (const l of inhaled) setStyle(l, "transformOrigin", "540px 960px");

        if (!priced) {
          const pu = M.punch(t, kicks, { amp: M.MOTION.punch.plate });
          const push = 1 + 0.012 * M.sweep(t, steps, { frames: 4 });
          setStyle(sg, "transform", `scale(${+(pu * push).toFixed(5)})`);
          for (const st of strips) {
            if (st.eng === "green") st.s.plate.setState(demos.plateState(t));
            st.s.plate.setGrade(demos.grade(st.eng, t));
            applyStamp(st.tag, M.stamp(t, st.free ? sFree : sTrial));
          }
          applyStamp(band, M.stamp(t, sTrial, { from: 1.06 }));
          setStyle(band, "transformOrigin", "72px 1440px");
        } else {
          whole.place({ cx: WHOLE.cx, cy: 1000, scale: WHOLE.scale * M.punch(t, kicks.filter((k) => k.t >= price.t - 0.01), { amp: M.MOTION.punch.plate }) });
          whole.setState(demos.plateState(t));
          whole.setGrade(demos.grade("green", t));
          whole.render(0, null);
        }

        // Type: the free headline until the price; then the price stack.
        setStyle(head, "visibility", priced ? "hidden" : "");
        setStyle(pr, "visibility", priced ? "" : "hidden");
        if (!priced) {
          applyStamp(head, M.stamp(t, bar82));
          ct.render(t, demos.settingsAt(t));
        } else {
          const sl = M.slam(t, price, { dir: [0, -1] });
          const pu = M.punch(t, [price], { amp: M.MOTION.punch.type });
          setStyle(p1.el, "transform", `translate(0px, ${px(sl.y)}) scale(${+pu.toFixed(5)})`);
          applyStamp(usdN.el, M.stamp(t, usd));
          applyStamp(onceN, M.stamp(t, once));
        }
        const a1 = M.flash(t, [f1], { peak: 0.3 });
        const a2 = M.flash(t, [f2], { peak: 0.3 });
        flash.render(t, Math.max(a1, a2), COLOR.fill.green, lib.flash.flashMode(a2 > a1 ? "T6-b" : "T6-a"));
        void f;
        void rowN;
      },
    };
  },
};
