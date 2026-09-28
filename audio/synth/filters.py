"""Filters: zero-delay-feedback SVF and ladder (time-varying cutoff), RBJ
biquads for EQ, and simple one-pole helpers."""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .core import SR, jit


# ----------------------------------------------------------------- TPT SVF

@jit
def _svf_kernel(x, fc, q, sr, mode):
    y = np.empty_like(x)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    nyq_guard = 0.49 * sr
    for i in range(len(x)):
        f = fc[i]
        if f > nyq_guard:
            f = nyq_guard
        if f < 1.0:
            f = 1.0
        g = math.tan(math.pi * f / sr)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2                      # low-pass
        elif mode == 1:
            y[i] = v1 * k                  # band-pass, unity peak gain
        elif mode == 2:
            y[i] = x[i] - k * v1 - v2      # high-pass
        else:
            y[i] = x[i] - k * v1           # notch
    return y


_SVF_MODES = {"lp": 0, "bp": 1, "hp": 2, "notch": 3}


def svf(x, cutoff, q=0.707, mode="lp", sr=SR):
    """Topology-preserving state-variable filter. cutoff may be a per-sample array
    (modulation is artefact-free). mode: lp, bp (unity peak), hp, notch."""
    x = np.ascontiguousarray(x, dtype=np.float64)
    fc = np.ascontiguousarray(np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape))
    if x.ndim == 2:
        return np.stack([_svf_kernel(np.ascontiguousarray(x[:, c]), np.ascontiguousarray(fc[:, c]),
                                     float(q), float(sr), _SVF_MODES[mode]) for c in range(x.shape[1])], 1)
    return _svf_kernel(x, fc, float(q), float(sr), _SVF_MODES[mode])


# ----------------------------------------------------------------- ladder

@jit
def _ladder_kernel(x, fc, res, drive, comp, sr):
    y = np.empty_like(x)
    s1 = 0.0
    s2 = 0.0
    s3 = 0.0
    s4 = 0.0
    k = 4.0 * res
    for i in range(len(x)):
        f = fc[i]
        if f > 0.45 * sr:
            f = 0.45 * sr
        if f < 5.0:
            f = 5.0
        g = math.tan(math.pi * f / sr)
        G = g / (1.0 + g)
        inv = 1.0 / (1.0 + g)
        # instantaneous response y4 = G^4 u + S
        S = G * G * G * s1 * inv + G * G * s2 * inv + G * s3 * inv + s4 * inv
        u = (x[i] * (1.0 + comp * k) - k * S) / (1.0 + k * G * G * G * G)
        # input stage saturation (OTA-style), unity small-signal slope
        u = math.tanh(drive * u) / drive
        v = (u - s1) * G
        y1 = v + s1
        s1 = y1 + v
        v = (y1 - s2) * G
        y2 = v + s2
        s2 = y2 + v
        v = (y2 - s3) * G
        y3 = v + s3
        s3 = y3 + v
        v = (y3 - s4) * G
        y4 = v + s4
        s4 = y4 + v
        y[i] = y4
    return y


def ladder(x, cutoff, resonance=0.2, drive=1.0, comp=0.5, sr=SR):
    """4-pole (24 dB/oct) zero-delay-feedback ladder low-pass with a tanh input
    stage. resonance 0..1 (1 = self-oscillation edge). comp restores passband
    level lost to resonance (0 none, 1 full). cutoff can be a per-sample array.
    Run at 2x the output rate when resonance or drive is high."""
    x = np.ascontiguousarray(x, dtype=np.float64)
    fc = np.ascontiguousarray(np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape))
    return _ladder_kernel(x, fc, float(np.clip(resonance, 0, 0.99)), float(max(drive, 1e-3)),
                          float(comp), float(sr))


# ----------------------------------------------------------------- biquads

def rbj(kind, f0, sr=SR, q=0.707, gain_db=0.0):
    """RBJ cookbook biquad coefficients (b, a). kind: lowpass, highpass, bandpass,
    notch, peak, lowshelf, highshelf, allpass."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * min(f0, 0.499 * sr) / sr
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * q)
    if kind == "lowpass":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "highpass":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "bandpass":
        b = [alpha, 0, -alpha]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "notch":
        b = [1, -2 * cw, 1]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "allpass":
        b = [1 - alpha, -2 * cw, 1 + alpha]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]; a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind in ("lowshelf", "highshelf"):
        sq = 2 * math.sqrt(A) * alpha
        if kind == "lowshelf":
            b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sq)]
            a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sq]
        else:
            b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sq)]
            a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sq]
    else:
        raise ValueError(kind)
    b, a = np.array(b, float), np.array(a, float)
    return b / a[0], a / a[0]


def biquad(x, kind, f0, sr=SR, q=0.707, gain_db=0.0):
    b, a = rbj(kind, f0, sr, q, gain_db)
    return signal.lfilter(b, a, x, axis=0)


def eq(x, bands, sr=SR):
    """Apply a list of bands: (kind, freq, gain_db, q). Example:
    eq(x, [("highpass", 80, 0, 0.7), ("peak", 2500, 3, 1.0), ("highshelf", 9000, -2, 0.7)])."""
    sos = []
    for kind, f0, g, q in bands:
        b, a = rbj(kind, f0, sr, q, g)
        sos.append(np.concatenate([b, a]))
    if not sos:
        return x
    return signal.sosfilt(np.array(sos), x, axis=0)


def butter(x, order, fc, kind="lowpass", sr=SR):
    sos = signal.butter(order, fc, kind, fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def one_pole_lp(x, fc, sr=SR):
    a = math.exp(-2 * math.pi * fc / sr)
    return signal.lfilter([1 - a], [1, -a], x, axis=0)


def one_pole_hp(x, fc, sr=SR):
    return x - one_pole_lp(x, fc, sr)


def tilt(x, db_per_oct, pivot=1000.0, sr=SR):
    """Gentle spectral tilt around a pivot using a shelving pair."""
    return eq(x, [("lowshelf", pivot, -db_per_oct * 1.5, 0.5), ("highshelf", pivot, db_per_oct * 1.5, 0.5)], sr)
