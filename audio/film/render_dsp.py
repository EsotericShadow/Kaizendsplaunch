#!/usr/bin/env python3
"""Real Choroboros renders for "Still Life" (treatment 8.4) through the local
choro-render CLI (referenced by path; never copied into this repo).

For every render in cues.json:
  - every knob is passed explicitly (the CLI factory profile is never heard),
    --block 128, --preroll 2 (Purple: swept), --tail 3, --meta, --quiet
  - automation JSON is generated from cues.json "gestures": the knob POSITION
    p(t) is eased with sine.inOut and sampled every 10 ms, then mapped to plugin
    display units with cues.json "position_maps" (Rate: hz = 0.005 + 19.995 p^4.35).
    HQ is a step (R04: 0 -> 1 at exactly 26.00, a block boundary at block 128)
  - inputs are the full-film-length mono stems, so every render is aligned to
    film time; output is film length + 3 s tail, stereo float32
  - the --meta JSON is verified (engine, core, HQ, final knob values within one
    host grid step, no non-finite or over-full-scale samples) and copied to
    audio/logs/render-meta/

Purple pre-roll sweep (R05): candidates with --preroll 0.00 .. 8.25 in 0.25 s
steps. The Orbit modulator runs on its own clock (it does not depend on the
input), so each candidate is analysed with a film-aligned white-noise input at
Mix 100% (same knobs, same automation, same pre-roll): Wiener deconvolution of
the wet output against the noise, 40 ms Hann windows every 20 ms, gives the
Orbit tap delays. A swoosh peaks when a tap arrives at 0 ms: the comb notch it
forms with the dry signal has raced to the top of the spectrum. Arrivals are
upward steps in the share of wet impulse-response energy at lag 0 (about +0.5
for the 60% main tap, +0.2 for the 40% minor tap). The kept candidate has
exactly one main-tap arrival in the Purple section before the Rate gesture,
inside the window (28.75-29.50), preferring candidates with no minor arrival
either, closest to the window centre.

Usage: python3 audio/film/render_dsp.py [--film main|vertical] [--only R01,R05] [--sweep] [--jobs 2]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import time

import numpy as np

from common import CHORO, LOGS, SR, Film, cues_replace_line, jdump, read, smp, write

CORES = {"green": ("Lagrange 3rd", "Lagrange 5th"), "blue": ("Cubic", "Thiran Allpass"), "red": ("BBD", "Tape"),
         "purple": ("Phase Warp", "Orbit"), "black": ("Linear", "Linear Ensemble")}
PERCENT = ("depth", "width", "color", "mix")


# ----------------------------------------------------------------- knob position maps (cues.json position_maps)

def p_from_display(param, v):
    if param == "rate":
        return ((float(v) - 0.005) / 19.995) ** (1 / 4.35)
    if param == "offset":
        return float(v) / 180.0
    if param == "width":
        return float(v) / 200.0
    return float(v) / 100.0


def display_from_p(param, p):
    if param == "rate":
        return 0.005 + 19.995 * p ** 4.35
    if param == "offset":
        return 180.0 * p
    if param == "width":
        return 200.0 * p
    return 100.0 * p


def raw_from_display(param, v):
    """Host parameter value (the grid the automation lands on)."""
    if param == "rate":
        return 0.01 + 9.99 * ((float(v) - 0.005) / 19.995) ** (1 / 4.35)
    if param == "offset":
        return float(v)
    return float(v) / 100.0          # depth/width/color/mix raw = fraction (width 0..2)


GRID = {"rate": 0.01, "depth": 0.01, "offset": 1.0, "width": 0.01, "color": 0.01, "mix": 0.01}


def sine_inout(u):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))


def gesture_curve(g, step=0.010):
    """[[t, display_value], ...] for one eased gesture (10 ms samples on p)."""
    par = g["param"]
    p0, p1 = p_from_display(par, g["from"]), p_from_display(par, g["to"])
    t0, t1 = float(g["t0"]), float(g["t1"])
    k = int(round((t1 - t0) / step))
    pts = [[0.0, g["from"]]]
    for i in range(k + 1):
        t = t0 + i * step
        u = (t - t0) / (t1 - t0)
        v = display_from_p(par, p0 + (p1 - p0) * float(sine_inout(u)))
        pts.append([round(t, 6), round(v, 6)])
    pts[-1][1] = g["to"]
    return pts


def automation_for(rid, cues):
    auto = {}
    for g in cues["gestures"]:
        if g["render"] != rid:
            continue
        if g["ease"] == "step":
            auto[g["param"]] = [[0.0, g["from"]], [float(g["t0"]), g["to"]]]
        else:
            pts = gesture_curve(g)
            if g["param"] in PERCENT:
                auto[g["param"]] = {"units": "percent", "points": pts}
            else:
                auto[g["param"]] = pts
    return auto


def final_knobs(rid, cues):
    r = cues["renders"][rid]
    k = dict(r["knobs"])
    hq = r["hq"]
    for g in cues["gestures"]:
        if g["render"] == rid:
            if g["param"] == "hq":
                hq = g["to"]
            else:
                k[g["param"]] = g["to"]
    return k, hq


# ----------------------------------------------------------------- one render

def cmd_for(film, rid, cues, out=None, meta=None, preroll=None, mix_override=None, inp=None, auto_path=None):
    r = cues["renders"][rid]
    k = r["knobs"]
    pre = preroll if preroll is not None else float(r.get("preroll", 2.0))
    c = [CHORO, "--in", inp or film.stem_path(r["stem"]), "--out", out or film.render_path(rid),
         "--engine", r["engine"], "--hq", str(int(r["hq"])),
         "--rate", f"{k['rate']}", "--depth", f"{k['depth']}%", "--offset", f"{k['offset']}",
         "--width", f"{k['width']}%", "--color", f"{k['color']}%",
         "--mix", f"{mix_override if mix_override is not None else k['mix']}%",
         "--block", str(cues.get("block", 128)), "--preroll", f"{pre:g}", "--tail", "3",
         "--meta", meta or film.p("renders", f"{rid}.json"), "--quiet"]
    if auto_path:
        c += ["--automation", auto_path]
    return c


def run(c):
    t = time.time()
    p = subprocess.run(c, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"choro-render failed ({p.returncode}): {' '.join(c)}\n{p.stderr[-2000:]}")
    return time.time() - t


def verify_meta(rid, cues, meta_path, preroll):
    m = json.load(open(meta_path))
    r = cues["renders"][rid]
    k_end, hq_end = final_knobs(rid, cues)
    checks = {}
    checks["engine"] = m["engine"] == r["engine"]
    checks["core"] = m["core"] == CORES[r["engine"]][int(hq_end)]
    checks["hq_final"] = bool(m["hq"]) == bool(hq_end)
    checks["block_128"] = int(m["blockSize"]) == int(cues.get("block", 128))
    checks["tail_3"] = abs(float(m["tailSec"]) - 3.0) < 1e-9
    checks["preroll"] = abs(float(m["prerollSec"]) - preroll) < 1e-6
    checks["license_unlocked"] = bool(m["licenseUnlocked"])
    checks["finite"] = int(m["outNonFinite"]) == 0
    checks["no_over_full_scale"] = int(m["outSamplesOverFullScale"]) == 0
    knob = {}
    for par, want in k_end.items():
        got = float(m["knobsAtEnd"][par])
        got_disp = got * 100.0 if par in PERCENT else got
        d_raw = abs(raw_from_display(par, got_disp) - raw_from_display(par, want))
        ok = d_raw <= GRID[par] + 1e-6
        knob[par] = {"want": want, "got": round(got_disp, 4), "raw_delta": round(d_raw, 5), "ok": ok}
    checks["knobs_within_one_grid_step"] = all(v["ok"] for v in knob.values())
    return {"pass": all(checks.values()), "checks": checks, "knobs": knob, "core": m["core"],
            "outPeakDb": m["outPeakDb"], "engineSwitchesDuringRender": m.get("engineSwitchesDuringRender")}


# ----------------------------------------------------------------- Purple swoosh analysis

def zero_lag_energy(wet, x, t0, t1, hop=0.020, win=0.040, max_lag=0.036, neg=48, zero=3):
    """Per 20 ms hop and channel: the share of the wet impulse-response energy
    (Wiener deconvolution of wet against the input x, Hann window win) that sits
    within +-zero samples of lag 0. A tap arriving at 0 ms raises it in a step:
    about +0.2 for the Orbit minor tap, about +0.5 for the main tap."""
    nw = smp(win)
    nfft = 1 << int(np.ceil(np.log2(nw + smp(max_lag) * 2 + neg)))
    w = np.hanning(nw)
    L = smp(max_lag)
    times = np.arange(t0, t1, hop)
    e0 = np.zeros((len(times), 2))
    for i, t in enumerate(times):
        a = smp(t) - nw // 2
        xs = x[a:a + nw] * w
        X = np.fft.rfft(xs, nfft)
        pxx = np.abs(X) ** 2
        lam = 0.01 * pxx.mean()
        for ch in range(2):
            Y = np.fft.rfft(wet[a:a + nw, ch] * w, nfft)
            h = np.fft.irfft(Y * np.conj(X) / (pxx + lam), nfft)
            e = np.concatenate([h[-neg:], h[:L]]) ** 2
            e0[i, ch] = e[neg - zero:neg + zero + 1].sum() / max(e[neg // 2:].sum(), 1e-30)
    return times, e0


def arrivals(times, e0, minor=0.10, major=0.25):
    """Tap arrivals at 0 ms (swoosh peaks): upward steps in the zero-lag energy
    share, measured as mean(+2..+6 hops) - mean(-6..-2 hops). Returns a list of
    dicts (t, step, channel, kind) with L/R arrivals closer than 0.25 s merged."""
    out = []
    n = len(times)
    for ch in range(2):
        v = e0[:, ch]
        d = np.full(n, 0.0)
        for i in range(6, n - 6):
            d[i] = v[i + 2:i + 7].mean() - v[i - 6:i - 1].mean()
        i = 6
        while i < n - 6:
            if d[i] >= minor:
                j = i
                while j < n - 6 and d[j] >= minor * 0.5:
                    j += 1
                k = i + int(np.argmax(d[i:j]))
                # the arrival frame: first frame after k-3 where the share has risen
                base = v[k - 6:k - 1].mean()
                top = v[k + 2:k + 7].mean()
                idx = [m for m in range(k - 4, k + 5) if v[m] >= base + 0.5 * (top - base)]
                m = idx[0] if idx else k
                out.append({"t": round(float(times[m]), 3), "step": round(float(d[k]), 3), "channel": "LR"[ch],
                            "kind": "main" if d[k] >= major else "minor"})
                i = j + 3
            else:
                i += 1
    out.sort(key=lambda e: e["t"])
    merged = []
    for e in out:
        if merged and e["t"] - merged[-1]["t"] < 0.25:
            if e["step"] > merged[-1]["step"]:
                merged[-1] = e
        else:
            merged.append(e)
    return merged


def purple_sweep(film, cues, rid="R05", jobs=2):
    """Render one analysis candidate per pre-roll (Mix 100%, white-noise input
    of film length, same automation), measure tap arrivals at 0 ms, and keep
    the candidate with exactly one main swoosh in the Purple section before the
    gesture, inside the window, preferring no minor arrival either."""
    r = cues["renders"][rid]
    sw = r.get("preroll_sweep", {})
    win = sw.get("window", [28.75, 29.5])
    sec0 = sw.get("section_start", 28.0)
    clear = sw.get("clear_until", 30.0)
    lo, hi = sw.get("range", [0.0, 8.25])
    step = sw.get("step", 0.25)
    t_an0, t_an1 = max(0.5, sec0 - 1.0), clear + 0.5
    tmpdir = film.p("cache", f"{rid}_sweep")
    os.makedirs(tmpdir, exist_ok=True)
    rng = np.random.default_rng(99)
    noise = rng.uniform(-1, 1, smp(t_an1 + 1.0)) * 0.1          # -20 dBFS peak, flat spectrum
    npath = os.path.join(tmpdir, "noise_in.wav")
    write(npath, noise)
    auto = automation_for(rid, cues)
    auto_path = film.p("auto", f"{rid}.json") if auto else None
    prerolls = [round(lo + step * k, 2) for k in range(int(round((hi - lo) / step)) + 1)]

    def job(pre):
        out = os.path.join(tmpdir, f"wet_{pre:.2f}.wav")
        meta = os.path.join(tmpdir, f"wet_{pre:.2f}.json")
        run(cmd_for(film, rid, cues, out=out, meta=meta, preroll=pre, mix_override=100, inp=npath,
                    auto_path=auto_path))
        wet = read(out)
        times, e0 = zero_lag_energy(wet, noise, t_an0, t_an1)
        np.save(os.path.join(tmpdir, f"e0_{pre:.2f}.npy"), np.column_stack([times, e0]))
        os.remove(out)
        arr = arrivals(times, e0)
        # departures (a tap leaving 0 ms: the notch sweeps back down) = arrivals in reversed time
        dep = arrivals(-times[::-1].copy(), e0[::-1].copy())
        dep = [dict(e, t=round(-e["t"], 3)) for e in dep][::-1]
        return pre, arr, dep

    results = []
    with cf.ThreadPoolExecutor(jobs) as ex:
        for pre, arr, dep in ex.map(job, prerolls):
            in_sec = [e for e in arr if sec0 <= e["t"] < clear]
            mains = [e for e in in_sec if e["kind"] == "main"]
            ok = len(mains) == 1 and win[0] <= mains[0]["t"] <= win[1]
            sw_t = mains[0]["t"] if ok else None
            others = []
            if ok:
                others = [e for e in in_sec + [d for d in dep if sec0 <= d["t"] < clear]
                          if e["kind"] == "main" and abs(e["t"] - sw_t) > 0.3]
            results.append({"preroll": pre, "arrivals": arr, "departures": dep, "main_in_section": len(mains),
                            "minor_in_section": len(in_sec) - len(mains), "ok": ok, "swoosh_t": sw_t,
                            "other_main_events_in_section": len(others) if ok else None})
    centre = 0.5 * (win[0] + win[1])
    good = [x for x in results if x["ok"]]
    best = min(good, key=lambda x: (x["other_main_events_in_section"], x["minor_in_section"],
                                    abs(x["swoosh_t"] - centre))) if good else None
    return {"method": "white-noise analysis input, Mix 100%, Wiener deconvolution 40 ms Hann / 20 ms hop; "
                      "swoosh peak = a tap arriving at 0 ms (step in the zero-lag energy share; main tap step "
                      ">= 0.25, minor tap 0.10-0.25); departures are the same test in reversed time",
            "selection": "exactly one main-tap arrival in [section_start, clear_until) and it lies in the window; "
                         "then fewest other main-tap arrivals/departures more than 0.3 s from it, fewest minor "
                         "arrivals, closest to the window centre",
            "window": win, "section_start": sec0, "clear_until": clear, "candidates": results,
            "n_ok": len(good), "chosen": best}


# ----------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    ap.add_argument("--only", default="")
    ap.add_argument("--sweep", action="store_true", help="run the Purple pre-roll sweep first")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    film = Film(a.film)
    cues = film.cues
    rids = [x for x in a.only.split(",") if x] or list(cues["renders"].keys())

    # automation files
    for rid in cues["renders"]:
        auto = automation_for(rid, cues)
        if auto:
            jdump(film.p("auto", f"{rid}.json"), auto)

    log = {}
    logp = film.log_path("render-log.json")
    if os.path.exists(logp):
        log = json.load(open(logp))

    purple = [rid for rid in rids if cues["renders"][rid].get("preroll_sweep")]
    if a.sweep and purple:
        for rid in purple:
            t = time.time()
            res = purple_sweep(film, cues, rid, a.jobs)
            res["seconds"] = round(time.time() - t, 1)
            log[f"{rid}_preroll_sweep"] = res
            ch = res["chosen"]
            if ch is None:
                raise SystemExit(f"{rid}: no pre-roll candidate puts one swoosh in {res['window']}")
            r = dict(cues["renders"][rid])
            r["preroll"] = ch["preroll"]
            r["swoosh_t"] = ch["swoosh_t"]
            cues_replace_line(film.cues_path, rf'^\s*"{rid}":\s*\{{', r)
            cues = film.cues
            print(f"{rid}: pre-roll {ch['preroll']} s, swoosh at {ch['swoosh_t']} s ({res['n_ok']} valid candidates; "
                  f"other main events in section: {ch['other_main_events_in_section']})")
            jdump(logp, log)

    jobs = []
    for rid in rids:
        r = cues["renders"][rid]
        auto = automation_for(rid, cues)
        pre = float(r.get("preroll", 2.0))
        c = cmd_for(film, rid, cues, preroll=pre, auto_path=film.p("auto", f"{rid}.json") if auto else None)
        jobs.append((rid, c, pre))

    def do(job):
        rid, c, pre = job
        secs = run(c)
        return rid, c, pre, secs

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for rid, c, pre, secs in ex.map(do, jobs):
            meta_p = film.p("renders", f"{rid}.json")
            v = verify_meta(rid, cues, meta_p, pre)
            shutil.copy(meta_p, os.path.join(LOGS, "render-meta", f"{rid}{film.log_suffix}.json"))
            if os.path.exists(film.p("auto", f"{rid}.json")):
                shutil.copy(film.p("auto", f"{rid}.json"),
                            os.path.join(LOGS, "render-meta", f"{rid}{film.log_suffix}.automation.json"))
            cmd_show = [x.replace(CHORO, "choro-render") for x in c]
            log[rid] = {"cmd": " ".join(cmd_show), "seconds": round(secs, 2), "preroll": pre, "verify": v}
            print(f"{rid}: {'PASS' if v['pass'] else 'FAIL'} core={v['core']} peak={v['outPeakDb']:.2f} dB "
                  f"({secs:.1f} s)")
            if not v["pass"]:
                print(json.dumps(v, indent=1))
    jdump(logp, log)


if __name__ == "__main__":
    main()
