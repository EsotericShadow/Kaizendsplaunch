"""Mobile master for the v5 films: one chain on the whole soundtrack, tuned for phone speakers.

The owner's mix sits at -11 LUFS but carries most of its energy below 300 Hz and little above
8 kHz, so on a phone speaker (which plays almost nothing below ~250 Hz) it reads as quiet and dull.
The chain:

  1. high-pass at 30 Hz and a -4 dB low shelf at 80 Hz (energy a phone cannot play but a limiter
     has to carry);
  2. bass harmonics: the 40-110 Hz band is soft-clipped and only its 2nd-5th harmonics
     (130-550 Hz) are added back, so the kick and bass are still heard on small speakers;
  3. linear-phase EQ: -2 dB at 250 Hz (Q 0.9), +3 dB at 2.5 kHz (Q 0.7), +3.5 dB high shelf at 10 kHz;
  4. a 2:1 glue compressor (slow attack) and a look-ahead true-peak limiter at -1.5 dBTP, with the
     gain set so the result lands on the target loudness (-9.5 LUFS integrated).

The dynamics in step 4 are SHARED: the compressor's gain curve is computed on the owner's mix through steps
1-3, the limiter's on the louder of the two true-peak envelopes (film and original), and both curves
are applied unchanged to the film and to the original, so the demos and the bypass get exactly the
same gain moves and the level match made before mastering survives it. A last safety limiter at the
same ceiling only guards against rounding. The demos' level match is re-measured after the
chain (film against the original mix through the same chain) and logged to
audio/logs/v5-mobile-master.json. Writes <name>_mobile.wav in the v5 build folder.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "audio"))
from synth import meter  # noqa: E402
from synth.effects import compressor, limiter, _forward_min, _release  # noqa: E402
import math  # noqa: E402

SR = 48000
V5 = os.environ.get("V5_OUT", "/home/user/build/v5")
TARGET_LUFS = float(os.environ.get("MOBILE_LUFS", "-9.5"))
CEILING = -1.5


def bass_harmonics(x, amount_db=-9.0):
    """Soft-clip the 40-110 Hz band and add back only the harmonics it creates (130-550 Hz)."""
    lo = signal.sosfiltfilt(signal.butter(4, [40, 110], "bandpass", fs=SR, output="sos"), x, axis=0)
    m = lo.mean(axis=1)
    rms = np.sqrt(np.mean(m ** 2)) + 1e-12
    k = 1.0 / (1.2 * rms)
    gen = np.tanh(k * lo) / k + 0.25 * np.abs(np.tanh(k * lo)) / k   # odd + even harmonics
    h = signal.sosfiltfilt(signal.butter(4, [130, 550], "bandpass", fs=SR, output="sos"), gen, axis=0)
    g = 10 ** (amount_db / 20) * np.sqrt(np.mean(lo ** 2)) / (np.sqrt(np.mean(h ** 2)) + 1e-12)
    return x + g * h


def eq_curve(f):
    """Desired magnitude in dB on frequency grid f (Hz)."""
    db = np.zeros_like(f)
    # -3 dB low shelf at 70 Hz (smooth logistic in log-frequency)
    db += -4.0 / (1 + (f / 80.0) ** 2)
    # bells: gain * exp(-(log2(f/fc))^2 / (2 s^2)); s from Q (bandwidth in octaves ~ 1.4/Q)
    for fc, gain, q in [(250.0, -2.0, 0.9), (2500.0, 3.0, 0.7)]:
        s = (1.4 / q) / 2.355
        db += gain * np.exp(-(np.log2(np.maximum(f, 1) / fc)) ** 2 / (2 * s ** 2))
    # +3 dB high shelf at 10 kHz
    db += 3.5 / (1 + (10000.0 / np.maximum(f, 1)) ** 2)
    return db


def linear_phase_eq(x, taps=8191):
    f = np.linspace(0, SR / 2, 4097)
    gain = 10 ** (eq_curve(f) / 20)
    h = signal.firwin2(taps, f, gain, fs=SR, window="blackmanharris")
    d = (taps - 1) // 2
    y = signal.fftconvolve(x, h[:, None], mode="full")[d:d + len(x)]
    return y


def linear_stage(x):
    x = signal.sosfiltfilt(signal.butter(2, 30, "highpass", fs=SR, output="sos"), x, axis=0)
    x = bass_harmonics(x)
    return linear_phase_eq(x)


def limiter_gain(pk, ceiling_dbtp, lookahead_ms=5.0, release_ms=150.0):
    """The gain curve synth.effects.limiter would apply to a signal with true-peak envelope pk."""
    L = max(1, int(lookahead_ms * SR / 1000))
    rel = math.exp(-1 / (release_ms * SR / 1000))
    target = 10 ** (ceiling_dbtp / 20)
    req = np.minimum(1.0, target / np.maximum(pk, 1e-12))
    h = _release(_forward_min(req, L), rel)
    return np.convolve(np.concatenate([np.full(L - 1, h[0]), h]), np.ones(L) / L, mode="valid")


def keyed_gains(ref_lin, proc_lin, target=TARGET_LUFS):
    """One set of dynamics for both signals. The compressor is keyed by the reference (the original
    mix after steps 1-3); the limiter by the louder of the two true-peak envelopes, so the chorus's
    extra peaks fit under the ceiling without the demos being limited harder than the original.
    The make-up gain is searched so the film lands on the target loudness."""
    _, comp_db = compressor(ref_lin, threshold_db=-16.0, ratio=2.0, attack_ms=30.0, release_ms=250.0,
                            knee_db=8.0, sidechain_hp=100.0, sr=SR, return_gr=True)
    cg = 10 ** (comp_db / 20)[:, None]
    n = min(len(ref_lin), len(proc_lin))
    c_ref, c_proc = ref_lin[:n] * cg[:n], proc_lin[:n] * cg[:n]
    pk = np.maximum(meter.true_peak_envelope(c_ref, SR), meter.true_peak_envelope(c_proc, SR))
    g = target - meter.integrated_lufs(c_proc, SR)
    for _ in range(8):
        lg = limiter_gain(pk * 10 ** (g / 20), CEILING - 0.1)
        y = c_proc * 10 ** (g / 20) * lg[:, None]
        err = target - meter.integrated_lufs(y, SR)
        if abs(err) < 0.02:
            break
        g += err * 1.3
    return comp_db, g, lg


def apply_keyed(x_lin, comp_db, g, lg):
    n = min(len(x_lin), len(lg))
    y = x_lin[:n] * (10 ** (comp_db[:n] / 20) * 10 ** (g / 20) * lg[:n])[:, None]
    return limiter(y, ceiling_dbtp=CEILING, lookahead_ms=5.0, release_ms=150.0, sr=SR)


def pre(x):
    x = signal.sosfiltfilt(signal.butter(2, 30, "highpass", fs=SR, output="sos"), x, axis=0)
    x = bass_harmonics(x)
    x = linear_phase_eq(x)
    x = compressor(x, threshold_db=-16.0, ratio=2.0, attack_ms=30.0, release_ms=250.0, knee_db=8.0,
                   sidechain_hp=100.0, sr=SR)
    return x


def finish(x, gain_db):
    y, info = limiter(x * 10 ** (gain_db / 20), ceiling_dbtp=CEILING, lookahead_ms=5.0, release_ms=150.0, sr=SR)
    return y, info


def master(x, target=TARGET_LUFS):
    """Returns (y, pre_signal, gain_db, limiter_info). Gain found by secant search on output LUFS."""
    p = pre(x)
    g = target - meter.integrated_lufs(p, SR)
    for _ in range(6):
        y, info = finish(p, g)
        err = target - meter.integrated_lufs(y, SR)
        if abs(err) < 0.02:
            break
        g += err * 1.3
    return y, p, g, info


def bar_lufs(y, t0, t1):
    s = y[int(t0 * SR):int(t1 * SR)]
    return meter.integrated_lufs(s, SR) if len(s) > SR // 2 else float("nan")


def levelmatch_after(y_film, y_ref, measured, offset=0.0):
    """Per-bar and per-demo loudness deltas after the chain, on the bars measured.json lists."""
    out = {}
    for name, d in measured.get("demos", {}).items():
        rows = []
        for b in d.get("bars", []):
            t0 = b["t0"] - offset
            t1 = t0 + 1.621622
            if t0 < 0 or t1 * SR > min(len(y_film), len(y_ref)):
                continue
            rows.append(round(bar_lufs(y_film, t0, t1) - bar_lufs(y_ref, t0, t1), 3))
        spans = [(a - offset, b - offset) for a, b in d.get("on_spans", [])]
        tot = []
        for a, b in spans:
            if a >= 0 and b * SR <= min(len(y_film), len(y_ref)):
                tot.append(round(bar_lufs(y_film, a, b) - bar_lufs(y_ref, a, b), 3))
        out[name] = {"bars_delta_lu": rows, "demo_delta_lu": tot,
                     "worst_bar": max((abs(v) for v in rows if v == v), default=0.0),
                     "worst_demo": max((abs(v) for v in tot if v == v), default=0.0)}
    return out


def proc_band(proc, orig, nd):
    """The plug-in's output inside the demos: BP(nd) + (processed - original). Scaling it by a gain is
    exactly a change of the plug-in's Output Trim (the drums and the rest of the mix are untouched)."""
    sos = signal.butter(4, [120.0, 5500.0], btype="bandpass", fs=SR, output="sos")
    bp = signal.sosfiltfilt(sos, nd, axis=0)
    return bp[:len(proc)] + (proc - orig)


def span_window(n, a, b, ramp=0.02):
    w = np.zeros(n)
    i0, i1, r = int(round(a * SR)), int(round(b * SR)), int(ramp * SR)
    i0, i1 = max(0, i0), min(n, i1)
    if i1 <= i0:
        return w
    w[i0:i1] = 1.0
    up = np.sin(np.linspace(0, np.pi / 2, r)) ** 2
    w[i0:i0 + r] *= up[:max(0, min(r, i1 - i0))]
    w[max(i0, i1 - r):i1] *= up[::-1][-max(0, min(r, i1 - i0)):]
    return w


def keyed_master(proc, orig):
    """Returns (y, y_ref, info): the film and the original mix through the same keyed chain."""
    ref_lin, proc_lin = linear_stage(orig), linear_stage(proc)
    comp_db, g, lg = keyed_gains(ref_lin, proc_lin)
    y_ref, _ = apply_keyed(ref_lin, comp_db, g, lg)
    y, safety = apply_keyed(proc_lin, comp_db, g, lg)
    gr = -20 * np.log10(np.maximum(lg, 1e-9))
    info = {"makeup_db": round(float(g), 2), "comp_gr_db_median": round(float(np.median(-comp_db)), 2),
            "comp_gr_db_p99": round(float(np.percentile(-comp_db, 99)), 2),
            "limiter_gr_db_median": round(float(np.median(gr)), 2), "limiter_gr_db_p99": round(float(np.percentile(gr, 99)), 2),
            "limiter_gr_db_max": round(float(gr.max()), 2), "safety_limiter": safety}
    return y, y_ref, info


def gr_stats(pre_sig, y, gain_db):
    """Short-term (50 ms) gain reduction of the limiter stage, in dB."""
    h = int(0.05 * SR)
    n = min(len(pre_sig), len(y)) // h * h
    a = (pre_sig[:n] * 10 ** (gain_db / 20)).mean(axis=1).reshape(-1, h)
    b = y[:n].mean(axis=1).reshape(-1, h)
    ra, rb = np.sqrt((a ** 2).mean(1)) + 1e-9, np.sqrt((b ** 2).mean(1)) + 1e-9
    gr = 20 * np.log10(ra / rb)
    gr = gr[ra > 10 ** (-40 / 20)]
    return {"median_db": round(float(np.median(gr)), 2), "p90_db": round(float(np.percentile(gr, 90)), 2),
            "p99_db": round(float(np.percentile(gr, 99)), 2), "share_over_3db": round(float((gr > 3).mean()), 3)}


def bands(x):
    m = x.mean(axis=1)
    n = min(len(m), SR * 60)
    F = np.abs(np.fft.rfft(m[:n])) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    tot = F.sum()
    edges = [(20, 100), (100, 300), (300, 1000), (1000, 3000), (3000, 8000), (8000, 16000)]
    return {f"{a}-{b}": round(10 * np.log10(F[(f >= a) & (f < b)].sum() / tot), 1) for a, b in edges}


def main():
    log = {"target_lufs": TARGET_LUFS, "ceiling_dbtp": CEILING, "chain": __doc__.strip().split("\n\n")[1]}
    src, _ = sf.read(os.path.join(V5, "master_src.wav"), dtype="float64", always_2d=True)

    jobs = [("film", "master_v5.wav", "master_v5_mobile.wav", 0.0, "data"),
            ("tiktok", "tiktok_v5_unity.wav", "tiktok_v5_mobile.wav", 123.648, "data-tiktok")]
    for key, fin, fout, off, ddir in jobs:
        proc, _ = sf.read(os.path.join(V5, fin), dtype="float64", always_2d=True)
        i0 = int(round(off * SR))
        orig = src[i0:i0 + len(proc)]
        meas = json.load(open(os.path.join(V5, ddir, "scope", "measured.json")))
        y, yr, info = keyed_master(proc, orig)
        sf.write(os.path.join(V5, fout), y.astype(np.float32), SR, subtype="PCM_24")
        lm = levelmatch_after(y, yr, meas, offset=off)
        phone = lambda z: meter.integrated_lufs(signal.sosfiltfilt(signal.butter(4, 250, "highpass", fs=SR, output="sos"), z, axis=0), SR)
        log[key] = {"in_lufs": round(meter.integrated_lufs(proc, SR), 2), "out_lufs": round(meter.integrated_lufs(y, SR), 2),
                    "in_phone_lufs_hp250": round(phone(proc), 2), "out_phone_lufs_hp250": round(phone(y), 2),
                    "out_tp": round(meter.true_peak(y, SR), 2), "dynamics": info,
                    "bands_in": bands(proc), "bands_out": bands(y), "levelmatch_after_chain": lm}
        L = log[key]
        print(key, L["in_lufs"], "->", L["out_lufs"], "LUFS | phone", L["in_phone_lufs_hp250"], "->", L["out_phone_lufs_hp250"],
              "| TP", L["out_tp"], "|", info, "| worst bar", max(v["worst_bar"] for v in lm.values()),
              "worst demo", max(v["worst_demo"] for v in lm.values()))
    json.dump(log, open(os.path.join(REPO, "audio", "logs", "v5-mobile-master.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
