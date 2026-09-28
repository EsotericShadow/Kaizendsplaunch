#!/usr/bin/env python3
"""Level matching per treatment 8.6.

1. Loudness of a bar = BS.1770-4 integrated loudness (K-weighted, gated) over
   its 2.000 s span, with audio/synth/meter.py. Cross-checked on one file with
   ffmpeg ebur128.
2. Like with like: the dry mono stem is measured as dual mono (copied to L and
   R), which is what the plugin receives.
3. Bars 1-4 and 9-18 (guitar): gain(b) = L_dry(b) - L_processed(b), the
   processed signal being the section edit (R01 ... R06). Bars 28-31 (pad):
   gain(b) = L_R09ref(b) - L_R09(b).
4. Gain curve: constant per bar with 20 ms ramps that end on the bar line;
   across a gesture the ramp follows the gesture's sine.inOut ease over its
   duration (on knob position, the same curve that drives the plugin).
   Because ramps and gesture bars mix neighbouring gains, the per-bar gains
   are solved iteratively until every residual is below 0.02 LU.
5. Re-measure; a bar passes if |L_after(b) - L_reference(b)| <= 0.3 LU.
6. Log: audio/logs/level-match.json (bar, section, render, L_reference,
   L_processed, gain, residual, pass) and the footnote decision. The same
   decision is written into cues.json levelmatch.result.

Outside the matched bars each guitar render keeps a constant makeup gain equal
to its matched steady-state gain (R01 at Mix 45%: mean of bars 3-4; R03 at
Offset 90 deg: bar 12), so the processed guitar keeps the dry take's loudness
wherever it plays. Gain curves go to <build>/edit/gain_<stem>.npy.

Usage: python3 audio/film/levelmatch.py [--film main|vertical]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile

import numpy as np

import edit
from common import SR, Film, bar_t, cues_replace_line, dual, jdump, lufs, read, sine_inout, smp, write
from render_dsp import p_from_display
from synth import io as sio

TOL = 0.3


def gesture_for(cues, rid, t0, t1):
    for g in cues["gestures"]:
        if g["render"] == rid and t0 - 1e-9 <= float(g["t0"]) < t1 - 1e-9:
            return g
    return None


def eased(g, t):
    """Gesture progress 0..1 at times t on the knob-position ease (the plugin
    receives display values mapped from the same eased position)."""
    u = np.clip((t - float(g["t0"])) / max(float(g["t1"]) - float(g["t0"]), 1e-9), 0, 1)
    if g["ease"] == "step":
        return (t >= float(g["t0"])).astype(float)
    return sine_inout(u)


def build_curve(n, bars, gains, prev_gain, plan_rid, cues, ramp=0.020):
    """Gain curve in dB over the matched range. bars: list of (bar, t0, t1).
    Before each bar's start the previous gain holds; each bar's gain arrives
    with a 20 ms ramp ending on its bar line, or, when a gesture starts in that
    bar, stays at the previous gain until the gesture and follows its ease to
    the bar's gain by the gesture end."""
    t = np.arange(n) / SR
    g = np.full(n, np.nan)
    last = prev_gain
    for (b, t0, t1), gb in zip(bars, gains):
        s0, s1 = smp(t0), smp(t1)
        rid = plan_rid(t0)
        ge = gesture_for(cues, rid, t0, t1)
        seg_t = t[s0:s1]
        if ge is not None and ge["ease"] != "step":
            e = eased(ge, seg_t)
            g[s0:s1] = last + (gb - last) * e
        else:
            g[s0:s1] = gb
            k = smp(ramp)
            a = max(0, s0 - k)
            if a < s0 and not np.isnan(g[a]):
                u = (np.arange(s0 - a) + 1) / (s0 - a)
                g[a:s0] = g[a:s0] + (gb - g[a:s0]) * sine_inout(u)
        last = gb
    return g


def solve(film, cues, stem, bars, ref, proc, prev_gain, max_iter=12):
    """Iteratively solve per-bar gains so each bar's loudness matches ref."""
    n = film.n
    plan = edit.stem_plan(cues, stem)

    def plan_rid(t):
        for (a, b, rid) in plan:
            if a - 1e-9 <= t < b - 1e-9:
                return rid
        return None

    L_ref = [lufs(ref[smp(t0):smp(t1)]) for (_, t0, t1) in bars]
    L_proc = [lufs(proc[smp(t0):smp(t1)]) for (_, t0, t1) in bars]
    gains = [lr - lp for lr, lp in zip(L_ref, L_proc)]
    lo, hi = smp(bars[0][1]), smp(bars[-1][2])
    for it in range(max_iter):
        curve = build_curve(n, bars, gains, prev_gain, plan_rid, cues)
        seg = proc[lo:hi] * (10 ** (curve[lo:hi] / 20))[:, None]
        L_after = [lufs(seg[smp(t0) - lo:smp(t1) - lo]) for (_, t0, t1) in bars]
        res = [la - lr for la, lr in zip(L_after, L_ref)]
        if max(abs(r) for r in res) < 0.02:
            break
        gains = [g - r for g, r in zip(gains, res)]
    rows = []
    for (b, t0, t1), lr, lp, g, la in zip(bars, L_ref, L_proc, gains, L_after):
        sec = [s["name"] for s in cues["sections"] if s["t0"] - 1e-9 <= t0 < s["t1"] - 1e-9]
        rid = plan_rid(t0)
        ge = gesture_for(cues, rid, t0, t1)
        rows.append({"bar": b, "t0": t0, "t1": t1, "section": sec[0] if sec else None, "render": rid,
                     "gesture": f"{ge['param']} {ge['from']}->{ge['to']} {ge['t0']}-{ge['t1']}" if ge else None,
                     "L_reference": round(lr, 3), "L_processed": round(lp, 3), "gain_db": round(g, 3),
                     "L_after": round(la, 3), "residual": round(la - lr, 3), "pass": bool(abs(la - lr) <= TOL)})
    return rows, gains, curve, it + 1


def ffmpeg_crosscheck(x, label):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.wav")
        write(p, x)
        ff = sio.ffmpeg_loudness(p)
    return {"file": label, "meter_py_lufs": round(lufs(x), 3), "ffmpeg_ebur128_lufs": ff.get("ebur128_I"),
            "delta_lu": round(lufs(x) - ff["ebur128_I"], 3) if ff.get("ebur128_I") is not None else None}


def makeup_gains(cues, gtr_rows):
    """Constant gains for each guitar render outside the matched bars: the mean
    gain of its matched bars that start after its gesture has ended (steady
    state at the final knob values), else its last matched bar."""
    out = {}
    for rid in sorted({r["render"] for r in gtr_rows if r["render"]}):
        rows = [r for r in gtr_rows if r["render"] == rid]
        ges = [g for g in cues["gestures"] if g["render"] == rid]
        t_end = max((float(g["t1"]) for g in ges), default=-1.0)
        steady = [r for r in rows if r["t0"] >= t_end - 1e-9]
        use = steady or rows[-1:]
        out[rid] = round(float(np.mean([r["gain_db"] for r in use])), 3)
    return out


def spans(t0, t1):
    """Split [t0, t1) at bar lines: [(bar, a, b), ...] (bar = 1-based bar of a)."""
    out = []
    a = t0
    while a < t1 - 1e-9:
        b = min(t1, (np.floor(a / 2.0 + 1e-9) + 1) * 2.0)
        out.append((int(np.floor(a / 2.0 + 1e-9)) + 1, float(a), float(b)))
        a = b
    return out


def gtr_curve(film, cues, rows_all, curve_matched, makeup):
    """Full-film guitar gain curve: matched bars from the solve, elsewhere the
    render's makeup gain, with 20 ms ramps ending on section boundaries."""
    n = film.n
    plan = edit.stem_plan(cues, "gtr")
    base = np.zeros(n)
    for (a, b, rid) in plan:
        base[smp(a):smp(b)] = makeup.get(rid, 0.0) if rid else 0.0
    m = ~np.isnan(curve_matched)
    base[m] = curve_matched[m]
    # 20 ms ramps ending on every section boundary and on the edges of the matched ranges
    edges = {smp(p[0]) for p in plan[1:]}
    d = np.diff(m.astype(int))
    edges |= {int(i) + 1 for i in np.nonzero(d)[0]}
    k = smp(0.020)
    u = (np.arange(k) + 1) / k
    for s in sorted(edges):
        if s - k - 1 < 0 or s >= n:
            continue
        g0, g1 = base[s - k - 1], base[s]
        if abs(g1 - g0) > 1e-9:
            base[s - k:s] = g0 + (g1 - g0) * sine_inout(u)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    film = Film(a.film)
    cues = film.cues
    n = film.n
    dry = dual(read(film.stem_path("gtr")))
    gtr = edit.edited(film, "gtr", cues)
    out = {"method": "BS.1770-4 integrated loudness per 2.000 s bar (audio/synth/meter.py, K-weighted, gated); dry "
                     "stem measured as dual mono; tolerance 0.3 LU; per-bar gains with 20 ms ramps ending on the "
                     "bar line, gesture bars ramp on the gesture's sine.inOut ease; solved iteratively",
           "tolerance_lu": TOL, "bars": []}
    curve_all = np.full(n, np.nan)
    gtr_rows = []
    lm = cues["levelmatch"]["sections"]
    for (t0, t1, ref_name) in lm:
        bars = spans(float(t0), float(t1))
        b0, b1 = bars[0][0], bars[-1][0]
        if ref_name == "dry":
            prev = 0.0 if b0 == 1 else None
            if prev is None:
                prev = gtr_rows[-1]["gain_db"] if gtr_rows else 0.0
            rows, gains, curve, iters = solve(film, cues, "gtr", bars, dry, gtr, prev)
            gtr_rows += rows
            m = ~np.isnan(curve)
            curve_all[m] = curve[m]
            stem = "gtr"
        else:
            ref = read(film.render_path(ref_name))[:n]
            pad = edit.edited(film, "pad", cues)
            rows, gains, curve, iters = solve(film, cues, "pad", bars, ref, pad, 0.0)
            np.save(film.p("edit", "gain_pad_matched.npy"), curve)
            stem = "pad"
        for r in rows:
            r["stem"] = stem
            r["reference"] = ref_name
        out["bars"] += rows
        print(f"{stem} bars {b0}-{b1} vs {ref_name}: {iters} iterations, worst residual "
              f"{max(abs(r['residual']) for r in rows):.3f} LU")
    makeup = makeup_gains(cues, gtr_rows)
    curve_full = gtr_curve(film, cues, gtr_rows, curve_all, makeup)
    np.save(film.p("edit", "gain_gtr.npy"), curve_full)
    out["makeup_gain_db_outside_matched_bars"] = makeup

    def ok(bs):
        sel = [r for r in out["bars"] if r["bar"] in bs and r["stem"] == ("pad" if min(bs) >= 28 else "gtr")]
        return bool(sel) and all(r["pass"] for r in sel)

    if a.film == "main":
        res = {"bars_1_4_pass": ok(range(1, 5)), "bars_9_18_pass": ok(range(9, 19)),
               "bars_28_31_pass": ok(range(28, 32))}
        res["footnote_shots_2_3"] = "LEVEL MATCHED" if res["bars_1_4_pass"] else None
        res["footnote_tour"] = "SAME TAKE · LEVEL MATCHED" if res["bars_9_18_pass"] else "SAME TAKE"
    else:
        gb = [r for r in out["bars"] if r["stem"] == "gtr"]
        pb = [r for r in out["bars"] if r["stem"] == "pad"]
        res = {"guitar_bars_1_7_pass": all(r["pass"] for r in gb), "pad_width_spans_pass": all(r["pass"] for r in pb)}
    out["result"] = res
    # ffmpeg cross-check on the processed, matched guitar over the tour (or the vertical's engine bars)
    lo, hi = (16.0, 36.0) if a.film == "main" else (0.0, 14.0)
    seg = gtr[smp(lo):smp(hi)] * (10 ** (curve_full[smp(lo):smp(hi)] / 20))[:, None]
    out["crosscheck"] = ffmpeg_crosscheck(seg, f"gtr edit after level gain, {lo}-{hi} s")
    jdump(film.log_path("level-match.json"), out)
    # record the decision in the cues file
    r = dict(cues["levelmatch"])
    r["result"] = res
    cues_replace_line(film.cues_path, r'^\s*"levelmatch":\s*\{', r)
    print(json.dumps(res, ensure_ascii=False))
    print("crosscheck", out["crosscheck"])


if __name__ == "__main__":
    main()
