"""Step 2: align every drum stem and the second mp3 ("thisone", called "other" here) to master time.

Method: band-limited GCC-PHAT between the master (mono sum) and each stem in 6 s windows spread over the
song, searched +-60 ms around a blind envelope estimate, peak refined to a fraction of a sample by
parabolic interpolation. A straight-line fit of lag against time gives the speed (slope, ppm) and the
offset; the residual shows any drift. Aligned copies (master length, 48 kHz, float) are written to
/home/user/build/v5/stems/{kick,snare,hihat,racktom,floortom,ohl,ohr,other}.wav with
aligned[n] = source[n + lag], lag rounded to the nearest sample (the fractional part is reported).
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BANDS = {"kick": (40, 6000), "snare": (150, 5000), "hihat": (3000, 12000), "racktom": (80, 3000),
         "floortom": (50, 2000), "ohl": (500, 10000), "ohr": (500, 10000), "other": (60, 6000)}
WIN = 6.0
SEARCH = 0.060


def band(x, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=C.SR, output="sos"), x)


def coarse(x, m):
    def env(v):
        e = np.abs(band(v, 60, 8000))
        e = np.convolve(e, np.ones(48) / 48, mode="same")[::48]
        d = np.maximum(np.diff(e, prepend=e[0]), 0)
        return (d - d.mean()) / (d.std() + 1e-12)
    es, em = env(x), env(m)
    c = fftconvolve(es, em[::-1], mode="full")
    return (int(np.argmax(c)) - (len(em) - 1)) * 48          # samples: source index = master index + lag


def gcc_phat(a, b, lo, hi, maxlag):
    """Lag L (samples, fractional) maximising sum a[n] b[n + L]; a is the reference window."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    A, B = np.fft.rfft(a, n), np.fft.rfft(b, n)
    f = np.fft.rfftfreq(n, 1 / C.SR)
    X = np.conj(A) * B
    X /= np.abs(X) + 1e-12
    X[(f < lo) | (f > hi)] = 0
    cc = np.fft.irfft(X, n)
    cc = np.concatenate([cc[-maxlag:], cc[:maxlag + 1]])
    k = int(np.argmax(cc))
    y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
    frac = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    others = np.concatenate([cc[:max(0, k - 48)], cc[k + 48:]])
    return k - maxlag + frac, float(y1), float(y1 / (np.max(others) + 1e-12))


def measure(src, m, lo, hi, lag0, centers):
    rows = []
    maxlag = int(SEARCH * C.SR)
    for tc in centers:
        i0, i1 = int((tc - WIN / 2) * C.SR), int((tc + WIN / 2) * C.SR)
        if i0 < 0 or i1 > len(m) or i0 + lag0 - maxlag < 0 or i1 + lag0 + maxlag > len(src):
            continue
        a = m[i0:i1]
        b = src[i0 + lag0 - maxlag:i1 + lag0 + maxlag]
        if np.sqrt(np.mean(b ** 2)) < 1e-5:
            continue
        # zero-pad a to the length of b so lag 0 means b[maxlag:] aligned with a
        a_pad = np.concatenate([np.zeros(maxlag), a, np.zeros(maxlag)])
        L, h, ratio = gcc_phat(band(a_pad, lo, hi), band(b, lo, hi), lo, hi, maxlag)
        rows.append((tc, lag0 + L, h, ratio))
    return np.array(rows)


def active_centers(x, lag0, n, top=24):
    """Window centres (master time) on the loudest 6 s stretches of a sparse stem (toms play in fills)."""
    hop = C.SR // 2
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    order = np.argsort(e)[::-1]
    picked = []
    for k in order:
        tc = (k * hop + hop / 2 - lag0) / C.SR
        if WIN / 2 + 0.2 < tc < n / C.SR - WIN / 2 - 0.2 and all(abs(tc - q) >= WIN / 2 for q in picked):
            picked.append(tc)
        if len(picked) >= top:
            break
    return sorted(picked)


def main():
    m2 = C.master()
    m = m2.mean(axis=1)
    grid_centers = np.arange(4.0, 166.0, 6.0)
    report = {}
    srcs = {k: sf.read(os.path.join(C.UP, f), dtype="float64")[0] for k, f in C.STEMS.items()}
    o, sro = sf.read(os.path.join(C.OUT, "work", "other48_gapless.wav"), dtype="float64", always_2d=True)
    assert sro == C.SR
    srcs["other"] = o.mean(axis=1)
    for name, x in srcs.items():
        lo, hi = BANDS[name]
        lag0 = coarse(x, m)
        centers = active_centers(x, lag0, len(m)) if name in ("racktom", "floortom") else grid_centers
        rows = measure(x, m, lo, hi, lag0, centers)
        good = rows[rows[:, 3] > 1.3]                          # clear single peak
        t, L = good[:, 0], good[:, 1]
        # robust line fit (two passes, drop > 2 samples from the first fit)
        p = np.polyfit(t, L, 1)
        keep = np.abs(L - np.polyval(p, t)) < 2.0
        p = np.polyfit(t[keep], L[keep], 1)
        res = L[keep] - np.polyval(p, t[keep])
        med = float(np.median(L[keep]))
        report[name] = dict(coarse_lag=lag0, windows=len(rows), clear=int(len(good)), used=int(keep.sum()),
                            median_lag=med, median_lag_s=med / C.SR, slope_ppm=p[0] / C.SR * 1e6,
                            fit_rms=float(np.sqrt(np.mean(res ** 2))), spread=float(np.ptp(L[keep])),
                            min_lag=float(L[keep].min()), max_lag=float(L[keep].max()),
                            per_window=[[round(float(a), 1), round(float(b), 2), round(float(r), 2)]
                                        for a, b, _, r in rows])
        print(f"{name:8s} lag {med:10.2f} smp = {med / C.SR:+.5f} s  slope {p[0] / C.SR * 1e6:+7.2f} ppm  "
              f"rms {report[name]['fit_rms']:.2f}  spread {report[name]['spread']:.2f}  used {keep.sum()}/{len(rows)}")
    C.write_json(os.path.join(C.OUT, "align.json"), report, indent=1)
    return report, srcs, len(m)


def write_aligned(report, srcs, n):
    os.makedirs(os.path.join(C.OUT, "stems"), exist_ok=True)
    for name, x in srcs.items():
        lag = int(round(report[name]["median_lag"]))
        if name == "other":
            x, _ = sf.read(os.path.join(C.OUT, "work", "other48_gapless.wav"), dtype="float64", always_2d=True)
        else:
            x = x[:, None]
        y = np.zeros((n, x.shape[1]))
        s0, s1 = max(0, lag), min(len(x), n + lag)
        y[s0 - lag:s1 - lag] = x[s0:s1]
        sf.write(os.path.join(C.OUT, "stems", f"{name}.wav"), y.astype(np.float32), C.SR, subtype="FLOAT")
        report[name]["applied_lag_samples"] = lag
        report[name]["frac_residual"] = report[name]["median_lag"] - lag
        report[name]["covered_master_s"] = [round((s0 - lag) / C.SR, 4), round((s1 - lag) / C.SR, 4)]
    C.write_json(os.path.join(C.OUT, "align.json"), report, indent=1)


if __name__ == "__main__":
    rep, srcs, n = main()
    write_aligned(rep, srcs, n)
