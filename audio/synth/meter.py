"""Objective measurement: loudness (ITU-R BS.1770-4 / EBU R128), true peak,
crest factor, octave-band balance, stereo image, tempo and key estimates.

All functions take float arrays, mono (n,) or stereo (n, 2), plus ``sr``.
``report()`` bundles everything into a JSON-friendly dict.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .core import SR, NOTE_NAMES, ensure_stereo, to_mono

OCTAVE_CENTRES = (31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)


# ----------------------------------------------------------------- loudness

def _k_weighting_sos(sr):
    """K-weighting as two biquads (pre-filter shelf + RLB high-pass), exact at
    any sample rate (same derivation as libebur128)."""
    # stage 1: high shelf
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = math.tan(math.pi * f0 / sr)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    # stage 2: high-pass
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / sr)
    a0 = 1 + K / Q + K * K
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    return np.array([b + a, b2 + a2])


def _block_powers(x, sr, block_s, step_s):
    """Mean square of K-weighted signal per block, summed over channels."""
    x = ensure_stereo(x)
    y = signal.sosfilt(_k_weighting_sos(sr), x, axis=0)
    p = (y ** 2).sum(axis=1)  # channel weights 1.0 for L and R
    n = int(round(block_s * sr))
    step = int(round(step_s * sr))
    if len(p) < n:
        return np.array([p.mean()]) if len(p) else np.array([0.0])
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, len(p) - n + 1, step)
    return (c[starts + n] - c[starts]) / n


def _lufs(power):
    return -0.691 + 10 * np.log10(np.maximum(power, 1e-20))


def integrated_lufs(x, sr=SR):
    z = _block_powers(x, sr, 0.4, 0.1)
    l = _lufs(z)
    z1 = z[l > -70]
    if len(z1) == 0:
        return -math.inf
    rel = _lufs(z1.mean()) - 10
    z2 = z[(l > -70) & (l > rel)]
    return float(_lufs(z2.mean())) if len(z2) else -math.inf


def short_term_lufs(x, sr=SR, step_s=0.1):
    """Short-term loudness (3 s window) sampled every step_s. Returns (times, lufs)
    where times are window end times in seconds."""
    z = _block_powers(x, sr, 3.0, step_s)
    t = 3.0 + np.arange(len(z)) * step_s
    return t, _lufs(z)


def momentary_lufs(x, sr=SR, step_s=0.1):
    z = _block_powers(x, sr, 0.4, step_s)
    t = 0.4 + np.arange(len(z)) * step_s
    return t, _lufs(z)


def loudness_range(x, sr=SR):
    """EBU Tech 3342 LRA in LU."""
    z = _block_powers(x, sr, 3.0, 0.1)
    l = _lufs(z)
    z1 = z[l > -70]
    if len(z1) < 2:
        return 0.0
    rel = _lufs(z1.mean()) - 20
    l2 = l[(l > -70) & (l > rel)]
    if len(l2) < 2:
        return 0.0
    return float(np.percentile(l2, 95) - np.percentile(l2, 10))


def true_peak(x, sr=SR):
    """True peak in dBTP via 4x polyphase oversampling (2x above 96 kHz)."""
    x = ensure_stereo(x)
    up = 4 if sr < 96000 else 2
    y = signal.resample_poly(x, up, 1, axis=0, window=("kaiser", 8.0))
    pk = max(np.abs(y).max(), np.abs(x).max())
    return float(20 * np.log10(max(pk, 1e-12)))


def true_peak_envelope(x, sr=SR):
    """Per-input-sample true peak magnitude (max over the oversampled phases)."""
    up = 4 if sr < 96000 else 2
    x = ensure_stereo(x)
    y = signal.resample_poly(x, up, 1, axis=0, window=("kaiser", 8.0))
    y = np.abs(y).max(axis=1)[: len(x) * up].reshape(len(x), up).max(axis=1)
    return np.maximum(y, np.abs(x).max(axis=1))


def sample_peak(x):
    return float(20 * np.log10(max(np.abs(x).max(), 1e-12)))


def rms_db(x):
    return float(10 * np.log10(max(np.mean(np.asarray(x) ** 2), 1e-24)))


def crest_factor_db(x, sr=SR):
    """Peak-to-RMS (sample peak) and true-peak-to-RMS over the whole signal, both
    channels pooled. Also returns PLR (true peak minus integrated loudness)."""
    r = rms_db(x)
    return {
        "sample_peak_to_rms_db": sample_peak(x) - r,
        "true_peak_to_rms_db": true_peak(x, sr) - r,
    }


def clipped_samples(x, threshold=0.999, run=3):
    """Number of runs of >= run consecutive samples at or above threshold."""
    a = np.abs(ensure_stereo(x)) >= threshold
    count = 0
    for ch in range(a.shape[1]):
        v = a[:, ch].astype(np.int8)
        if not v.any():
            continue
        d = np.diff(np.concatenate([[0], v, [0]]))
        starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        count += int(np.sum((ends - starts) >= run))
    return count


# ----------------------------------------------------------------- spectrum

def octave_bands(x, sr=SR, centres=OCTAVE_CENTRES):
    """Power per octave band of the mono sum. Returns dict centre -> dB relative
    to the total power (so a flat-power signal would read about -10 dB per band,
    pink noise reads equal values)."""
    m = to_mono(x)
    nper = min(16384, len(m))
    f, pxx = signal.welch(m, sr, nperseg=nper, noverlap=nper // 2, window="hann")
    total = np.trapezoid(pxx, f) if hasattr(np, "trapezoid") else np.trapz(pxx, f)
    out = {}
    for c in centres:
        lo, hi = c / math.sqrt(2), min(c * math.sqrt(2), sr / 2)
        sel = (f >= lo) & (f < hi)
        pw = pxx[sel].sum() * (f[1] - f[0]) if sel.any() else 0.0
        out[c] = float(10 * np.log10(max(pw, 1e-24) / max(total, 1e-24)))
    return out


def spectral_centroid(x, sr=SR):
    m = to_mono(x)
    f, pxx = signal.welch(m, sr, nperseg=min(8192, len(m)))
    return float((f * pxx).sum() / max(pxx.sum(), 1e-24))


def spectral_tilt_db_per_oct(bands):
    """Least-squares slope of octave-band levels between 125 Hz and 8 kHz."""
    cs = np.array([c for c in bands if 125 <= c <= 8000], dtype=float)
    v = np.array([bands[c] for c in bands if 125 <= c <= 8000])
    k = np.polyfit(np.log2(cs), v, 1)
    return float(k[0])


# ----------------------------------------------------------------- stereo

def stereo_stats(x, sr=SR):
    """Correlation and side/mid ratio, overall and in three bands."""
    x = ensure_stereo(x)
    out = {}

    def stats(l, r):
        el, er = np.dot(l, l), np.dot(r, r)
        corr = float(np.dot(l, r) / math.sqrt(max(el * er, 1e-30)))
        m, s = 0.5 * (l + r), 0.5 * (l - r)
        sm = float(10 * np.log10(max(np.dot(s, s), 1e-30) / max(np.dot(m, m), 1e-30)))
        bal = float(10 * np.log10(max(el, 1e-30) / max(er, 1e-30)))
        return corr, sm, bal

    c, sm, bal = stats(x[:, 0], x[:, 1])
    out.update(correlation=c, side_to_mid_db=sm, lr_balance_db=bal)
    bands = {"low_<200Hz": ("lowpass", 200), "mid_200-2kHz": ("bandpass", (200, 2000)),
             "high_>2kHz": ("highpass", 2000)}
    for name, (kind, fc) in bands.items():
        sos = signal.butter(4, fc, kind, fs=sr, output="sos")
        y = signal.sosfiltfilt(sos, x, axis=0)
        c, sm, _ = stats(y[:, 0], y[:, 1])
        out[name] = {"correlation": c, "side_to_mid_db": sm}
    return out


def correlation_curve(x, sr=SR, win_s=1.0):
    x = ensure_stereo(x)
    n = int(win_s * sr)
    res = []
    for i in range(0, len(x) - n + 1, n):
        l, r = x[i:i + n, 0], x[i:i + n, 1]
        d = math.sqrt(max(np.dot(l, l) * np.dot(r, r), 1e-30))
        res.append(float(np.dot(l, r) / d))
    return res


# ----------------------------------------------------------------- rhythm

def onset_envelope(x, sr=SR, hop=256, n_fft=2048):
    """Log-compressed, band-summed spectral flux. Returns (envelope, frame_rate)."""
    m = to_mono(x)
    f, t, Z = signal.stft(m, sr, nperseg=n_fft, noverlap=n_fft - hop, boundary=None, padded=False)
    mag = np.log1p(100 * np.abs(Z))
    # 48 log-spaced bands from 40 Hz to 16 kHz
    edges = np.geomspace(40, min(16000, sr / 2 - 1), 49)
    idx = np.searchsorted(f, edges)
    bands = np.stack([mag[idx[i]:max(idx[i + 1], idx[i] + 1)].mean(axis=0) for i in range(48)])
    flux = np.maximum(np.diff(bands, axis=1), 0).sum(axis=0)
    flux = np.concatenate([[0.0], flux])
    # remove slow trend
    w = max(3, int(0.5 * sr / hop))
    trend = np.convolve(flux, np.ones(w) / w, mode="same")
    env = np.maximum(flux - trend, 0)
    return env, sr / hop


def onset_times(x, sr=SR, threshold=0.3, min_gap_s=0.07):
    env, fr = onset_envelope(x, sr)
    if env.max() <= 0:
        return []
    e = env / env.max()
    peaks, _ = signal.find_peaks(e, height=threshold, distance=max(1, int(min_gap_s * fr)))
    return [float(p / fr) for p in peaks]


def tempo_estimate(x, sr=SR, lo=60.0, hi=200.0, prior_bpm=110.0):
    """Autocorrelation of the onset envelope with a log-normal tempo prior.
    Returns dict(bpm, confidence 0..1, candidates=[(bpm, strength)])."""
    env, fr = onset_envelope(x, sr)
    env = env - env.mean()
    if not np.any(env):
        return {"bpm": None, "confidence": 0.0, "candidates": []}
    ac = signal.correlate(env, env, mode="full", method="fft")[len(env) - 1:]
    ac /= max(ac[0], 1e-12)
    lags = np.arange(len(ac))
    bpm_of = lambda lag: 60.0 * fr / lag
    lmin, lmax = int(60 * fr / hi), min(int(60 * fr / lo) + 1, len(ac) - 1)
    if lmax <= lmin + 2:
        return {"bpm": None, "confidence": 0.0, "candidates": []}
    seg = ac[lmin:lmax]
    bpms = bpm_of(lags[lmin:lmax])
    prior = np.exp(-0.5 * (np.log2(bpms / prior_bpm) / 1.0) ** 2)
    score = np.maximum(seg, 0) * prior
    peaks, _ = signal.find_peaks(score)
    if len(peaks) == 0:
        return {"bpm": None, "confidence": 0.0, "candidates": []}
    order = peaks[np.argsort(score[peaks])[::-1]]
    cands = []
    for p in order[:4]:
        # parabolic interpolation of the lag
        if 0 < p < len(seg) - 1:
            a, b, c = seg[p - 1], seg[p], seg[p + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if den != 0 else 0.0
        else:
            off = 0.0
        cands.append((round(float(bpm_of(lmin + p + off)), 1), round(float(seg[p]), 3)))
    return {"bpm": cands[0][0], "confidence": cands[0][1], "candidates": cands}


# ----------------------------------------------------------------- tonality

# Krumhansl-Kessler key profiles
_KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def chroma(x, sr=SR, fmin=55.0, fmax=5000.0, n_fft=16384, hop=4096, a4=440.0):
    """Mean 12-bin chroma (C..B), normalised to max 1. Uses whitened log
    magnitude and Gaussian weighting around semitone centres, so broadband noise
    and slightly detuned bins count less."""
    m = to_mono(x)
    if len(m) < n_fft:
        m = np.pad(m, (0, n_fft - len(m)))
    f, t, Z = signal.stft(m, sr, nperseg=n_fft, noverlap=n_fft - hop, boundary=None, padded=False)
    mag = np.abs(Z)
    sel = (f >= fmin) & (f <= fmax)
    f, mag = f[sel], mag[sel]
    lm = np.log1p(1000 * mag / max(mag.max(), 1e-12))
    # whiten: subtract a running median across frequency (removes noise floor)
    floor = signal.medfilt(lm.mean(axis=1), 31)[:, None]
    lm = np.maximum(lm - floor, 0)
    midi = 69 + 12 * np.log2(f / a4)
    dev = midi - np.round(midi)
    w = np.exp(-0.5 * (dev / 0.2) ** 2)
    pcs = np.mod(np.round(midi).astype(int), 12)
    ch = np.zeros(12)
    energy = (lm * w[:, None]).sum(axis=1)
    for pc in range(12):
        ch[pc] = energy[pcs == pc].sum()
    return ch / max(ch.max(), 1e-12)


def key_estimate(x, sr=SR, bass_weight=0.0):
    """Krumhansl-Kessler key match on the mean chroma (55 Hz-5 kHz). bass_weight
    > 0 adds a 30-250 Hz chroma, which helps when the bass carries the roots
    but hurts when drums are tuned off-key. Treat the result as a tonal-centre
    candidate: relative major/minor and pedal-tone confusions are common (the
    demo, in G major with an F# pedal, reads as B minor). Check the runner-up."""
    ch = chroma(x, sr)
    if bass_weight:
        cb = chroma(x, sr, fmin=30.0, fmax=250.0)
        ch = ch + bass_weight * cb
        ch = ch / max(ch.max(), 1e-12)
    best = []
    for tonic in range(12):
        for mode, prof in (("major", _KK_MAJOR), ("minor", _KK_MINOR)):
            r = np.corrcoef(ch, np.roll(prof, tonic))[0, 1]
            best.append((float(r), f"{NOTE_NAMES[tonic]} {mode}"))
    best.sort(reverse=True)
    top_pcs = [NOTE_NAMES[i] for i in np.argsort(ch)[::-1][:5]]
    return {"key": best[0][1], "correlation": round(best[0][0], 3),
            "runner_up": best[1][1], "runner_up_correlation": round(best[1][0], 3),
            "strongest_pitch_classes": top_pcs,
            "chroma": [round(float(v), 3) for v in ch]}


# ----------------------------------------------------------------- summary

def activity(x, sr=SR, win_s=0.1, floor_db=-60.0):
    """Fraction of windows above floor_db RMS, and first/last active time."""
    m = np.abs(ensure_stereo(x)).max(axis=1)
    n = int(win_s * sr)
    k = len(m) // n
    if k == 0:
        return {"active_fraction": 0.0, "first_active_s": None, "last_active_s": None}
    r = np.sqrt((ensure_stereo(x)[: k * n] ** 2).mean(axis=1).reshape(k, n).mean(axis=1))
    act = 20 * np.log10(np.maximum(r, 1e-12)) > floor_db
    idx = np.nonzero(act)[0]
    return {"active_fraction": float(act.mean()),
            "first_active_s": float(idx[0] * win_s) if len(idx) else None,
            "last_active_s": float((idx[-1] + 1) * win_s) if len(idx) else None}


def report(x, sr=SR, *, tempo=True, key=True):
    x = np.asarray(x, dtype=np.float64)
    st = ensure_stereo(x)
    il = integrated_lufs(st, sr)
    tp = true_peak(st, sr)
    bands = octave_bands(st, sr)
    t_st, l_st = short_term_lufs(st, sr, step_s=0.5)
    rep = {
        "duration_s": round(len(st) / sr, 3),
        "sample_rate": sr,
        "channels": 1 if x.ndim == 1 else x.shape[1],
        "integrated_lufs": round(il, 2),
        "loudness_range_lu": round(loudness_range(st, sr), 2),
        "max_short_term_lufs": round(float(l_st.max()), 2) if len(l_st) else None,
        "max_momentary_lufs": round(float(momentary_lufs(st, sr)[1].max()), 2),
        "true_peak_dbtp": round(tp, 2),
        "sample_peak_dbfs": round(sample_peak(st), 2),
        "rms_dbfs": round(rms_db(st), 2),
        "plr_db": round(tp - il, 2),
        "crest": {k: round(v, 2) for k, v in crest_factor_db(st, sr).items()},
        "dc_offset": [float(f"{v:.2e}") for v in st.mean(axis=0)],
        "clipped_runs": clipped_samples(st),
        "octave_bands_db_rel": {str(k): round(v, 1) for k, v in bands.items()},
        "spectral_tilt_db_per_oct_125_8k": round(spectral_tilt_db_per_oct(bands), 2),
        "spectral_centroid_hz": round(spectral_centroid(st, sr), 0),
        "stereo": _round(stereo_stats(st, sr)),
        "activity": activity(st, sr),
        "short_term_lufs_every_0.5s": [round(float(v), 1) for v in l_st],
    }
    if tempo:
        rep["tempo"] = tempo_estimate(st, sr)
    if key:
        rep["key"] = key_estimate(st, sr)
    return rep


def _round(d, n=3):
    if isinstance(d, dict):
        return {k: _round(v, n) for k, v in d.items()}
    if isinstance(d, float):
        return round(d, n)
    return d
