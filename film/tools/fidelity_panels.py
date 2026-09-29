#!/usr/bin/env python3
"""Compare the film plate with the owner's full-panel renders, for the engines the release editor
cannot show to a new user (Blue, Red, Black are paid engines) and as a second check on Green and
Purple (film/UI_FIDELITY.md).

  python3 film/tools/fidelity_panels.py <stills dir> <out dir> [tag]

<stills dir>: stills of film/gallery/fidelity.html, one per second; after the reference states
come six in the switch-panel pose (HQ lit, knobs at 12 o'clock, COLOR 50 %) for green, blue, red,
purple, black, white, window at (0, 0), scale 1. The owner's panels (Choroboros/assets/switch-panels/<engine>-on.png, 1774 x 887, body
only, no readouts) are registered onto the plate body by a per-axis scale and offset fitted on the
backpanel texture (phase correlation on a grid of patches, controls masked out). Then each control
is registered on its own: the printed shift is where the plate's control sits relative to the
owner's (plate px, + = the plate's is right / below). Writes <tag>-panel-<engine>-side.png
(owner | plate), -blend.png (50/50) and -diff.png (x4), and <tag>-panels.json.
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OWNER = os.path.join(REPO, "Choroboros/assets/switch-panels")
K = 1400 / 638
HEADER = 56 * K
BODY = (1400, round(330 * K))  # 1400 x 724
ENGINES = ["green", "blue", "red", "purple", "black"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rc_layout import ENGINES as RC_ENGINES, layout_for  # noqa: E402


def shift(a, b):
    """Sub-pixel (dx, dy) to apply to b to align it with a (windowed phase correlation)."""
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.fft2((a - a.mean()) * win)
    fb = np.fft.fft2((b - b.mean()) * win)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.real(np.fft.ifft2(r))
    iy, ix = np.unravel_index(np.argmax(c), c.shape)

    def sub(i, n, axis):
        lo = c[(iy - 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix - 1) % c.shape[1]]
        m = c[iy, ix]
        hi = c[(iy + 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix + 1) % c.shape[1]]
        d = lo - 2 * m + hi
        v = i + (0.5 * (lo - hi) / d if abs(d) > 1e-12 else 0.0)
        return v - n if v > n / 2 else v

    return sub(ix, c.shape[1], 1), sub(iy, c.shape[0], 0), float(c.max())


def grad(a):
    a = ndimage.gaussian_filter(a, 0.8)
    return np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1))


def control_boxes(engine):
    """Control rects in body plate px from the RC layout (knobs, mix, hq, color slider)."""
    L = json.load(open(os.path.join(os.environ.get("CHORO_RC", "/home/user/choroboros-rc"), "json_defaults_dump.json")))["layout"]
    g = layout_for(L, RC_ENGINES.index(engine))
    out = {}
    for k in ("rate", "depth", "offset", "width", "mix", "hq", "color"):
        x, y, w, h = g[k]
        out[k] = (x * K, (y - 56) * K, w * K, h * K)
    return out


def fit(plate_g, owner_g, mask):
    """Per-axis owner_px = s * plate_px + t from texture patches outside the controls."""
    H, W = plate_g.shape
    ow = np.asarray(Image.fromarray(owner_g.astype(np.float32)).resize((W, H), Image.LANCZOS), np.float64)
    pts, d = [], []
    for y in range(30, H - 150, 60):
        for x in range(30, W - 150, 70):
            if mask[y:y + 120, x:x + 120].mean() > 0.15:
                continue
            a = plate_g[y:y + 120, x:x + 120]
            if a.std() < 5:
                continue
            dx, dy, peak = shift(grad(a), grad(ow[y:y + 120, x:x + 120]))
            if peak < 0.05:
                continue
            pts.append((x + 60, y + 60))
            d.append((dx, dy))
    pts, d = np.array(pts, float), np.array(d, float)
    sx0, sy0 = owner_g.shape[1] / W, owner_g.shape[0] / H
    res = []
    for ax, s0 in ((0, sx0), (1, sy0)):
        X = np.c_[pts[:, ax], np.ones(len(pts))]
        yv = pts[:, ax] - d[:, ax]  # plate p -> resized-owner coordinate
        for _ in range(4):
            coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
            r = yv - X @ coef
            keep = np.abs(r) < max(0.6, 3 * np.median(np.abs(r)))
            X, yv = X[keep], yv[keep]
        res.append((coef[0] * s0, coef[1] * s0, float(np.abs(yv - X @ coef).mean()), int(len(yv))))
    return res


def main():
    stills_dir, out_dir = sys.argv[1:3]
    tag = sys.argv[3] if len(sys.argv) > 3 else "cmp"
    os.makedirs(out_dir, exist_ok=True)
    n_states = len(json.load(open("/home/user/build/film/data/fidelity/states.json")))
    stills = sorted(f for f in os.listdir(stills_dir) if f.startswith("still-"))[n_states:n_states + 6]
    report = {}
    for engine, still in zip(ENGINES, stills):
        full = Image.open(os.path.join(stills_dir, still)).convert("RGB")
        hdr = round(HEADER)
        plate = full.crop((0, hdr, BODY[0], hdr + BODY[1]))
        owner = Image.open(os.path.join(OWNER, f"{engine}-on.png")).convert("RGB")
        pa = np.asarray(plate, np.float64)
        oa = np.asarray(owner, np.float64)
        boxes = control_boxes(engine)
        mask = np.zeros(pa.shape[:2])
        for (x, y, w, h) in boxes.values():
            mask[int(max(0, y - 10)):int(y + h + 10), int(max(0, x - 10)):int(x + w + 10)] = 1
        (sx, tx, rx, nx), (sy, ty, ry, ny) = fit(pa.mean(2), oa.mean(2), mask)
        Y, X = np.mgrid[0:BODY[1], 0:BODY[0]].astype(np.float64)
        qx, qy = sx * (X + 0.5) + tx - 0.5, sy * (Y + 0.5) + ty - 0.5
        warped = np.stack([ndimage.map_coordinates(oa[..., c], [qy, qx], order=3, mode="nearest") for c in range(3)], 2)
        warped = np.clip(warped, 0, 255)
        wi = Image.fromarray(warped.astype(np.uint8))
        d = np.abs(warped - pa)
        ctrl = {}
        for k, (x, y, w, h) in boxes.items():
            pad = 8
            x0, y0 = int(max(0, x - pad)), int(max(0, y - pad))
            x1, y1 = int(min(BODY[0], x + w + pad)), int(min(BODY[1], y + h + pad))
            a = warped[y0:y1, x0:x1].mean(2)
            b = pa[y0:y1, x0:x1].mean(2)
            dx, dy, _ = shift(grad(a), grad(b))
            ctrl[k] = {"shift": [round(-dx, 2), round(-dy, 2)], "mae": round(float(np.abs(a - b).mean()), 2)}
        report[engine] = {
            "owner_from_plate": {"x": [round(sx, 5), round(tx, 2), round(rx, 3), nx], "y": [round(sy, 5), round(ty, 2), round(ry, 3), ny]},
            "mae_body": round(float(d.mean()), 2),
            "controls": ctrl,
        }
        side = Image.new("RGB", (BODY[0] * 2 + 20, BODY[1] + 40), (20, 20, 20))
        side.paste(wi, (0, 40))
        side.paste(plate, (BODY[0] + 20, 40))
        dr = ImageDraw.Draw(side)
        dr.text((10, 10), f"OWNER PANEL ({engine}-on.png, registered)", fill=(255, 255, 255))
        dr.text((BODY[0] + 30, 10), f"FILM PLATE ({tag})", fill=(255, 255, 255))
        side.resize((side.width // 2, side.height // 2), Image.LANCZOS).save(os.path.join(out_dir, f"{tag}-panel-{engine}-side.png"))
        Image.blend(wi, plate, 0.5).save(os.path.join(out_dir, f"{tag}-panel-{engine}-blend.png"))
        Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, f"{tag}-panel-{engine}-diff.png"))
    with open(os.path.join(out_dir, f"{tag}-panels.json"), "w") as f:
        json.dump(report, f, indent=1)
    for e, r in report.items():
        print(e, "fit", r["owner_from_plate"], "mae", r["mae_body"])
        for k, v in r["controls"].items():
            print(f"   {k:7s} shift {v['shift'][0]:+6.2f} {v['shift'][1]:+6.2f}  mae {v['mae']:.1f}")


if __name__ == "__main__":
    main()
