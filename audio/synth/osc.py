"""Band-limited oscillators and noise.

``saw``, ``pulse`` and ``square`` are additive: every harmonic below ``fmax``
(default 20 kHz, with a short cosine taper) is summed with a Chebyshev sine
recurrence, so there is no aliasing at any pitch or render rate, and pitch and
pulse width can change every sample. ``saw_blep`` / ``pulse_blep`` are cheaper
2-point PolyBLEP versions (about -30 dB alias energy on high notes at 1x).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .core import SR, jit, pjit, prange


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


def saw_blep(freq, n, sr=SR, phase0=0.0):
    t, dt = phase_ramp(freq, n, sr, phase0)
    return 2.0 * t - 1.0 - _blep(t, dt)


def pulse_blep(freq, n, sr=SR, width=0.5, phase0=0.0):
    """PolyBLEP pulse with width 0..1 (scalar or per-sample). DC removed."""
    t, dt = phase_ramp(freq, n, sr, phase0)
    w = np.clip(np.broadcast_to(np.asarray(width, dtype=np.float64), (n,)), 0.02, 0.98)
    y = np.where(t < w, 1.0, -1.0)
    y += _blep(t, dt)
    y -= _blep(np.mod(t - w + 1.0, 1.0), dt)
    return y - (2.0 * w - 1.0)


@pjit
def _additive(phase, freq, width, fmax, pulse_mode):
    """Sum of sin(h*theta)/h for h*f < fmax via the recurrence
    s(h+1) = 2cos(theta) s(h) - s(h-1), with a cosine taper over the top 15%
    of the band. pulse_mode subtracts the same series shifted by the pulse
    width (difference of two saws)."""
    n = len(phase)
    y = np.empty(n)
    two_pi = 2.0 * math.pi
    fmin = 1e9
    for i in range(n):
        if 0.0 < freq[i] < fmin:
            fmin = freq[i]
    if fmin == 1e9:
        return np.zeros(n)
    hcap = int(fmax / fmin) + 2
    inv = np.empty(hcap + 1)
    inv[0] = 0.0
    for h in range(1, hcap + 1):
        inv[h] = 1.0 / h
    taper_start = 0.85 * fmax
    for i in prange(n):
        f = freq[i]
        if f <= 0.0:
            y[i] = 0.0
            continue
        hmax = int(fmax / f)
        ht = min(int(taper_start / f), hmax)
        th = two_pi * phase[i]
        c2 = 2.0 * math.cos(th)
        s_prev = 0.0
        s = math.sin(th)
        acc = 0.0
        if pulse_mode:
            th2 = th - two_pi * width[i]
            c2b = 2.0 * math.cos(th2)
            sb_prev = 0.0
            sb = math.sin(th2)
            for h in range(1, ht + 1):
                acc += (s - sb) * inv[h]
                s_next = c2 * s - s_prev
                s_prev = s
                s = s_next
                sb_next = c2b * sb - sb_prev
                sb_prev = sb
                sb = sb_next
            for h in range(ht + 1, hmax + 1):
                x = (h * f - taper_start) / (fmax - taper_start)
                acc += (0.5 + 0.5 * math.cos(math.pi * x)) * (s - sb) * inv[h]
                s_next = c2 * s - s_prev
                s_prev = s
                s = s_next
                sb_next = c2b * sb - sb_prev
                sb_prev = sb
                sb = sb_next
        else:
            for h in range(1, ht + 1):
                acc += s * inv[h]
                s_next = c2 * s - s_prev
                s_prev = s
                s = s_next
            for h in range(ht + 1, hmax + 1):
                x = (h * f - taper_start) / (fmax - taper_start)
                acc += (0.5 + 0.5 * math.cos(math.pi * x)) * s * inv[h]
                s_next = c2 * s - s_prev
                s_prev = s
                s = s_next
        y[i] = acc
    return y


def _phase_and_freq(freq, n, sr, phase0):
    f = np.ascontiguousarray(np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,)))
    ph = np.mod(phase0 + np.concatenate([[0.0], np.cumsum(f[:-1] / sr)]), 1.0)
    return ph, f


def saw(freq, n, sr=SR, phase0=0.0, fmax=20000.0):
    """Band-limited rising saw (-1..1 shape of 2*phase-1)."""
    ph, f = _phase_and_freq(freq, n, sr, phase0)
    fmax = min(fmax, 0.49 * sr)
    return -(2.0 / math.pi) * _additive(ph, f, f, fmax, False)


def pulse(freq, n, sr=SR, width=0.5, phase0=0.0, fmax=20000.0):
    """Band-limited pulse, width 0..1 (scalar or per-sample for PWM), DC-free."""
    ph, f = _phase_and_freq(freq, n, sr, phase0)
    w = np.ascontiguousarray(np.clip(np.broadcast_to(np.asarray(width, dtype=np.float64), (n,)), 0.02, 0.98))
    fmax = min(fmax, 0.49 * sr)
    return (2.0 / math.pi) * _additive(ph, f, w, fmax, True)


def square(freq, n, sr=SR, phase0=0.0, fmax=20000.0):
    return pulse(freq, n, sr, 0.5, phase0, fmax)


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
