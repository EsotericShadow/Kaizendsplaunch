// Product-clip footage as image sequences (the renderer forbids <video>). `film/film.sh frames`
// extracts each clip window from cues.json to /data/frames/<name>/frame-NNNN.webp at 60 fps, with
// 0.5 s of margin, and writes meta.json { start, fps, count, clip_in, clip_out }.
//
//   const fold = await clipSequence("fold", { canvas });     // in build(); return fold.seq in sequences
//   fold.drawClipTime(1.0 + (t - 62.25), { scale });         // draw by CLIP time, in render(t)

import { ImageSequence } from "/__render/composition.js";

export async function clipSequence(name, { canvas = null, fit = "cover" } = {}) {
  const r = await fetch(`/data/frames/${name}/meta.json`);
  if (!r.ok) throw new Error(`clip ${name}: run film/film.sh frames (${r.status})`);
  const meta = await r.json();
  const seq = new ImageSequence({
    pattern: `/data/frames/${name}/frame-{i}.webp`,
    count: meta.count,
    pad: 4,
    fps: meta.fps,
    canvas,
    fit,
    blend: false,
  });
  return {
    meta,
    seq,
    /** Draw the frame at clip time tc (seconds in the source clip). */
    drawClipTime(tc, view = null) {
      return seq.drawAt(tc - meta.start, view);
    },
  };
}
