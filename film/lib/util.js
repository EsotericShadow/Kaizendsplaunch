// Small pure helpers. Everything here depends only on its arguments, so it is safe to call from
// render(t) in any seek order.

export { noise, seededRandom } from "/__render/composition.js";

export const TAU = Math.PI * 2;

export const clamp = (x, lo = 0, hi = 1) => (x < lo ? lo : x > hi ? hi : x);
export const lerp = (a, b, u) => a + (b - a) * u;
export const invLerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
/** 0..1 progress of t through [t0, t1], clamped. */
export const progress = (t, t0, t1) => clamp(invLerp(t0, t1, t));
export const smoothstep = (u) => {
  u = clamp(u);
  return u * u * (3 - 2 * u);
};
/** The plugin's switch blend: t^3 (t (6t - 15) + 10). */
export const smootherstep = (u) => {
  u = clamp(u);
  return u * u * u * (u * (u * 6 - 15) + 10);
};

// GSAP-compatible eases (same formulas as gsap 3), so audio automation, picture and tweens agree.
export const EASES = {
  linear: (u) => u,
  none: (u) => u,
  "sine.in": (u) => 1 - Math.cos((u * Math.PI) / 2),
  "sine.out": (u) => Math.sin((u * Math.PI) / 2),
  "sine.inOut": (u) => -(Math.cos(Math.PI * u) - 1) / 2,
  "power1.inOut": (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2),
  "power2.inOut": (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2),
  "power2.out": (u) => 1 - Math.pow(1 - u, 3),
  "power2.in": (u) => u * u * u,
  "expo.out": (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u)),
  smootherstep,
  step: (u) => (u > 0 ? 1 : 0),
};

export function ease(name, u) {
  const f = EASES[name];
  if (!f) throw new Error(`Unknown ease "${name}"`);
  return f(clamp(u));
}

/** Eased value of a [t0, t1] move from a to b at time t (holds a before, b after). */
export function tweenAt(t, t0, t1, a, b, easeName = "sine.inOut") {
  if (t <= t0) return a;
  if (t >= t1) return b;
  return lerp(a, b, ease(easeName, (t - t0) / (t1 - t0)));
}

/** Opacity for a hold with optional fade in/out ramps (seconds). */
export function envelope(t, t0, t1, fadeIn = 0, fadeOut = 0) {
  if (t < t0 || t >= t1) return 0;
  let a = 1;
  if (fadeIn > 0) a = Math.min(a, (t - t0) / fadeIn);
  if (fadeOut > 0) a = Math.min(a, (t1 - t) / fadeOut);
  return clamp(a);
}

/** True when t is inside [t0, t1). */
export const inWindow = (t, t0, t1) => t >= t0 && t < t1;

/** Frame index for time t at fps (the renderer's rounding). */
export const frameOf = (t, fps = 60) => Math.round(t * fps);

/** Parse "#rrggbb" into [r, g, b]. */
export function hexToRgb(hex) {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.replace(/(.)/g, "$1$1") : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
export function rgba(hex, a) {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${+a.toFixed(4)})`;
}

/** Smooth 1D value noise in [-1, 1], deterministic. */
export function valueNoise(x, salt = 0) {
  const i = Math.floor(x);
  const f = x - i;
  const h = (k) => {
    let n = (Math.imul(k, 374761393) + Math.imul(salt | 0, 668265263)) >>> 0;
    n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
    return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
  };
  const u = f * f * (3 - 2 * f);
  return lerp(h(i), h(i + 1), u) * 2 - 1;
}

// DOM helpers --------------------------------------------------------------------------------

/** document.createElement with class, inline style object and text. */
export function el(tag, { cls = "", style = null, text = null, html = null, attrs = null, parent = null } = {}) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (style) Object.assign(n.style, style);
  if (text != null) n.textContent = text;
  if (html != null) n.innerHTML = html;
  if (attrs) for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
}

const SVGNS = "http://www.w3.org/2000/svg";
export function svg(tag, attrs = {}, parent = null) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
}

/**
 * Write a style property only when it changes. Cuts style invalidation when render(t) runs for
 * every scene on every frame.
 */
export function setStyle(node, prop, value) {
  const cache = node.__st || (node.__st = {});
  if (cache[prop] === value) return;
  cache[prop] = value;
  node.style[prop] = value;
}

/**
 * Show or hide with visibility (keeps layout, so canvases keep their size while hidden). "Shown"
 * clears the property so the node inherits: a hidden layer hides everything inside it.
 */
export function show(node, on) {
  setStyle(node, "visibility", on ? "" : "hidden");
}

export function setText(node, text) {
  if (node.__txt === text) return;
  node.__txt = text;
  node.textContent = text;
}

/** Round to 1/1000 px for style strings (keeps strings stable between identical frames). */
export const px = (v) => `${Math.round(v * 1000) / 1000}px`;
