"""Shared constants and small signal helpers.

Conventions used across the package:
- Sample rate is 48 kHz unless a function takes ``sr``.
- Mono signals are 1-D float64 arrays. Stereo signals are float64 arrays of
  shape (n, 2). Files are written as float32.
- Gains in dB, pans in -1 (left) .. +1 (right), velocities in 0..1.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

SR = 48000

try:  # Optional JIT. Every kernel also runs as plain Python, only slower.
    from numba import njit as _njit

    from numba import prange

    def jit(fn):
        return _njit(cache=True, fastmath=False)(fn)

    def pjit(fn):
        """JIT with loop parallelism (use prange for independent iterations)."""
        return _njit(cache=True, fastmath=False, parallel=True)(fn)

    HAVE_NUMBA = True
except Exception:  # pragma: no cover - exercised only without numba
    prange = range

    def jit(fn):
        return fn

    pjit = jit
    HAVE_NUMBA = False


# ----------------------------------------------------------------- units

def db_to_amp(db):
    return np.power(10.0, np.asarray(db, dtype=np.float64) / 20.0)


def amp_to_db(a, floor=-200.0):
    a = np.maximum(np.abs(np.asarray(a, dtype=np.float64)), 10.0 ** (floor / 20.0))
    return 20.0 * np.log10(a)


def midi_to_hz(n, a4=440.0):
    return a4 * np.power(2.0, (np.asarray(n, dtype=np.float64) - 69.0) / 12.0)


def hz_to_midi(f, a4=440.0):
    return 69.0 + 12.0 * np.log2(np.asarray(f, dtype=np.float64) / a4)


_NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note(name: str) -> int:
    """'A4' -> 69, 'F#3' -> 54, 'Bb2' -> 46 (scientific pitch, C4 = 60)."""
    name = name.strip()
    pc = _NOTE_INDEX[name[0].upper()]
    i = 1
    while i < len(name) and name[i] in "#b":
        pc += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    return 12 * (octave + 1) + pc


def note_name(n: int) -> str:
    return f"{NOTE_NAMES[int(n) % 12]}{int(n) // 12 - 1}"


def cents_to_ratio(c):
    return np.power(2.0, np.asarray(c, dtype=np.float64) / 1200.0)


# ----------------------------------------------------------------- shapes

def ensure_stereo(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        return np.stack([x, x], axis=1)
    if x.shape[1] == 1:
        return np.repeat(x, 2, axis=1)
    return x


def to_mono(x):
    x = np.asarray(x, dtype=np.float64)
    return x if x.ndim == 1 else x.mean(axis=1)


def pad_to(x, n):
    """Zero-pad or trim along axis 0 to exactly n samples."""
    if len(x) >= n:
        return x[:n]
    pad = [(0, n - len(x))] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad)


def add_at(dest, src, offset):
    """Add src into dest starting at integer sample offset, clipping to dest bounds."""
    offset = int(offset)
    if offset >= len(dest) or offset + len(src) <= 0:
        return dest
    s0 = max(0, -offset)
    d0 = max(0, offset)
    n = min(len(src) - s0, len(dest) - d0)
    if n > 0:
        dest[d0:d0 + n] += src[s0:s0 + n]
    return dest


def pan(mono, position=0.0, law_db=-3.0):
    """Pan a mono signal into stereo. position -1..1. Default -3 dB centre law
    (constant power). law_db=-4.5 or -6 are also accepted."""
    mono = np.asarray(mono, dtype=np.float64)
    p = float(np.clip(position, -1.0, 1.0))
    theta = (p + 1.0) * math.pi / 4.0
    l, r = math.cos(theta), math.sin(theta)
    if law_db != -3.0:  # blend towards linear law
        k = (-law_db - 3.0) / 3.0
        l = (1 - k) * l + k * (1 - p) / 2
        r = (1 - k) * r + k * (1 + p) / 2
    return np.stack([mono * l, mono * r], axis=1)


def balance(stereo, position=0.0):
    """Stereo balance control for a stereo source (keeps centre at unity)."""
    x = ensure_stereo(stereo).copy()
    p = float(np.clip(position, -1.0, 1.0))
    if p > 0:
        x[:, 0] *= math.cos(p * math.pi / 2)
    elif p < 0:
        x[:, 1] *= math.cos(-p * math.pi / 2)
    return x


def ms_width(stereo, width=1.0):
    """Mid/side width. 0 = mono, 1 = unchanged, >1 = wider."""
    x = ensure_stereo(stereo)
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1]) * width
    return np.stack([m + s, m - s], axis=1)


# ----------------------------------------------------------------- envelopes

def adsr(gate_s, a, d, s, r, sr=SR, *, curve=4.0, peak=1.0):
    """Click-free ADSR.

    gate_s: note length in seconds (key held). The envelope is gate + release long.
    a, d, r: seconds. s: sustain level 0..1. curve > 0 bends the attack (0 is linear)
    and makes decay/release exponential-like; the release always starts from the
    level reached at gate off, so an early release never jumps.
    Minimum 1 ms attack and 3 ms release are enforced to keep edges smooth.
    """
    a = max(a, 0.001)
    r = max(r, 0.003)
    ng = max(1, int(round(gate_s * sr)))
    nr = max(1, int(round(r * sr)))
    t = np.arange(ng) / sr
    env = np.empty(ng)
    att = t < a
    # attack: 1 - exp(-curve*x) normalised; decay: exponential towards s
    xa = t[att] / a
    if curve > 1e-6:
        env[att] = peak * (1 - np.exp(-curve * xa)) / (1 - math.exp(-curve))
    else:
        env[att] = peak * xa
    td = t[~att] - a
    tau = max(d, 1e-4) / max(curve, 1e-3)
    env[~att] = s * peak + (peak - s * peak) * np.exp(-td / tau)
    level = env[-1]
    tr = np.arange(1, nr + 1) / sr
    tau_r = r / max(curve, 1e-3)
    rel = level * (np.exp(-tr / tau_r) - math.exp(-r / tau_r)) / (1 - math.exp(-r / tau_r))
    return np.concatenate([env, np.maximum(rel, 0.0)])


def exp_decay(n, tau_s, sr=SR, attack_s=0.0005):
    """Percussive envelope: short raised-cosine attack then exponential decay,
    forced to exactly zero at the last sample."""
    t = np.arange(n) / sr
    env = np.exp(-t / max(tau_s, 1e-5))
    na = max(1, int(attack_s * sr))
    if na > 1 and na < n:
        env[:na] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(na) / na)
    return env * fade_curve(n, 0, max(8, n // 50))


def fade_curve(n, fade_in, fade_out):
    """Raised-cosine fade in/out gain curve of length n (fades in samples)."""
    g = np.ones(n)
    fi = int(min(fade_in, n))
    fo = int(min(fade_out, n))
    if fi > 0:
        g[:fi] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(fi) / fi)
    if fo > 0:
        g[n - fo:] *= 0.5 + 0.5 * np.cos(np.pi * (np.arange(fo) + 1) / fo)
    return g


def fade(x, fade_in_s=0.0, fade_out_s=0.0, sr=SR):
    g = fade_curve(len(x), int(fade_in_s * sr), int(fade_out_s * sr))
    return x * (g[:, None] if np.ndim(x) == 2 else g)


def smooth(x, time_s, sr=SR):
    """One-pole smoother (time constant time_s), zero-phase not implied."""
    a = math.exp(-1.0 / max(time_s * sr, 1e-9))
    y, _ = signal.lfilter([1 - a], [1, -a], np.asarray(x, dtype=np.float64),
                          zi=[np.asarray(x).flat[0] * a])
    return y


# ----------------------------------------------------------------- cleanup

def dc_block(x, fc=8.0, sr=SR):
    """2nd-order Butterworth high-pass (default 8 Hz) applied forwards only."""
    sos = signal.butter(2, fc, "highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def soft_clip(x, drive=1.0):
    """Unity-slope tanh saturation (drive 1 = gentle)."""
    if drive <= 0:
        return x
    return np.tanh(x * drive) / drive


def rng(seed=0):
    return np.random.default_rng(seed)


def trim_silence_tail(x, threshold_db=-90.0, keep_s=0.05, sr=SR):
    """Cut trailing samples below threshold (keeps keep_s after last loud sample)."""
    a = np.abs(x) if x.ndim == 1 else np.abs(x).max(axis=1)
    idx = np.nonzero(a > 10 ** (threshold_db / 20))[0]
    if len(idx) == 0:
        return x[:1]
    end = min(len(x), idx[-1] + int(keep_s * sr))
    return x[:end]
