// ChorusType (treatment G3): an italic accent as one dry layer that never moves, plus wet copies in
// the engine hue that move at the heard settings. It is a visual translation of the chorus, not a
// measurement (the scope is the measurement).
//
//   const ct = createChorusType(accentSpan, { law: "SINE", engine: "green" });
//   ct.render(t, cues.settingsAt("R01", t));          // or any { rate, depth, offset, width, color, mix, cycles }
//
// Laws, with R (Hz), D (0..1), Phi (offset, radians), W (0..2), phase = 2 pi cycles:
//   SINE   wet L x = -(W-1) 0.12em + D 0.5em sin(phase), wet R x = +(W-1) 0.12em + D 0.5em sin(phase + Phi),
//          blur 0.4 px. Black Ensemble adds two layers at R x 1.07, opacity (0.18 + 0.32 Color) 0.6 Mix.
//   STEP   SINE with x quantised to 3 px, blur 0.8 px (Red BBD).
//   WOW    SINE x (1 + 0.25 sin 2 pi 0.33 t) plus 0.6 px sin(2 pi 5.8 t), blur 1.2 px (Red Tape).
//   ORBIT  wet layers travel 0.5em x 0.2em ellipses at R, R layer +90 deg, axis turns at 0.03 Hz.
// Wet opacity 0.6 x Mix, mix-blend-mode screen.

import { el, setStyle, px, TAU, clamp } from "./util.js";
import { HUE } from "./type.js";

export const LAWS = ["SINE", "STEP", "WOW", "ORBIT"];

export class ChorusType {
  /**
   * target: the element holding the accent text (its text is copied into the layers).
   * opts: { law, engine, hue, ensemble (default: engine === "black"), dryColor }
   */
  constructor(target, { law = "SINE", engine = "green", hue = null, ensemble = null, dryColor = "#d0bdff" } = {}) {
    this.target = target;
    this.law = law;
    this.engine = engine;
    this.hue = hue || HUE[engine];
    this.ensemble = ensemble ?? engine === "black";
    const text = target.textContent;
    target.textContent = "";
    Object.assign(target.style, { position: "relative", display: "inline-block" });
    // The dry layer stays in flow, so the accent keeps its exact place in the line.
    this.dry = el("span", { parent: target, text, style: { color: dryColor, position: "relative" } });
    const wet = () =>
      el("span", {
        parent: target,
        text,
        style: {
          position: "absolute",
          left: "0px",
          top: "0px",
          color: this.hue,
          mixBlendMode: "screen",
          whiteSpace: "pre",
          pointerEvents: "none",
        },
      });
    this.wet = [wet(), wet()];
    this.ens = this.ensemble ? [wet(), wet()] : [];
    this.fontPx = null;
  }

  setLaw(law) {
    this.law = law;
  }

  _em() {
    if (this.fontPx == null) this.fontPx = parseFloat(getComputedStyle(this.target).fontSize) || 100;
    return this.fontPx;
  }

  /**
   * s: { rate, depth (%), offset (deg), width (%), color (%), mix (%), cycles } in display units,
   * as Cues.settingsAt returns. cycles is the integrated LFO phase; without it rate * t is used.
   */
  render(t, s, { opacity = 1 } = {}) {
    const em = this._em();
    const R = s.rate;
    const D = s.depth / 100;
    const W = s.width / 100;
    const Phi = (s.offset * Math.PI) / 180;
    const mix = s.mix / 100;
    const cyc = s.cycles ?? R * t;
    const ph = TAU * cyc;
    const law = this.law;
    let blur = 0.4;
    let pos;
    if (law === "ORBIT") {
      blur = 0.4;
      const ax = TAU * 0.03 * t;
      const a = 0.25 * em;
      const b = 0.1 * em;
      const spread = (W - 1) * 0.12 * em;
      const orbit = (angle, side) => {
        const ex = a * Math.cos(angle);
        const ey = b * Math.sin(angle);
        return [side * spread + ex * Math.cos(ax) - ey * Math.sin(ax), ex * Math.sin(ax) + ey * Math.cos(ax)];
      };
      pos = [orbit(ph, -1), orbit(ph + Math.PI / 2, 1)];
    } else {
      const amp = D * 0.5 * em;
      let xl = -(W - 1) * 0.12 * em + amp * Math.sin(ph);
      let xr = (W - 1) * 0.12 * em + amp * Math.sin(ph + Phi);
      if (law === "STEP") {
        blur = 0.8;
        xl = Math.round(xl / 3) * 3;
        xr = Math.round(xr / 3) * 3;
      } else if (law === "WOW") {
        blur = 1.2;
        const k = 1 + 0.25 * Math.sin(TAU * 0.33 * t);
        const flutter = 0.6 * Math.sin(TAU * 5.8 * t);
        xl = xl * k + flutter;
        xr = xr * k + flutter;
      }
      pos = [[xl, 0], [xr, 0]];
    }
    const wetA = clamp(0.6 * mix * opacity);
    for (let i = 0; i < 2; i++) {
      const n = this.wet[i];
      setStyle(n, "transform", `translate(${px(pos[i][0])}, ${px(pos[i][1])})`);
      setStyle(n, "opacity", String(+wetA.toFixed(4)));
      setStyle(n, "filter", `blur(${blur}px)`);
    }
    if (this.ens.length) {
      const ph2 = TAU * cyc * 1.07;
      const amp = D * 0.5 * em;
      const xs = [-(W - 1) * 0.12 * em + amp * Math.sin(ph2 + Math.PI / 3), (W - 1) * 0.12 * em + amp * Math.sin(ph2 + Phi + Math.PI / 3)];
      const a = clamp((0.18 + 0.32 * (s.color / 100)) * 0.6 * mix * opacity);
      for (let i = 0; i < 2; i++) {
        const n = this.ens[i];
        setStyle(n, "transform", `translate(${px(xs[i])}, 0px)`);
        setStyle(n, "opacity", String(+a.toFixed(4)));
        setStyle(n, "filter", `blur(${blur}px)`);
      }
    }
    setStyle(this.dry, "opacity", opacity >= 1 ? "" : String(+opacity.toFixed(4)));
  }
}

export function createChorusType(target, opts) {
  return new ChorusType(target, opts);
}
