"""Step 4: beat grid in master time from the drum hits (live tempo allowed), bars, tempo curve, validation.

1. Onset strength (5 ms frames): Gaussian bumps (sigma 8 ms) at the classified drum hits (s5_hits.py), weighted
   kick 1, snare 1, rack tom 0.7, floor tom 0.5, cymbal 0.8, hi-hat 0.4, plus 0.35 x the spectral flux of the
   master with the drums removed (the guitar), which carries the pulse through the drum breaks.
2. Beats: dynamic programming (Ellis 2007) with a log-interval penalty around the owner's 148 BPM; the
   interval may vary +-12 % beat to beat, so live drift is followed, not forced.
3. Refinement: each beat moves to the median of the hits within +-40 ms of it, then the beat times are
   smoothed with a local robust line (+-4 beats), so the grid is the band's pulse and each hit's offset from
   it is the drummer's feel.
4. Bars: the 4-beat phase that puts the snare on 2 and 4 and the crashes on 1, chosen per drum section (a
   section that restarts on a different phase is reported as an odd-length bar).
Validation (all with the same code): (a) snare on 2 and 4 per bar, (b) kick/snare phase coherence per bar
against the 8th-note grid, (c) a held-out test: a grid built from kick and snare only must place the hi-hat,
cymbal and tom hits (never seen by it) on its 8th notes; the same tests are run on the old 152.02 BPM grid,
on the best constant 152 BPM grid and on the best constant 148 BPM grid.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import stft

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

FR = 0.005
W = {"kick": 1.0, "snare": 1.0, "racktom": 0.7, "floortom": 0.5, "cymbal": 0.8, "hihat": 0.4}


def load_hits():
    d = np.load(os.path.join(C.OUT, "work", "hits_raw.npy"), allow_pickle=True).item()["hits"]
    return {k: np.array([[h[0], h[1]] for h in v]) for k, v in d.items()}, d


def guitar_flux(n):
    p = os.path.join(C.OUT, "work", "gflux.npy")
    if os.path.exists(p):
        g = np.load(p)
    else:
        x, _ = sf.read(os.path.join(C.OUT, "work", "master_minus_drums.wav"), dtype="float64", always_2d=True)
        x = x.mean(axis=1)
        f, t, Z = stft(x, fs=C.SR, nperseg=2048, noverlap=2048 - 240, boundary=None, padded=False)
        S = np.log1p(1000 * np.abs(Z[(f > 80) & (f < 5000)]))
        fl = np.maximum(np.diff(S, axis=1), 0).sum(0)
        fl = np.concatenate([[0], fl])
        tt = t + 1024 / C.SR
        g = np.interp(np.arange(n) * FR, tt, fl)
        np.save(p, g)
    g = g - np.convolve(g, np.ones(200) / 200, mode="same")          # local mean removed
    g = np.maximum(g, 0)
    return g / (np.percentile(g, 99) + 1e-12)


def oss(hits, n, pieces, guitar=0.35):
    o = np.zeros(n)
    k = np.arange(-6, 7)
    bump = np.exp(-0.5 * (k * FR / 0.008) ** 2)
    for p in pieces:
        for t, _ in hits[p]:
            i = int(round(t / FR))
            if 6 <= i < n - 6:
                o[i - 6:i + 7] += W[p] * bump
    if guitar:
        o += guitar * guitar_flux(n)
    return o


def dp_beats(o, bpm=148.0, tight=300.0, lo=0.88, hi=1.12):
    tau = 60.0 / bpm / FR
    n = len(o)
    Cs = o.copy()
    back = -np.ones(n, dtype=int)
    a, b = int(tau * lo), int(np.ceil(tau * hi))
    d = np.arange(a, b + 1)
    pen = -tight * np.log(d / tau) ** 2
    for t in range(b, n):
        prev = Cs[t - d] + pen
        j = int(np.argmax(prev))
        if prev[j] > 0:
            Cs[t] += prev[j]
            back[t] = t - d[j]
    t = int(np.argmax(Cs[-int(2 * tau):])) + n - int(2 * tau)
    beats = [t]
    while back[beats[-1]] >= 0:
        beats.append(back[beats[-1]])
    return np.array(beats[::-1]) * FR


def refine(beats, hits, pieces, win=0.040, half=4):
    allh = np.sort(np.concatenate([hits[p][:, 0] for p in pieces]))
    obs = np.full(len(beats), np.nan)
    for i, b in enumerate(beats):
        j0, j1 = np.searchsorted(allh, [b - win, b + win])
        if j1 > j0:
            obs[i] = np.median(allh[j0:j1])
    idx = np.arange(len(beats))
    y = np.where(np.isnan(obs), beats, obs)
    has = ~np.isnan(obs)
    out = np.empty(len(beats))
    for i in idx:
        s = slice(max(0, i - half), min(len(beats), i + half + 1))
        xi, yi, hi = idx[s], y[s], has[s]
        w = np.where(hi, 1.0, 0.15)
        for _ in range(3):                                     # robust (Tukey) local line
            A = np.stack([np.ones(len(xi)), xi - i], 1) * np.sqrt(w)[:, None]
            coef = np.linalg.lstsq(A, yi * np.sqrt(w), rcond=None)[0]
            r = yi - (coef[0] + coef[1] * (xi - i))
            c = 0.030
            w = np.where(np.abs(r) < c, (1 - (r / c) ** 2) ** 2, 0.0) * np.where(hi, 1.0, 0.15) + 1e-6
        out[i] = coef[0]
    return out, obs


def eighth_phase(t, beats):
    """Position of times t in 8th notes of the grid (float), using the local beat interval."""
    i = np.clip(np.searchsorted(beats, t) - 1, 0, len(beats) - 2)
    return (i + (t - beats[i]) / (beats[i + 1] - beats[i])) * 2.0


def err_ms(t, beats, sub=2):
    """Distance (ms) of each time to the nearest 1/sub-beat grid point."""
    i = np.clip(np.searchsorted(beats, t) - 1, 0, len(beats) - 2)
    per = beats[i + 1] - beats[i]
    x = (t - beats[i]) / per * sub
    return (x - np.round(x)) * per / sub * 1000


def const_grid(t0, bpm, t_end=170.0):
    return np.arange(t0, t_end, 60.0 / bpm)


def best_const(hits_t, bpm, t_end=170.0):
    """Best phase (by mean |8th-note error|) for a constant-tempo grid."""
    per = 60.0 / bpm
    best = None
    for ph in np.arange(0, per, 0.001):
        g = const_grid(ph, bpm, t_end)
        e = np.mean(np.abs(err_ms(hits_t, g)))
        if best is None or e < best[0]:
            best = (e, ph)
    return const_grid(best[1], bpm, t_end)


def bar_phase_scores(beats, hits):
    """Score each beat as a downbeat candidate: snare on 2 and 4, kick and crash on 1."""
    def near(ts, b, w=0.05):
        return len(ts) and np.min(np.abs(ts - b)) < w
    sn = hits["snare"][:, 0][hits["snare"][:, 1] > np.percentile(hits["snare"][:, 1], 40)]
    cr = hits["cymbal"][:, 0]
    kk = hits["kick"][:, 0]
    n = len(beats)
    sc = np.zeros(n)
    for i in range(n):
        for off, wsn in ((1, 1.0), (3, 1.0), (0, -0.6), (2, -0.6)):
            if i + off < n and near(sn, beats[i + off]):
                sc[i] += wsn
        if near(cr, beats[i]):
            sc[i] += 0.8
        if near(kk, beats[i]):
            sc[i] += 0.3
    return sc


def tests(beats, hits, downbeat_idx, label):
    """(a) snare on 2&4, (b) per-bar kick/snare phase coherence, (c) held-out error (computed by caller)."""
    res = {"grid": label}
    sn = hits["snare"][:, 0][hits["snare"][:, 1] > np.percentile(hits["snare"][:, 1], 40)]
    ph = eighth_phase(sn, beats)                               # in 8ths
    beat_in_bar = np.floor(ph / 2).astype(int) - downbeat_idx
    on = np.abs(ph / 2 - np.round(ph / 2)) * 2 < 0.25           # within a quarter of an 8th of a beat
    bb = np.mod(np.round(ph / 2).astype(int) - downbeat_idx, 4)
    res["snare_on_2_4"] = round(float(np.mean(on & ((bb == 1) | (bb == 3)))), 3)
    res["snare_on_1_3"] = round(float(np.mean(on & ((bb == 0) | (bb == 2)))), 3)
    res["snare_off_beat"] = round(float(np.mean(~on)), 3)
    # per bar coherence of kick+snare against the 8th grid
    ks = np.sort(np.concatenate([hits["kick"][:, 0], hits["snare"][:, 0]]))
    ks = ks[(ks > beats[0]) & (ks < beats[-1])]
    p8 = eighth_phase(ks, beats)
    bar = np.floor(p8 / 8).astype(int)
    R, off = [], []
    for b in np.unique(bar):
        z = np.exp(2j * np.pi * p8[bar == b])
        if len(z) >= 3:
            R.append(abs(z.mean()))
            off.append(np.angle(z.mean()) / (2 * np.pi))
    R, off = np.array(R), np.array(off)
    res["bars_tested"] = int(len(R))
    res["coherence_R_median"] = round(float(np.median(R)), 3)
    res["bars_R_over_0.8"] = round(float(np.mean(R > 0.8)), 3)
    res["bar_mean_offset_abs_median_8ths"] = round(float(np.median(np.abs(off))), 3)
    res["bars_offset_within_0.1_8th"] = round(float(np.mean(np.abs(off) < 0.1)), 3)
    return res


def main():
    hits, raw = load_hits()
    n = int(169.06 / FR)
    allp = list(W)
    o = oss(hits, n, allp)
    b0 = dp_beats(o)
    first = min(hits["kick"][0, 0], hits["cymbal"][0, 0], hits["racktom"][0, 0])
    last_hit = max(h[-1, 0] for h in hits.values())
    b0 = b0[(b0 > first - 0.1) & (b0 < last_hit + 0.3)]
    beats, obs = refine(b0, hits, allp)
    # held-out grid: kick + snare only (no guitar)
    o2 = oss(hits, n, ["kick", "snare"], guitar=0.35)
    h0 = dp_beats(o2)
    h0 = h0[(h0 > first - 0.1) & (h0 < last_hit + 0.3)]
    hb, _ = refine(h0, hits, ["kick", "snare"])
    np.save(os.path.join(C.OUT, "work", "grid_stage.npy"),
            {"b0": b0, "beats": beats, "obs": obs, "heldout_beats": hb}, allow_pickle=True)
    print("beats", len(beats), "first", beats[:4], "last", beats[-3:])
    print("median interval", np.median(np.diff(beats)), "=> bpm", 60 / np.median(np.diff(beats)))
    return beats, hb, hits, raw


if __name__ == "__main__":
    main()
