"""Transition effects. Each function returns a stereo (n, 2) array. Risers and
the reverse cymbal END at their last sample, so place them at
``downbeat_time - duration``; downlifters and impacts START on the hit.
"""
from __future__ import annotations

import math

import numpy as np

from .core import SR, dc_block, fade_curve
from .filters import biquad, eq, svf
from .osc import saw
from .drums import metallic


def _noise2(n, rng):
    return rng.uniform(-1, 1, (n, 2))


def riser(duration_s=4.0, sr=SR, seed=20, f_start=250.0, f_end=9000.0, q=2.5, pitched=True,
          curve=2.2, level=0.35):
    """Filtered-noise sweep that builds into a downbeat (independent L/R noise),
    optionally with a quiet saw rising two octaves."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * sr)
    x = np.linspace(0, 1, n)
    fc = f_start * (f_end / f_start) ** (x ** 1.3)
    nz = _noise2(n, rng)
    y = np.stack([svf(nz[:, c], fc, q, "bp", sr) for c in range(2)], 1)
    y += 0.25 * np.stack([svf(nz[:, c], fc * 1.5, 0.7, "hp", sr) for c in range(2)], 1)
    if pitched:
        f = 110.0 * 4 ** (x ** 1.5)
        s = saw(f, n, sr)
        s = svf(s, np.minimum(fc * 1.2, 16000), 0.9, "lp", sr)
        y += 0.18 * s[:, None]
    env = x ** curve
    y *= env[:, None]
    y *= fade_curve(n, int(0.02 * sr), int(0.004 * sr))[:, None]
    y /= max(np.abs(y).max(), 1e-9)
    return dc_block(y, 20, sr) * level


def downlifter(duration_s=3.0, sr=SR, seed=21, f_start=9000.0, f_end=180.0, level=0.3):
    """Noise sweeping down with a falling sine, fading out."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * sr)
    x = np.linspace(0, 1, n)
    fc = f_start * (f_end / f_start) ** (x ** 0.6)
    nz = _noise2(n, rng)
    y = np.stack([svf(nz[:, c], fc, 0.8, "lp", sr) for c in range(2)], 1)
    f = 320.0 * (55.0 / 320.0) ** x
    ph = np.cumsum(f) / sr
    y += 0.5 * np.sin(2 * np.pi * ph)[:, None]
    env = (1 - x) ** 1.8 * (1 - np.exp(-np.arange(n) / (0.003 * sr)))
    y *= env[:, None]
    y *= fade_curve(n, 0, int(0.05 * sr))[:, None]
    y /= max(np.abs(y).max(), 1e-9)
    return dc_block(y, 20, sr) * level


def impact(duration_s=3.5, sr=SR, seed=22, sub_start=75.0, sub_end=32.0, level=0.6):
    """Cinematic hit: sub drop + noise crack + low rumble tail (stereo tail)."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    f = sub_end + (sub_start - sub_end) * np.exp(-t / 0.35)
    ph = np.cumsum(f) / sr
    sub = np.sin(2 * np.pi * ph) * np.exp(-t / 1.1) * (1 - np.exp(-t / 0.001))
    sub = np.tanh(1.5 * sub) / math.tanh(1.5)
    nz = _noise2(n, rng)
    crack = np.stack([biquad(nz[:, c], "lowpass", 3500, sr, 0.7) for c in range(2)], 1)
    crack *= (np.exp(-t / 0.06) * (1 - np.exp(-t / 0.0005)))[:, None]
    rumble = np.stack([eq(nz[:, c], [("lowpass", 180, 0, 0.7), ("highpass", 30, 0, 0.7)], sr) for c in range(2)], 1)
    rumble *= (np.exp(-t / 0.9) * (1 - np.exp(-t / 0.02)))[:, None]
    rumble /= max(np.abs(rumble).max(), 1e-9)
    y = sub[:, None] * 0.9 + 0.35 * crack / max(np.abs(crack).max(), 1e-9) + 0.35 * rumble
    y *= fade_curve(n, 0, int(0.3 * sr))[:, None]
    y /= max(np.abs(y).max(), 1e-9)
    return dc_block(y, 18, sr) * level


def cymbal(duration_s=3.0, sr=SR, seed=23, tune=2.3, decay_s=1.1):
    """Crash-like cymbal (metallic cluster + noise, bright band-pass)."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    out = []
    for c in range(2):
        met = metallic(n, sr, rng, tune)
        nz = rng.uniform(-1, 1, n)
        x = 0.55 * met + 0.45 * nz
        x = svf(x, 7000, 0.6, "bp", sr) + 0.6 * biquad(x, "highpass", 4000, sr, 0.7)
        x = biquad(x, "highpass", 1800, sr, 0.7)
        env = np.exp(-t / decay_s) * (1 - np.exp(-t / 0.0005))
        out.append(x * env)
    y = np.stack(out, 1)
    return y / max(np.abs(y).max(), 1e-9)


def reverse_cymbal(duration_s=2.0, sr=SR, seed=24, level=0.3):
    """A reversed cymbal swell that peaks at its final sample."""
    c = cymbal(duration_s + 0.2, sr, seed)
    y = c[::-1][-int(duration_s * sr):]
    n = len(y)
    y = y * fade_curve(n, int(0.05 * sr), int(0.003 * sr))[:, None]
    return y / max(np.abs(y).max(), 1e-9) * level
