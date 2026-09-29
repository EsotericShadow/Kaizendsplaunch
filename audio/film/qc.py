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
from common import SR, Film, correlation, dual, hard_silence, jdump, lufs, read, smp
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


PC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def chroma(x, fmin=55.0, fmax=2000.0, nfft=8192):
    """12-bin pitch-class energy of a (mono-summed) excerpt, normalised to sum 1.
    STFT bins between fmin and fmax are folded to the nearest semitone and
    weighted by cos^2 of their distance from it."""
    from scipy import signal
    m = dual(x).mean(axis=1)
    f, _, Z = signal.stft(m, SR, nperseg=nfft, noverlap=nfft - smp(0.01))
    P = (np.abs(Z) ** 2).mean(axis=1)
    sel = (f >= fmin) & (f <= fmax)
    midi = 69 + 12 * np.log2(f[sel] / 440.0)
    c = np.zeros(12)
    np.add.at(c, np.round(midi).astype(int) % 12, P[sel] * np.cos(np.pi * (midi - np.round(midi))) ** 2)
    return c / max(c.sum(), 1e-30)


def clip_bed_check(film, cues, keep):
    """Under each product clip: which stems sound (max |x| > 0), whether only the
    kept ones do, and the chroma clash between the bed and the clip (semitone =
    energy a minor second or major seventh away; a flat chroma would read 2/12 =
    0.167 semitone and 1/12 = 0.083 unison)."""
    names = [k for k in ("gtr", "gtr_oct", "pad", "ep", "lead", "pluck", "arp", "bells", "bass", "drums", "fx",
                         "plate", "hall", "delay") if os.path.exists(film.p("mix", f"stem_{k}.wav"))]
    st = {k: read(film.p("mix", f"stem_{k}.wav")) for k in names}
    clips = read(film.p("mix", "stem_clips.wav"))
    out = {}
    for sec in cues["sections"]:
        if "clip_at" not in sec:
            continue
        a = float(sec["clip_at"])
        b = a + float(sec["clip_out"]) - float(sec["clip_in"])
        s0, s1 = smp(a), smp(b)
        sounding = [k for k in names if np.abs(st[k][s0:s1]).max() > 0.0]
        bed = sum(st[k][s0:s1] for k in names)
        row = {"window": [a, b], "keep": keep.get(sec["name"], []), "sounding": sounding,
               "pass": set(sounding) <= set(keep.get(sec["name"], []))}
        cc = chroma(clips[s0:s1])
        row["clip_chroma_top"] = [PC[i] for i in np.argsort(cc)[::-1][:4]]
        if sounding:
            bc = chroma(bed)
            row["bed_lufs"] = round(lufs(bed), 1)
            row["bed_chroma_top"] = [PC[i] for i in np.argsort(bc)[::-1][:4]]
            row["clash_semitone"] = round(float(cc @ (np.roll(bc, 1) + np.roll(bc, -1))), 3)
            row["unison"] = round(float(cc @ bc), 3)
        out[sec["name"]] = row
    return out


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

    # production pass: honesty zones
    hz = [tuple(z) for z in mix_info["plan"]["honesty_zones"]]
    hon = {"zones": hz}
    gpath = film.p("mix", "gtr_total_gain.npy")
    if os.path.exists(gpath):
        G = np.load(gpath)
        e = edit.edited(film, "gtr", cues)
        sg = read(film.p("mix", "stem_gtr.wav"))
        errs = []
        for (z0, z1) in hz:
            s_, t_ = smp(z0), smp(z1)
            rec = e * G[:, None]
            for (q0, q1) in edit.silences(cues):
                rec = hard_silence(rec, q0, q1)
            ref = rec[s_:t_]
            errs.append(float(np.abs(sg[s_:t_] - ref).max() / max(np.abs(sg[s_:t_]).max(), 1e-12)))
        hon["featured_gtr_is_render_times_gain"] = {"max_rel_error": max(errs),
                                                    "pass": max(errs) < 1e-5,
                                                    "note": "stem_gtr == Choroboros edit x one scalar gain curve "
                                                            "(level match, fader, zone level, master, limiter), "
                                                            "identical in L and R"}
    lg = np.load(film.p("mix", "limiter_gain.npy")) if os.path.exists(film.p("mix", "limiter_gain.npy")) else None
    if lg is not None:
        mn = min(float(lg[smp(z0):smp(z1)].min()) for (z0, z1) in hz)
        hon["no_limiting_in_zones"] = {"min_limiter_gain": mn, "pass": mn >= 1 - 1e-9}
    zero = {}
    for k in ("plate", "hall", "delay", "gtr_oct", "pad", "ep", "lead", "pluck", "arp", "bells", "clips"):
        p = film.p("mix", f"stem_{k}.wav")
        if os.path.exists(p):
            x = read(p)
            zero[k] = max(float(np.abs(x[smp(z0):smp(z1)]).max()) for (z0, z1) in hz)
    hon["no_reverb_delay_or_other_music_in_zones"] = {"max_abs": zero, "pass": all(v == 0.0 for v in zero.values())}
    bk = read(film.p("mix", "stem_drums.wav")) + read(film.p("mix", "stem_bass.wav"))
    hon["backing_mono_in_zones"] = {"correlation": [round(correlation(bk[smp(z0):smp(z1)]), 6) for (z0, z1) in hz]}
    hon["backing_mono_in_zones"]["pass"] = all(abs(c - 1) < 1e-9 for c in hon["backing_mono_in_zones"]["correlation"])
    if a.film == "main":
        blocks = [16.0, 20.0, 24.0, 28.0]
        ref = bk[smp(16.0):smp(20.0)]
        diffs = [float(np.abs(bk[smp(t):smp(t) + len(ref)] - ref).max()) for t in blocks[1:]]
        d5 = float(np.abs(bk[smp(32.0):smp(35.49)] - ref[:smp(3.49)]).max())
        hon["tour_backing_sample_identical"] = {
            "max_abs_diff_pass_2_3_4_vs_1": diffs, "pass_5_until_35.49_vs_1": d5,
            "pass": max(diffs + [d5]) == 0.0,
            "note": "drums + bass as heard in the master; pass 5 (Black) stops at 35.50 per the treatment (the "
                    "fill it replaces starts with a ghost note humanised 1.1 ms early, so the comparison ends at 35.49)"}
    hon["pass"] = all(v.get("pass", True) for v in hon.values() if isinstance(v, dict))
    qc["gates"]["honesty_zones"] = hon

    # the product clips stand alone (mix revision): only the kept bed stems sound under each clip
    cb = (mix_info.get("plan") or {}).get("clip_bed")
    if cb and any("clip_at" in sec for sec in cues["sections"]):
        rows = clip_bed_check(film, cues, cb["keep"])
        qc["checks"]["clip_bed"] = {"pass": all(r["pass"] for r in rows.values()), "clips": rows,
                                    "method": clip_bed_check.__doc__.strip()}

    # arc: per-bar loudness, short-term, crest, onsets, mono drop (from the mix report)
    bars = mix_info["report"].get("bars")
    if bars:
        jdump(film.log_path("arc.json"), {"note": "per bar: BS.1770 loudness of the 2 s bar, short-term (3 s) at "
                                                  "the bar end, crest (sample peak/RMS), onset count, mono-fold drop",
                                          "bars": bars})
        qc["checks"]["arc_log"] = film.log_path("arc.json")

    # extra: stems sum to the master
    tot = sum(read(film.p("mix", f"stem_{k}.wav")) for k in mix_info["files"]["stems"])
    fl = read(film.p("mix", "mix.wav"))
    qc["checks"]["stems_sum_to_mix"] = {"max_abs_diff": float(np.abs(tot - fl).max())}
    qc["checks"]["master_24bit_vs_float_max_diff"] = float(np.abs(fl - y).max())

    qc["pass"] = all(v.get("pass", True) for v in qc["gates"].values()) and \
        qc["checks"]["digital_silences"]["pass"] and qc["checks"].get("p_block_identical", {}).get("pass", True) and \
        qc["checks"].get("clip_bed", {}).get("pass", True)
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
    if "clip_bed" in qc["checks"]:
        for k, r in qc["checks"]["clip_bed"]["clips"].items():
            print(f"clip bed {k:10s} sounding {r['sounding']} pass {r['pass']} semitone clash {r.get('clash_semitone')}"
                  f" unison {r.get('unison')}")
    print("stems sum diff", qc["checks"]["stems_sum_to_mix"]["max_abs_diff"],
          "master 24-bit vs float", qc["checks"]["master_24bit_vs_float_max_diff"])
    print("OVERALL", "PASS" if qc["pass"] else "FAIL")


if __name__ == "__main__":
    main()
