#!/usr/bin/env python3
"""QC gates for the soundtrack (treatment 11, items 1-4 and 10) plus the
checks the brief adds: mono fold, digital silences, click-free joins, the
sample-identical P block, stems summing to the master, file formats.

Writes audio/logs/qc.json (or qc-vertical.json).

Usage: python3 audio/film/qc.py [--film main|vertical]
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import soundfile as sf

import edit
from common import SR, Film, correlation, dual, jdump, lufs, read, smp
from synth import io as sio
from synth import meter
from synth.filters import eq

SOURCE_STEMS = ["gtr", "pad", "ep", "lead", "pluck", "bells", "bass", "drums", "fx"]


def click_score(x, t, kind="join", win=0.002, ctx=0.1, guard=0.004):
    """Join/cut click check. High-pass (> 5 kHz) energy in the 2 ms window at
    t, relative to the loudest 2 ms HF burst in the surrounding +-100 ms outside
    +-4 ms of t (dB; <= 0 means nothing at the join sticks out above the
    natural transients around it). For a cut into silence only the material
    before is the reference, for a hard start only the material after. Also
    returns the absolute HF burst level at the join (dBFS)."""
    x = dual(x)
    a, b = max(0, smp(t - ctx)), min(len(x), smp(t + ctx))
    hp = eq(x[a:b], [("highpass", 5000, 0, 0.7), ("highpass", 5000, 0, 0.7)], SR)
    k = smp(win)
    starts = np.arange(0, len(hp) - k, max(1, k // 2))
    e = np.array([np.sum(hp[i:i + k] ** 2, axis=0).max() for i in starts])
    tt = (starts + k / 2) / SR + a / SR
    at = np.abs(tt - t) <= win
    if kind == "cut":
        ref = (tt < t - guard)
    elif kind == "start":
        ref = (tt > t + guard)
    else:
        ref = np.abs(tt - t) > guard
    ref &= e > 1e-18
    if not np.any(at) or e[at].max() <= 1e-20:
        return {"rel_db": None, "abs_dbfs": None}
    peak = e[at].max()
    rel = 10 * np.log10(peak / e[ref].max()) if np.any(ref) else None
    return {"rel_db": None if rel is None else round(float(rel), 1),
            "abs_dbfs": round(float(10 * np.log10(peak / k)), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    film = Film(a.film)
    cues = film.cues
    n = film.n
    qc = {"film": a.film, "gates": {}}

    # 1. source stems mono, L/R correlation +1.0 as the plugin receives them
    rows = {}
    for s in SOURCE_STEMS:
        p = film.stem_path(s)
        info = sf.info(p)
        x = read(p)
        rows[s] = {"channels": info.channels, "samplerate": info.samplerate, "subtype": info.subtype,
                   "frames": info.frames, "duration_s": round(info.frames / info.samplerate, 6),
                   "correlation_dual_mono": round(correlation(x), 6) if np.abs(x).max() > 0 else None,
                   "finite": bool(np.all(np.isfinite(x)))}
    ok1 = all(r["channels"] == 1 and r["samplerate"] == SR and r["frames"] == n and
              (r["correlation_dual_mono"] in (None, 1.0)) and r["finite"] for r in rows.values())
    qc["gates"]["1_source_stems_mono_correlation_1"] = {"pass": ok1, "stems": rows,
                                                        "note": "every source stem is a 1-channel file; "
                                                                "choro-render copies mono to both inputs"}

    # 2. level match
    lm = json.load(open(film.log_path("level-match.json")))
    qc["gates"]["2_level_match"] = {"pass": bool(all(r["pass"] for r in lm["bars"])), "result": lm["result"],
                                    "worst_residual_lu": max(abs(r["residual"]) for r in lm["bars"]),
                                    "ffmpeg_crosscheck": lm.get("crosscheck")}

    # 3. render meta
    rl = json.load(open(film.log_path("render-log.json")))
    meta = {rid: {"pass": rl[rid]["verify"]["pass"], "core": rl[rid]["verify"]["core"],
                  "checks": rl[rid]["verify"]["checks"]} for rid in cues["renders"] if rid in rl}
    qc["gates"]["3_render_meta"] = {"pass": all(v["pass"] for v in meta.values()) and
                                    len(meta) == len(cues["renders"]), "renders": meta}

    # 4. Purple swoosh
    sw = None
    for rid, r in cues["renders"].items():
        if r.get("preroll_sweep"):
            win = r["preroll_sweep"]["window"]
            t = r.get("swoosh_t")
            sw = {"render": rid, "preroll": r.get("preroll"), "swoosh_t": t, "window": win,
                  "pass": t is not None and win[0] <= t <= win[1],
                  "chosen_detail": rl.get(f"{rid}_preroll_sweep", {}).get("chosen")}
    if sw:
        qc["gates"]["4_purple_swoosh"] = sw

    # 10. master
    mp = os.path.join(os.path.dirname(film.out), "vertical-master.wav") if a.film == "vertical" else \
        os.path.join(film.out, "master.wav")
    mi = sf.info(mp)
    y = read(mp)
    mix_info = json.load(open(film.p("mix", "mix_info.json")))
    L = lufs(y)
    tp = meter.true_peak(y, SR)
    target = cues["master"]["lufs"]
    tol = cues["master"]["lufs_tol"]
    ff = sio.ffmpeg_loudness(mp)
    m10 = {"integrated_lufs": round(L, 3), "target": target, "tolerance": tol,
           "true_peak_dbtp": round(tp, 3), "ceiling": cues["master"]["true_peak_dbtp"],
           "sample_peak_dbfs": round(meter.sample_peak(y), 3),
           "clipped_runs_3_samples_at_fs": meter.clipped_samples(y),
           "samples_at_or_over_full_scale": int(np.sum(np.abs(y) >= 1.0)),
           "non_finite": int(np.sum(~np.isfinite(y))),
           "limiter_max_gain_reduction_db": mix_info["limiter"]["max_gain_reduction_db"],
           "format": {"samplerate": mi.samplerate, "channels": mi.channels, "subtype": mi.subtype,
                      "frames": mi.frames, "duration_s": mi.frames / mi.samplerate},
           "ffmpeg_ebur128": ff}
    m10["pass"] = bool(abs(L - target) <= tol and tp <= cues["master"]["true_peak_dbtp"] + 1e-6 and
                       m10["clipped_runs_3_samples_at_fs"] == 0 and m10["samples_at_or_over_full_scale"] == 0 and
                       m10["non_finite"] == 0 and m10["limiter_max_gain_reduction_db"] <= 1.0 and
                       mi.samplerate == SR and mi.subtype == "PCM_24" and mi.frames == n)
    qc["gates"]["10_master"] = m10

    # extra: mono fold
    mono = 0.5 * (y[:, 0] + y[:, 1])
    mf = {"integrated_lufs_stereo": round(L, 3), "integrated_lufs_mono_fold": round(lufs(np.stack([mono, mono], 1)), 3)}
    mf["drop_lu"] = round(mf["integrated_lufs_stereo"] - mf["integrated_lufs_mono_fold"], 3)
    mf["correlation_overall"] = round(correlation(y), 4)
    mf["sections"] = []
    for s in cues["sections"]:
        t0, t1 = s["t0"], s["t1"]
        if t1 - t0 < 1.0:
            continue
        seg = y[smp(t0):smp(t1)]
        m = 0.5 * (seg[:, 0] + seg[:, 1])
        mf["sections"].append({"name": s["name"], "t0": t0, "t1": t1,
                               "drop_lu": round(lufs(seg) - lufs(np.stack([m, m], 1)), 2),
                               "correlation": round(correlation(seg), 3)})
    mf["worst_section_drop_lu"] = max(r["drop_lu"] for r in mf["sections"])
    qc["checks"] = {"mono_fold": mf}

    # extra: digital silences
    sil = []
    for (s0, s1) in edit.silences(cues):
        seg = y[smp(s0):smp(s1)]
        sil.append({"t0": s0, "t1": s1, "max_abs": float(np.abs(seg).max()), "exact_zero": bool(np.all(seg == 0))})
    qc["checks"]["digital_silences"] = {"pass": all(r["exact_zero"] for r in sil), "windows": sil}

    # extra: clicks at every join and hard cut (on the master and on each edited stem)
    events = {}
    for st in ("gtr", "pad", "ep", "lead", "pluck"):
        for (t, a_, b_) in edit.joins(cues, st):
            events[round(t, 3)] = "join"
    for (s0, s1) in edit.silences(cues):
        events[round(s0, 3)] = "cut"
        events[round(s1, 3)] = "start"
    clicks = []
    stems = {k: read(film.p("mix", f"stem_{k}.wav")) for k in ("gtr", "pad", "ep", "lead", "pluck")
             if os.path.exists(film.p("mix", f"stem_{k}.wav"))}
    for t in sorted(events):
        if t <= 0.1 or t >= film.duration - 0.1:
            continue
        kind = events[t]
        row = {"t": t, "kind": kind, "master": click_score(y, t, kind)}
        for k, v in stems.items():
            if np.abs(v[smp(t - 0.05):smp(t + 0.05)]).max() > 1e-4:
                row[k] = click_score(v, t, kind)
        clicks.append(row)
    vals = [r["master"]["rel_db"] for r in clicks if r["master"]["rel_db"] is not None]
    worst = max(vals) if vals else None
    qc["checks"]["joins_click_scan"] = {"method": click_score.__doc__.strip(), "events": clicks,
                                        "worst_master_rel_db": worst}

    # extra: block P sample-identical in the gtr stem (main film)
    if a.film == "main":
        g = read(film.stem_path("gtr"))
        ref = g[smp(16.0):smp(20.0)]
        pastes = [16.0, 20.0, 24.0, 28.0, 32.0, 50.0, 58.0]
        qc["checks"]["p_block_identical"] = {"pass": all(np.array_equal(ref, g[smp(t):smp(t + 4.0)]) for t in pastes),
                                             "pastes": pastes}

    # extra: stems sum to the master
    tot = sum(read(film.p("mix", f"stem_{k}.wav")) for k in mix_info["files"]["stems"])
    fl = read(film.p("mix", "mix.wav"))
    qc["checks"]["stems_sum_to_mix"] = {"max_abs_diff": float(np.abs(tot - fl).max())}
    qc["checks"]["master_24bit_vs_float_max_diff"] = float(np.abs(fl - y).max())

    qc["pass"] = all(v.get("pass", True) for v in qc["gates"].values()) and \
        qc["checks"]["digital_silences"]["pass"] and qc["checks"].get("p_block_identical", {}).get("pass", True)
    jdump(film.log_path("qc.json"), qc)
    for k, v in qc["gates"].items():
        print(f"{k:40s} {'PASS' if v['pass'] else 'FAIL'}")
    print("mono fold drop", mf["drop_lu"], "LU; worst section", mf["worst_section_drop_lu"])
    print("silences exact zero:", qc["checks"]["digital_silences"]["pass"], " P identical:",
          qc["checks"].get("p_block_identical", {}).get("pass"))
    print("click scan (master, dB vs loudest nearby HF burst; <= 0 = nothing sticks out) worst", worst)
    for r in clicks:
        print("  ", r["t"], r["kind"], "master", r["master"], " ".join(f"{k}:{v['rel_db']}" for k, v in r.items()
                                                                 if k not in ("t", "kind", "master")))
    print("stems sum diff", qc["checks"]["stems_sum_to_mix"]["max_abs_diff"],
          "master 24-bit vs float", qc["checks"]["master_24bit_vs_float_max_diff"])
    print("OVERALL", "PASS" if qc["pass"] else "FAIL")


if __name__ == "__main__":
    main()
