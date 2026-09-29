// S01 Still + Mix turn (TREATMENT section 2, ACT I). 0.000 to the bar-2 kick (frames 0 to 120).
//
// Frames 0-23: a dead still. The Green plate as an L-MACRO on MIX (knob element 600 px, centred
// at (540, 1180)), graded s 0.12 except the MIX readout "0%" and a 3 px lavender ring at 1.12x the
// knob; an empty 300 px scope graticule at (770, 560); "Great" / "sound" at 180 px.
// f24 (crash + kick + rack 0.4074): white FLASH [0.45, 0.20, 0.06], SHAKE 14 px (type 2 px), the
// five-hue type BURST (+-40 px, snapping back over 10 frames, power3.out), Mix click-stop 1, the
// colour floods with the knob, the scope trace blooms.
// f48, f72, f97: Mix click-stops 2-4 with PUNCH (macro, x 0.6 in the tom groove) and a ring pulse
// 1.12 -> 1.18 -> 1.12 over 8 frames. f108: the ring fades out over 0.3 s.

import { hookHeadline, ringSvg, scrim, drawGraticule } from "./a00-common.js";

const KNOB_PX = 600; // mix knob element across
const KNOB_AT = [540, 1180];
// The spec puts the scope at (770, 520); it sits 40 px lower so its rim clears the one-line
// "Great sound" of S02 (and S01 keeps the same position for continuity across the cut).
export const SCOPE = [770, 560];
const KNOB_VISIBLE = 0.75; // the knob inside its mix-sheet frame (512 px frames, 64 px border)

export default {
  id: "a01-still-mixturn",
  t0: 0,
  t1: 2.0253, // replaced in build() by the frame of the bar-2 kick
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M } = ctx;
    const { COLOR } = ctx.portrait;
    const { el, setStyle, show, px } = lib.util;

    // Hits (named by their master time, TREATMENT section 2).
    const first = b.hitNear("kick", 0.4074); // crash + kick + rack, f24
    const kicks = [0.4074, 0.8106, 1.216, 1.6217].map((x) => b.hitNear("kick", x));
    const ringOut = b.hitNear("floortom", 1.808); // f108
    const next = b.hitNear("kick", 2.0253); // bar 2: S02 cuts in on its frame
    const T1 = next.tf; // first frame that is not ours
    this.t1 = T1;
    this.events.push(
      { t: first.tm, kind: "flash", hit: "crash+kick+rack 0.4074" },
      ...kicks.map((k, i) => ({ t: k.tm, kind: "click", hit: `kick ${k.tm} (Mix step ${i + 1})` })),
      { t: ringOut.tm, kind: "gesture", hit: "floor+rack 1.808 (ring out)" },
    );
    lib.registerFlash({ t: first.t, peak: M.MOTION.flash.first[0], color: "#ffffff", id: "S01-first" });

    // Picture: the plate macro.
    const L = ctx.layer("plate", 10);
    const probe = lib.createPlate("green", { parent: L, scale: 1, hiRes: true, header: false });
    const zoom = KNOB_PX / probe.controlRect("mix").size;
    const plate = probe;
    // Every knob frame and readout M01 shows over this shot.
    plate.require(demos.statesIn(0, T1));
    const vignette = el("div", {
      parent: L,
      style: {
        position: "absolute",
        inset: "0",
        background: `radial-gradient(circle at ${KNOB_AT[0]}px ${KNOB_AT[1]}px, rgba(5,5,6,0) 0px, rgba(5,5,6,0) 400px, rgba(5,5,6,0.62) 700px, rgba(5,5,6,0.9) 1000px)`,
      },
    });
    const bottom = el("div", { parent: L, style: { position: "absolute", left: "0px", top: "1560px", width: "1080px", height: "360px", background: "linear-gradient(rgba(5,5,6,0), #050506 70%)" } });
    scrim(L, { top: 0.72, to: 720 });

    // The ring: 3 px lavender at 1.12x the knob.
    const RL = ctx.layer("ring", 12);
    const ring = ringSvg(RL, { color: COLOR.lavender, width: 3 });

    // The empty scope graticule, then the trace (canvas: moved by left/top only).
    const SL = ctx.layer("scope", 14);
    const scope = lib.createScope(SL, { cx: SCOPE[0], cy: SCOPE[1], size: 300, stem: "wet", color: COLOR.hue.green, disc: "rgba(5,5,6,0.55)", labelSize: 16 });

    // Flash (under the type).
    const FL = ctx.layer("flash", 30);
    const flash = lib.createFlash(FL);

    // Type: "Great" / "sound", 180 px, with the five-hue burst copies behind the dry words.
    const TL = ctx.layer("type", 40);
    const head = hookHeadline(TL, lib, { lines: ["Great", "sound"], size: 180, baselines: [470, 640], burst: true });

    return {
      render(t) {
        const on = t >= 0 && t < T1;
        for (const l of [L, RL, SL, FL, TL]) show(l, on);
        if (!on) return;
        const f = b.frameAt(t);

        // SHAKE (picture 14 px, type 2 px) and PUNCH (macro x 0.6) from the first hit.
        const sh = M.shake(t, [first], { amp: M.MOTION.shake.first });
        const pu = M.punch(t, kicks, { amp: M.MOTION.punch.macro * M.MOTION.tomGroove });
        plate.focus({ on: "mix", zoom: zoom * pu, at: KNOB_AT, dx: sh.x, dy: sh.y });
        const st = demos.plateState(t);
        plate.setState(st);
        plate.setGrade({ ...demos.grade("green", t), keep: ["mix"] });
        setStyle(vignette, "transform", `translate(${px(sh.x)}, ${px(sh.y)})`);

        // Ring: pulses on each step, fades out over 0.3 s from f108.
        const r = plate.controlScreenRect("mix");
        let k = 1.12;
        for (const h of kicks) {
          const df = f - h.frame;
          if (df >= 0 && df <= 8) k = 1.12 + 0.06 * Math.sin((Math.PI * df) / 8);
        }
        const out = b.since(t, ringOut.t);
        const ra = out < 0 ? 1 : Math.max(0, 1 - out / 0.3);
        ring.render({ cx: r.cx, cy: r.cy, d: r.size * KNOB_VISIBLE * k, alpha: ra });

        // Scope: an empty graticule until the first hit, then the trace.
        scope.moveTo(SCOPE[0] + sh.x, SCOPE[1] + sh.y);
        if (f < first.frame) {
          drawGraticule(scope);
        } else {
          scope.draw(t, { stem: "wet", color: COLOR.hue.green });
        }

        // FLASH white on frames 24, 25, 26.
        flash.render(t, M.flash(t, [first], { frames: M.MOTION.flash.first }), "#ffffff");

        // Type: 2 px shake; the burst sprays +-40 px and snaps back over 10 frames.
        const ts = M.shake(t, [first], { amp: M.MOTION.shake.type, salt: 5 });
        head.render(t, { dx: ts.x, dy: ts.y, burstHit: first, beats: b });
      },
    };
  },
};
