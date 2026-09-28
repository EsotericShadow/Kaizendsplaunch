// Film grain (treatment G0): the site's 200 px grain tile, tiled at 5% in overlay blend. Each frame
// shifts the tile by a hash of the frame number, so it is deterministic in any seek order; in
// stillness (G1) it is frozen at one offset. Plain CSS background: no canvas, no animation.
//
//   const grain = createGrain(layer, { opacity: 0.05 });
//   grain.render(t, { frozen: t < 2.25 });

import { el, setStyle, noise } from "./util.js";

export const GRAIN_URL = "/art/site/film/grain.png";

export class Grain {
  constructor(parent, { opacity = 0.05, tile = 200, url = GRAIN_URL, blend = "overlay", salt = 7 } = {}) {
    this.tile = tile;
    this.salt = salt;
    this.el = el("div", {
      parent,
      cls: "grain",
      style: {
        position: "absolute",
        inset: "0",
        backgroundImage: `url("${url}")`,
        backgroundSize: `${tile}px ${tile}px`,
        backgroundRepeat: "repeat",
        mixBlendMode: blend,
        opacity: String(opacity),
        pointerEvents: "none",
      },
    });
  }

  /** frozen: hold one offset (G1 stillness). opacity: optional override. */
  render(t, { frozen = false, opacity = null, frozenFrame = 0 } = {}) {
    const f = frozen ? frozenFrame : Math.round(t * 60);
    const x = Math.floor(noise(f, this.salt) * this.tile);
    const y = Math.floor(noise(f, this.salt + 1) * this.tile);
    setStyle(this.el, "backgroundPosition", `${x}px ${y}px`);
    if (opacity != null) setStyle(this.el, "opacity", String(+opacity.toFixed(4)));
  }
}

export function createGrain(parent, opts) {
  return new Grain(parent, opts);
}
