// The 3D hero camera move: 97 WebP frames (1760x990, every 2nd frame of the 24 fps master) drawn
// on a canvas with adjacent-frame blending, a grade and a zoom inside the draw call.
//
//   const hero = createHero(layer, { width: 1920, height: 1080 });   // return hero.seq from build()
//   hero.draw(96 * (t - 3) / 9, { scale: 1.02, grade: { saturate: 1 } });
//
// The canvas is placed with left/top and never transformed; push-ins go through `scale`.

import { ImageSequence } from "/__render/composition.js";
import { el, clamp } from "./util.js";

export const HERO_PATTERN = "/art/site/film/hero-frames/desktop/frame-{i}.webp";
export const HERO_FRAMES = 97;

export class Hero {
  constructor(parent, { x = 0, y = 0, width = 1920, height = 1080 } = {}) {
    this.w = width;
    this.h = height;
    this.canvas = el("canvas", { parent, cls: "hero" });
    Object.assign(this.canvas.style, { position: "absolute", left: `${x}px`, top: `${y}px`, width: `${width}px`, height: `${height}px` });
    // fps 1: the "time" given to drawAt is the frame index itself.
    this.seq = new ImageSequence({ pattern: HERO_PATTERN, count: HERO_FRAMES, pad: 3, fps: 1, canvas: this.canvas, fit: "cover", blend: true });
  }

  _size() {
    const dpr = window.devicePixelRatio || 1;
    const W = Math.round(this.w * dpr);
    const H = Math.round(this.h * dpr);
    if (this.canvas.width !== W || this.canvas.height !== H) {
      this.canvas.width = W;
      this.canvas.height = H;
      this.seq.ctx = this.canvas.getContext("2d", { alpha: true });
    }
  }

  /**
   * frame: fractional frame index 0..96 (blended between neighbours).
   * scale/originX/originY: zoom inside the draw. grade: { saturate, brightness, contrast }.
   */
  draw(frame, { scale = 1, originX = 0.5, originY = 0.5, grade = null } = {}) {
    this._size();
    const ctx = this.seq.ctx;
    const g = grade || {};
    const parts = [];
    if (g.saturate != null && g.saturate !== 1) parts.push(`saturate(${+g.saturate.toFixed(4)})`);
    if (g.brightness != null && g.brightness !== 1) parts.push(`brightness(${+g.brightness.toFixed(4)})`);
    if (g.contrast != null && g.contrast !== 1) parts.push(`contrast(${+g.contrast.toFixed(4)})`);
    ctx.filter = parts.length ? parts.join(" ") : "none";
    this.seq.drawAt(clamp(frame, 0, HERO_FRAMES - 1), { scale, originX, originY });
    ctx.filter = "none";
  }

  clear() {
    this._size();
    this.seq.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
}

export function createHero(parent, opts) {
  return new Hero(parent, opts);
}
