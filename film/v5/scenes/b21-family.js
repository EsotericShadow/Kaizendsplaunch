// S21 More from Kaizen DSP (TREATMENT section 2, ACT VII). Bars 49-51, 78.243 to 83.107
// (frames 4694-4985). Heard DRY: the bypass span 78.244 to 83.310, so the chip reads
// "○ GUITAR · BYPASS" and nothing suggests these products are heard.
//
// Fold (f4694, crash + kick 78.244): the Fold clip frames (clips.js), portrait-cropped in zone H
// (y 560 to 1240), CUT between two Fold crops on the crashes 78.850 and 79.662. No flash.
// Echolalia (f4791, a hard CUT on the bar-50 line 79.864): its clip frames on #080706; the kick at
// 80.066 PUNCHes it (1.03); the snares 80.271 and 81.081 CUT between crops, so an event lands at
// least every 2 beats.
// Stovetop (f4889, kick + crash 81.486): stovetop-hero.jpg shown whole, never cropped, 900 px wide,
// centred at y 930 (30 px under the spec's 900 so its top clears the pill, y 460 to 510), on
// #151517. The crashes 82.095 and 82.904 PUNCH it (1.02) with a #ff7a2e edge glow.
// Eyebrow "MORE FROM KAIZEN DSP" for all three; per card the name (104 px, Stovetop in Sedgwick
// Ave Display 110 px #ff7a2e), the status pill (y 460 to 510) and the line at 1420.
// The clips are canvases: drawn with their crop and zoom inside the draw call, never transformed.

import { hitAt, barT, inF, ev, fitter, headLine, bodyLine, eyebrowLine, applyStamp, vis, pillLabel, solid, flashBank } from "./b00-common.js";

const ZONE = { x: 0, y: 560, w: 1080, h: 680 };
const STOVE_FONT = "/art/site/stovetop/SedgwickAveDisplay-Regular.ttf";
// Crops: the source point (fraction of the frame) at the zone centre, and the zoom over "cover".
const FOLD_CROPS = [
  { cx: 0.5, cy: 0.5, zoom: 1.0 },
  { cx: 0.36, cy: 0.52, zoom: 1.7 },
  { cx: 0.5, cy: 0.5, zoom: 1.0 },
];
const ECHO_CROPS = [
  { cx: 0.5, cy: 0.5, zoom: 1.0 },
  { cx: 0.62, cy: 0.5, zoom: 1.55 },
  { cx: 0.38, cy: 0.48, zoom: 1.3 },
];

function drawCover(c2d, img, { cx, cy, zoom }, k = 1) {
  const W = ZONE.w;
  const H = ZONE.h;
  const iw = img.naturalWidth || img.width;
  const ih = img.naturalHeight || img.height;
  const s = Math.max(W / iw, H / ih) * zoom * k;
  const sw = W / s;
  const sh = H / s;
  const sx = Math.min(iw - sw, Math.max(0, cx * iw - sw / 2));
  const sy = Math.min(ih - sh, Math.max(0, cy * ih - sh / 2));
  c2d.clearRect(0, 0, W, H);
  c2d.imageSmoothingEnabled = true;
  c2d.imageSmoothingQuality = "high";
  c2d.drawImage(img, sx, sy, sw, sh, 0, 0, W, H);
}

export default {
  id: "b21-family",
  t0: 4694 / 60,
  t1: 4986 / 60,
  events: [],
  async build(ctx) {
    const { lib, beats: b, motion: M, portrait: P } = ctx;
    const { show, el, setStyle, px } = lib.util;
    const { COLOR } = P;
    const face = new FontFace("Sedgwick Ave Display", `url("${STOVE_FONT}")`);
    await face.load();
    document.fonts.add(face);

    const fold = hitAt(b, 78.2437);
    const foldCuts = [78.8501, 79.6621].map((x) => hitAt(b, x));
    const echoT = barT(b, 50); // 79.864, the bar line (no hit on it)
    const echoKick = hitAt(b, 80.0663);
    const echoCuts = [80.271, 81.081].map((x) => hitAt(b, x));
    const stove = hitAt(b, 81.4864);
    const stovePush = [82.0946, 82.9045].map((x) => hitAt(b, x));
    const F0 = fold.frame;
    const FE = b.onsetFrame(echoT);
    const FS = stove.frame;
    const F1 = b.onsetFrame(barT(b, 52)); // 83.107, S22
    ev(this, b, fold, "cut", "crash + kick 78.244 (Fold)");
    ev(this, b, fold, "stamp", "crash + kick 78.244 (eyebrow, Fold.)");
    foldCuts.forEach((h) => ev(this, b, h, "cut", `crash + kick ${h.tm} (Fold crop)`));
    ev(this, b, echoT, "cut", "bar line 79.864 (Echolalia)");
    echoCuts.forEach((h) => ev(this, b, h, "cut", `snare ${h.tm} (Echolalia crop)`));
    ev(this, b, stove, "cut", "kick + crash 81.486 (Stovetop)");
    stovePush.forEach((h) => ev(this, b, h, "flash", `crash + kick ${h.tm} (Stovetop PUNCH + edge glow)`));

    const fc = await lib.clipSequence("fold", { canvas: null });
    const ec = await lib.clipSequence("echolalia", { canvas: null });

    const BG = ctx.layer("bg", 8);
    const bgEcho = solid(BG, COLOR.family.echolaliaInk);
    const bgStove = solid(BG, COLOR.family.stovetopChar);
    const CL = ctx.layer("clip", 12);
    const canvas = el("canvas", { parent: CL, style: { position: "absolute", left: px(ZONE.x), top: px(ZONE.y), width: px(ZONE.w), height: px(ZONE.h) } });
    canvas.width = ZONE.w;
    canvas.height = ZONE.h;
    const c2d = canvas.getContext("2d");
    // Soft edges into the card background (gradients over the canvas, never masks).
    const edgeTop = el("div", { parent: CL, style: { position: "absolute", left: "0px", top: px(ZONE.y - 2), width: "1080px", height: "90px" } });
    const edgeBot = el("div", { parent: CL, style: { position: "absolute", left: "0px", top: px(ZONE.y + ZONE.h - 88), width: "1080px", height: "90px" } });
    const IL = ctx.layer("stove", 12);
    const SW = 900;
    const SH = (SW / 1200) * 1077;
    const stoveImg = el("img", { parent: IL, attrs: { src: "/art/site/stovetop/stovetop-hero.jpg", alt: "", draggable: "false" }, style: { position: "absolute", left: px(540 - SW / 2), top: px(930 - SH / 2), width: px(SW), height: px(SH), borderRadius: "12px", transformOrigin: "50% 50%" } });

    const flashes = flashBank(ctx, lib, stovePush.map((h) => ({ h, color: COLOR.family.stovetop, peak: 0.3, edge: true })));

    const TL = ctx.layer("type", 40);
    const fit = fitter();
    const brow = eyebrowLine(TL, fit, "MORE FROM KAIZEN DSP", { baseline: 300 });
    const cards = {
      fold: {
        name: headLine(TL, fit, { text: "Fold.", size: 104, baseline: 420 }).el,
        pill: pillLabel(TL, "FREE · COMING SOON", { x: 72, y: 460, h: 50, color: COLOR.family.fold, border: COLOR.family.fold, padX: 18 }),
        lines: [bodyLine(TL, fit, "A free spectral stereo shaper.", { size: 44, baseline: 1420 })],
      },
      echo: {
        name: headLine(TL, fit, { text: "Echolalia.", size: 104, baseline: 420 }).el,
        pill: pillLabel(TL, "DELAY + REVERB · COMING SOON", { x: 72, y: 460, h: 50, color: COLOR.family.echolalia, border: COLOR.family.echolalia, padX: 18 }),
        lines: [bodyLine(TL, fit, "Echoes that change", { size: 44, baseline: 1420 }), bodyLine(TL, fit, "as they return.", { size: 44, baseline: 1470, color: "#d8a066" })],
      },
      stove: {
        name: el("div", { parent: TL, text: "Stovetop.", style: { font: `400 110px "Sedgwick Ave Display", ${lib.type.FONT.display}`, color: COLOR.family.stovetop, transformOrigin: "0% 80%" } }),
        pill: pillLabel(TL, "IN DEVELOPMENT", { x: 72, y: 460, h: 50, color: COLOR.family.stovetop, border: COLOR.family.stovetop, padX: 18 }),
        lines: [bodyLine(TL, fit, "Add a little something-something.", { size: 44, baseline: 1420 })],
      },
    };
    lib.type.placeText(cards.stove.name, { x: 72, baseline: 420 });
    setStyle(cards.echo.lines[1], "fontStyle", "italic");

    const edge = (color) => [`linear-gradient(${color}, rgba(0,0,0,0))`, `linear-gradient(rgba(0,0,0,0), ${color})`];
    return {
      sequences: [fc.seq, ec.seq],
      setup() {
        fit.run();
      },
      render(t) {
        const on = inF(b, t, F0, F1);
        for (const l of [BG, CL, IL, TL]) show(l, on);
        flashes.render(t, on);
        if (!on) return;
        const f = b.frameAt(t);
        const card = f < FE ? "fold" : f < FS ? "echo" : "stove";
        vis(bgEcho, card === "echo");
        vis(bgStove, card === "stove");
        show(CL, card !== "stove");
        show(IL, card === "stove");

        if (card === "fold") {
          const k = b.stepIndex(foldCuts, t) + 1;
          const img = fc.seq.frames[Math.max(0, Math.min(fc.seq.count - 1, Math.round((1.0 + (t - fold.tf) - fc.meta.start) * fc.meta.fps)))];
          drawCover(c2d, img, FOLD_CROPS[k]);
          const [a, z] = edge("#050506");
          setStyle(edgeTop, "background", a);
          setStyle(edgeBot, "background", z);
        } else if (card === "echo") {
          const k = b.stepIndex(echoCuts, t) + 1;
          const pu = M.punch(t, [echoKick], { amp: 0.03 });
          const img = ec.seq.frames[Math.max(0, Math.min(ec.seq.count - 1, Math.round((ec.meta.clip_in + (t - b.onsetTime(echoT)) - ec.meta.start) * ec.meta.fps)))];
          drawCover(c2d, img, ECHO_CROPS[k], pu);
          const [a, z] = edge(COLOR.family.echolaliaInk);
          setStyle(edgeTop, "background", a);
          setStyle(edgeBot, "background", z);
        } else {
          const pu = M.punch(t, stovePush, { amp: 0.02 });
          setStyle(stoveImg, "transform", pu === 1 ? "" : `scale(${+pu.toFixed(5)})`);
        }

        // Type: the eyebrow holds; each card's name, pill and line cut in with the card.
        applyStamp(brow, M.stamp(t, fold));
        const cardHit = { fold, echo: echoT, stove };
        for (const [id, c] of Object.entries(cards)) {
          const mine = id === card;
          const st = mine ? M.stamp(t, cardHit[id]) : { on: false };
          applyStamp(c.name, st);
          vis(c.pill, mine);
          for (const n of c.lines) vis(n, mine);
        }
      },
    };
  },
};
