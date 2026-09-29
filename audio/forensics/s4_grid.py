"""Step 4: beat grid in master time, bars, tempo curve, and a validation that cannot pass by accident.

Finding: the drums sit on ONE constant-tempo grid for the whole song (kick and snare attacks fall within about
1 ms of it, drum breaks included), so the grid is t(beat n) = T0 + n * 60 / BPM. Method:
1. Fit set = kick and snare attacks (s5_hits.py). Each attack is assigned to its nearest 16th note and
   (T0, period) are solved by least squares, iterated, attacks further than 30 ms from the line dropped.
2. Live-tempo check (nothing forces a constant tempo): (a) the same fit in every 8 s window gives a local
   BPM and a local phase offset; (b) an independent dynamic-programming beat tracker (Ellis 2007, log-interval
   penalty, +-12 % beat-to-beat freedom) on all drum hits plus the guitar's spectral flux, beat times then
   pulled to the median of the hits within 40 ms; its beats are compared with the constant grid.
3. Bars: 4/4 phase = the beat phase that puts the loud snares on 2 and 4 and the crashes on 1, scored over
   the whole song and per drum section (a section preferring another phase would reveal an odd bar).
4. Validation, the same code for every candidate grid: (a) share of loud snares on beats 2/4 vs 1/3 vs off
   the beat, (b) per-bar kick/snare phase coherence against the 8th-note grid and per-bar mean offset,
   (c) held-out: hi-hat and tom attacks and the overheads' own rise times of crashes and cymbals (none of
   them used by the fit) vs the 16th grid.
   Candidates: this grid; the old 152.02 BPM grid (/home/user/build/track/grid.json) as written and at its
   best time shift; the best constant 152 BPM grid; the DP live grid.
Output: film/v5/grid.json (timing data only).
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
W = {"kick": 1.0, "snare": 1.0, "racktom": 0.7, "floortom": 0.5, "crash": 0.8, "ride": 0.5, "hihat": 0.4}
SONG_END = 169.054


def load_hits():
    d = np.load(os.path.join(C.OUT, "work", "hits_raw.npy"), allow_pickle=True).item()["hits"]
    out = {k: np.array([[h[0], h[1]] for h in v]) for k, v in d.items()}
    # the overheads' own rise times of crashes and cymbals (independent of the kick/snare attacks)
    out["crash_rise"] = np.array([[h[5], h[1]] for h in d["crash"]])
    out["ride_rise"] = np.array([[h[5], h[1]] for h in d["ride"]])
    return out


# ---------------------------------------------------------------- constant grid fit
def fit_const(t, period0=60 / 148, t00=0.406, sub=4, it=8, gate=0.030):
    t0, P = t00, period0
    for _ in range(it):
        n = np.round((t - t0) / (P / sub))
        r = t - (t0 + n * P / sub)
        keep = np.abs(r) < gate
        A = np.stack([np.ones(keep.sum()), n[keep] / sub], 1)
        (t0, P), *_ = np.linalg.lstsq(A, t[keep], rcond=None)
    n = np.round((t - t0) / (P / sub))
    r = t - (t0 + n * P / sub)
    keep = np.abs(r) < gate
    A = np.stack([np.ones(keep.sum()), n[keep] / sub], 1)
    res = r[keep]
    cov = np.linalg.inv(A.T @ A) * np.var(res)
    return t0, P, res, keep, np.sqrt(np.diag(cov))


# ---------------------------------------------------------------- DP live-tempo tracker (independent check)
def guitar_flux(n):
    p = os.path.join(C.OUT, "work", "gflux.npy")
    if os.path.exists(p):
        g = np.load(p)
    else:
        x, _ = sf.read(os.path.join(C.OUT, "stems", "nondrums.wav"), dtype="float64", always_2d=True)
        f, t, Z = stft(x.mean(axis=1), fs=C.SR, nperseg=2048, noverlap=2048 - 240, boundary=None, padded=False)
        S = np.log1p(1000 * np.abs(Z[(f > 80) & (f < 5000)]))
        fl = np.concatenate([[0], np.maximum(np.diff(S, axis=1), 0).sum(0)])
        g = np.interp(np.arange(n) * FR, t + 1024 / C.SR, fl)
        np.save(p, g)
    g = g[:n]
    g = np.maximum(g - np.convolve(g, np.ones(200) / 200, mode="same"), 0)
    return g / (np.percentile(g, 99) + 1e-12)


def dp_grid(hits, n):
    o = np.zeros(n)
    k = np.arange(-6, 7)
    bump = np.exp(-0.5 * (k * FR / 0.008) ** 2)
    for p, w in W.items():
        for t, _ in hits[p]:
            i = int(round(t / FR))
            if 6 <= i < n - 6:
                o[i - 6:i + 7] += w * bump
    o += 0.35 * guitar_flux(n)
    tau = 60 / 148 / FR
    Cs, back = o.copy(), -np.ones(n, dtype=int)
    d = np.arange(int(tau * 0.88), int(np.ceil(tau * 1.12)) + 1)
    pen = -300.0 * np.log(d / tau) ** 2
    for t in range(d[-1], n):
        prev = Cs[t - d] + pen
        j = int(np.argmax(prev))
        if prev[j] > 0:
            Cs[t] += prev[j]
            back[t] = t - d[j]
    t = int(np.argmax(Cs[-int(2 * tau):])) + n - int(2 * tau)
    b = [t]
    while back[b[-1]] >= 0:
        b.append(back[b[-1]])
    b = np.array(b[::-1]) * FR
    allh = np.sort(np.concatenate([hits[p][:, 0] for p in W]))
    out = b.copy()
    for i, x in enumerate(b):
        j0, j1 = np.searchsorted(allh, [x - 0.04, x + 0.04])
        if j1 > j0:
            out[i] = np.median(allh[j0:j1])
    return out


# ---------------------------------------------------------------- validation helpers
def pos(t, beats):
    """Fractional beat index of times t on a grid of beat times (extrapolated linearly at the ends)."""
    i = np.clip(np.searchsorted(beats, t) - 1, 0, len(beats) - 2)
    return i + (t - beats[i]) / (beats[i + 1] - beats[i]), beats[i + 1] - beats[i]


def err16(t, beats):
    x, per = pos(t, beats)
    return (x * 4 - np.round(x * 4)) * per / 4 * 1000


def validate(beats, bar0_beat, hits, held):
    """bar0_beat: index (into beats) of a downbeat. Returns the test results for this grid."""
    r = {}
    sn = hits["snare"]
    loud = sn[sn[:, 1] > np.percentile(sn[:, 1], 30), 0]
    x, per = pos(loud, beats)
    on = np.abs(x - np.round(x)) * per < 0.035
    bib = np.mod(np.round(x).astype(int) - bar0_beat, 4)          # 0 = beat 1
    r["loud_snares"] = int(len(loud))
    r["snare_on_2_or_4"] = round(float(np.mean(on & (bib % 2 == 1))), 3)
    r["snare_on_1_or_3"] = round(float(np.mean(on & (bib % 2 == 0))), 3)
    r["snare_off_beat"] = round(float(np.mean(~on)), 3)
    ks = np.sort(np.concatenate([hits["kick"][:, 0], hits["snare"][:, 0]]))
    ks = ks[(ks > beats[0]) & (ks < beats[-1])]
    x, per = pos(ks, beats)
    bar = np.floor((x - bar0_beat) / 4).astype(int)
    R, off = [], []
    for b in np.unique(bar):
        z = np.exp(2j * np.pi * 2 * x[bar == b])                     # 8th-note phase
        if len(z) >= 3:
            R.append(abs(z.mean()))
            off.append(np.angle(z.mean()) / (2 * np.pi) * per[bar == b].mean() / 2 * 1000)
    R, off = np.array(R), np.array(off)
    r["bars_with_3plus_kick_snare"] = int(len(R))
    r["bar_coherence_R_median"] = round(float(np.median(R)), 3)
    r["bars_R_over_0.9"] = round(float(np.mean(R > 0.9)), 3)
    r["bar_offset_ms_median_abs"] = round(float(np.median(np.abs(off))), 1)
    r["bars_offset_within_10ms"] = round(float(np.mean(np.abs(off) < 10)), 3)
    e = np.abs(err16(held, beats))
    r["heldout_hits"] = int(len(held))
    r["heldout_err16_ms_median"] = round(float(np.median(e)), 1)
    r["heldout_within_10ms"] = round(float(np.mean(e < 10)), 3)
    r["heldout_chance_within_10ms"] = round(float(20 / (np.median(per) / 4 * 1000)), 3)
    return r


def best_downbeat(beats, hits, lo=None, hi=None):
    sn = hits["snare"]
    loud = sn[sn[:, 1] > np.percentile(sn[:, 1], 30), 0]
    cr = hits["crash"][:, 0]
    sel = lambda a: a[(a >= (lo if lo is not None else -1)) & (a < (hi if hi is not None else 1e9))]
    loud, cr = sel(loud), sel(cr)
    sc = []
    for ph in range(4):
        s = 0.0
        for t, w in [(loud, 1.0), (cr, 1.0)]:
            if not len(t):
                continue
            x, per = pos(t, beats)
            on = np.abs(x - np.round(x)) * per < 0.035
            bib = np.mod(np.round(x).astype(int) - ph, 4)
            if w and t is loud:
                s += np.sum(on & (bib % 2 == 1)) - np.sum(on & (bib % 2 == 0))
            else:
                s += np.sum(on & (bib == 0)) - 0.5 * np.sum(on & (bib != 0))
        sc.append(float(s))
    return int(np.argmax(sc)), sc


def main():
    hits = load_hits()
    fit_t = np.sort(np.concatenate([hits["kick"][:, 0], hits["snare"][:, 0]]))
    t0, P, res, keep, se = fit_const(fit_t)
    bpm = 60 / P
    bpm_se = 60 / P ** 2 * se[1]
    print(f"constant grid: T0 {t0:.5f} s, period {P:.6f} s, BPM {bpm:.4f} +- {bpm_se:.4f}; "
          f"|res| median {np.median(np.abs(res)) * 1000:.2f} ms, p90 {np.percentile(np.abs(res), 90) * 1000:.2f} ms, "
          f"kept {keep.mean():.3f}")
    first_event = min(hits[k][0, 0] for k in hits)
    last_event = max(hits[k][-1, 0] for k in hits)
    n_last = int(np.ceil((last_event - t0) / P)) + 1
    beats = t0 + np.arange(0, n_last + 1) * P
    beats = beats[beats < SONG_END]
    # local tempo / phase in 8 s windows (fit set only), and the DP live-tempo tracker
    local = []
    for a in np.arange(0, 168, 8.0):
        s = (fit_t >= a) & (fit_t < a + 8)
        if s.sum() < 8:
            continue
        lt0, lP, lres, lk, _ = fit_const(fit_t[s], P, t0)
        n_mid = np.round(((a + 4) - t0) / P)
        off = (lt0 + n_mid * lP) - (t0 + n_mid * P)
        local.append([a, a + 8, int(s.sum()), round(60 / lP, 3), round(off * 1000, 2)])
    n = int(SONG_END / FR) + 1
    dp = dp_grid(hits, n)
    dp = dp[(dp > first_event - 0.1) & (dp < last_event + 0.3)]
    x = (dp - t0) / P
    dev = (x - np.round(x)) * P * 1000
    dp_dev = {"dp_beats": int(len(dp)), "median_abs_ms": round(float(np.median(np.abs(dev))), 2),
              "p95_abs_ms": round(float(np.percentile(np.abs(dev), 95)), 2),
              "max_abs_ms": round(float(np.max(np.abs(dev))), 2),
              "beats_not_on_a_grid_beat": int(np.sum(np.abs(dev) > 40))}
    print("local", local)
    print("DP vs constant", dp_dev)
    # downbeat phase
    ph, sc = best_downbeat(beats, hits)
    print("phase scores (downbeat = beat index mod 4)", sc, "->", ph)
    held = np.sort(np.concatenate([hits[k][:, 0] for k in ("hihat", "racktom", "floortom", "crash_rise", "ride_rise")]))
    tests = {"this grid (constant 148)": validate(beats, ph, hits, held)}
    old = json.load(open("/home/user/build/track/grid.json"))
    ob = old["offset"] + np.arange(-2, 450) * old["period"]
    ob = ob[(ob > -1) & (ob < 171)]
    oph = int(np.round((old["bars"][0] - ob[0]) / old["period"])) % 4
    tests["old grid 152.02 BPM as written"] = validate(ob, oph, hits, held)
    shifts = np.arange(-0.2, 0.2, 0.001)
    sh = shifts[int(np.argmin([np.mean(np.abs(err16(fit_t, ob + s))) for s in shifts]))]
    tests[f"old grid 152.02 BPM, best shift {sh * 1000:+.0f} ms"] = validate(ob + sh, oph, hits, held)
    p152 = 60 / 152
    ph152 = np.arange(0, p152, 0.001)
    b152 = min((np.mean(np.abs(err16(fit_t, x0 + np.arange(-1, 440) * p152))), x0) for x0 in ph152)[1]
    g152 = b152 + np.arange(-1, 440) * p152
    g152 = g152[g152 < 171]
    ph2, _ = best_downbeat(g152, hits)
    tests["best constant 152 BPM"] = validate(g152, ph2, hits, held)
    phd, _ = best_downbeat(dp, hits)
    tests["DP live-tempo grid"] = validate(dp, phd, hits, held)
    for k, v in tests.items():
        print(k, v)
    # per-section phase check
    return dict(t0=t0, P=P, bpm=bpm, bpm_se=bpm_se, res=res, keep=keep, beats=beats, phase=ph, phase_scores=sc,
                local=local, dp_dev=dp_dev, tests=tests, hits=hits, first_event=first_event, last_event=last_event)


if __name__ == "__main__":
    main()
