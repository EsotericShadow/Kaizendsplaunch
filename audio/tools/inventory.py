#!/usr/bin/env python3
"""Measure every audio clip on the Kaizen DSP website and write a JSON report
plus a spectrogram PNG per clip.

Usage:
    python3 audio/tools/inventory.py [--site /home/user/kaizendsp/public] [--out /home/user/build/audio-inventory]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from synth import io, meter, viz  # noqa: E402

CLIPS = [
    "fold/neutral.m4a", "fold/narrow-lows.m4a", "fold/wide-lows.m4a", "fold/fold-motion-sound.mp4",
    "stovetop/slow-drip-dry.wav", "stovetop/slow-drip-before.wav", "stovetop/slow-drip-after.wav",
    "stovetop/classic-bangers-wide.mp4", "stovetop/classic-bangers-mobile.mp4",
    "stovetop/classic-bangers-mobile-loop.mp4", "film/echolalia/time-sound-preview.mp4",
]
SILENT_VIDEOS = ["fold/fold-motion.mp4", "film/echolalia/phosphor-light-study.mp4",
                 "film/choroboros-desktop.mp4", "film/choroboros-mobile.mp4"]

# Chapter marks from app/gifts/echolalia/InstrumentPreview.tsx
ECHOLALIA_CHAPTERS = [(0, 4, "Steady"), (4, 9, "Bend down"), (9, 14, "Bend up"),
                      (14, 22, "Tempo sync"), (22, 38, "Evolution"), (38, 44.1, "The tail")]


def per_second(x, sr):
    """RMS dBFS, side/mid dB and spectral centroid for each whole second."""
    rows = []
    n = sr
    for i in range(0, len(x) - n // 2, n):
        seg = x[i:i + n]
        m, s = 0.5 * (seg[:, 0] + seg[:, 1]), 0.5 * (seg[:, 0] - seg[:, 1])
        rms = 10 * np.log10(max(np.mean(seg ** 2), 1e-20))
        sm = 10 * np.log10(max(np.mean(s ** 2), 1e-20) / max(np.mean(m ** 2), 1e-20))
        spec = np.abs(np.fft.rfft(m * np.hanning(len(m))))
        f = np.fft.rfftfreq(len(m), 1 / sr)
        cen = float((f * spec ** 2).sum() / max((spec ** 2).sum(), 1e-20))
        rows.append({"t": i // sr, "rms_dbfs": round(float(rms), 1), "side_mid_db": round(float(sm), 1),
                     "centroid_hz": round(cen)})
    return rows


def segment_stats(x, sr, t0, t1):
    seg = x[int(t0 * sr):int(t1 * sr)]
    return {"from_s": t0, "to_s": t1, "lufs": round(meter.integrated_lufs(seg, sr), 1),
            "rms_dbfs": round(meter.rms_db(seg), 1),
            "stereo": meter._round(meter.stereo_stats(seg, sr)),
            "centroid_hz": round(meter.spectral_centroid(seg, sr))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="/home/user/kaizendsp/public")
    ap.add_argument("--out", default="/home/user/build/audio-inventory")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    results = {}
    decoded = {}
    for rel in CLIPS:
        path = os.path.join(a.site, rel)
        x, sr = io.decode(path)
        decoded[rel] = (x, sr)
        rep = meter.report(x, sr)
        rep["ffmpeg"] = io.ffmpeg_loudness(path)
        rep["onsets_s"] = [round(t, 2) for t in meter.onset_times(x, sr, threshold=0.35)]
        rep["per_second"] = per_second(x, sr)
        rep["correlation_per_second"] = [round(c, 2) for c in meter.correlation_curve(x, sr)]
        png = os.path.join(a.out, rel.replace("/", "__") + ".png")
        marks = [(c[0], c[2]) for c in ECHOLALIA_CHAPTERS] if "echolalia" in rel else None
        viz.spectrogram_png(x, png, sr, title=rel, markers=marks)
        rep["spectrogram_png"] = png
        results[rel] = rep
        print(f"{rel}: {rep['duration_s']} s, {rep['integrated_lufs']} LUFS, TP {rep['true_peak_dbtp']} dBTP, "
              f"tempo {rep['tempo']['bpm']} ({rep['tempo']['confidence']}), key {rep['key']['key']} "
              f"({rep['key']['correlation']}), corr {rep['stereo']['correlation']}")

    extra = {}
    # Echolalia chapters
    x, sr = decoded["film/echolalia/time-sound-preview.mp4"]
    extra["echolalia_chapters"] = [dict(label=c[2], **segment_stats(x, sr, c[0], c[1])) for c in ECHOLALIA_CHAPTERS]
    # Classic Bangers HEAT ramp in 4 s slices
    x, sr = decoded["stovetop/classic-bangers-wide.mp4"]
    extra["classic_bangers_wide_slices"] = [segment_stats(x, sr, t, t + 4) for t in range(0, 24, 4)]
    # Fold comparison, per band
    extra["fold_comparison"] = {k: meter._round(meter.stereo_stats(*decoded[k])) for k in
                                ("fold/neutral.m4a", "fold/narrow-lows.m4a", "fold/wide-lows.m4a")}
    # Slow Drip: are they level matched, how different are they
    d, sr = decoded["stovetop/slow-drip-dry.wav"]
    b, _ = decoded["stovetop/slow-drip-before.wav"]
    f, _ = decoded["stovetop/slow-drip-after.wav"]
    n = min(len(d), len(b), len(f))
    extra["slow_drip_differences_db"] = {
        "before_minus_dry_residual_rel_dry": round(meter.rms_db(b[:n] - d[:n]) - meter.rms_db(d[:n]), 1),
        "after_minus_dry_residual_rel_dry": round(meter.rms_db(f[:n] - d[:n]) - meter.rms_db(d[:n]), 1),
        "after_minus_before_residual_rel_dry": round(meter.rms_db(f[:n] - b[:n]) - meter.rms_db(d[:n]), 1),
    }
    # Are the two vertical cuts the same audio?
    m1, sr = decoded["stovetop/classic-bangers-mobile.mp4"]
    m2, _ = decoded["stovetop/classic-bangers-mobile-loop.mp4"]
    n = min(len(m1), len(m2))
    extra["mobile_vs_mobile_loop_residual_db"] = round(meter.rms_db(m1[:n] - m2[:n]) - meter.rms_db(m1[:n]), 1)
    # first 15 s of widescreen vs mobile
    w, _ = decoded["stovetop/classic-bangers-wide.mp4"]
    extra["wide_first15_vs_mobile_residual_db"] = round(meter.rms_db(w[:n] - m1[:n]) - meter.rms_db(m1[:n]), 1)
    # Fold motion clip loops? compare first and last 0.25 s levels
    x, sr = decoded["fold/fold-motion-sound.mp4"]
    extra["fold_motion_edges_rms_dbfs"] = [round(meter.rms_db(x[: sr // 4]), 1), round(meter.rms_db(x[-sr // 4:]), 1)]

    results["_comparisons"] = extra
    results["_silent_videos"] = {v: io.has_audio(os.path.join(a.site, v)) for v in SILENT_VIDEOS}
    with open(os.path.join(a.out, "inventory.json"), "w") as fh:
        json.dump(results, fh, indent=1)
    print(json.dumps(extra, indent=1))
    print("silent videos (has_audio):", results["_silent_videos"])


if __name__ == "__main__":
    main()
