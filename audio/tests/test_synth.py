#!/usr/bin/env python3
"""Numerical quality checks for the synth package.

Run: python3 audio/tests/test_synth.py   (pytest also works if installed)
Each test prints its measured value, so the output doubles as a spec sheet.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from synth import (SR, Bass, Clap, EPiano, Guitar, HiHat, JunoPad, Kick, Reverb, Snare, StereoDelay,  # noqa: E402
                   adsr, compressor, fx, io, limiter, meter, midi_to_hz, osc)
from synth.filters import ladder  # noqa: E402

RESULTS = {}


def record(name, value, ok):
    RESULTS[name] = (value, ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {value}")
    assert ok, name


def test_lufs_and_true_peak_match_ffmpeg():
    rng = np.random.default_rng(0)
    x = np.stack([osc.pink_noise(10 * SR, rng), osc.pink_noise(10 * SR, rng)], 1) * 0.1
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "p.wav")
        io.write_wav(p, x)
        ref = io.ffmpeg_loudness(p)
    l, tp = meter.integrated_lufs(x), meter.true_peak(x)
    record("LUFS vs ffmpeg ebur128 (LU)", round(l - ref["ebur128_I"], 3), abs(l - ref["ebur128_I"]) < 0.1)
    record("true peak vs ffmpeg (dB)", round(tp - ref["ebur128_TP"], 3), abs(tp - ref["ebur128_TP"]) < 0.3)


def _alias_ratio_db(y, f0, sr=SR):
    """Energy away from harmonics of f0 relative to total, in dB."""
    y = y[sr // 10: sr // 10 + sr]
    S = np.abs(np.fft.rfft(y * np.kaiser(len(y), 20.0))) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    h = np.round(f / f0)
    near = (np.abs(f - h * f0) < 10.0) & (h >= 1)
    return 10 * np.log10(S[~near & (f > 20)].sum() / S.sum())


def test_saw_aliasing():
    f0 = 1760.0 * 1.0137  # an off-grid pitch so aliases do not land on harmonics
    n = SR + SR // 5
    naive = 2 * np.mod(np.arange(n) * f0 / SR, 1.0) - 1
    blep1 = osc.saw_blep(f0, n, SR)
    blep2 = osc.decimate(osc.saw_blep(f0, 2 * n, 2 * SR), 2)
    add1 = osc.saw(f0, n, SR)
    add2 = osc.decimate(osc.pulse(f0, 2 * n, 2 * SR, 0.3), 2)
    a0, a1, a2, a3, a4 = (_alias_ratio_db(v, f0) for v in (naive, blep1, blep2, add1, add2))
    print(f"      naive saw {a0:.1f} dB, PolyBLEP 1x {a1:.1f} dB, PolyBLEP 2x {a2:.1f} dB, "
          f"additive saw 1x {a3:.1f} dB, additive pulse 2x {a4:.1f} dB")
    record("saw alias energy at 1.78 kHz, additive (dB rel. total)", round(a3, 1), a3 < -90)
    record("pulse alias energy at 1.78 kHz, additive at 2x (dB)", round(a4, 1), a4 < -90)


def test_guitar_tuning():
    g = Guitar(humanize=0)
    worst = 0.0
    for p in (40, 45, 50, 55, 59, 64, 69, 76, 83):
        y = g.voice(p, 0.8, 1.5, {})
        seg = y[int(0.2 * SR): int(1.2 * SR)] * np.hanning(SR)
        S = np.abs(np.fft.rfft(seg, 16 * SR))
        f = np.fft.rfftfreq(16 * SR, 1 / SR)
        f0 = float(midi_to_hz(p))
        k = np.argmax(S * ((f > f0 * 0.95) & (f < f0 * 1.05)))
        a, b, c = np.log(S[k - 1:k + 2])
        fe = (k + 0.5 * (a - c) / (a - 2 * b + c)) * (f[1] - f[0])
        worst = max(worst, abs(1200 * math.log2(fe / f0)))
    record("guitar worst tuning error (cents)", round(worst, 3), worst < 0.5)


def test_instruments_dc_and_peaks():
    worst_dc, worst_pk = 0.0, -200.0
    voices = [(Guitar(), 52), (Guitar(tone="clean_amp"), 64), (EPiano(), 60), (JunoPad(), 55), (Bass(), 36),
              (Bass(kind="sub"), 31), (Kick(), 36), (Snare(), 38), (Clap(), 39), (HiHat(), 42), (HiHat(), 46)]
    for inst, p in voices:
        v = inst.post(inst.voice(p, 1.0, 1.0, {}))
        worst_dc = max(worst_dc, float(np.abs(np.mean(v, axis=0)).max()))
        worst_pk = max(worst_pk, meter.true_peak(v))
    record("worst DC offset of any voice at full velocity", f"{worst_dc:.1e}", worst_dc < 1e-3)
    record("worst true peak of any single voice (dBTP)", round(worst_pk, 2), worst_pk < 0.0)


def test_voice_edges_are_silent():
    """Every voice must start and end at (near) zero: no clicks at note on/off."""
    worst = 0.0
    for inst, p in ((Guitar(), 57), (EPiano(), 72), (JunoPad(), 60), (Bass(), 40), (Kick(), 36),
                    (Snare(), 38), (HiHat(), 42)):
        v = np.atleast_2d(inst.voice(p, 1.0, 0.4, {}).T).T
        pk = np.abs(v).max()
        worst = max(worst, float(np.abs(v[-1]).max() / pk))
    record("worst last-sample level relative to voice peak", f"{worst:.1e}", worst < 1e-3)


def test_adsr_slew():
    e = adsr(0.5, 0.002, 0.2, 0.5, 0.01, SR)
    slew = np.abs(np.diff(e)).max()
    # fastest legal change: full scale over the 2 ms attack, with curve factor
    record("ADSR max per-sample step (2 ms attack)", round(float(slew), 4), slew < 4.5 / (0.002 * SR))
    record("ADSR ends at zero", float(e[-1]), abs(e[-1]) < 1e-9)


def test_ladder_slope():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(4 * SR) * 0.1
    y = ladder(x, 1000.0, 0.0, 1.0, 0.0)
    fx_ = np.fft.rfftfreq(len(x), 1 / SR)
    H = np.abs(np.fft.rfft(y)) / np.abs(np.fft.rfft(x))

    def at(f):
        sel = (fx_ > f * 0.97) & (fx_ < f * 1.03)
        return 20 * np.log10(np.median(H[sel]))
    slope = at(8000) - at(4000)
    record("ladder gain at cutoff (dB, ideal -12)", round(at(1000), 1), abs(at(1000) + 12) < 1.5)
    record("ladder slope 4k->8k (dB/oct, ideal about -24)", round(slope, 1), -27 < slope < -20)


def test_reverb_rt60():
    imp = np.zeros((6 * SR, 2))
    imp[100] = 1.0
    for rt in (1.2, 2.5):
        ir = Reverb(rt60=rt, hf_ratio=0.9, low_cut=20, high_cut=20000, mod_depth_ms=0.0)(imp)
        m = ir.mean(axis=1)
        from synth.filters import butter
        m = butter(m, 4, (500, 2000), "bandpass")
        edc = np.cumsum((m ** 2)[::-1])[::-1]
        edc = 10 * np.log10(edc / edc[0] + 1e-30)
        t = np.arange(len(edc)) / SR
        sel = (edc < -5) & (edc > -35)
        k = np.polyfit(t[sel], edc[sel], 1)[0]
        rt_meas = -60 / k
        record(f"reverb RT60 set {rt} s, measured (T30, 500 Hz-2 kHz)", round(rt_meas, 2), abs(rt_meas / rt - 1) < 0.2)
    corr = meter.stereo_stats(ir)["correlation"]
    record("reverb L/R correlation (decorrelated tail)", round(corr, 3), abs(corr) < 0.3)


def test_delay_times():
    imp = np.zeros((SR, 2))
    imp[0] = 1.0
    d = StereoDelay(0.25, 0.375, feedback=0.0, lp_hz=20000, hp_hz=5)(imp)
    kl, kr = int(np.argmax(np.abs(d[:, 0]))), int(np.argmax(np.abs(d[:, 1])))
    record("delay first repeat L/R (samples)", (kl, kr), kl == int(0.25 * SR) and kr == int(0.375 * SR))


def test_compressor_static_curve():
    t = np.arange(2 * SR) / SR
    x = 10 ** (-6 / 20) * np.sin(2 * np.pi * 1000 * t)
    y = compressor(np.stack([x, x], 1), threshold_db=-18, ratio=4, knee_db=0.0, attack_ms=1, release_ms=50,
                   sidechain_hp=None)
    gr = 20 * np.log10(np.abs(y[SR:, 0]).max() / np.abs(x[SR:]).max())
    record("compressor GR for 12 dB over at 4:1 (dB, ideal -9)", round(gr, 2), abs(gr + 9) < 0.5)


def test_limiter_true_peak():
    rng = np.random.default_rng(3)
    x = np.stack([osc.pink_noise(8 * SR, rng), osc.pink_noise(8 * SR, rng)], 1) * 0.5
    x[SR * 3: SR * 3 + 200] *= 4.0  # a sharp overshoot
    y, info = limiter(x, -1.0)
    tp = meter.true_peak(y)
    record("limiter output true peak (ceiling -1.0 dBTP)", round(tp, 3), tp <= -0.99)
    record("limiter clipped runs", meter.clipped_samples(y), meter.clipped_samples(y) == 0)


def test_fx_edges():
    r = fx.riser(2.0)
    d = fx.downlifter(2.0)
    i = fx.impact(2.0)
    c = fx.reverse_cymbal(1.5)
    worst = max(float(np.abs(v[0]).max()) for v in (r, d, i, c))
    tail = max(float(np.abs(v[-1]).max()) for v in (r, d, i, c))
    record("FX first-sample level (onsets are shaped)", f"{worst:.1e}", worst < 0.05)
    record("FX last-sample level", f"{tail:.1e}", tail < 1e-2)


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError:
                fails += 1
    print(f"\n{len(RESULTS) - fails} passed, {fails} failed")
    sys.exit(1 if fails else 0)
