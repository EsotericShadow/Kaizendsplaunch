"""Mixing effects: FDN reverb, stereo delay, bus compressor, true-peak-safe
limiter and loudness normalisation. All processors take and return stereo
(n, 2) float arrays; reverb and delay return the wet signal only (use them on
send buses)."""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .core import SR, db_to_amp, ensure_stereo, jit, ms_width
from .filters import eq
from . import meter


# ----------------------------------------------------------------- reverb

def _next_prime(n):
    def is_prime(k):
        if k < 2:
            return False
        for d in range(2, int(k ** 0.5) + 1):
            if k % d == 0:
                return False
        return True
    while not is_prime(n):
        n += 1
    return n


@jit
def _allpass_chain(x, delays, g):
    y = x.copy()
    for j in range(len(delays)):
        D = delays[j]
        buf = np.zeros(D)
        idx = 0
        out = np.empty_like(y)
        for i in range(len(y)):
            dv = buf[idx]
            w = y[i] + g * dv
            out[i] = dv - g * w
            buf[idx] = w
            idx += 1
            if idx >= D:
                idx = 0
        y = out
    return y


@jit
def _fdn_kernel(inL, inR, delays, g_dc, b_lp, bL, bR, cL, cR, mod_depth, mod_rate, sr):
    N = len(delays)
    n = len(inL)
    maxd = 0
    for i in range(N):
        if delays[i] > maxd:
            maxd = delays[i]
    size = maxd + int(mod_depth) + 4
    buf = np.zeros((N, size))
    widx = 0
    lp = np.zeros(N)
    v = np.zeros(N)
    outL = np.zeros(n)
    outR = np.zeros(n)
    two_pi = 2.0 * math.pi
    for t in range(n):
        # read (lines 0 and 1 are slowly modulated to break up metallic modes)
        for i in range(N):
            d = float(delays[i])
            if i < 2 and mod_depth > 0.0:
                d += mod_depth * (1.0 + math.sin(two_pi * mod_rate * (1.0 + 0.37 * i) * t / sr + 1.7 * i))
            rp = widx - d
            while rp < 0:
                rp += size
            i0 = int(rp)
            fr = rp - i0
            i1 = i0 + 1
            if i1 >= size:
                i1 = 0
            s = buf[i, i0] * (1.0 - fr) + buf[i, i1] * fr
            # frequency-dependent absorption (Jot): one-pole low-pass with DC gain g_dc
            lp[i] = g_dc[i] * (1.0 - b_lp[i]) * s + b_lp[i] * lp[i]
            v[i] = lp[i]
        # outputs
        yl = 0.0
        yr = 0.0
        for i in range(N):
            yl += cL[i] * v[i]
            yr += cR[i] * v[i]
        outL[t] = yl
        outR[t] = yr
        # Householder feedback matrix: A = I - (2/N) 1 1^T
        s = 0.0
        for i in range(N):
            s += v[i]
        s *= 2.0 / N
        for i in range(N):
            buf[i, widx] = v[i] - s + bL[i] * inL[t] + bR[i] * inR[t]
        widx += 1
        if widx >= size:
            widx = 0
    return outL, outR


class Reverb:
    """8-line feedback delay network with Householder mixing.

    rt60: decay time at low frequencies (s). hf_ratio: RT60 at Nyquist / RT60 at DC.
    size: scales the line lengths (1.0 = medium hall). predelay_ms.
    diffusion: 0..0.8 input allpass diffusion. mod_depth_ms: slow modulation of two
    lines (keep small; 0 disables). low_cut / high_cut: wet EQ. width: wet M/S width.
    """

    BASE_MS = (29.7, 37.1, 41.1, 43.7, 53.3, 59.9, 67.7, 73.1)

    def __init__(self, rt60=2.2, hf_ratio=0.4, size=1.0, predelay_ms=18.0, diffusion=0.65,
                 mod_depth_ms=0.25, mod_rate=0.25, low_cut=160.0, high_cut=8500.0, width=1.0, sr=SR):
        self.rt60, self.hf_ratio, self.size = rt60, hf_ratio, size
        self.predelay_ms, self.diffusion = predelay_ms, diffusion
        self.mod_depth_ms, self.mod_rate = mod_depth_ms, mod_rate
        self.low_cut, self.high_cut, self.width, self.sr = low_cut, high_cut, width, sr

    def __call__(self, x):
        sr = self.sr
        x = ensure_stereo(x)
        N = 8
        delays = np.array([_next_prime(int(ms * self.size * sr / 1000)) for ms in self.BASE_MS], dtype=np.int64)
        t60_dc = self.rt60
        t60_ny = max(self.rt60 * self.hf_ratio, 0.05)
        k_dc = 10 ** (-3 * delays / (sr * t60_dc))
        k_ny = 10 ** (-3 * delays / (sr * t60_ny))
        b_lp = (k_dc - k_ny) / (k_dc + k_ny)
        # input and output vectors (orthogonal sign patterns)
        bL = np.array([1, 1, 1, 1, -1, -1, -1, -1], float) * 0.35
        bR = np.array([1, -1, 1, -1, 1, -1, 1, -1], float) * 0.35
        cL = np.array([1, 1, -1, -1, 1, 1, -1, -1], float) / math.sqrt(N)
        cR = np.array([1, -1, -1, 1, 1, -1, -1, 1], float) / math.sqrt(N)
        pd = int(self.predelay_ms * sr / 1000)
        inp = np.concatenate([np.zeros((pd, 2)), x], 0)[: len(x)]
        if self.diffusion > 0:
            ap = np.array([_next_prime(int(ms * sr / 1000)) for ms in (4.77, 3.59, 12.73, 9.29)], dtype=np.int64)
            apR = np.array([_next_prime(int(ms * sr / 1000)) for ms in (4.97, 3.37, 13.11, 8.87)], dtype=np.int64)
            inL = _allpass_chain(np.ascontiguousarray(inp[:, 0]), ap, float(self.diffusion))
            inR = _allpass_chain(np.ascontiguousarray(inp[:, 1]), apR, float(self.diffusion))
        else:
            inL, inR = np.ascontiguousarray(inp[:, 0]), np.ascontiguousarray(inp[:, 1])
        oL, oR = _fdn_kernel(inL, inR, delays, k_dc, b_lp, bL, bR, cL, cR,
                             self.mod_depth_ms * sr / 1000, self.mod_rate, float(sr))
        y = np.stack([oL, oR], 1)
        y = eq(y, [("highpass", self.low_cut, 0, 0.7), ("lowpass", self.high_cut, 0, 0.7)], sr)
        return ms_width(y, self.width)


# ----------------------------------------------------------------- delay

@jit
def _delay_kernel(inL, inR, dl, dr, fb, cross, lp_a, hp_a, sat):
    n = len(inL)
    size = max(dl, dr) + 2
    bl = np.zeros(size)
    br = np.zeros(size)
    w = 0
    outL = np.zeros(n)
    outR = np.zeros(n)
    lpl = 0.0
    lpr = 0.0
    hpl = 0.0
    hpr = 0.0
    for t in range(n):
        il = w - dl
        if il < 0:
            il += size
        ir = w - dr
        if ir < 0:
            ir += size
        yl = bl[il]
        yr = br[ir]
        outL[t] = yl
        outR[t] = yr
        # feedback tone: one-pole low-pass then one-pole high-pass (via LP subtraction)
        lpl = (1 - lp_a) * yl + lp_a * lpl
        lpr = (1 - lp_a) * yr + lp_a * lpr
        hpl = (1 - hp_a) * lpl + hp_a * hpl
        hpr = (1 - hp_a) * lpr + hp_a * hpr
        fl = lpl - hpl
        fr = lpr - hpr
        # straight (cross=0) or ping-pong (cross=1) feedback, soft-limited
        nl = inL[t] + fb * ((1 - cross) * fl + cross * fr)
        nr = inR[t] + fb * ((1 - cross) * fr + cross * fl)
        bl[w] = math.tanh(sat * nl) / sat
        br[w] = math.tanh(sat * nr) / sat
        w += 1
        if w >= size:
            w = 0
    return outL, outR


class StereoDelay:
    """Stereo / ping-pong delay (wet only).

    time_l, time_r: seconds, or use StereoDelay.synced(bpm, beats_l, beats_r, ...).
    feedback 0..0.95, cross 0 (independent) .. 1 (ping-pong), lp_hz/hp_hz shape the
    repeats, mono_in: feed only the mono sum into the left line (classic ping-pong).
    """

    def __init__(self, time_l=0.375, time_r=0.5, feedback=0.35, cross=0.0, lp_hz=5500.0, hp_hz=250.0,
                 mono_in=False, sr=SR):
        self.dl, self.dr = int(time_l * sr), int(time_r * sr)
        self.fb, self.cross, self.lp, self.hp, self.mono_in, self.sr = feedback, cross, lp_hz, hp_hz, mono_in, sr

    @classmethod
    def synced(cls, bpm, beats_l=0.75, beats_r=1.0, **kw):
        spb = 60.0 / bpm
        return cls(beats_l * spb, beats_r * spb, **kw)

    def __call__(self, x):
        x = ensure_stereo(x)
        sr = self.sr
        if self.mono_in:
            m = 0.5 * (x[:, 0] + x[:, 1])
            inL, inR = m, np.zeros_like(m)
        else:
            inL, inR = x[:, 0].copy(), x[:, 1].copy()
        lp_a = math.exp(-2 * math.pi * self.lp / sr)
        hp_a = math.exp(-2 * math.pi * self.hp / sr)
        oL, oR = _delay_kernel(np.ascontiguousarray(inL), np.ascontiguousarray(inR), self.dl, self.dr,
                               float(self.fb), float(self.cross), lp_a, hp_a, 1.0)
        return np.stack([oL, oR], 1)


# ----------------------------------------------------------------- dynamics

@jit
def _smooth_gain(target_db, att, rel):
    """Decoupled attack/release smoothing of a gain-reduction curve (dB, <= 0)."""
    y = np.empty_like(target_db)
    s = 0.0
    for i in range(len(target_db)):
        x = target_db[i]
        if x < s:
            s = att * s + (1 - att) * x
        else:
            s = rel * s + (1 - rel) * x
        y[i] = s
    return y


def compressor(x, threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0, knee_db=6.0,
               makeup_db=0.0, sidechain_hp=90.0, detector="rms", rms_ms=5.0, mix=1.0, sr=SR,
               return_gr=False):
    """Stereo-linked feed-forward compressor with soft knee (glue style)."""
    x = ensure_stereo(x)
    sc = x
    if sidechain_hp:
        sc = eq(x, [("highpass", sidechain_hp, 0, 0.7)], sr)
    if detector == "rms":
        p = (sc ** 2).max(axis=1)
        a = math.exp(-1 / (rms_ms * sr / 1000))
        p = signal.lfilter([1 - a], [1, -a], p)
        lvl = 10 * np.log10(np.maximum(p * 2, 1e-12))   # sine RMS reads as its peak level
    else:
        lvl = 20 * np.log10(np.maximum(np.abs(sc).max(axis=1), 1e-12))
    over = lvl - threshold_db
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, (1 / ratio - 1) * over,
                           (1 / ratio - 1) * (over + knee_db / 2) ** 2 / (2 * max(knee_db, 1e-9))))
    att = math.exp(-1 / (attack_ms * sr / 1000))
    rel = math.exp(-1 / (release_ms * sr / 1000))
    g_db = _smooth_gain(gr, att, rel)
    y = x * db_to_amp(g_db + makeup_db)[:, None]
    y = mix * y + (1 - mix) * x
    return (y, g_db) if return_gr else y


def limiter(x, ceiling_dbtp=-1.0, lookahead_ms=5.0, release_ms=80.0, sr=SR, max_passes=4):
    """Look-ahead brickwall limiter driven by 4x-oversampled (true) peaks.

    Offline, so the look-ahead needs no delay: h[n] = min(req[n .. n+L-1]) is
    released exponentially, then g[n] = mean(h[n-L+1 .. n]). Every term of that
    mean has req[n] inside its window, so g[n] <= req[n] always, and the gain
    ramps down over L samples before each peak. The result is re-measured and
    the ceiling tightened until the true peak is at or below the target.
    Returns (y, info)."""
    x = ensure_stereo(x)
    L = max(1, int(lookahead_ms * sr / 1000))
    rel = math.exp(-1 / (release_ms * sr / 1000))
    target = db_to_amp(ceiling_dbtp)
    y = x
    info = {}
    pk = meter.true_peak_envelope(x, sr)
    for p in range(max_passes):
        req = np.minimum(1.0, target / np.maximum(pk, 1e-12))
        h = _forward_min(req, L)
        h = _release(h, rel)
        g = np.convolve(np.concatenate([np.full(L - 1, h[0]), h]), np.ones(L) / L, mode="valid")
        y = x * g[:, None]
        tp = meter.true_peak(y, sr)
        info = {"passes": p + 1, "true_peak_dbtp": tp, "max_gain_reduction_db": float(-20 * np.log10(g.min()))}
        if tp <= ceiling_dbtp + 0.01:
            break
        target *= db_to_amp(ceiling_dbtp - tp - 0.05)
    return y, info


def _forward_min(x, L):
    """out[n] = min(x[n .. n+L-1]) (window clipped at the end)."""
    from scipy.ndimage import minimum_filter1d
    xr = x[::-1]
    # backward-looking min on the reversed signal == forward-looking min on x
    b = minimum_filter1d(xr, size=L, origin=(L - 1) // 2, mode="nearest")
    return b[::-1]


@jit
def _release(h, rel):
    y = np.empty_like(h)
    s = 1.0
    for i in range(len(h)):
        s = rel * s + (1 - rel) * 1.0 if h[i] >= s else h[i]
        if s > h[i]:
            s = h[i]
        y[i] = s
    return y


def normalize_lufs(x, target_lufs=-16.0, sr=SR):
    l = meter.integrated_lufs(x, sr)
    if not np.isfinite(l):
        return x, 0.0
    g = target_lufs - l
    return x * db_to_amp(g), g


def saturate(x, drive_db=3.0, bias=0.0):
    """Unity-gain tanh saturation with optional even-harmonic bias."""
    d = db_to_amp(drive_db)
    y = (np.tanh(d * x + bias) - math.tanh(bias)) / d
    return y


def duck(x, key, depth_db=3.0, attack_ms=4.0, release_ms=160.0, sr=SR):
    """Sidechain-style ducking: lower x by up to depth_db whenever key (e.g. the
    kick stem) is loud. The key envelope is normalised to its own peak, so depth
    is the reduction on the loudest hits."""
    k = np.abs(ensure_stereo(key)).max(axis=1)
    k = k / max(k.max(), 1e-12)
    att = math.exp(-1 / (attack_ms * sr / 1000))
    rel = math.exp(-1 / (release_ms * sr / 1000))
    env = -_smooth_gain(-k, att, rel)          # peak follower (fast up, slow down)
    g = db_to_amp(-depth_db * np.clip(env, 0, 1))
    n = min(len(x), len(g))
    y = np.array(x, dtype=np.float64, copy=True)
    y[:n] = (y[:n].T * g[:n]).T
    return y
