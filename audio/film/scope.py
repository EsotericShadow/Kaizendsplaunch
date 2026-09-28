#!/usr/bin/env python3
"""Goniometer ("the line") data per cues.json "scope" (treatment 3.1 G7, 8.7).

For each stem as heard in the final mix (after the section edit, level gain,
faders, zone levels, ducking, master gain, limiter gain and fade: the files
<build>/mix/stem_<name>.wav, which sum to the master) and for the mix itself:
  frame f covers samples [800 f, 800 f + 800) at 48 kHz (60 fps)
  M = (L + R) / 2, S = (L - R) / 2
  800 samples -> 400 points by averaging sample pairs
  value = round(clamp(x * gain, -1, 1) * 32767), int16 little-endian,
  interleaved (mid, side) per point: 400 points x 2 values x 2 bytes = 1600 bytes per frame
One fixed film gain: -12 dBFS maps to 0.45, gain = 0.45 / 10^(-12/20) = 1.79135.
Files: <scope_dir>/<stem>.i16 and <scope_dir>/index.json.

Usage: python3 audio/film/scope.py [--film main|vertical]
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from common import SR, Film, jdump, read

STEMS = ["gtr", "pad", "ep", "lead", "pluck", "mix"]
SPF = 800            # samples per frame at 60 fps
PTS = 400
GAIN = 0.45 / 10 ** (-12 / 20)


def encode(x, frames):
    x = np.asarray(x, dtype=np.float64)
    need = frames * SPF
    if len(x) < need:
        x = np.concatenate([x, np.zeros((need - len(x), 2))])
    x = x[:need]
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1])
    m = m.reshape(frames * PTS, 2).mean(axis=1)
    s = s.reshape(frames * PTS, 2).mean(axis=1)
    q = np.empty((frames * PTS, 2))
    q[:, 0] = np.clip(m * GAIN, -1, 1)
    q[:, 1] = np.clip(s * GAIN, -1, 1)
    return np.round(q * 32767).astype("<i2"), m, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    film = Film(a.film)
    cues = film.cues
    sc = cues["scope"]
    frames = int(sc["frames"])
    assert frames * SPF == film.n, (frames, film.n)
    assert int(sc["points_per_frame"]) == PTS
    files, stats = {}, {}
    for st in sc["stems"]:
        src = film.p("mix", "mix.wav") if st == "mix" else film.p("mix", f"stem_{st}.wav")
        x = read(src)
        q, m, s = encode(x, frames)
        out = os.path.join(film.scope_dir, f"{st}.i16")
        q.tofile(out)
        assert os.path.getsize(out) == frames * PTS * 2 * 2
        files[st] = os.path.basename(out)
        clipped = int(np.sum(np.abs(q) >= 32767))
        stats[st] = {"source": src, "bytes": os.path.getsize(out), "clipped_points": clipped,
                     "max_abs_mid": round(float(np.abs(m).max() * GAIN), 4),
                     "max_abs_side": round(float(np.abs(s).max() * GAIN), 4)}
        print(st, stats[st])
    index = {
        "format": "int16 little-endian, interleaved (mid, side) per point",
        "fps": int(cues["fps"]), "sample_rate": SR, "samples_per_frame": SPF, "points_per_frame": PTS,
        "frames": frames, "bytes_per_frame": PTS * 2 * 2, "duration_s": film.duration,
        "frame_f_covers_samples": "[800 f, 800 f + 800)",
        "mid_side": "mid = (L + R) / 2, side = (L - R) / 2; x = side, y = mid, so mono is a vertical line",
        "decimation": "800 samples -> 400 points, mean of each sample pair",
        "gain": round(GAIN, 6), "gain_rule": "-12 dBFS maps to 0.45 (one fixed gain for the whole film)",
        "value": "round(clamp(x * gain, -1, 1) * 32767)", "decode": "x_display = value / 32767",
        "files": files, "stems": list(files.keys()),
        "stem_source": "each stem as heard in the final mix (edit, level gain, faders, ducking, master gain, "
                       "limiter gain and fade applied); 'mix' is the master in float",
        "featured": sc.get("featured"), "stats": stats,
    }
    jdump(os.path.join(film.scope_dir, "index.json"), index)


if __name__ == "__main__":
    main()
