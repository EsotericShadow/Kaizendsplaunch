// S08 The five voices (TREATMENT section 2, ACT II). Bars 13-14, 19.864 to 23.108 (frames 1191 to
// 1385; this scene also draws the first 6 frames of S09's collapse).
//
// kick 19.856 / crash 19.928 (f1191): the deck FANS into five knob-row strips (slices.js: each plate
// at scale 0.72, clipped to its knob row, 1008 x 200, 16 px gaps, y 560 to 1624; the last strip runs
// under the bottom UI, picture only). The fan takes 12 frames (expo.out), from the deck rects.
// Each strip's tag brightens (55 % -> 100 %) and the strip PUNCHes on its snare: Green 20.270, Blue
// 21.081, Red 21.892, Purple 22.703, Black 22.904. crash + kick 21.283: FLASH Green (0.30) and all
// strips PUNCH. The double kicks (20.675 + 20.877, 22.297 + 22.500) step the stack in, +0.8 % a
// step. Colour = sound: Green s 1.0, the others s 0.35.
// f1386 (the stop hit, S09): the four other strips collapse into the Blue strip over 6 frames
// (power2.in) while a09-blue.js opens the Blue strip into L-TOUR.
// Tags (mono 28 px, engine hue, top left of each strip): GREEN · WARM, BLUE · WIDE, RED · VINTAGE,
// PURPLE · EXPERIMENTAL, BLACK · DENSE. The headline holds (a07-lineup.js owns it).

import { DECK, ENGINES, DEMO_OF, PICKUP_STEP } from "./a07-lineup.js";
import { checkSafe, monoLine } from "./a00-common.js";

export const STRIP = { x: 36, y0: 560, w: 1008, h: 200, gap: 16, scale: 0.72 };
export const stripY = (i) => STRIP.y0 + i * (STRIP.h + STRIP.gap);
const TAGS = ["GREEN · WARM", "BLUE · WIDE", "RED · VINTAGE", "PURPLE · EXPERIMENTAL", "BLACK · DENSE"];
const FAN_FRAMES = 12;
const COLLAPSE_FRAMES = 6;

export default {
  id: "a08-five-voices",
  t0: 1191 / 60,
  t1: 1386 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { show, setStyle, el, lerp, clamp, ease } = lib.util;
    const { COLOR } = ctx.portrait;

    const fan = b.hitNear("kick", 19.8563);
    const snares = [20.2703, 21.0809, 21.8923, 22.7025, 22.9037].map((x) => b.hitNear("snare", x));
    const crash = b.hitNear("kick", 21.283);
    const doubles = [20.6755, 20.8773, 22.2973, 22.5001].map((x) => b.hitNear("kick", x));
    const stop = b.hitNear("kick", 23.1083); // S09
    const T0 = fan.tf;
    const T1 = stop.tf;
    this.t0 = T0;
    this.t1 = T1;
    const TEND = T1 + COLLAPSE_FRAMES / 60;
    const kicks = b.hitsIn("kick", fan.t - 0.01, stop.t - 0.01);
    this.events.push(
      { t: fan.tm, kind: "cut", hit: "kick 19.856 / crash 19.928 (the fan)" },
      ...snares.map((h, i) => ({ t: h.tm, kind: "stamp", hit: `snare ${h.tm} (${TAGS[i]})` })),
      { t: crash.tm, kind: "flash", hit: "crash + kick 21.283 (Green 0.30, all strips punch)" },
      ...doubles.map((h) => ({ t: h.tm, kind: "sweep", hit: `kick ${h.tm} (stack step)` })),
    );
    lib.registerFlash({ t: crash.t, peak: 0.3, color: COLOR.fill.green, id: "S08-a" });

    const L = ctx.layer("strips", 10);
    const group = el("div", { parent: L, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: "540px 1092px" } });
    const strips = ENGINES.map((eng, i) => {
      const s = lib.createSlice(group, eng, { x: STRIP.x, y: stripY(i), w: STRIP.w, h: STRIP.h, scale: STRIP.scale });
      if (DEMO_OF[eng]) {
        const st = demos.plateState(T0, DEMO_OF[eng]);
        s.plate.require(st);
        s.plate.setState(st);
      } else s.plate.require(demos.statesIn(T0, TEND));
      return s;
    });
    // The deck at the end of S07 (after the two pickup steps), where the fan starts.
    const deckRect = (i) => ({ x: DECK.x + i * DECK.dx, y: DECK.y + i * DECK.dy - 2 * PICKUP_STEP, w: 1400 * DECK.scale, h: 847.02 * DECK.scale });

    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    const TL = ctx.layer("tags", 40);
    const tags = TAGS.map((txt, i) => monoLine(TL, txt, { x: 72, baseline: stripY(i) + 40, size: 28, color: COLOR.hue[ENGINES[i]], tracking: 0.12 }));
    // A solid dark pad behind each tag (the text stays at x 72 and on its baseline) so it never
    // prints over the plates' RATE and DEPTH engravings.
    tags.forEach((n) => {
      Object.assign(n.style, { padding: "3px 10px", margin: "-3px 0px 0px -10px", background: "rgba(5,5,6,0.78)", borderRadius: "6px" });
    });

    return {
      setup() {
        checkSafe([TL], "S08");
      },
      render(t) {
        const on = t >= T0 && t < TEND;
        show(L, on);
        show(FL, t >= T0 && t < T1);
        show(TL, t >= T0 && t < T1);
        if (!on) return;
        const f = b.frameAt(t);
        const collapsing = f >= stop.frame;
        const uf = clamp((f - fan.frame + 1) / FAN_FRAMES); // moving on the hit frame
        const u = ease("expo.out", uf);
        const step = collapsing ? 1 + 0.008 * 4 : 1 + 0.008 * M.sweep(t, doubles);
        setStyle(group, "transform", step === 1 ? "" : `scale(${+step.toFixed(5)})`);
        const allPunch = M.punch(t, [crash], { amp: M.MOTION.punch.plate });
        strips.forEach((s, i) => {
          const eng = ENGINES[i];
          if (collapsing && eng === "blue") {
            s.show(false); // a09-blue.js opens it
            return;
          }
          s.show(true);
          const d = deckRect(i);
          let y = lerp(d.y, stripY(i), u);
          let h = lerp(d.h, STRIP.h, u);
          let alpha = 1;
          if (collapsing) {
            const c = ease("power2.in", clamp((f - stop.frame + 1) / COLLAPSE_FRAMES));
            const target = stripY(1);
            y = lerp(stripY(i), target, c);
            h = lerp(STRIP.h, STRIP.h * 0.6, c);
            y += (STRIP.h - h) / 2;
            alpha = 1 - c;
          }
          const pu = M.punch(t, [snares[i]], { amp: M.MOTION.punch.plate }) * allPunch * M.punch(t, kicks, { amp: M.MOTION.punch.plate * 0.35 });
          s.place({ x: lerp(d.x, STRIP.x, u), y, w: lerp(d.w, STRIP.w, u), h, scale: lerp(DECK.scale, STRIP.scale, u) * pu });
          setStyle(s.el, "opacity", alpha >= 1 ? "" : String(+alpha.toFixed(4)));
          if (!DEMO_OF[eng]) s.plate.setState(demos.plateState(t));
          s.plate.setGrade(demos.grade(eng, t));
        });
        if (collapsing) return;
        // Tags: in with the fan's end at 55 %, full from their snare on.
        tags.forEach((n, i) => {
          const vis = uf >= 1;
          setStyle(n, "visibility", vis ? "" : "hidden");
          const lit = b.after(t, snares[i].t);
          setStyle(n, "opacity", lit ? "" : "0.55");
        });
        flash.render(t, M.flash(t, [crash], { peak: 0.3 }), COLOR.fill.green, lib.flash.flashMode("S08-a"));
      },
    };
  },
};
