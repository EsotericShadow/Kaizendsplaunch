"""Shared paths, timing helpers and small signal utilities for the "Still Life"
soundtrack build (main film and vertical cutdown).

Conventions
- 48 kHz, mono sources are 1-D float64, stereo is (n, 2).
- Film time in seconds. Bar n (1-based) starts at 2 (n - 1) s at 120 BPM.
- Heavy outputs go to /home/user/build/film/ (never committed). Code and the
  small JSON logs live in the repo.
- The Choroboros renderer is referenced by path only; nothing proprietary is
  copied into the repo.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "audio"))

from synth import io as sio  # noqa: E402
from synth import meter  # noqa: E402

SR = 48000
BPM = 120.0
BEAT = 0.5
BAR = 2.0
CHORO = os.environ.get("CHORO_RENDER", "/home/user/build/choro-render/build/choro-render")
BUILD = os.environ.get("FILM_BUILD", "/home/user/build/film")
LOGS = os.path.join(REPO, "audio", "logs")


class Film:
    """Paths and length for one cut (main or vertical)."""

    def __init__(self, name="main"):
        self.name = name
        if name == "main":
            self.cues_path = os.path.join(REPO, "film", "cues.json")
            self.out = os.path.join(BUILD, "audio")
            self.scope_dir = os.path.join(BUILD, "data", "scope")
            self.log_suffix = ""
        elif name == "vertical":
            self.cues_path = os.path.join(REPO, "film", "cues-vertical.json")
            self.out = os.path.join(BUILD, "audio", "vertical")
            self.scope_dir = os.path.join(BUILD, "data", "scope-vertical")
            self.log_suffix = "-vertical"
        else:
            raise ValueError(name)
        for sub in ("stems", "renders", "auto", "edit", "mix", "png", "cache"):
            os.makedirs(os.path.join(self.out, sub), exist_ok=True)
        os.makedirs(self.scope_dir, exist_ok=True)
        os.makedirs(os.path.join(LOGS, "render-meta"), exist_ok=True)

    @property
    def cues(self):
        with open(self.cues_path) as f:
            return json.load(f)

    @property
    def duration(self):
        return float(self.cues["duration"])

    @property
    def n(self):
        return int(round(self.duration * SR))

    def p(self, *parts):
        return os.path.join(self.out, *parts)

    def stem_path(self, name):
        return self.p("stems", f"{name}.wav")

    def render_path(self, rid):
        return self.p("renders", f"{rid}.wav")

    def log_path(self, base):
        root, ext = os.path.splitext(base)
        return os.path.join(LOGS, f"{root}{self.log_suffix}{ext}")


# ----------------------------------------------------------------- time

def bar_t(n):
    """Start time (s) of 1-based bar n."""
    return BAR * (n - 1)


def smp(t):
    return int(round(t * SR))


# ----------------------------------------------------------------- io

def read(path):
    x, sr = sio.read_wav(path)
    assert sr == SR, (path, sr)
    return x


def write(path, x, subtype="FLOAT"):
    return sio.write_wav(path, x, SR, subtype=subtype)


def fit(x, n):
    """Zero-pad or trim along axis 0."""
    if len(x) >= n:
        return x[:n]
    pad = [(0, n - len(x))] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad)


def dual(x):
    x = np.asarray(x, dtype=np.float64)
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


# ----------------------------------------------------------------- gains, fades

def db(x):
    return 10 ** (np.asarray(x, dtype=np.float64) / 20.0)


def todb(a, floor=-200.0):
    return 20 * np.log10(np.maximum(np.abs(a), 10 ** (floor / 20)))


def hard_silence(x, t0, t1, fade_s=0.003):
    """Digital silence from t0 to t1 with a short raised-cosine fade to zero
    ending at t0 (no click), and a hard start of the next material at t1."""
    x = np.array(x, dtype=np.float64, copy=True)
    a, b = smp(t0), smp(t1)
    nf = max(1, smp(fade_s))
    g = 0.5 + 0.5 * np.cos(np.pi * (np.arange(nf) + 1) / nf)   # 1 -> 0, last sample 0
    lo = max(0, a - nf)
    seg = x[lo:a]
    gg = g[nf - len(seg):]
    x[lo:a] = seg * (gg[:, None] if x.ndim == 2 else gg)
    x[a:b] = 0.0
    return x


def ramp_curve(n_total, points, kind="linear"):
    """Piecewise gain curve in dB from [(t, db), ...] (film seconds); holds the
    first and last values. Linear interpolation between points."""
    t = np.arange(n_total) / SR
    ts = np.array([p[0] for p in points], dtype=float)
    vs = np.array([p[1] for p in points], dtype=float)
    return np.interp(t, ts, vs)


def sine_inout(u):
    u = np.clip(u, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * u)


def equal_power_xfade(a, b, t_end, dur=0.020):
    """Cross-fade from a to b over [t_end - dur, t_end]: equal power (cos/sin),
    b alone from t_end on, a alone before. Arrays must match in shape."""
    n = len(a)
    e = smp(t_end)
    s = max(0, e - smp(dur))
    ga = np.ones(n)
    gb = np.zeros(n)
    k = e - s
    if k > 0:
        u = (np.arange(k) + 1) / k
        ga[s:e] = np.cos(0.5 * np.pi * u)
        gb[s:e] = np.sin(0.5 * np.pi * u)
    ga[e:] = 0.0
    gb[e:] = 1.0
    if a.ndim == 2:
        return a * ga[:, None] + b * gb[:, None]
    return a * ga + b * gb


def section_edit(renders_by_section, n, fade=0.020):
    """Build one continuous track from per-section sources.

    renders_by_section: list of (t0, t1, array or None) in time order covering
    the film. Each join is a 20 ms equal-power cross-fade that ends exactly on
    the section boundary. A None source is silence. All arrays are full-film
    length and time-aligned, so the outgoing and incoming sources are both
    already running across the join."""
    shape = ()
    for _, _, arr in renders_by_section:
        if arr is not None:
            shape = arr.shape[1:]
            break
    out = np.zeros((n,) + tuple(shape))
    kf = smp(fade)
    last = len(renders_by_section) - 1
    for i, (t0, t1, arr) in enumerate(renders_by_section):
        if arr is None:
            continue
        s0, s1 = smp(t0), smp(t1)
        g = np.zeros(n)
        g[s0:s1] = 1.0
        if i == 0:
            g[:s0] = 1.0
        if i == last:
            g[s1:] = 1.0
        if i > 0:        # fade in over the 20 ms that end on t0
            a = max(0, s0 - kf)
            u = (np.arange(s0 - a) + 1) / max(1, s0 - a)
            g[a:s0] = np.sin(0.5 * np.pi * u)
        if i < last:     # fade out over the 20 ms that end on t1
            a = max(s0, s1 - kf)
            u = (np.arange(s1 - a) + 1) / max(1, s1 - a)
            g[a:s1] = np.cos(0.5 * np.pi * u)
        a = fit(arr, n)
        out += a * (g[:, None] if a.ndim == 2 else g)
    return out


# ----------------------------------------------------------------- measurement helpers

def lufs(x):
    return meter.integrated_lufs(dual(x) if np.ndim(x) == 1 else x, SR)


def lufs_span(x, t0, t1):
    return lufs(x[smp(t0):smp(t1)])


def correlation(x):
    x = dual(x)
    l, r = x[:, 0], x[:, 1]
    d = math.sqrt(max(float(np.dot(l, l)) * float(np.dot(r, r)), 1e-30))
    return float(np.dot(l, r) / d) if d > 1e-15 else 1.0


def stats(x):
    x = np.asarray(x, dtype=np.float64)
    st = dual(x)
    out = {
        "integrated_lufs": round(lufs(st), 2),
        "true_peak_dbtp": round(meter.true_peak(st, SR), 2),
        "sample_peak_dbfs": round(meter.sample_peak(st), 2),
        "crest_db": round(meter.crest_factor_db(st, SR)["sample_peak_to_rms_db"], 2),
        "octave_bands_db_rel": {str(k): round(v, 1) for k, v in meter.octave_bands(st, SR).items()},
    }
    out["tilt_db_per_oct_125_8k"] = round(meter.spectral_tilt_db_per_oct(
        {float(k): v for k, v in out["octave_bands_db_rel"].items()}), 2)
    return out


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=_json_default)
        f.write("\n")


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


# ----------------------------------------------------------------- cues.json line editing

def cues_replace_line(path, key_regex, new_obj, indent="    ", trailing_comma=None):
    """Replace one single-line JSON object in a cues file, keeping the rest of
    the hand formatting. key_regex must match exactly one line. If the line is a
    '"KEY": {...}' entry the key is kept."""
    with open(path) as f:
        lines = f.read().split("\n")
    hits = [i for i, ln in enumerate(lines) if re.search(key_regex, ln)]
    if len(hits) != 1:
        raise RuntimeError(f"{key_regex!r} matched {len(hits)} lines in {path}")
    i = hits[0]
    ln = lines[i]
    comma = ln.rstrip().endswith(",") if trailing_comma is None else trailing_comma
    m = re.match(r'^(\s*)("[^"]+":\s*)?\{', ln)
    lead = m.group(1) if m else indent
    keypart = m.group(2) or "" if m else ""
    lines[i] = f"{lead}{keypart}{json.dumps(new_obj, ensure_ascii=False)}{',' if comma else ''}"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    # validate
    with open(path) as f:
        json.load(f)
