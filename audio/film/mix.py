#!/usr/bin/env python3
"""Mix and master "Still Life" (treatment 8.5, 7.8, 11 item 10).

Signal flow (no reverb, no delay, no stereo tools anywhere):
  processed parts: render (Choroboros) -> section edit (edit.py, 20 ms
      equal-power joins ending on the downbeat) -> level-match gain
      (levelmatch.py) -> fader
  dry parts (bells, bass, drums, fx) and product clips: dual mono / as is -> fader
  bed ducking under the product clips: gain only, after Choroboros
  sum -> master gain to -14 LUFS integrated -> true-peak limiter at -1.0 dBTP
  (at most 1 dB gain reduction) -> master fade 84.50-86.00 -> hard silences
Outputs (<build>/): mix/stem_<name>.wav (as heard: fader, ducking, master gain
and the limiter's gain, so the stems sum to the master), mix/mix.wav (48 kHz
float), master.wav (48 kHz 24-bit), mix/mix_info.json.

Usage: python3 audio/film/mix.py [--film main]
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

import edit
from common import SR, Film, db, dual, hard_silence, jdump, lufs, read, sine_inout, smp, write
from synth import meter
from synth.effects import _forward_min, _release

# ----------------------------------------------------------------- fader plan (dB), main film
# (t0, t1, dB): the value holds from t0; changes ramp over the 20 ms ending at t0.

FADERS = {
    # level-matched guitar edit (0 dB = dry take loudness, about -23.2 LUFS dual mono)
    "gtr": [(0.0, 3.2), (8.0, 4.0), (16.0, 5.5), (36.0, 5.5), (42.0, 2.0), (50.0, 5.2), (54.0, 5.2), (58.0, 5.7),
            (62.0, 5.7), (70.0, 3.2)],
    # pad: 0 dB = its offer-peak level; breakdown -4, bed -12, end card -18 (treatment 7.5, 7.6)
    "pad": [(0.0, 0.0), (36.0, -1.0), (50.0, 3.5), (54.0, 3.5), (58.0, 4.0), (62.0, -9.0), (70.0, -9.0),
            (74.0, -15.0), (78.0, -6.0)],
    "ep": [(0.0, 0.5)],
    "lead": [(0.0, 10.0)],
    "pluck": [(0.0, 0.0)],
    "bells": [(0.0, 0.0)],
    "bass": [(0.0, 0.0), (8.0, -3.0), (36.0, -5.0), (48.0, -4.0), (50.0, -2.5), (62.0, -7.0), (74.0, -8.0)],
    "drums": [(0.0, 0.0), (8.0, 1.0), (36.0, -3.0), (48.0, 0.0), (50.0, 2.0), (58.0, 1.0), (62.0, -2.0),
              (74.0, -4.0)],
    "fx": [(0.0, 0.0)],
    "clips": [(0.0, 0.0)],
}
DUCKED = ("pad", "bass", "drums")          # the bed under the product clips
DUCK_DB = -6.0
PROCESSED = ("gtr", "pad", "ep", "lead", "pluck")
DRY = ("bells", "bass", "drums", "fx")
MASTER_LUFS, CEILING, MAX_GR = -14.4, -1.1, 1.0      # -14 LUFS +-0.5 and -1.0 dBTP (QC gates); aimed 0.4 LU under
                                                     # and 0.1 dB under so 24-bit rounding and meters agree
# Headroom zones: if a zone's pre-limiter true peak would need more than
# GR_BUDGET dB of limiting, the whole zone (every stem) is trimmed by the
# excess, constant over the zone (a bus fader move at bar lines; the tour is
# one zone so every pass stays identical, bars 1-4 are one zone so the dry vs
# processed comparison holds).
ZONES = [(0.0, 8.0), (8.0, 16.0), (16.0, 36.0), (36.0, 46.0), (46.0, 50.0), (50.0, 54.0), (54.0, 58.0),
         (58.0, 62.0), (62.0, 70.0), (70.0, 78.0), (78.0, 86.0)]
GR_BUDGET = 0.85
# Designed bus level per zone (dB, all stems): shapes the arc (7.8) on top of the
# per-stem faders. The absolute-level stems (clips at -18 LUFS, bells at -24
# dBFS, FX risers in dBFS) are compensated for the master gain so they land at
# their specified level in the master.
ZONE_LEVEL = {(0.0, 8.0): -1.7, (8.0, 16.0): -1.5, (16.0, 36.0): -1.7, (46.0, 50.0): -1.5, (50.0, 54.0): -1.8,
              (54.0, 58.0): -1.2,
              (70.0, 78.0): -1.2, (78.0, 86.0): -0.6}
ABSOLUTE = ("fx", "bells", "clips")
FADE = (84.50, 86.00)

# ----------------------------------------------------------------- vertical cutdown plan (treatment 9)
PLANS = {
    "main": {"faders": FADERS, "zones": ZONES, "zone_level": ZONE_LEVEL, "fade": FADE},
    "vertical": {
        "faders": {
            # guitar constant over the engine blocks (0-14) so every block keeps the dry take's loudness
            "gtr": [(0.0, 3.2), (14.0, 5.2), (20.0, 5.7), (22.0, 3.6)],
            "pad": [(0.0, 0.0), (14.0, 3.5), (17.0, 3.5), (20.0, 4.0), (22.0, -6.0)],
            "ep": [(0.0, 0.5)],
            "lead": [(0.0, 10.0)],
            "pluck": [(0.0, 0.0)],
            "bells": [(0.0, 0.0)],
            "bass": [(0.0, -3.0), (14.0, -2.5), (22.0, -7.0)],
            "drums": [(0.0, 1.0), (14.0, 2.0), (20.0, 1.0), (22.0, -4.0)],
            "fx": [(0.0, 0.0)],
        },
        "zones": [(0.0, 14.0), (14.0, 17.0), (17.0, 20.0), (20.0, 22.0), (22.0, 24.0), (24.0, 28.0)],
        "zone_level": {(0.0, 14.0): -1.7, (14.0, 17.0): -1.6, (17.0, 20.0): -1.2, (22.0, 24.0): -1.2,
                       (24.0, 28.0): -0.6},
        "fade": (27.00, 28.00),
    },
}


def use_plan(name):
    global FADERS, ZONES, ZONE_LEVEL, FADE
    p = PLANS[name]
    FADERS, ZONES, ZONE_LEVEL, FADE = p["faders"], p["zones"], p["zone_level"], p["fade"]


def fader_curve(n, plan, ramp=0.020):
    g = np.zeros(n)
    for i, (t0, v) in enumerate(plan):
        g[smp(t0):] = v
    k = smp(ramp)
    u = (np.arange(k) + 1) / k
    for i in range(1, len(plan)):
        s = smp(plan[i][0])
        g0, g1 = plan[i - 1][1], plan[i][1]
        if g0 != g1 and s - k >= 0:
            g[s - k:s] = g0 + (g1 - g0) * sine_inout(u)
    return g


def duck_curve(n, spans, depth_db=DUCK_DB, attack=0.040, release=0.150):
    """-depth under each clip span: ramps down over the clip's own 40 ms fade-in
    and recovers over 150 ms after it ends (sidechain-style, gain only)."""
    env = np.zeros(n)
    t = np.arange(n) / SR
    for (a, b) in spans:
        on = np.clip((t - a) / attack, 0, 1)
        off = np.clip(1 - (t - b) / release, 0, 1)
        e = np.where(t < b, on, off)
        e[t < a] = 0
        env = np.maximum(env, sine_inout(e))
    return env * depth_db


def tp_limiter(x, ceiling_dbtp=CEILING, lookahead_ms=5.0, release_ms=80.0, max_passes=6):
    """synth.effects.limiter, returning its gain curve too (stereo-linked)."""
    L = max(1, int(lookahead_ms * SR / 1000))
    rel = math.exp(-1 / (release_ms * SR / 1000))
    target = 10 ** (ceiling_dbtp / 20)
    pk = meter.true_peak_envelope(x, SR)
    g = np.ones(len(x))
    for p in range(max_passes):
        req = np.minimum(1.0, target / np.maximum(pk, 1e-12))
        h = _release(_forward_min(req, L), rel)
        g = np.convolve(np.concatenate([np.full(L - 1, h[0]), h]), np.ones(L) / L, mode="valid")
        y = x * g[:, None]
        tp = meter.true_peak(y, SR)
        if tp <= ceiling_dbtp + 0.005:
            break
        target *= 10 ** ((ceiling_dbtp - tp - 0.02) / 20)
    return y, g, {"passes": p + 1, "true_peak_dbtp": round(tp, 3),
                  "max_gain_reduction_db": round(float(-20 * np.log10(g.min())), 3),
                  "samples_limited": int(np.sum(g < 0.9999))}


def short_term_at(x, t):
    """Short-term loudness (3 s window ending at t)."""
    a = max(0, smp(t - 3.0))
    return lufs(x[a:smp(t)])


def build_stems(film, cues, faders=None):
    faders = faders or FADERS
    n = film.n
    stems = {}
    gain_gtr = np.load(film.p("edit", "gain_gtr.npy"))
    gain_pad = np.zeros(n)
    pm = film.p("edit", "gain_pad_matched.npy")
    if os.path.exists(pm):
        c = np.load(pm)
        m = ~np.isnan(c)
        gain_pad[m] = c[m]
    for s in PROCESSED:
        y = edit.edited(film, s, cues)
        lg = gain_gtr if s == "gtr" else gain_pad if s == "pad" else 0.0
        stems[s] = y * db(lg + fader_curve(n, faders[s]))[:, None]
    for s in DRY:
        stems[s] = dual(read(film.stem_path(s))) * db(fader_curve(n, faders[s]))[:, None]
    clips_p = film.p("edit", "clips.wav")
    if os.path.exists(clips_p) and "clips" in faders:
        stems["clips"] = read(clips_p)[:n] * db(fader_curve(n, faders["clips"]))[:, None]
        spans = []
        for sec in cues["sections"]:
            if "clip_at" in sec:
                spans.append((sec["clip_at"], sec["clip_at"] + sec["clip_out"] - sec["clip_in"]))
        dk = db(duck_curve(n, spans))
        for s in DUCKED:
            stems[s] = stems[s] * dk[:, None]
    return stems


def master_gain_for(stems, tcurve, lufs_target, iters=4):
    """Master gain meeting the loudness target when the ABSOLUTE stems are
    pre-compensated by the same gain (they must not move)."""
    n = len(tcurve)
    design = db(-trim_curve(n, {z: ZONE_LEVEL.get(z, 0.0) for z in ZONES}))
    rel = sum(v for k, v in stems.items() if k not in ABSOLUTE) * db(tcurve)[:, None]
    ab = sum((v for k, v in stems.items() if k in ABSOLUTE), np.zeros_like(rel)) * (db(tcurve) * design)[:, None]
    g = lufs_target - lufs(rel + ab)
    for _ in range(iters):
        g = g + (lufs_target - lufs((rel + ab * db(-g)) * db(g)))
    return g, (rel + ab * db(-g))


def zone_trims(film, stems, lufs_target=MASTER_LUFS, zones=None, budget=GR_BUDGET, iters=8):
    """Per-zone trims (dB, <= 0) so no zone needs more than `budget` dB of
    true-peak limiting at the master gain that meets the loudness target."""
    n = film.n
    zones = zones or ZONES
    trims = {z: ZONE_LEVEL.get(z, 0.0) for z in zones}
    ceil_pre = CEILING + budget
    for it in range(iters):
        tc = trim_curve(n, trims)
        g, x = master_gain_for(stems, tc, lufs_target)
        env = meter.true_peak_envelope(x * db(g), SR)
        changed = False
        for z in zones:
            a, b = smp(z[0]), smp(z[1])
            pk = 20 * np.log10(max(env[a:b].max(), 1e-12))
            over = pk - ceil_pre
            if over > 0.02:
                trims[z] -= over + 0.05
                changed = True
        if not changed:
            break
    return trims


def trim_curve(n, trims, ramp=0.020):
    zs = sorted(trims)
    plan = [(z[0], trims[z]) for z in zs]
    return fader_curve(n, plan, ramp)


def master(film, stems, silences, fade=None, lufs_target=MASTER_LUFS):
    fade = fade or FADE
    n = film.n
    trims = zone_trims(film, stems, lufs_target)
    tcurve = trim_curve(n, trims)
    g_master, _ = master_gain_for(stems, tcurve, lufs_target)
    tc = db(tcurve)
    design = db(-trim_curve(n, {z: ZONE_LEVEL.get(z, 0.0) for z in ZONES}))     # absolute stems ignore the design
    stems = {k: v * tc[:, None] * ((db(-g_master) * design)[:, None] if k in ABSOLUTE else 1.0)
             for k, v in stems.items()}
    pre = sum(stems.values())
    info = {"zone_levels_db": {f"{a:g}-{b:g}": round(v, 2) for (a, b), v in trims.items()},
            "zone_levels_design_db": {f"{a:g}-{b:g}": v for (a, b), v in ZONE_LEVEL.items()},
            "absolute_stems_compensated_db": round(-g_master, 3)}
    for it in range(4):
        x = pre * db(g_master)
        y, g_lim, linfo = tp_limiter(x)
        fcurve = np.ones(n)
        if fade:
            a, b = smp(fade[0]), smp(fade[1])
            fcurve[a:b] = 0.5 + 0.5 * np.cos(np.pi * np.arange(b - a) / (b - a))
            fcurve[b:] = 0.0
        y = y * fcurve[:, None]
        for (s0, s1) in silences:
            y = hard_silence(y, s0, s1)
        L = lufs(y)
        if abs(L - lufs_target) < 0.02:
            break
        g_master += lufs_target - L
        pre = pre   # the ABSOLUTE stems keep their first compensation (differences < 0.05 dB)
    info.update(master_gain_db=round(g_master, 3), limiter=linfo, integrated_lufs=round(L, 3))
    total = db(g_master) * g_lim * fcurve
    out = {k: v * total[:, None] for k, v in stems.items()}
    for k in out:
        for (s0, s1) in silences:
            out[k] = hard_silence(out[k], s0, s1)
    return y, out, info


def report(y, stems, cues, film):
    rep = {}
    rep["integrated_lufs"] = round(lufs(y), 3)
    rep["true_peak_dbtp"] = round(meter.true_peak(y, SR), 3)
    rep["sample_peak_dbfs"] = round(meter.sample_peak(y), 3)
    rep["clipped_runs"] = meter.clipped_samples(y)
    rep["non_finite"] = int(np.sum(~np.isfinite(y)))
    rep["loudness_range_lu"] = round(meter.loudness_range(y, SR), 2)
    mono = 0.5 * (y[:, 0] + y[:, 1])
    rep["mono_fold"] = {"integrated_lufs_mono_as_dual": round(lufs(np.stack([mono, mono], 1)), 3)}
    rep["mono_fold"]["drop_lu"] = round(rep["integrated_lufs"] - rep["mono_fold"]["integrated_lufs_mono_as_dual"], 3)
    rep["octave_bands_db_rel"] = {str(k): round(v, 1) for k, v in meter.octave_bands(y, SR).items()}
    rep["tilt_db_per_oct_125_8k"] = round(meter.spectral_tilt_db_per_oct(meter.octave_bands(y, SR)), 2)
    rep["crest_db"] = round(meter.crest_factor_db(y, SR)["sample_peak_to_rms_db"], 2)
    secs = []
    for s in cues["sections"]:
        t0, t1 = float(s["t0"]), float(s["t1"])
        if t1 - t0 < 1.0:
            continue
        row = {"shot": s["shot"], "name": s["name"], "t0": t0, "t1": t1,
               "lufs": round(lufs(y[smp(t0):smp(t1)]), 2),
               "short_term_at_end": round(short_term_at(y, t1), 2) if t1 >= 3 else None,
               "mono_drop_lu": None}
        seg = y[smp(t0):smp(t1)]
        m = 0.5 * (seg[:, 0] + seg[:, 1])
        row["mono_drop_lu"] = round(lufs(seg) - lufs(np.stack([m, m], 1)), 2)
        row["stems"] = {k: round(lufs(v[smp(t0):smp(t1)]), 1) for k, v in stems.items()
                        if np.abs(v[smp(t0):smp(t1)]).max() > 1e-6}
        secs.append(row)
    rep["sections"] = secs
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    use_plan(a.film)
    film = Film(a.film)
    cues = film.cues
    stems = build_stems(film, cues)
    y, out, info = master(film, stems, edit.silences(cues))
    rep = report(y, out, cues, film)
    info["report"] = rep
    for k, v in out.items():
        write(film.p("mix", f"stem_{k}.wav"), v)
    write(film.p("mix", "mix.wav"), y)
    mp = os.path.join(os.path.dirname(film.out) if a.film == "vertical" else film.out,
                      "vertical-master.wav" if a.film == "vertical" else "master.wav")
    write(mp, y, subtype="PCM_24")
    info["files"] = {"master": mp, "mix_float": film.p("mix", "mix.wav"),
                     "stems": {k: film.p("mix", f"stem_{k}.wav") for k in out}}
    jdump(film.p("mix", "mix_info.json"), info)
    print(json.dumps({k: info[k] for k in ("master_gain_db", "limiter", "integrated_lufs")}))
    print("TP", rep["true_peak_dbtp"], "LRA", rep["loudness_range_lu"], "mono drop", rep["mono_fold"]["drop_lu"],
          "tilt", rep["tilt_db_per_oct_125_8k"], "bands", rep["octave_bands_db_rel"])
    for r in rep["sections"]:
        print(f"{r['shot']:>3} {r['name']:11s} {r['t0']:6.2f}-{r['t1']:6.2f} L {r['lufs']:6.1f} ST_end "
              f"{r['short_term_at_end'] if r['short_term_at_end'] is not None else '':>6}  mono -{r['mono_drop_lu']:.2f}  "
              + " ".join(f"{k}:{v}" for k, v in r["stems"].items()))


if __name__ == "__main__":
    main()
