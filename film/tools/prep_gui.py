#!/usr/bin/env python3
"""Slice the Choroboros filmstrip sheets into one image per frame, for the film's GUI plate.

A page that references the whole sheets makes Chromium decode several 3132 px and 7552 px images
per plate and evict them again, so every frame re-decodes gigabytes. One small file per frame keeps
the decoded footprint tiny. Frames are copied 1:1 (no resampling), so the pixels are the plugin's.

Reads the release-candidate art and writes outside the repo (the art is proprietary):
  /home/user/choroboros-rc/Assets  ->  /home/user/build/film/data/gui/<set>/<sheet>/<NNN>.png
Sets: green, blue, red, purple, black (rate_off ... width_on, mix, switch), white (main, mix),
shared (switch_a). Writes gui/index.json last; re-running skips finished sheets.

Also writes plates2x/<engine>_light_{off,on}.png (2800 x 1450) for close-ups, for every engine that
has 2800 px source art (green, blue, red, purple; black's extra plate is a legacy 1024 px copy and
the white Create canvas has none). The product draws the shipped 1400 x 725 bitmap (MIX/), and the
2800 px art is not exactly that bitmap at 2x: green is offset by about 2.7 px and scaled 0.4 %, red
by about 9 px and 1.3 %, and every "on" plate has a different lamp glow. So each 2x plate is the
shipped bitmap upsampled (Lanczos) plus only the fine detail of the 2800 px art, registered to the
shipped bitmap by a fitted per-axis scale and offset (phase correlation on a grid of patches):
    plate2x = up(ship) + (hiReg - up(down(hiReg)))
A 2x plate reduced to 1400 px equals the shipped bitmap (checked, mean error written to index.json),
so a camera that crosses scale 1 never changes the plate's colour, glow or geometry.

And lit1x/<engine>.png: the light-on plate at 638 x 330, as the editor's HQ lit overlay caches it.
"""

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

from PIL import Image

SRC = os.environ.get("CHORO_ASSETS", "/home/user/choroboros-rc/Assets")
DST = os.environ.get("FILM_GUI_OUT", "/home/user/build/film/data/gui")

# (frame size, first frame offset, step, columns, frame count)
MAIN = (300, 12, 312, 10, 100)
MIX = (512, 64, 576, 13, 156)
WHITE_MIX = (150, 12, 162, 10, 100)
SWITCH = (512, 0, 512, 5, 18)

ENGINES = ["green", "blue", "red", "purple", "black"]
KNOBS = [("rate", 1), ("depth", 2), ("offset", 3), ("width", 4)]


def jobs():
    for e in ENGINES:
        for name, n in KNOBS:
            for state in ("off", "on"):
                yield (f"{e}/{name}/{e}_{n}_{state}.png", f"{e}/{name}_{state}", MAIN)
        yield (f"{e}/{e}_mix_knob_spritesheet.png", f"{e}/mix", MIX)
        yield (f"{e}/{e}_switch_spritesheet.png", f"{e}/switch", SWITCH)
    yield ("MIX/white_main_knob_spritesheet.png", "white/main", MAIN)
    yield ("MIX/white_mix_knob_spritesheet.png", "white/mix", WHITE_MIX)
    yield ("switch_a_spritesheet.png", "shared/switch_a", SWITCH)


def slice_sheet(job):
    src, dst, (size, off, step, cols, count) = job
    out = os.path.join(DST, dst)
    done = os.path.join(out, ".done")
    if os.path.exists(done):
        return dst, count, "skip"
    os.makedirs(out, exist_ok=True)
    im = Image.open(os.path.join(SRC, src))
    im.load()
    for f in range(count):
        r, c = divmod(f, cols)
        x, y = off + c * step, off + r * step
        im.crop((x, y, x + size, y + size)).save(os.path.join(out, f"{f:03d}.png"), compress_level=3)
    with open(done, "w") as fh:
        fh.write(src + "\n")
    return dst, count, "ok"


PLATES_2X = ["green", "blue", "red", "purple"]
LIT_ENGINES = ["green", "blue", "red", "purple", "black", "white"]


def lit_editor(engine):
    """The lit plate as the editor shows it (HQLitOverlay): the shipped light-on bitmap cached at
    the overlay's size, 638 x 330 logical px, then drawn with drawImageAt, i.e. magnified from 638
    px on any screen above 1x. Reduced here with Lanczos (CoreGraphics high quality on macOS)."""
    out = os.path.join(DST, "lit1x", f"{engine}.png")
    if os.path.exists(out):
        return engine, "skip"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im = Image.open(os.path.join(SRC, f"MIX/{engine}_light_on_backpanel.png")).convert("RGB")
    im.resize((638, 330), Image.LANCZOS).save(out, compress_level=3)
    return engine, "ok"


def _shift(a, b):
    """Sub-pixel (dx, dy) to apply to b to align it with a (windowed phase correlation)."""
    import numpy as np

    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.fft2((a - a.mean()) * win)
    fb = np.fft.fft2((b - b.mean()) * win)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.real(np.fft.ifft2(r))
    iy, ix = np.unravel_index(np.argmax(c), c.shape)

    def sub(i, n, axis):
        l = c[(iy - 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix - 1) % c.shape[1]]
        m = c[iy, ix]
        h = c[(iy + 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix + 1) % c.shape[1]]
        d = l - 2 * m + h
        v = i + (0.5 * (l - h) / d if abs(d) > 1e-12 else 0.0)
        return v - n if v > n / 2 else v

    return sub(ix, c.shape[1], 1), sub(iy, c.shape[0], 0)


def _fit(ship_g, hid_g):
    """Per-axis q = s p + t (1400 px space) mapping a shipped pixel to the reduced 2800 px art."""
    import numpy as np

    pts, d = [], []
    H, W = ship_g.shape
    for y in range(40, H - 168, 90):
        for x in range(40, W - 168, 110):
            a = ship_g[y:y + 128, x:x + 128]
            if a.std() < 6:
                continue
            pts.append((x + 64, y + 64))
            d.append(_shift(a, hid_g[y:y + 128, x:x + 128]))
    pts, d = np.array(pts, float), np.array(d, float)
    fit = []
    for ax in (0, 1):
        X = np.c_[pts[:, ax], np.ones(len(pts))]
        yv = pts[:, ax] - d[:, ax]
        for _ in range(3):
            coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
            r = yv - X @ coef
            keep = np.abs(r) < max(0.5, 3 * np.median(np.abs(r)))
            X, yv = X[keep], yv[keep]
        fit.append((float(coef[0]), float(coef[1]), float(np.abs(yv - X @ coef).mean())))
    return fit


def plate2x(job):
    import numpy as np
    from scipy import ndimage

    engine, state = job
    out = os.path.join(DST, "plates2x", f"{engine}_light_{state}.png")
    if os.path.exists(out):
        return engine, state, "skip", None
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ship_im = Image.open(os.path.join(SRC, f"MIX/{engine}_light_{state}_backpanel.png")).convert("RGB")
    hi_im = Image.open(os.path.join(SRC, f"{engine}/{engine}_light_{state}_backpanel.png")).convert("RGB")
    W, H = ship_im.size
    ship = np.asarray(ship_im, np.float64)
    hi = np.asarray(hi_im, np.float64)
    hid = np.asarray(hi_im.resize((W, H), Image.LANCZOS), np.float64)
    (sx, tx, rx), (sy, ty, ry) = _fit(ship.mean(2), hid.mean(2))
    # Register the 2800 px art onto the shipped bitmap's 2x grid (bicubic).
    Y, X = np.mgrid[0:2 * H, 0:2 * W].astype(np.float64)
    qx = (sx * (X + 0.5) / 2 + tx) * 2 - 0.5
    qy = (sy * (Y + 0.5) / 2 + ty) * 2 - 0.5
    reg = np.stack([ndimage.map_coordinates(hi[..., c], [qy, qx], order=3, mode="nearest") for c in range(3)], 2)
    reg = np.clip(reg, 0, 255)

    def resize(a, size):
        return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS), np.float64)

    detail = reg - resize(resize(reg, (W, H)), (2 * W, 2 * H))
    res = np.clip(resize(ship, (2 * W, 2 * H)) + detail, 0, 255).astype(np.uint8)
    Image.fromarray(res).save(out, compress_level=3)
    back = np.asarray(Image.fromarray(res).resize((W, H), Image.LANCZOS), np.float64)
    info = {"fit_x": [round(sx, 5), round(tx, 3), round(rx, 3)], "fit_y": [round(sy, 5), round(ty, 3), round(ry, 3)],
            "reduced_vs_shipped_mae": round(float(np.abs(back - ship).mean()), 3)}
    return engine, state, "ok", info


def main():
    workers = int(os.environ.get("PREP_WORKERS", "2"))
    todo = list(jobs())
    index = {}
    plates = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for dst, count, status in ex.map(slice_sheet, todo):
            index[dst] = count
            print(f"{status:4s} {dst} ({count})", flush=True)
        for engine, status in ex.map(lit_editor, LIT_ENGINES):
            print(f"{status:4s} lit1x/{engine}", flush=True)
        for engine, state, status, info in ex.map(plate2x, [(e, s) for e in PLATES_2X for s in ("off", "on")]):
            plates[f"{engine}_{state}"] = info or "prepared earlier"
            print(f"{status:4s} plates2x/{engine}_light_{state} {json.dumps(info) if info else ''}", flush=True)
    with open(os.path.join(DST, "index.json"), "w") as fh:
        json.dump({"source": SRC, "sheets": index, "plates2x": plates, "lit1x": LIT_ENGINES}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
