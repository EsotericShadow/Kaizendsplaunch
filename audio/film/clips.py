#!/usr/bin/env python3
"""Product clip audio for shots 19-21 (treatment 5, shots 19-21, and 8.5).

- Fold: public/fold/fold-motion-sound.mp4, clip time 1.00-3.25 at film 62.25-64.50.
- Echolalia: public/film/echolalia/time-sound-preview.mp4, clip time 9.50-11.75 at
  film 64.75-67.00, kept only if a pitch bend of the repeats is measurable in
  that window; otherwise the window slides within 8.00-13.00 (and the picture
  must use the same window, recorded in cues.json).
- Stovetop: public/stovetop/slow-drip-after.wav, 2.5 s from a strong downbeat,
  film 67.00-69.50, 40 ms in, 120 ms out ending at 69.50.

Each excerpt: raised-cosine fades (40 ms; Stovetop out 120 ms), gain so its
BS.1770 loudness over the excerpt is -18 LUFS (a 2.25-2.5 s excerpt is shorter
than the 3 s short-term window, so the whole excerpt is the measurement span).
The clips stay stereo (they are the other products' own audio, not our mono
sources). Chosen windows are written to cues.json (clip_src, clip_in,
clip_out, clip_at, ...) and to audio/logs/clips.json.

Echolalia bend test: spectral peaks of the side signal (the repeats are wide,
the dry riff is centred) are tracked with an 8192-point STFT every 10 ms and
parabolic interpolation; glide segments are 120 ms runs whose fitted slope
exceeds 330 cents/s. The window passes if it holds at least 10 rising glide
segments.

Usage: python3 audio/film/clips.py [--film main]
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from scipy import signal

from common import LOGS, SR, Film, cues_replace_line, jdump, lufs, read, smp, write
from synth import io as sio
from synth.filters import eq

PUBLIC = "/home/user/kaizendsp/public"
SRC = {
    "fold": "fold/fold-motion-sound.mp4",
    "echolalia": "film/echolalia/time-sound-preview.mp4",
    "stovetop": "stovetop/slow-drip-after.wav",
}
TARGET_LUFS = -18.0


def decoded(film, key):
    p = film.p("cache", f"clip_{key}.wav")
    if not os.path.exists(p):
        x, sr = sio.decode(os.path.join(PUBLIC, SRC[key]), sr=SR)
        write(p, x)
    return read(p)


# ----------------------------------------------------------------- Echolalia bend analysis

def peak_tracks(sig, t0, t1, nfft=8192, hop=0.01, fmin=150.0, fmax=2500.0, rel_db=-30.0, link_cents=25.0):
    a = max(0, smp(t0) - nfft // 2)
    b = smp(t1) + nfft // 2
    fr, tt, Z = signal.stft(sig[a:b], SR, nperseg=nfft, noverlap=nfft - smp(hop), boundary=None, padded=False)
    tt = tt + a / SR
    M = 20 * np.log10(np.abs(Z) + 1e-12)
    lo, hi = np.searchsorted(fr, fmin), np.searchsorted(fr, fmax)
    act, done = [], []
    for j in range(M.shape[1]):
        col = M[:, j]
        mx = col[lo:hi].max()
        pk = []
        for i in range(lo + 1, hi - 1):
            if col[i] > col[i - 1] and col[i] >= col[i + 1] and col[i] > mx + rel_db:
                den = col[i - 1] - 2 * col[i] + col[i + 1]
                d = 0.5 * (col[i - 1] - col[i + 1]) / den if den != 0 else 0.0
                pk.append((i + d) * fr[1])
        used, new = set(), []
        for tr in act:
            fl = tr[-1][1]
            best = None
            for k, fq in enumerate(pk):
                if k in used:
                    continue
                c = abs(1200 * np.log2(fq / fl))
                if c < link_cents and (best is None or c < best[0]):
                    best = (c, k)
            if best:
                used.add(best[1])
                tr.append((tt[j], pk[best[1]]))
                new.append(tr)
            else:
                done.append(tr)
        for k, fq in enumerate(pk):
            if k not in used:
                new.append([(tt[j], fq)])
        act = new
    done += act
    return [t for t in done if len(t) >= 12]


def glide_segments(tracks, win=12, min_slope=330.0):
    out = []
    for tr in tracks:
        t = np.array([p[0] for p in tr])
        c = 1200 * np.log2(np.array([p[1] for p in tr]) / tr[0][1])
        for i in range(0, len(t) - win, win // 2):
            sl = float(np.polyfit(t[i:i + win], c[i:i + win], 1)[0])
            if abs(sl) >= min_slope:
                out.append({"t": round(float(t[i]), 3), "f_hz": round(float(tr[i][1]), 1), "cents_per_s": round(sl)})
    return out


def echolalia_window(film, w0=9.50, w1=11.75, span=(8.0, 13.0), need=10):
    x = decoded(film, "echolalia")
    side = 0.5 * (x[:, 0] - x[:, 1])
    segs = glide_segments(peak_tracks(side, span[0] - 0.5, span[1] + 0.5))

    def count(a, b):
        up = [s for s in segs if a <= s["t"] < b and s["cents_per_s"] > 0]
        dn = [s for s in segs if a <= s["t"] < b and s["cents_per_s"] < 0]
        return up, dn

    up, dn = count(w0, w1)
    bins = []
    for a in np.arange(span[0], span[1], 0.25):
        u, d = count(a, a + 0.25)
        bins.append({"t0": round(float(a), 2), "rising": len(u), "falling": len(d)})
    res = {"method": "side-signal spectral peak tracks (8192-point STFT, 10 ms hop, parabolic peaks, 25 cent "
                     "linking); glide = 120 ms run with fitted slope >= 330 cents/s",
           "window_default": [w0, w1], "rising_in_default": len(up), "falling_in_default": len(dn),
           "median_rising_slope_cents_per_s": float(np.median([s["cents_per_s"] for s in up])) if up else None,
           "per_quarter_second": bins}
    if len(up) >= need:
        res["chosen"] = [w0, w1]
        res["slid"] = False
    else:
        best = None
        for a in np.arange(span[0], span[1] - (w1 - w0) + 1e-9, 0.25):
            u, _ = count(a, a + (w1 - w0))
            if best is None or len(u) > best[1]:
                best = (float(a), len(u))
        res["chosen"] = [round(best[0], 2), round(best[0] + (w1 - w0), 2)]
        res["slid"] = True
    return res


# ----------------------------------------------------------------- Stovetop downbeat

def stovetop_downbeat(film, bar_s=3.0, need_s=2.5):
    x = decoded(film, "stovetop")
    m = x.mean(axis=1)
    low = eq(m, [("lowpass", 120, 0, 0.7), ("lowpass", 120, 0, 0.7)], SR)
    k = smp(0.005)
    e = np.sqrt(np.convolve(low ** 2, np.ones(k) / k, mode="same"))
    le = 20 * np.log10(e + 1e-9)
    d = np.concatenate([np.zeros(smp(0.01)), le[smp(0.01):] - le[:-smp(0.01)]])
    cands = []
    t = 0.0
    while t + need_s + 0.1 < len(m) / SR:
        a, b = smp(max(0.0, t - 0.08)), smp(t + 0.08)
        i = a + int(np.argmax(d[a:b]))
        rise = float(d[i])
        pk = float(20 * np.log10(e[i:i + smp(0.1)].max() + 1e-12))
        if i / SR >= 0.04:
            cands.append({"bar_nominal": round(t, 2), "onset_s": round(i / SR, 3), "rise_db": round(rise, 1),
                          "low_peak_dbfs": round(pk, 1), "score": round(rise + pk, 1)})
        t += bar_s
    best = max(cands, key=lambda c: c["score"])
    return {"method": "kick onsets: rise of the 120 Hz low-passed 5 ms RMS envelope over 10 ms, at each nominal "
                      "80 BPM bar line (3.0 s); score = rise dB + low-band peak dBFS",
            "candidates": cands, "chosen_downbeat_s": best["onset_s"]}


# ----------------------------------------------------------------- build

def excerpt(x, c_in, c_out, fade_in, fade_out):
    y = x[smp(c_in):smp(c_in) + smp(c_out - c_in)].copy()
    n = len(y)
    g = np.ones(n)
    fi, fo = smp(fade_in), smp(fade_out)
    g[:fi] = 0.5 - 0.5 * np.cos(np.pi * np.arange(fi) / fi)
    g[n - fo:] = 0.5 + 0.5 * np.cos(np.pi * (np.arange(fo) + 1) / fo)
    return y * g[:, None]


def build(film=None, write_cues=True):
    film = film or Film("main")
    cues = film.cues
    n = film.n
    ech = echolalia_window(film)
    stv = stovetop_downbeat(film)
    d = stv["chosen_downbeat_s"]
    plan = {
        "fold": {"shot": 19, "clip_in": 1.00, "clip_out": 3.25, "clip_at": 62.25, "fade_in": 0.040, "fade_out": 0.040},
        "echolalia": {"shot": 20, "clip_in": ech["chosen"][0], "clip_out": ech["chosen"][1], "clip_at": 64.75,
                      "fade_in": 0.040, "fade_out": 0.040},
        "stovetop": {"shot": 21, "clip_in": round(d - 0.040, 3), "clip_out": round(d - 0.040 + 2.5, 3),
                     "clip_at": 67.00, "fade_in": 0.040, "fade_out": 0.120},
    }
    bus = np.zeros((n, 2))
    info = {}
    for key, p in plan.items():
        x = decoded(film, key)
        y = excerpt(x, p["clip_in"], p["clip_out"], p["fade_in"], p["fade_out"])
        l0 = lufs(y)
        g = TARGET_LUFS - l0
        y = y * 10 ** (g / 20)
        s = smp(p["clip_at"])
        bus[s:s + len(y)] += y[: n - s]
        p.update({"clip_src": f"public/{SRC[key]}", "source_lufs": round(l0, 2), "gain_db": round(g, 2),
                  "lufs_after": round(lufs(y), 2), "film_t0": p["clip_at"],
                  "film_t1": round(p["clip_at"] + (p["clip_out"] - p["clip_in"]), 3)})
        info[key] = p
        write(film.p("edit", f"clip_{key}.wav"), y)
    write(film.p("edit", "clips.wav"), bus)
    log = {"target_lufs": TARGET_LUFS, "loudness_note": "BS.1770 loudness over each whole excerpt (shorter than the "
                                                        "3 s short-term window)",
           "clips": info, "echolalia_bend_check": ech, "stovetop_downbeat": stv}
    jdump(os.path.join(LOGS, "clips.json"), log)
    if write_cues:
        for s in cues["sections"]:
            key = {"fold": "fold", "echolalia": "echolalia", "stovetop": "stovetop"}.get(s["name"])
            if not key:
                continue
            p = info[key]
            s2 = dict(s)
            s2["audio"] = dict(s["audio"])
            s2["audio"]["clip"] = f"{os.path.splitext(os.path.basename(SRC[key]))[0]} {p['clip_in']:.2f}-{p['clip_out']:.2f}"
            s2["clip_src"] = p["clip_src"]
            s2["clip_in"] = p["clip_in"]
            s2["clip_out"] = p["clip_out"]
            s2["clip_at"] = p["clip_at"]
            s2["clip_fades_s"] = [p["fade_in"], p["fade_out"]]
            s2["clip_gain_db"] = p["gain_db"]
            s2["clip_lufs"] = TARGET_LUFS
            cues_replace_line(film.cues_path, rf'^\s*\{{"t0":\s*{s["t0"]:.2f},\s*"t1":\s*{s["t1"]:.2f},\s*"shot":\s*{s["shot"]},', s2)
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    lg = build(Film(a.film))
    for k, v in lg["clips"].items():
        print(k, {kk: v[kk] for kk in ("clip_in", "clip_out", "clip_at", "source_lufs", "gain_db", "lufs_after")})
    e = lg["echolalia_bend_check"]
    print("echolalia: rising", e["rising_in_default"], "falling", e["falling_in_default"], "chosen", e["chosen"],
          "slid" if e["slid"] else "kept")
    print("stovetop downbeat", lg["stovetop_downbeat"]["chosen_downbeat_s"])
