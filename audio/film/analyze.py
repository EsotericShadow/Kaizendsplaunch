#!/usr/bin/env python3
"""Spectrogram PNGs and objective numbers for stems, renders and mixes.

python3 audio/film/analyze.py stems [--film main|vertical] [--names gtr,pad]
python3 audio/film/analyze.py file PATH [--t0 16 --t1 36] [--title ...]

PNGs go to <build>/png/, a JSON summary to <build>/png/analysis.json. Numbers:
integrated loudness, true peak, crest factor (sample peak to RMS), octave-band
balance (dB relative to total power) and its tilt from 125 Hz to 8 kHz, L/R
correlation.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from common import SR, Film, correlation, dual, jdump, read, smp, stats
from synth import viz

MARKERS_MAIN = [(7.85, "stop"), (8.0, "impact"), (16, "Green"), (20, "Blue"), (24, "Red"), (28, "Purple"),
                (32, "Black"), (36, "cores"), (40, "Create"), (46, "looks"), (50, "free"), (54, "trial"),
                (58, "price"), (62, "Fold"), (64.5, "Echolalia"), (67, "Stovetop"), (70, "payoff"),
                (78, "chord"), (82, "note")]


def png(x, path, title="", t0=0.0, t1=None, markers=None, fmax=16000.0):
    x = np.asarray(x, dtype=np.float64)
    a, b = smp(t0), smp(t1) if t1 is not None else len(x)
    seg = x[a:b]
    mk = [(t - t0, lab) for (t, lab) in (markers or []) if t0 <= t < (t1 if t1 is not None else 1e9)]
    viz.spectrogram_png(seg, path, SR, title=title, markers=mk, fmax=fmax)
    return path


def summary(x, t0=0.0, t1=None):
    a, b = smp(t0), smp(t1) if t1 is not None else len(x)
    seg = np.asarray(x)[a:b]
    out = stats(seg)
    out["correlation"] = round(correlation(seg), 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["stems", "file"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--film", default="main")
    ap.add_argument("--names", default="")
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--title", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    film = Film(a.film)
    res = {}
    if a.what == "stems":
        names = [x for x in a.names.split(",") if x] or ["gtr", "pad", "ep", "lead", "pluck", "bells", "bass",
                                                         "drums", "fx"]
        for nm in names:
            x = read(film.stem_path(nm))
            p = png(x, film.p("png", f"stem_{nm}.png"), f"stem {nm}", a.t0, a.t1,
                    MARKERS_MAIN if a.film == "main" else None)
            res[nm] = summary(x, a.t0, a.t1)
            print(nm, json.dumps(res[nm]))
            print("  ", p)
        prev = {}
        pj = film.p("png", "analysis.json")
        if os.path.exists(pj):
            prev = json.load(open(pj))
        prev.update({f"stem_{k}": v for k, v in res.items()})
        jdump(pj, prev)
    else:
        x = read(a.path)
        out = a.out or film.p("png", os.path.splitext(os.path.basename(a.path))[0] + ".png")
        png(x, out, a.title or os.path.basename(a.path), a.t0, a.t1, MARKERS_MAIN if a.film == "main" else None)
        print(json.dumps(summary(x, a.t0, a.t1)))
        print(out)


if __name__ == "__main__":
    main()
