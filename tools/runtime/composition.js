// Browser-side runtime for deterministic compositions.
//
// Served by the render server at /__render/composition.js. Import it as an ES module:
//
//   import { defineComposition, ImageSequence } from "/__render/composition.js";
//
// The contract the renderer relies on is only this global:
//
//   window.__composition = { width, height, fps, duration, seek: async (t) => {} }
//
// seek(t) must leave the page in the exact visual state for time t (seconds), no matter which
// time was shown before. This module builds that object for you and handles the usual traps:
// fonts, image decode, GSAP's wall-clock ticker, CSS animations and transitions.

const EPS = 1e-6;

// GSAP's default force3D: "auto" writes 3D transforms while a tween is mid-flight, which promotes
// the element to a compositor layer. Compositor layers (mask-image in particular) are rasterized
// with scale heuristics that depend on earlier frames, so the same t could give different pixels
// depending on seek history (measured: up to 5/255 inside a mask). 2D transforms are painted by
// Blink at the exact scale every frame. This runs when this module is imported, i.e. before the
// importing module builds its timeline, as long as gsap.min.js is loaded by a classic <script>
// before it. from() tweens render at creation, so setting this later would be too late.
if (typeof window !== "undefined" && window.gsap) window.gsap.config({ force3D: false });

/** Resolve after DOMContentLoaded. */
function domReady() {
  if (document.readyState !== "loading") return Promise.resolve();
  return new Promise((resolve) => document.addEventListener("DOMContentLoaded", resolve, { once: true }));
}

/** Resolve after window "load" (all initial <img>, <link> and fonts referenced in CSS started). */
function windowLoaded() {
  if (document.readyState === "complete") return Promise.resolve();
  return new Promise((resolve) => window.addEventListener("load", resolve, { once: true }));
}

// ---------------------------------------------------------------------------------------------
// Deterministic randomness

/** Seeded PRNG (mulberry32). Returns a function like Math.random. */
export function seededRandom(seed = 1) {
  let a = seed >>> 0;
  return function random() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Stateless hash noise in [0, 1). Same inputs always give the same output, so it is safe to call
 * from render(t) in any seek order. Example: noise(frame, 3) for per-frame grain offsets.
 */
export function noise(i, salt = 0) {
  let h = (Math.floor(i) * 374761393 + Math.floor(salt) * 668265263) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
  h = (h ^ (h >>> 16)) >>> 0;
  return h / 4294967296;
}

// ---------------------------------------------------------------------------------------------
// Fonts

function familyOf(spec) {
  // CSS font shorthand: "[style] [weight] size[/lh] family[, fallback]". Take the first family.
  const m = spec.match(/(?:^|\s)[\d.]+(?:px|pt|em|rem|%)(?:\/\S+)?\s+(.+)$/);
  const fam = (m ? m[1] : spec).split(",")[0].trim();
  return fam.replace(/^["']|["']$/g, "");
}

/**
 * Load fonts and fail loudly if any is missing. specs are CSS font shorthands, e.g.
 * ["600 100px Fraunces", "italic 400 100px Fraunces", "700 20px Inter"].
 * document.fonts.check() alone is not enough: it returns true for a family that has no
 * @font-face at all (it just falls back), so we also require a loaded FontFace of that family.
 */
export async function loadFonts(specs = []) {
  const results = await Promise.all(specs.map((s) => document.fonts.load(s).catch(() => [])));
  await document.fonts.ready;
  const missing = [];
  specs.forEach((spec, i) => {
    const fam = familyOf(spec);
    const loadedFaces = results[i].filter((f) => f.status === "loaded");
    const anyFace = [...document.fonts].some(
      (f) => f.family.replace(/^["']|["']$/g, "") === fam && f.status === "loaded",
    );
    if (!loadedFaces.length || !anyFace || !document.fonts.check(spec)) missing.push(spec);
  });
  if (missing.length) {
    throw new Error(
      `Fonts not available: ${missing.join(" | ")}. Check the @font-face / fontsource <link> and the family name.`,
    );
  }
}

// ---------------------------------------------------------------------------------------------
// Images

/** Load and decode one image URL. Rejects on 404 or decode error. */
export function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "sync";
    img.onload = () => img.decode().then(() => resolve(img), () => resolve(img));
    img.onerror = () => reject(new Error(`Image failed to load: ${url}`));
    img.src = url;
  });
}

/** Load many URLs with limited concurrency. Returns images in input order. */
export async function preloadImages(urls, { concurrency = 8, onProgress } = {}) {
  const out = new Array(urls.length);
  let next = 0;
  let done = 0;
  async function worker() {
    while (next < urls.length) {
      const i = next++;
      out[i] = await loadImage(urls[i]);
      done++;
      if (onProgress) onProgress(done, urls.length);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, urls.length) }, worker));
  return out;
}

/** Wait until every <img> in root is loaded and decoded. Throws on broken images. */
export async function decodeImages(root = document) {
  const imgs = [...root.querySelectorAll("img")];
  await Promise.all(
    imgs.map(async (img) => {
      if (img.loading === "lazy") img.loading = "eager";
      if (!img.complete) {
        await new Promise((resolve) => {
          img.addEventListener("load", resolve, { once: true });
          img.addEventListener("error", resolve, { once: true });
        });
      }
      if (img.currentSrc && img.naturalWidth === 0) throw new Error(`Broken image: ${img.currentSrc}`);
      if (img.currentSrc) await img.decode().catch(() => {});
    }),
  );
}

/** Preload url(...) images used in computed background-image / mask-image / border-image. */
export async function preloadCssImages(root = document) {
  const urls = new Set();
  const re = /url\(["']?([^"')]+)["']?\)/g;
  for (const el of root.querySelectorAll("*")) {
    const cs = getComputedStyle(el);
    for (const prop of ["backgroundImage", "maskImage", "webkitMaskImage", "borderImageSource", "listStyleImage"]) {
      const v = cs[prop];
      if (!v || v === "none") continue;
      for (const m of v.matchAll(re)) if (!m[1].startsWith("data:")) urls.add(m[1]);
    }
  }
  await preloadImages([...urls]);
}

// ---------------------------------------------------------------------------------------------
// Image sequences (use these instead of <video>)

/**
 * A pre-extracted frame sequence drawn onto a <canvas>.
 *
 *   const seq = new ImageSequence({
 *     pattern: "/assets/hero/frame-{i}.webp", count: 97, pad: 3, fps: 12,
 *     canvas: "#hero", fit: "cover", blend: true,
 *   });
 *   // pass it to defineComposition({ sequences: [seq] }) so it is preloaded before frame 0,
 *   // then in render(t): seq.drawAt(t - startTime, { scale: 1 + 0.02 * t })
 *
 * Every frame is fetched and decoded before the first seek. Drawing is a synchronous
 * drawImage() of an already decoded image, so what you draw is on screen when seek() resolves.
 * Swapping <img>.src per frame is NOT safe: decode is async and you can capture a stale frame.
 *
 * fit: null (default) sizes the canvas bitmap to the image and draws it 1:1 (use CSS to place
 * it). fit: "cover" | "contain" | "fill" sizes the bitmap to the canvas's CSS box times
 * devicePixelRatio and draws the image into it with high-quality smoothing, so --scale 2 gets
 * real 4K pixels.
 *
 * Zoom and pan (Ken Burns) go through the `view` argument of drawAt(), NOT a CSS transform on
 * the canvas or a parent: canvases are compositor layers, and animated transforms around them
 * can make pixels depend on earlier frames (see render-pipeline.md, determinism rules).
 */
export class ImageSequence {
  constructor({
    urls = null,
    pattern = null,
    start = 0,
    count = 0,
    pad = 3,
    fps = 24,
    canvas = null,
    fit = null,
    blend = false,
    loop = false,
    bitmaps = false,
    concurrency = 8,
  } = {}) {
    if (!urls) {
      if (!pattern || !count) throw new Error("ImageSequence needs urls[] or pattern + count");
      urls = Array.from({ length: count }, (_, k) => pattern.replace("{i}", String(start + k).padStart(pad, "0")));
    }
    if (fit && !["cover", "contain", "fill"].includes(fit)) throw new Error(`ImageSequence fit "${fit}" is not cover|contain|fill`);
    this.urls = urls;
    this.count = urls.length;
    this.fps = fps;
    this.fit = fit;
    this.blend = blend;
    this.loop = loop;
    this.bitmaps = bitmaps;
    this.concurrency = concurrency;
    this.canvas = typeof canvas === "string" ? document.querySelector(canvas) : canvas;
    if (canvas && !this.canvas) throw new Error(`ImageSequence: canvas ${canvas} not found`);
    this.frames = null;
    this.width = 0;
    this.height = 0;
  }

  /** Duration in seconds when played at its own fps. */
  get duration() {
    return this.count / this.fps;
  }

  async load() {
    if (this.frames) return;
    if (this.bitmaps) {
      // Fully decoded ImageBitmaps: fastest drawing, but costs width*height*4 bytes per frame.
      this.frames = await Promise.all(
        this.urls.map(async (u) => {
          const r = await fetch(u);
          if (!r.ok) throw new Error(`Sequence frame ${r.status}: ${u}`);
          return createImageBitmap(await r.blob());
        }),
      );
    } else {
      this.frames = await preloadImages(this.urls, { concurrency: this.concurrency });
    }
    const f0 = this.frames[0];
    this.width = f0.naturalWidth || f0.width;
    this.height = f0.naturalHeight || f0.height;
    if (this.canvas) {
      let w = this.width;
      let h = this.height;
      if (this.fit) {
        const r = this.canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        w = Math.max(1, Math.round(r.width * dpr));
        h = Math.max(1, Math.round(r.height * dpr));
      }
      if (this.canvas.width !== w || this.canvas.height !== h) {
        this.canvas.width = w;
        this.canvas.height = h;
      }
      this.ctx = this.canvas.getContext("2d", { alpha: true });
    }
  }

  /** Continuous frame position for local time tLocal (seconds since the sequence started). */
  positionAt(tLocal) {
    let p = tLocal * this.fps;
    if (this.loop) p = ((p % this.count) + this.count) % this.count;
    else p = Math.min(Math.max(p, 0), this.count - 1);
    return p;
  }

  /** Integer frame index for local time. */
  indexAt(tLocal) {
    return Math.min(this.count - 1, Math.floor(this.positionAt(tLocal) + EPS));
  }

  /**
   * Draw the frame for tLocal. With blend: true, crossfades neighbouring frames (slow motion).
   * view: { scale = 1, originX = 0.5, originY = 0.5, x = 0, y = 0 } zooms around the origin
   * (fractions of the canvas) and pans by x/y (fractions of the canvas).
   */
  drawAt(tLocal, view = null, ctx = this.ctx) {
    const p = this.positionAt(tLocal);
    const i0 = Math.min(this.count - 1, Math.floor(p + EPS));
    const frac = p - i0;
    if (!this.blend || frac < 1e-4) return this.drawFrame(i0, { view, ctx });
    const i1 = this.loop ? (i0 + 1) % this.count : Math.min(i0 + 1, this.count - 1);
    this.drawFrame(i0, { view, ctx });
    this.drawFrame(i1, { view, ctx, alpha: frac, clear: false });
    return i0;
  }

  /** Destination rectangle for the image in canvas pixels, after fit and view. */
  destRect(cw, ch, view) {
    const iw = this.width;
    const ih = this.height;
    let dw = cw;
    let dh = ch;
    if (this.fit === "cover" || this.fit === "contain") {
      const k = this.fit === "cover" ? Math.max(cw / iw, ch / ih) : Math.min(cw / iw, ch / ih);
      dw = iw * k;
      dh = ih * k;
    }
    let dx = (cw - dw) / 2;
    let dy = (ch - dh) / 2;
    if (view) {
      const s = view.scale ?? 1;
      const ox = (view.originX ?? 0.5) * cw;
      const oy = (view.originY ?? 0.5) * ch;
      dx = ox + (dx - ox) * s + (view.x ?? 0) * cw;
      dy = oy + (dy - oy) * s + (view.y ?? 0) * ch;
      dw *= s;
      dh *= s;
    }
    return [dx, dy, dw, dh];
  }

  drawFrame(i, { alpha = 1, ctx = this.ctx, clear = true, view = null } = {}) {
    if (!this.frames) throw new Error("ImageSequence.drawFrame before load()");
    if (!ctx) throw new Error("ImageSequence has no canvas");
    const img = this.frames[Math.max(0, Math.min(this.count - 1, i))];
    const { width: cw, height: ch } = ctx.canvas;
    if (clear) ctx.clearRect(0, 0, cw, ch);
    ctx.globalAlpha = alpha;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, ...this.destRect(cw, ch, view));
    ctx.globalAlpha = 1;
    return i;
  }
}

// ---------------------------------------------------------------------------------------------
// Animation clocks

/** Put every CSS animation / WAAPI animation on the composition clock and finish transitions. */
export function syncDocumentAnimations(t) {
  const ms = t * 1000;
  for (const a of document.getAnimations()) {
    if (typeof CSSTransition !== "undefined" && a instanceof CSSTransition) {
      a.finish();
      continue;
    }
    if (a.playState !== "paused") a.pause();
    a.currentTime = ms;
  }
}

/** Stop GSAP from advancing anything on the wall clock. Seek your own timeline instead. */
export function freezeGsap(gsap, master) {
  if (!gsap || gsap.__frozenForRender) return;
  gsap.__frozenForRender = true;
  gsap.config({ force3D: false });
  gsap.ticker.lagSmoothing(0);
  if (gsap.updateRoot) gsap.ticker.remove(gsap.updateRoot);
  const stray = gsap.globalTimeline.getChildren(false, true, true).filter((c) => c !== master);
  if (stray.length) {
    console.warn(
      `[composition] ${stray.length} GSAP animation(s) are not in the master timeline; they will not move. ` +
        "Add them to the timeline you pass to defineComposition().",
    );
  }
}

/**
 * Warn (console.warn, shown by the renderer) about constructs that measured as seek-order
 * dependent in Chromium 141. Both come from compositor layers, whose raster scale depends on
 * earlier frames. <canvas>, <video> and <iframe> are always compositor layers; will-change and
 * 3D transforms make one too.
 *   Rule 1: a CSS mask-image on, or around, a compositor layer.
 *   Rule 2: a tweened scale / 3D transform on an element that contains a canvas or video.
 * Called once when the composition is ready. Returns the list of problems.
 */
export function lintDeterminism(root = document, timeline = null) {
  const problems = [];
  const id = (n) => n.tagName.toLowerCase() + (n.id ? `#${n.id}` : "") + (n.classList.length ? "." + [...n.classList].join(".") : "");
  const LAYER = "canvas, video, iframe";
  // Rule 2: an element whose scale / 3D transform is tweened and which contains a canvas or
  // video. Chromium splits it into compositor layers whose raster scale depends on earlier frames
  // (measured: 11 of 12 re-captures differed, up to 31/255). will-change: transform only moves
  // the problem: the raster scale is then fixed at the first visible frame, which differs per
  // worker. Zoom inside the canvas instead (ImageSequence.drawAt(t, { scale })).
  if (timeline && typeof timeline.getChildren === "function") {
    const SCALE_PROPS = ["scale", "scaleX", "scaleY", "transform", "rotationX", "rotationY", "rotateX", "rotateY", "z", "transformPerspective"];
    const seen = new Set();
    for (const tw of timeline.getChildren(true, true, false)) {
      const vars = { ...(tw.vars || {}), ...((tw.vars && tw.vars.startAt) || {}) };
      if (!SCALE_PROPS.some((k) => k in vars)) continue;
      for (const el of tw.targets()) {
        if (!(el instanceof Element) || seen.has(el) || el.matches(LAYER)) continue;
        seen.add(el);
        if (el.querySelector(LAYER)) {
          problems.push(`${id(el)} has a tweened scale/3D transform and contains ${id(el.querySelector(LAYER))}; zoom inside the canvas draw instead`);
        }
      }
    }
  }
  // Rule 1: CSS mask over a compositor layer.
  for (const el of root.querySelectorAll("*")) {
    const cs = getComputedStyle(el);
    const mask = cs.maskImage || cs.webkitMaskImage;
    if (!mask || mask === "none") continue;
    const layered = [el, ...el.querySelectorAll("*")].find((n) => {
      if (/^(CANVAS|VIDEO|IFRAME)$/.test(n.tagName)) return true;
      const s = getComputedStyle(n);
      return /transform|opacity/.test(s.willChange) || /matrix3d|3d\(|perspective/.test(s.transform);
    });
    if (layered) {
      problems.push(`mask-image on ${id(el)} covers compositor layer ${id(layered)}; use a gradient overlay or mask inside the canvas`);
    }
  }
  for (const p of problems) {
    console.warn(`[composition] non-deterministic construct: ${p}. See docs/brief/render-pipeline.md (determinism rules).`);
  }
  return problems;
}

// ---------------------------------------------------------------------------------------------
// The composition

/**
 * defineComposition({
 *   width: 1920, height: 1080, fps: 60, duration: 5,
 *   timeline,            // optional paused GSAP timeline; seek(t) calls timeline.seek(t)
 *   fonts: [],           // CSS font shorthands that must be loaded before frame 0
 *   sequences: [],       // ImageSequence instances to preload
 *   setup: async () => {},        // extra async preparation
 *   render: (t, info) => {},      // per-frame procedural drawing, called after the timeline seek
 *   cssAnimations: true,          // drive CSS animations / transitions from t
 *   timelineEvents: false,        // fire GSAP callbacks on seek (off: not seek-order safe)
 * })
 */
export function defineComposition(opts) {
  const {
    width = 1920,
    height = 1080,
    fps = 60,
    duration,
    timeline = null,
    fonts = [],
    sequences = [],
    setup = null,
    render = null,
    cssAnimations = true,
    timelineEvents = false,
  } = opts;
  if (!(duration > 0)) throw new Error("defineComposition: duration (seconds) is required");

  const comp = {
    width,
    height,
    fps,
    duration,
    time: NaN,
    frame: -1,
    ready: null,
    error: null,
    async seek(t) {
      await comp.ready;
      if (!Number.isFinite(t)) throw new Error(`seek(${t}): not a number`);
      comp.time = t;
      comp.frame = Math.round(t * fps);
      if (timeline) timeline.seek(t, !timelineEvents);
      if (cssAnimations) syncDocumentAnimations(t);
      if (render) await render(t, { frame: comp.frame, fps, duration, width, height });
      if (cssAnimations) syncDocumentAnimations(t); // render() may have started new animations
      await settle();
      return comp.frame;
    },
  };

  async function settle() {
    if (document.fonts.status !== "loaded") await document.fonts.ready;
    const pending = [...document.images].filter((img) => !img.complete);
    if (pending.length) await decodeImages(document);
  }

  comp.ready = (async () => {
    await domReady();
    if (timeline && window.gsap) freezeGsap(window.gsap, timeline);
    if (timeline && typeof timeline.pause === "function") timeline.pause();
    await windowLoaded();
    await loadFonts(fonts);
    await Promise.all(sequences.map((s) => s.load()));
    if (setup) await setup();
    await decodeImages(document);
    await preloadCssImages(document);
    await document.fonts.ready;
    lintDeterminism(document, timeline);
    if (document.querySelector("video")) {
      console.warn("[composition] <video> elements are not frame-accurate. Use an ImageSequence.");
    }
  })();
  comp.ready.catch((e) => {
    comp.error = String((e && e.stack) || e);
    console.error("[composition] setup failed:", comp.error);
  });

  window.__composition = comp;
  return comp;
}
