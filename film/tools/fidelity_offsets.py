#!/usr/bin/env python3
"""Per-element registration of the film plate against a render of the real editor.

  python3 film/tools/fidelity_offsets.py <real.png> <plate still.png>

For each detail box (editor px) finds the shift (plate px, sub-pixel) that best aligns the plate
crop with the real crop (phase correlation of gradient magnitude) and prints it with the residual
mean absolute error after alignment. A shift of (+2, 0) means the plate's element sits 2 px to the
left of the real one (it must move right by 2).
"""

import sys

import numpy as np
from PIL import Image
from scipy import ndimage

K = 1400 / 638

BOXES = {
    "flask icon": (8, 14, 26, 26),
    "drawer chevron": (44, 18, 14, 18),
    "minus": (82, 12, 32, 32),
    "plus": (118, 12, 32, 32),
    "preset text": (158, 18, 50, 20),
    "preset chevron": (212, 20, 18, 16),
    "wordmark": (246, 10, 132, 36),
    "engine text": (398, 18, 60, 20),
    "engine chevron": (484, 20, 18, 16),
    "TRIM": (510, 10, 40, 14),
    "meter": (510, 22, 116, 12),
    "dB text": (540, 32, 60, 14),
    "rate knob": (34, 128, 127, 127),
    "depth knob": (167, 128, 127, 127),
    "offset knob": (364, 128, 127, 127),
    "width knob": (493, 128, 127, 127),
    "rate text": (56, 252, 82, 24),
    "depth text": (188, 251, 82, 24),
    "offset text": (388, 252, 82, 24),
    "width text": (517, 252, 82, 24),
    "color text": (302, 330, 55, 19),
    "mix text": (537, 358, 48, 12),
    "thumb": (200, 272, 70, 72),
    "hq lever": (300, 150, 60, 100),
    "mix knob": (530, 305, 62, 62),
    "corner": (612, 360, 26, 26),
}


def grad(a):
    a = ndimage.gaussian_filter(a, 0.7)
    return np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1))


def shift(a, b):
    """Sub-pixel shift (dx, dy) to apply to b to align it with a (phase correlation)."""
    fa = np.fft.fft2(a - a.mean())
    fb = np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.real(np.fft.ifft2(r))
    iy, ix = np.unravel_index(np.argmax(c), c.shape)

    def sub(i, n, axis):
        l = c[(iy - 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix - 1) % c.shape[1]]
        m = c[iy, ix]
        h = c[(iy + 1) % c.shape[0], ix] if axis == 0 else c[iy, (ix + 1) % c.shape[1]]
        d = l - 2 * m + h
        off = 0.5 * (l - h) / d if abs(d) > 1e-12 else 0.0
        v = i + off
        return v - n if v > n / 2 else v

    return sub(ix, c.shape[1], 1), sub(iy, c.shape[0], 0)


def main():
    real = np.asarray(Image.open(sys.argv[1]).convert("L"), dtype=np.float64)
    ours = np.asarray(Image.open(sys.argv[2]).convert("L"), dtype=np.float64)[: real.shape[0], : real.shape[1]]
    only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    for name, (x, y, w, h) in BOXES.items():
        if only and name not in only:
            continue
        pad = 6
        x0, y0 = int(round(x * K)) - pad, int(round(y * K)) - pad
        x1, y1 = int(round((x + w) * K)) + pad, int(round((y + h) * K)) + pad
        a = real[max(0, y0):y1, max(0, x0):x1]
        b = ours[max(0, y0):y1, max(0, x0):x1]
        win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
        dx, dy = shift(grad(a) * win, grad(b) * win)
        bs = ndimage.shift(b, (dy, dx), order=1, mode="nearest")
        m = slice(pad, -pad)
        print(f"{name:16s} shift x {dx:+6.2f}  y {dy:+6.2f} plate px   mae {np.abs(a - b)[m, m].mean():6.2f} -> {np.abs(a - bs)[m, m].mean():6.2f}")


if __name__ == "__main__":
    main()
