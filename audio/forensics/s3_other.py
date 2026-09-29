"""Step 3: what is the second mp3 (the non-drum file, "other" here), and can it replace the guitar in the master?

A. Decode it gapless (it is 48 kHz already; Lavc tag: encoder delay 576, padding 577).
B. Drum removal from the master: STFT least squares (lsfit.py), master(f, t) ~ sum_k H_k(f) drum_k(f, t) per
   channel, gains refit every 3 s (6 s windows). nondrums = master - fitted drums, sample-locked to master by
   construction. Written to /home/user/build/v5/stems/nondrums.wav (stereo).
C. Lag curve: GCC-PHAT (100-3000 Hz) between the non-drum master and the other file in 2 s windows every
   0.5 s, tracked from window to window (search +-40 ms around the previous confident lag), sub-sample peak.
   Speed and drift: straight-line fit of lag against time, plus the plateaus and steps of the residual.
D. Tempo comb: |sum_t o(t) exp(-2 pi i h f t)| / sum o over the whole file (o = spectral flux onset
   strength), scanned 146.5-150 BPM, for the master, the non-drum master and the other file.
E. Contents: per-band levels in drum-free and drum sections, versus the master, nondrums and drum stems.
F. Model test, per 6 s window and per octave band (mono): residual energy of master - fit, relative to the
   master, for (1) drums only, (2) drums + other at the best single constant lag, (3) drums + other warped
   through the measured lag curve. If the file were the guitar bus of this master, (3) would cancel to far
   below -20 dB.
G. /home/user/build/v5/stems/other.wav = the other file warped to master time through the lag curve (best
   effort; NOT sample-locked, see the report), and /home/user/build/v5/other_report.json.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft, welch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import lsfit  # noqa: E402

W = os.path.join(C.OUT, "work")


def decode_other():
    p = os.path.join(W, "other48_gapless.wav")
    if not os.path.exists(p):
        C.decode_mp3(C.OTHER_MP3, p, gapless=True)
    x, sr = sf.read(p, dtype="float64", always_2d=True)
    assert sr == C.SR
    return x


def nondrums(m2):
    p = os.path.join(C.OUT, "stems", "nondrums.wav")
    if os.path.exists(p):
        return sf.read(p, dtype="float64", always_2d=True)[0]
    drums = [C.stem(k)[:, 0] for k in C.DRUMS]
    n = len(m2)
    Xs = [lsfit.spec(d)[2].astype(np.complex64) for d in drums]
    out = np.zeros_like(m2)
    fitted = np.zeros_like(m2)
    for ch in range(2):
        _, _, M = lsfit.spec(m2[:, ch])
        Fz, _, _ = lsfit.fit(M.astype(np.complex64), Xs)
        fitted[:, ch] = lsfit.ispec(Fz, n)
        out[:, ch] = m2[:, ch] - fitted[:, ch]
    sf.write(p, out.astype(np.float32), C.SR, subtype="FLOAT")
    sf.write(os.path.join(W, "drums_fit.wav"), fitted.astype(np.float32), C.SR, subtype="FLOAT")
    return out


def band(x, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=C.SR, output="sos"), x)


def gcc(a, b, maxlag, lo, hi):
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    A, B = np.fft.rfft(a, n), np.fft.rfft(b, n)
    f = np.fft.rfftfreq(n, 1 / C.SR)
    X = np.conj(A) * B
    X /= np.abs(X) + 1e-12
    X[(f < lo) | (f > hi)] = 0
    cc = np.fft.irfft(X, n)
    cc = np.concatenate([cc[-maxlag:], cc[:maxlag + 1]])
    k = int(np.clip(np.argmax(cc), 1, len(cc) - 2))
    y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
    frac = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    others = np.concatenate([cc[:max(0, k - 48)], cc[k + 48:]])
    return k - maxlag + frac, float(y1 / (np.max(others) + 1e-12))


def lag_curve(r, o, win=2.0, hop=0.5, lo=100, hi=3000, search=0.040, start=-0.445):
    rb, ob = band(r, lo, hi), band(o, lo, hi)
    ml = int(search * C.SR)
    prev = start
    rows = []
    for tc in np.arange(win / 2 + 0.3, len(r) / C.SR - win / 2, hop):
        i0, i1 = int((tc - win / 2) * C.SR), int((tc + win / 2) * C.SR)
        L0 = int(round(prev * C.SR))
        if i0 + L0 - ml < 0 or i1 + L0 + ml > len(o):
            continue
        a = rb[i0:i1]
        if np.std(a) < 1e-4:
            rows.append((tc, np.nan, 0.0, 0.0))
            continue
        a_pad = np.concatenate([np.zeros(ml), a, np.zeros(ml)])
        b = ob[i0 + L0 - ml:i1 + L0 + ml]
        L, pr = gcc(a_pad, b, ml, lo, hi)
        Li = int(round(L))
        bb = ob[i0 + L0 + Li:i1 + L0 + Li]
        rho = float(np.dot(a, bb) / np.sqrt(np.dot(a, a) * np.dot(bb, bb) + 1e-20))
        lag = (L0 + L) / C.SR
        rows.append((tc, lag, pr, rho))
        if pr > 2.0 and rho > 0.4:
            prev = lag
    return np.array(rows)


def smooth_lag(rows, n):
    """Lag at every master sample: confident windows only, held piecewise, linearly joined."""
    ok = (rows[:, 2] > 2.0) & (rows[:, 3] > 0.4)
    t, L = rows[ok, 0], rows[ok, 1]
    return np.interp(np.arange(n) / C.SR, t, L), ok


def warp(o, lag_s):
    """y[n] = o[n + lag(n)] (fractional, linear interpolation), both channels."""
    pos = np.arange(len(lag_s)) + lag_s * C.SR
    y = np.zeros((len(lag_s), o.shape[1]))
    for ch in range(o.shape[1]):
        y[:, ch] = np.interp(pos, np.arange(len(o)), o[:, ch], left=0.0, right=0.0)
    return y


def flux(x):
    f, t, Z = stft(x, fs=C.SR, nperseg=2048, noverlap=2048 - 240, boundary=None, padded=False)
    S = np.log1p(1000 * np.abs(Z[(f > 80) & (f < 5000)]))
    fl = np.maximum(np.diff(S, axis=1), 0).sum(0)
    fl = fl - np.convolve(fl, np.ones(100) / 100, mode="same")
    return t[1:] + 1024 / C.SR, np.maximum(fl, 0)


def comb(x):
    t, o = flux(x)
    s = t > 0.3
    t, o = t[s], o[s]
    bpms = np.arange(146.5, 150.0, 0.005)
    out = {}
    for h in (1, 2, 4):
        mag = np.array([abs(np.sum(o * np.exp(-2j * np.pi * (b / 60 * h) * t))) / o.sum() for b in bpms])
        k = int(np.argmax(mag))
        l, r = k, k
        while l > 0 and mag[l] > mag[k] / 2:
            l -= 1
        while r < len(mag) - 1 and mag[r] > mag[k] / 2:
            r += 1
        out[f"x{h}"] = {"peak_bpm": round(float(bpms[k]), 3), "strength": round(float(mag[k]), 3),
                        "half_width_bpm": round(float(bpms[r] - bpms[l]), 3)}
    return out


OCT = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000),
       (8000, 16000)]


def band_levels(x):
    f, p = welch(x, C.SR, nperseg=4096)
    return [round(float(10 * np.log10(p[(f >= a) & (f < b)].sum() + 1e-20)), 1) for a, b in OCT]


def model_test(m, drums, regs, win=280, hop=140):
    """Residual (dB re master) per window and octave for master ~ drums + regs (all mono)."""
    _, _, M = lsfit.spec(m)
    f = np.fft.rfftfreq(lsfit.NFFT, 1 / C.SR)
    Xd = [lsfit.spec(d)[2].astype(np.complex64) for d in drums]
    out = {}
    for name, extra in regs.items():
        Xs = Xd + [lsfit.spec(e)[2].astype(np.complex64) for e in extra]
        Fz, _, starts = lsfit.fit(M.astype(np.complex64), Xs, win_frames=win, hop_frames=hop)
        Rz = M - Fz
        per_band = []
        for a, b in OCT:
            s = (f >= a) & (f < b)
            per_band.append(round(float(10 * np.log10(np.sum(np.abs(Rz[s]) ** 2) / np.sum(np.abs(M[s]) ** 2))), 1))
        T = M.shape[1]
        tw = []
        for s0 in range(0, T - 94, 94):                      # ~2 s blocks
            e_r = np.sum(np.abs(Rz[:, s0:s0 + 94]) ** 2)
            e_m = np.sum(np.abs(M[:, s0:s0 + 94]) ** 2)
            tw.append([round((s0 * lsfit.HOP - lsfit.NFFT) / C.SR + 1.0, 1),
                       round(float(10 * np.log10(e_r / (e_m + 1e-20) + 1e-20)), 1)])
        tot = round(float(10 * np.log10(np.sum(np.abs(Rz) ** 2) / np.sum(np.abs(M) ** 2))), 1)
        out[name] = {"total_db": tot, "per_band_db": per_band, "over_time_db": tw}
        print(f"  model {name:28s} residual re master {tot:6.1f} dB  per band {per_band}")
    return out


def main():
    rep = {}
    m2 = C.master()
    n = len(m2)
    o2 = decode_other()
    rep["other_file"] = {"sr": C.SR, "channels": 2, "duration_s": round(len(o2) / C.SR, 4),
                         "tag": "Lavc60.31, encoder delay 576, padding 577 (gapless decode)",
                         "rms_dbfs": round(float(20 * np.log10(np.sqrt(np.mean(o2 ** 2)))), 1),
                         "master_rms_dbfs": round(float(20 * np.log10(np.sqrt(np.mean(m2 ** 2)))), 1)}
    nd = nondrums(m2)
    print("nondrums ready")
    r, o = nd.mean(axis=1), o2.mean(axis=1)
    rows = lag_curve(r, o)
    np.save(os.path.join(W, "other_lag_rows.npy"), rows)
    lag_s, ok = smooth_lag(rows, n)
    t, L = rows[ok, 0], rows[ok, 1]
    p = np.polyfit(t, L, 1)
    res = L - np.polyval(p, t)
    steps = np.diff(L)
    rep["lag"] = {
        "definition": "other_t = master_t + lag (s); negative = the same sound comes earlier in the other file",
        "windows": int(len(rows)), "confident": int(ok.sum()),
        "first": [round(float(t[0]), 2), round(float(L[0]) * 1000, 2)],
        "last": [round(float(t[-1]), 2), round(float(L[-1]) * 1000, 2)],
        "range_ms": [round(float(L.min()) * 1000, 1), round(float(L.max()) * 1000, 1)],
        "linear_fit": {"slope_ppm": round(float(p[0]) * 1e6, 1), "intercept_ms": round(float(p[1]) * 1000, 1),
                       "rate_other_vs_master": round(1 + float(p[0]), 6),
                       "residual_rms_ms": round(float(np.sqrt(np.mean(res ** 2))) * 1000, 2),
                       "residual_range_ms": [round(float(res.min()) * 1000, 1), round(float(res.max()) * 1000, 1)]},
        "adjacent_window_step_ms": {"median_abs": round(float(np.median(np.abs(steps))) * 1000, 3),
                                    "share_under_0.1ms": round(float(np.mean(np.abs(steps) < 1e-4)), 3),
                                    "share_over_2ms": round(float(np.mean(np.abs(steps) > 2e-3)), 3)},
        "curve_every_2s": [[round(float(a), 1), round(float(b) * 1000, 2)] for a, b in
                           zip(np.arange(1, 169, 2.0), np.interp(np.arange(1, 169, 2.0), t, L))],
    }
    print("lag", json.dumps({k: v for k, v in rep["lag"].items() if k != "curve_every_2s"}))
    rep["tempo_comb"] = {"master": comb(m2.mean(axis=1)), "nondrums": comb(r), "other": comb(o)}
    print("comb", json.dumps(rep["tempo_comb"]))
    drums = [C.stem(k)[:, 0] for k in C.DRUMS]
    dsum = np.sum(drums, axis=0)
    ow = warp(o2, lag_s)
    sf.write(os.path.join(C.OUT, "stems", "other.wav"), ow.astype(np.float32), C.SR, subtype="FLOAT")
    lvl = {}
    for a, b, tag in [(30.5, 35.5, "no drums"), (86.5, 90.5, "no drums"), (112, 116.5, "no drums"),
                      (17, 22, "drums"), (55, 60, "drums, crash every bar"), (95, 100, "tom groove"),
                      (145, 150, "drums")]:
        i0, i1 = int(a * C.SR), int(b * C.SR)
        lvl[f"{a}-{b} {tag}"] = {"master": band_levels(m2[i0:i1].mean(1)), "other_warped": band_levels(ow[i0:i1].mean(1)),
                                 "nondrums": band_levels(r[i0:i1]), "drum_stems_sum": band_levels(dsum[i0:i1])}
    rep["band_levels_dbfs"] = {"bands_hz": OCT, "windows": lvl}
    # model test
    const_lag = int(round(float(np.median(L)) * C.SR))
    oc = np.zeros(n)
    s0, s1 = max(0, const_lag), min(len(o), n + const_lag)
    oc[s0 - const_lag:s1 - const_lag] = o[s0:s1]
    print("model test")
    rep["model_test"] = model_test(m2.mean(axis=1), drums, {
        "drums only": [], "drums + other, constant lag": [oc], "drums + other, lag curve": [ow.mean(axis=1)]})
    rep["model_test"]["note"] = ("6 s windows, one complex gain per stem per 11.7 Hz bin, refit every 3 s; "
                                 "values are residual energy relative to the master, dB")
    C.write_json(os.path.join(C.OUT, "other_report.json"), rep, indent=1)
    return rep


if __name__ == "__main__":
    main()
