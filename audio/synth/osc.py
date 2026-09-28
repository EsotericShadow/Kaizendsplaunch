"""Band-limited oscillators and noise.

Saw, pulse and square use PolyBLEP correction at every discontinuity. For
clean results at high pitches render at 2x (see ``oversampled``); the pad and
bass voices do that by default.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from .core import SR, jit


def phase_ramp(freq, n, sr=SR, phase0=0.0):
    """Normalised phase 0..1 and per-sample increment for a constant or per-sample
    frequency (Hz). Returns (phase, dt)."""
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    dt = f / sr
    ph = phase0 + np.concatenate([[0.0], np.cumsum(dt[:-1])])
    return np.mod(ph, 1.0), dt


def _blep(t, dt):
    """2-point PolyBLEP residual for phase t in 0..1 with increment dt."""
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def saw(freq, n, sr=SR, phase0=0.0):
    t, dt = phase_ramp(freq, n, sr, phase0)
    return 2.0 * t - 1.0 - _blep(t, dt)


def pulse(freq, n, sr=SR, width=0.5, phase0=0.0):
    """Pulse with width 0..1 (scalar or per-sample, for PWM). DC removed."""
    t, dt = phase_ramp(freq, n, sr, phase0)
    w = np.clip(np.broadcast_to(np.asarray(width, dtype=np.float64), (n,)), 0.02, 0.98)
    y = np.where(t < w, 1.0, -1.0)
    y += _blep(t, dt)
    y -= _blep(np.mod(t - w + 1.0, 1.0), dt)
    return y - (2.0 * w - 1.0)


def square(freq, n, sr=SR, phase0=0.0):
    return pulse(freq, n, sr, 0.5, phase0)


@jit
def _leaky_integrate(x, dt, leak):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = acc * leak + 4.0 * dt[i] * x[i]
        y[i] = acc
    return y


def triangle(freq, n, sr=SR, phase0=0.0):
    """Integrated band-limited square (amplitude about +-1)."""
    t, dt = phase_ramp(freq, n, sr, phase0 + 0.25)
    sq = np.where(t < 0.5, 1.0, -1.0) + _blep(t, dt) - _blep(np.mod(t + 0.5, 1.0), dt)
    y = _leaky_integrate(sq, dt, 0.9995)
    return y - np.mean(y)


def sine(freq, n, sr=SR, phase0=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    ph = phase0 + np.concatenate([[0.0], np.cumsum(f[:-1] / sr)])
    return np.sin(2 * np.pi * ph)


def white_noise(n, rng=None):
    rng = rng or np.random.default_rng()
    return rng.uniform(-1.0, 1.0, n)


def pink_noise(n, rng=None):
    """1/f noise by spectral shaping, normalised to unit RMS."""
    rng = rng or np.random.default_rng()
    w = rng.standard_normal(n)
    W = np.fft.rfft(w)
    f = np.arange(len(W), dtype=np.float64)
    f[0] = 1.0
    W /= np.sqrt(f)
    W[0] = 0.0
    y = np.fft.irfft(W, n)
    return y / max(np.sqrt(np.mean(y ** 2)), 1e-12)


def oversampled(fn, factor=2):
    """Decorator-style helper: run fn(sr=sr*factor) then decimate back with a
    steep Kaiser low-pass. fn must accept ``sr`` and return a 1-D array."""
    def wrapped(*args, sr=SR, **kw):
        y = fn(*args, sr=sr * factor, **kw)
        return decimate(y, factor)
    return wrapped


def decimate(y, factor=2):
    if factor == 1:
        return y
    return signal.resample_poly(y, 1, factor, axis=0, window=("kaiser", 10.0))


def upsample(y, factor=2):
    if factor == 1:
        return y
    return signal.resample_poly(y, factor, 1, axis=0, window=("kaiser", 10.0))
