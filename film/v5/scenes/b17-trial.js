// S17 Trial (TREATMENT section 2, ACT V). Bars 35-38, 55.540 to 62.026 (frames 3332-3720).
//
// A 2 x 2 grid of plates at scale 0.30 (420 x 254), x 72 to 928, y 640 to 1164, gap 16: Blue and
// Red on top, Black and the white Create canvas below. The heard tile is at s 1.0 with a 3 px ring
// in its hue; the others at 0.35. Blue from f3332 (M08), Red (lever at TAPE, lit) from f3417 (M09),
// Black from f3527 (M10): each switch is a FLASH in the new hue (0.30) plus a STAMP of the tile.
// f3624: the Create tile STAMPs with a white ring (the chip still reads BLACK). Snares PUNCH the
// tile labels and re-stamp the heard tile's ring (the backbeat events of the verse).
// 61.621 (snare): a WHIP up (dir [0, -1]). The grid and the body lines leave upwards; the incoming
// shot is S18's Blue plate in its zone S place (scale 0.58, x 134, y 1290), not yet heard (s 0.35),
// so the S18 slam on 62.027 lands on the same plate. The headline holds to the S18 cut.
// Type: "30-day free trial. / No payment card." (96 px) on f3332; the unlock lines on 56.341; the
// muted lines on 58.784. Tile labels BLUE / RED / BLACK / CREATE (mono 26 px, engine hue).

import { hitAt, inF, ev, fitter, headLine, bodyLine, applyStamp, applyOn, flashBank, vis } from "./b00-common.js";

const S = 0.3;
const TILES = [
  { id: "blue", engine: "blue", demo: "M08", x: 72, y: 640, label: "BLUE" },
  { id: "red", engine: "red", demo: "M09", x: 508, y: 640, label: "RED" },
  { id: "black", engine: "black", demo: "M10", x: 72, y: 910, label: "BLACK" },
  { id: "create", engine: "white", demo: null, x: 508, y: 910, label: "CREATE" },
];
const WHITE_STATE = { rate: 0.45, depth: 30, offset: 60, width: 100, color: 50, mix: 40, hq: 1 };
export const S18_PLATE = { scale: 0.58, x: 134, y: 1290 }; // S18's zone S Blue plate

export default {
  id: "b17-trial",
  t0: 3332 / 60,
  t1: 3721 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, demos, motion: M, portrait: P } = ctx;
    const { show, setStyle, px, el } = lib.util;
    const { COLOR } = P;
    const cut = hitAt(b, 55.5404);
    const next = hitAt(b, 62.0271);
    const F0 = cut.frame;
    const F1 = next.frame;
    const sw = { blue: cut, red: hitAt(b, 56.9581), black: hitAt(b, 58.784), create: hitAt(b, 60.4054) };
    const lines1 = hitAt(b, 56.3406);
    const lines2 = hitAt(b, 58.784);
    const whipH = hitAt(b, 61.6215);
    const snares = b.hitsIn("snare", cut.t, next.t - 0.01, { minDb: -20 });
    ev(this, b, cut, "cut", "crash + kick 55.540 (the trial grid)");
    ev(this, b, cut, "stamp", "crash + kick 55.540 (headline, Blue tile)");
    ev(this, b, cut, "flash", "crash + kick 55.540 (FLASH Blue)");
    ev(this, b, lines1, "text", "hat + kick 56.341 (unlock lines)");
    ev(this, b, sw.red, "stamp", "crash + kick 56.958 (Red tile, TAPE)");
    ev(this, b, sw.red, "flash", "crash + kick 56.958 (FLASH Red)");
    ev(this, b, sw.black, "stamp", "kick + crash 58.784 (Black tile)");
    ev(this, b, sw.black, "flash", "kick + crash 58.784 (FLASH Black)");
    ev(this, b, lines2, "text", "kick + crash 58.784 (after-the-trial lines)");
    ev(this, b, sw.create, "stamp", "cymbal + kick 60.405 (Create tile, white ring)");
    snares.filter((h) => h.frame < whipH.frame).forEach((h) => ev(this, b, h, "stamp", `snare ${h.tm} (the heard tile's ring re-stamps)`));
    ev(this, b, whipH, "whip", "snare 61.621 (WHIP up into S18)");

    const GL = ctx.layer("grid", 12);
    const grid = el("div", { parent: GL, style: { position: "absolute", inset: "0", transformOrigin: "540px 900px" } });
    const tiles = TILES.map((d) => {
      const wrap = el("div", { parent: grid, style: { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px", transformOrigin: `${d.x + 210}px ${d.y + 127}px` } });
      const p = lib.createPlate(d.engine, { parent: wrap, scale: S, header: true, hiRes: false });
      if (d.demo) p.require(demos.statesIn(cut.t, next.t, d.demo, 4));
      else p.require(WHITE_STATE);
      p.place({ x: d.x, y: d.y, scale: S });
      const hue = d.engine === "white" ? "#ffffff" : COLOR.hue[d.engine];
      const ring = el("div", { parent: wrap, style: { position: "absolute", left: px(d.x - 7), top: px(d.y - 7), width: px(420 + 14), height: px(254 + 14), boxSizing: "border-box", border: `3px solid ${hue}`, borderRadius: "12px", boxShadow: `0 0 18px ${hue}66`, visibility: "hidden", transformOrigin: "50% 50%" } });
      const label = el("div", { parent: wrap, text: d.label, style: { position: "absolute", left: px(d.x + 10), top: px(d.y + 4), padding: "2px 10px 2px 12px", font: `600 26px ${lib.type.FONT.mono}`, letterSpacing: "0.12em", color: hue, background: "rgba(5,5,6,0.88)", borderRadius: "6px", transformOrigin: "0% 50%", whiteSpace: "pre" } });
      return { ...d, wrap, p, ring, label };
    });
    // The incoming shot of the whip: S18's Blue plate, not yet heard.
    const IL = ctx.layer("incoming", 13);
    const blue18 = lib.createPlate("blue", { parent: IL, scale: S18_PLATE.scale, header: true, hiRes: false });
    blue18.require(demos.statesIn(62.1, 62.2, "M11", 4));

    const flashes = flashBank(ctx, lib, [
      { h: cut, color: COLOR.fill.blue, peak: 0.3 },
      { h: sw.red, color: COLOR.fill.red, peak: 0.3 },
      { h: sw.black, color: COLOR.fill.black, peak: 0.3 },
    ]);

    const TL = ctx.layer("type", 40);
    const BL = ctx.layer("body", 41); // the body lines leave with the grid on the whip
    const fit = fitter();
    const h1 = headLine(TL, fit, { text: "30-day free trial.", size: 96, baseline: 380 });
    const h2 = headLine(TL, fit, { text: "", accent: "No payment card.", size: 96, baseline: 480 });
    const u1 = bodyLine(BL, fit, "The trial unlocks Blue, Red,", { size: 44, baseline: 1260 });
    const u2 = bodyLine(BL, fit, "Black and Create.", { size: 44, baseline: 1314 });
    const a1 = bodyLine(BL, fit, "After the trial, Green and", { size: 40, baseline: 1380, color: COLOR.muted });
    const a2 = bodyLine(BL, fit, "Purple stay free.", { size: 40, baseline: 1430, color: COLOR.muted });

    const order = ["blue", "red", "black"];
    return {
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [GL, IL, TL, BL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const f = b.frameAt(t);
        const heardId = order.filter((k) => f >= sw[k].frame).pop();
        const lastSnare = snares.filter((h) => h.frame <= f).pop();

        for (const d of tiles) {
          const swHit = sw[d.id];
          const st = M.stamp(t, swHit);
          const isHeard = d.id === heardId;
          const stamped = f >= swHit.frame && f < swHit.frame + 6;
          // Backbeat: each snare re-STAMPs the heard tile (1.07 -> 1.00 over 5 frames) and flares its
          // ring, so the verse's 2 and 4 read on a phone (a label punch alone was too small).
          const snareHit = isHeard && lastSnare && lastSnare.frame > swHit.frame && f < lastSnare.frame + 6 ? lastSnare : null;
          const ss = snareHit ? M.stamp(t, snareHit, { from: 1.07 }).scale : 1;
          const sc = stamped ? st.scale : ss;
          setStyle(d.wrap, "transform", sc !== 1 ? `scale(${+sc.toFixed(5)})` : "");
          setStyle(d.ring, "boxShadow", snareHit ? `0 0 ${Math.round(18 + 30 * (1 - (f - snareHit.frame) / 6))}px ${d.engine === "white" ? "#ffffff" : COLOR.hue[d.engine]}cc` : `0 0 18px ${d.engine === "white" ? "#ffffff" : COLOR.hue[d.engine]}66`);
          if (d.demo) d.p.setState(demos.plateState(t, d.demo));
          else d.p.setState(WHITE_STATE);
          d.p.setGrade(demos.grade(d.engine, t));
          const ringOn = isHeard || (d.id === "create" && f >= swHit.frame);
          vis(d.ring, ringOn);
          if (ringOn) {
            const rs = lastSnare && lastSnare.frame >= swHit.frame ? M.stamp(t, lastSnare, { from: 1.04 }).scale : 1;
            setStyle(d.ring, "transform", rs === 1 ? "" : `scale(${+rs.toFixed(5)})`);
          }
          const lk = M.punch(t, snares, { amp: M.MOTION.punch.macro });
          setStyle(d.label, "transform", lk === 1 ? "" : `scale(${+lk.toFixed(5)})`);
        }

        // WHIP up on 61.621: the grid and body lines out (180 px up, blurred), S18's plate in from below.
        const w = M.whip(t, whipH, { dir: [0, -1] });
        const outGone = w.cut && !w.active;
        const blurPx = w.active ? 10 * Math.sin(Math.PI * w.u) : 0;
        show(GL, !w.cut);
        show(BL, !w.cut);
        if (!w.cut) {
          setStyle(grid, "transform", w.active ? `translateY(${px(w.outY)})` : "");
          setStyle(grid, "filter", blurPx > 0.05 ? `blur(${blurPx.toFixed(2)}px)` : "");
          for (const n of [u1, u2, a1, a2]) setStyle(n, "translate", w.active ? `0px ${px(w.outY)}` : "");
        }
        show(IL, w.cut);
        if (w.cut) {
          blue18.place({ x: S18_PLATE.x, y: S18_PLATE.y + (outGone ? 0 : w.inY), scale: S18_PLATE.scale });
          blue18.setState(demos.plateState(62.1, "M11"));
          blue18.setGrade({ sat: 0.35, bright: 0.75 });
          setStyle(blue18.el, "filter", w.active && blurPx > 0.05 ? `blur(${blurPx.toFixed(2)}px)` : "");
        }

        const st = M.stamp(t, cut);
        applyStamp(h1.el, st);
        applyStamp(h2.el, st);
        applyOn(b, t, u1, lines1);
        applyOn(b, t, u2, lines1);
        applyOn(b, t, a1, lines2);
        applyOn(b, t, a2, lines2);
      },
    };
  },
};
