#!/usr/bin/env python3
"""Measure the film's GUI plate against reference images, control by control.

Input: stills of film/gallery/verify.html (one engine per still, plate at 1.0 at (0, 0)).
References (read in place, nothing copied):
  capture  public/engines/<e>-on.png   real plugin captures (older build: shared lever sheet)
  pillow   build/gui_verify/<e>.png    the Pillow rebuild that was checked against the captures
  v2       public/engines/v2/<e>-on.webp  the site's scripted composites (their own placement)
For every knob, the mix knob, the COLOR thumb and the switch it finds the offset (plate px) that
best aligns our crop with the reference (normalised cross-correlation of gradient magnitude,
sub-pixel peak). For readouts it compares the ink boxes of the text. Writes a JSON report and
side-by-side / blend images next to the stills.

  python3 film/tools/verify_plate.py /home/user/build/film/stills/verify
"""

import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

SITE = "/home/user/kaizendsp/public"
PILLOW = "/home/user/build/gui_verify"
ENGINES = ["green", "blue", "red", "purple", "black"]
READOUT = {"green": (0x9D, 0xBD, 0x78), "blue": (0x7F, 0xB8, 0xFF), "red": (0xFF, 0x8D, 0x8B), "purple": (0xB8, 0x8D, 0xD8), "black": (0xD4, 0xD4, 0xD4)}

sys.path.insert(0, os.path.dirname(__file__))


def layout():
    """Parse the plate layout from film/lib/layout.js (the single source for positions)."""
    src = open(os.path.join(os.path.dirname(__file__), "..", "lib", "layout.js")).read()
    out = {}
    import re

    for e in ENGINES:
        if e == "green":
            block = src[src.index("const G = {"):src.index("export const LAYOUT")]
        else:
            start = src.index(f"  {e}: {{")
            block = src[start:src.index("\n  },\n", start)]
        d = {}
        for key in ["rate", "depth", "offset", "width", "mix", "slider", "hq"]:
            m = re.search(rf"\b{key}: \[([^\]]+)\]", block)
            d[key] = [float(x) for x in m.group(1).split(",")]
        vals = {}
        vb = block[block.index("values: {"):]
        for key in ["rate", "depth", "offset", "width", "color", "mix"]:
            m = re.search(rf"\b{key}: \[([^\]]+)\]", vb)
            vals[key] = [float(x) for x in m.group(1).split(",")]
        d["values"] = vals
        out[e] = d
    return out


def gray(im):
    return np.asarray(im.convert("L"), dtype=np.float64)


def grad(a):
    gx = ndimage.sobel(a, 1)
    gy = ndimage.sobel(a, 0)
    return np.hypot(gx, gy)


def ncc_offset(a, b, box, search=12):
    """Offset (dx, dy) such that b(x + dx, y + dy) best matches a(x, y) inside box."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    A = a[y0:y1, x0:x1]
    A = A - A.mean()
    na = np.sqrt((A * A).sum()) + 1e-9
    best = None
    scores = np.full((2 * search + 1, 2 * search + 1), -1.0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            yy0, xx0 = y0 + dy, x0 + dx
            if yy0 < 0 or xx0 < 0 or yy0 + A.shape[0] > b.shape[0] or xx0 + A.shape[1] > b.shape[1]:
                continue
            B = b[yy0:yy0 + A.shape[0], xx0:xx0 + A.shape[1]]
            B = B - B.mean()
            s = (A * B).sum() / (na * (np.sqrt((B * B).sum()) + 1e-9))
            scores[dy + search, dx + search] = s
            if best is None or s > best[0]:
                best = (s, dx, dy)
    s, dx, dy = best
    iy, ix = dy + search, dx + search

    def sub(c, m, p):
        den = m - 2 * c + p
        return 0.0 if abs(den) < 1e-12 else 0.5 * (m - p) / den

    fx = sub(scores[iy, ix], scores[iy, ix - 1], scores[iy, ix + 1]) if 0 < ix < 2 * search else 0.0
    fy = sub(scores[iy, ix], scores[iy - 1, ix], scores[iy + 1, ix]) if 0 < iy < 2 * search else 0.0
    return round(float(dx + fx), 2), round(float(dy + fy), 2), round(float(s), 3)


def ink_box(rgb, box, color, tol=70):
    """Bounding box of pixels close to the readout colour (the text core) inside box."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    a = rgb[y0:y1, x0:x1].astype(np.float64)
    d = np.sqrt(((a - np.array(color, dtype=np.float64)) ** 2).sum(-1))
    lum = a.mean(-1)
    m = (d < tol) & (lum > 0.55 * np.mean(color))
    ys, xs = np.nonzero(m)
    if len(xs) < 5:
        return None
    return [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1)]


def capture_in_plate(e):
    """The real capture scaled into plate coordinates (1400x725), aligned by global search."""
    cap = Image.open(f"{SITE}/engines/{e}-on.png").convert("RGB")
    body = cap.crop((0, 52, 640, 384))
    return body.resize((1400, 725), Image.BICUBIC)


def v2_in_plate(e):
    """The v2 composite back in plate coordinates: it is the plate scaled to 1200 wide (621 tall), top 10 px cut."""
    im = Image.open(f"{SITE}/engines/v2/{e}-on.webp").convert("RGB")
    s = 1400 / 1200
    full = Image.new("RGB", (1200, 621))
    full.paste(im, (0, 10))
    return full.resize((1400, 725), Image.BICUBIC)


def main():
    stills_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/user/build/film/stills/verify"
    files = sorted(f for f in os.listdir(stills_dir) if f.startswith("still-") and f.endswith(".png"))
    L = layout()
    report = {}
    for i, e in enumerate(ENGINES):
        mine = Image.open(os.path.join(stills_dir, files[i])).convert("RGB").crop((0, 0, 1400, 725))
        refs = {
            "capture": capture_in_plate(e),
            "pillow": Image.open(f"{PILLOW}/{e}.png").convert("RGB"),
            "v2": v2_in_plate(e),
        }
        gm = grad(gray(mine))
        rm = np.asarray(mine)
        lay = L[e]
        er = {}
        for rname, ref in refs.items():
            gr = grad(gray(ref))
            rr = np.asarray(ref)
            res = {}
            for k in ["rate", "depth", "offset", "width", "mix"]:
                cx, cy, w, h = lay[k]
                r = w / 2 + 6
                res[k] = ncc_offset(gm, gr, (cx - r, cy - r, cx + r, cy + r))
            sx, sy, sw, sh, tw, th, ty = lay["slider"]
            tx = 473.8 + 498.5 * 0.5
            res["thumb"] = ncc_offset(gm, gr, (tx - tw / 2 - 4, ty - th / 2 - 2, tx + tw / 2 + 4, ty + th / 2 + 2))
            if rname == "v2":
                hx, hy, hw, hh = lay["hq"]
                k = hw / 512
                res["switch"] = ncc_offset(gm, gr, (hx + 190 * k, hy + 80 * k, hx + 322 * k, hy + 330 * k))
            ro = {}
            for k, (bx, by, bw, bh, right, fpx) in lay["values"].items():
                box = (bx - 10, by - 6, bx + bw + 10, by + bh + 6)
                a = ink_box(rm, box, READOUT[e])
                b = ink_box(rr, box, READOUT[e], tol=90)
                if a and b:
                    ro[k] = {"right": round(a[2] - b[2], 1), "cy": round((a[1] + a[3]) / 2 - (b[1] + b[3]) / 2, 1), "h": round((a[3] - a[1]) - (b[3] - b[1]), 1)}
                else:
                    ro[k] = None
            res["readouts"] = ro
            er[rname] = res
            # Visual: 50/50 blend.
            Image.blend(mine, ref, 0.5).save(os.path.join(stills_dir, f"blend-{e}-{rname}.png"))
        report[e] = er
    out = os.path.join(stills_dir, "verify-report.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=1)
    # Summary table: worst absolute offset per reference.
    for e in ENGINES:
        for rname, res in report[e].items():
            parts = []
            for k, v in res.items():
                if k == "readouts":
                    rs = [f"{kk}:{vv['right']:+.0f}/{vv['cy']:+.0f}" for kk, vv in v.items() if vv]
                    parts.append("text(right/cy) " + " ".join(rs))
                else:
                    parts.append(f"{k} {v[0]:+.1f},{v[1]:+.1f} ({v[2]:.2f})")
            print(f"{e:6s} {rname:7s} " + " | ".join(parts))
    print("report:", out)


if __name__ == "__main__":
    main()
