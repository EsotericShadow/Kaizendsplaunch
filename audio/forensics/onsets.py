"""Onset detection on the aligned drum stems, with sample-level attack times and a bleed test.

Envelope: band-limited signal, rectified and smoothed (1 ms), level in dB on a 1 ms hop. A candidate is a
local maximum of the 6 ms rise in dB (> RISE dB) separated by at least SEP s from the previous candidate
of the same stem. The attack time is the first sample, in the 25 ms before the envelope peak, where the
smoothed rectified signal reaches 25 % of that peak (so a hit's time is its audible start, not its peak).
Level: peak of the smoothed envelope in dBFS (band-limited).
"""
import numpy as np
from scipy.signal import butter, sosfiltfilt

SR = 48000
BANDS = {"kick": (40, 160), "snare": (180, 2500), "hihat": (5000, 16000), "racktom": (70, 400),
         "floortom": (50, 250), "ohl": (5000, 16000), "ohr": (5000, 16000)}
HOP = 48                      # 1 ms


def bandpass(x, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x)


def smooth_env(x, ms=1.0):
    k = max(1, int(SR * ms / 1000))
    return np.convolve(np.abs(x), np.ones(k) / k, mode="same")


def env_db(e):
    n = len(e) // HOP
    fr = e[:n * HOP].reshape(n, HOP).max(axis=1)
    return 20 * np.log10(fr + 1e-9)


def detect(x, lo, hi, rise=9.0, sep=0.045, floor_db=-60.0, rel_floor=45.0):
    """Returns (attack_s, peak_dbfs, rise_db) arrays."""
    y = bandpass(x, lo, hi)
    e = smooth_env(y, 1.0)
    L = env_db(e)
    d = L - np.concatenate([np.full(6, L[0]), L[:-6]])              # 6 ms rise
    top = np.percentile(L, 99.5)
    thr_level = max(floor_db, top - rel_floor)
    cand = []
    i, n = 1, len(d)
    sepf = int(sep * 1000)
    while i < n - 1:
        if d[i] > rise and d[i] >= d[i - 1] and d[i] >= d[i + 1]:
            j = i + int(np.argmax(L[i:i + 30]))                      # envelope peak within 30 ms
            if L[j] > thr_level:
                if cand and i - cand[-1][0] < sepf:
                    if d[i] > cand[-1][2]:
                        cand[-1] = (i, j, d[i])
                else:
                    cand.append((i, j, d[i]))
        i += 1
    att, pk, rs = [], [], []
    for i, j, r in cand:
        p0 = max(0, (j - 25) * HOP)
        p1 = (j + 1) * HOP
        seg = e[p0:p1]
        peak = seg.max()
        k = int(np.argmax(seg >= 0.25 * peak))
        att.append((p0 + k) / SR)
        pk.append(20 * np.log10(peak + 1e-12))
        rs.append(r)
    return np.array(att), np.array(pk), np.array(rs), y, e


def level_at(e, t, w_ms=20):
    """Peak of a smoothed envelope in [t - 2 ms, t + w_ms] (dBFS), for arrays of times."""
    out = np.empty(len(t))
    for q, tt in enumerate(t):
        a = max(0, int((tt - 0.002) * SR))
        b = min(len(e), int((tt + w_ms / 1000) * SR))
        out[q] = 20 * np.log10(e[a:b].max() + 1e-12) if b > a else -240
    return out
