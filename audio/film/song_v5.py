"""Choroboros v5: the audio for the portrait launch film and the 15 s TikTok.

Implements film/v5/demos.json (the machine twin of film/v5/TREATMENT.md section 3 and 7.3) exactly:

* Film time = master time. The owner's song plays straight through from its first sample: nothing
  is cut, looped, reordered or time-stretched. Everywhere outside the demos, and in every bypass
  span, the output is the master itself, bit for bit.
* Every demo uses the BP path: out = master - BP(nd) + choro_trim(BP(nd)), where nd is the master's
  own non-drum part (master minus the fitted drums, sample-locked) and BP a zero-phase Butterworth
  band-pass (120 Hz to 5.5 kHz, 4th order per edge, sosfiltfilt). In the guitar-alone windows the
  drums are digitally silent, so nd = master and the master itself is processed with no path switch.
* The real Choroboros processor (choro-render, called by path) renders each demo with 3 s of real
  pre-roll so the delay lines and LFOs are running on the first kept sample. Every knob is passed
  explicitly; gestures are sampled every 10 ms from the same curves the picture reads; HQ is stepped;
  the plug-in's Output Trim does the level matching (automated when it follows Mix or changes at a
  split bar line).
* Joins are equal-power crossfades: 20 ms ending on the hit (engine on a hit), 20 ms centred on the
  bar line (engine on a bar line), 10 ms with the midpoint 5 ms before the hit (bypass toggles).
* Level matching per bar (BS.1770) against the same bars of the master (split at a failing bar line).
  No limiter on the mix: where the processed song would pass -1 dBTP, only the Choroboros change is
  pulled back towards the master (whose own true peak is -1.14 dBTP), so the drums are never touched.
* The Choroboros change (out - master) is band-limited by a zero-phase 6 kHz FIR, and joins crossfade
  that change (equal-power) over the untouched master, so a join can neither dip nor bump the drums.

Outputs (never in the repo): /home/user/build/v5/master_v5.wav, tiktok_v5.wav (-14 LUFS, -1 dBTP),
tiktok_v5_unity.wav (the same stretch at the master's level), scope data for both films, QC
spectrograms and a report. The log goes to audio/logs/v5-song.json.

    python3 audio/film/song_v5.py            # everything
"""
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "audio"))
from synth import meter  # noqa: E402
from synth.effects import limiter  # noqa: E402

CHORO = os.environ.get("CHORO_RENDER", "/home/user/build/choro-render/build/choro-render")
V5 = os.environ.get("V5_OUT", "/home/user/build/v5")
MASTER = os.path.join(V5, "master_src.wav")
ND = os.path.join(V5, "stems", "nondrums.wav")
WORK = os.path.join(V5, "work", "song_v5")
QC = os.path.join(V5, "qc")
DEMOS = os.path.join(REPO, "film", "v5", "demos.json")
GRID = os.path.join(REPO, "film", "v5", "grid.json")
LOG = os.path.join(REPO, "audio", "logs", "v5-song.json")

SR = 48000
FPS = 60
SPF = SR // FPS            # 800 samples per frame
PTS = 400                  # scope points per frame
BLOCK = 128
PREROLL = 3.0              # seconds of real input before each demo's first kept sample
TAIL = 0.1                 # seconds rendered past each demo's end (crossfade room)
WORKERS = 2
BP_LO, BP_HI = 120.0, 5500.0
SCOPE_FILL = 0.60          # typical guitar trace radius on screen, as a fraction of the circle
DISPLAY_GAIN = 3.0         # film/lib/scope.js DISPLAY_GAIN (radial tanh knee 1.0)


def smp(t):
    return int(round(t * SR))


G = json.load(open(GRID))
T0, PERIOD = G["t0"], G["period_s"]
BAR = 4 * PERIOD


def bar_line(n):
    return T0 + (n - 1) * BAR


def lufs(x):
    return meter.integrated_lufs(x, SR)


def tp(x):
    return meter.true_peak(x, SR)


def db(x):
    return 20 * math.log10(max(float(x), 1e-12))


def sine_inout(u):
    u = np.clip(u, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * u)


# --------------------------------------------------------------------------------------------- curves

def knob_curve(d, param):
    """Piecewise description of a continuous knob over master time: list of (t0, t1, v0, v1) ramps
    (sine-inout) plus the value at the demo's t0. Returns f(t) -> value (vectorised)."""
    v_start = d["knobs_at_t0"][{"rate": "rate_hz", "depth": "depth_pct", "offset": "offset_deg",
                                "width": "width_pct", "color": "color_pct", "mix": "mix_pct"}[param]]
    ramps = []
    for g in d.get("gestures", []):
        if g.get("param") != param:
            continue
        if g.get("shape") == "click-steps":
            for s in g["steps"]:
                ramps.append((s["t"], s["t"] + g["ramp_s"], s["from"], s["to"]))
        else:
            ramps.append((g["t0"], g["t1"], g["from"], g["to"]))
    ramps.sort()

    def f(t):
        t = np.asarray(t, dtype=float)
        v = np.full(t.shape, float(v_start))
        for a, b, v0, v1 in ramps:
            v = np.where(t >= a, v0 + (v1 - v0) * sine_inout((t - a) / (b - a)), v)
        return v
    return f, ramps


def follows_mix(d):
    return any(g.get("param") == "trim" and g.get("shape") == "follows-mix" for g in d.get("gestures", []))


def trim_curve(d, parts):
    """Output Trim over master time: a step per part (10 ms linear ramp centred on each split line),
    times Mix/40 when the trim follows Mix."""
    mixf, _ = knob_curve(d, "mix")
    full_mix = d["knobs_at_t0"]["mix_pct"] if not follows_mix(d) else max(
        [s["to"] for g in d["gestures"] if g.get("shape") == "click-steps" for s in g["steps"]]
        + [g["to"] for g in d["gestures"] if g.get("param") == "mix" and "to" in g] + [1e-9])

    def f(t):
        t = np.asarray(t, dtype=float)
        v = np.full(t.shape, parts[0][2])
        for (a, b, tr_prev), (a2, b2, tr) in zip(parts[:-1], parts[1:]):
            u = np.clip((t - (a2 - 0.005)) / 0.01, 0, 1)
            v = v + (tr - tr_prev) * u
        if follows_mix(d):
            v = v * mixf(t) / full_mix
        return v
    return f


# --------------------------------------------------------------------------------------------- render

def render(tag, bp, d, parts, r0, r1):
    """Render bp[r0:r1] (master time; zero-padded before the first sample) through Choroboros with every
    knob explicit and all automation relative to r0. Returns (wet on master samples [smp(r0), smp(r1)), meta)."""
    i0, i1 = smp(r0), smp(r1)
    x = np.zeros((i1 - i0, 2), dtype=np.float32)
    a, b = max(i0, 0), min(i1, len(bp))
    x[a - i0:b - i0] = bp[a:b]
    p_in = os.path.join(WORK, f"{tag}_in.wav")
    p_out = os.path.join(WORK, f"{tag}.wav")
    sf.write(p_in, x, SR, subtype="FLOAT")
    k = d["knobs_at_t0"]
    ts = np.round(np.arange(r0, r1 + 1e-9, 0.01), 6)
    auto = {}
    for param, unit in (("rate", None), ("depth", "percent"), ("offset", None), ("color", "percent"),
                        ("mix", "percent"), ("width", "percent")):
        f, ramps = knob_curve(d, param)
        if not ramps:
            continue
        pts = [[round(float(t - r0), 4), round(float(v), 4)] for t, v in zip(ts, f(ts))]
        auto[param] = {"units": "percent", "points": pts} if unit else pts
    tr = trim_curve(d, parts)
    if follows_mix(d) or len(parts) > 1:
        auto["trim"] = [[round(float(t - r0), 4), round(float(v), 3)] for t, v in zip(ts, tr(ts))]
    hq0 = d["hq"]
    if "hq_switch" in d:
        auto["hq"] = [[0.0, d["hq_switch"]["from"]], [round(d["hq_switch"]["t"] - r0, 4), d["hq_switch"]["to"]]]
    args = [CHORO, "--in", p_in, "--out", p_out, "--engine", d["engine"], "--hq", str(hq0),
            "--rate", f"{k['rate_hz']}", "--depth", f"{k['depth_pct']}%", "--offset", f"{k['offset_deg']}",
            "--width", f"{k['width_pct']}%", "--color", f"{k['color_pct']}%", "--mix", f"{k['mix_pct']}%",
            "--trim", f"{float(tr(np.array([r0]))[0]):.3f}",
            "--block", str(BLOCK), "--preroll", "0", "--tail", "0", "--quiet", "--meta", p_out.replace(".wav", ".json")]
    if auto:
        ap = p_out.replace(".wav", ".automation.json")
        json.dump(auto, open(ap, "w"))
        args += ["--automation", ap]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    y, sr = sf.read(p_out, dtype="float64", always_2d=True)
    assert sr == SR and len(y) == len(x), (sr, len(y), len(x))
    meta = json.load(open(p_out.replace(".wav", ".json")))
    cmd = " ".join(os.path.basename(a) if a.startswith(WORK) else a for a in args[1:])
    return y, {"cmd": cmd, "latencySamples": meta.get("latencySamples"), "core": meta.get("core"),
               "knobsAtEnd": meta.get("knobsAtEnd"), "outPeakDb": round(meta.get("outPeakDb", 0), 2),
               "automated": sorted(auto)}


# --------------------------------------------------------------------------------------------- band limit, peaks

DIFF_LP_HZ = 6000.0
_LP = signal.firwin(1023, DIFF_LP_HZ, window=("kaiser", 11.5), fs=SR)   # linear phase, centred => zero phase
CEIL_DBTP = -1.0


def band_limit(x):
    """Zero-phase low-pass of the Choroboros change at 6 kHz (stopband > 100 dB by 6.5 kHz), so out - master
    stays inside the guitar band even where the engines' own colour adds a little air."""
    return signal.fftconvolve(x, _LP[:, None], mode="same", axes=0)


def peak_control(m, D):
    """out = m + g * D with g <= 1 the smallest pull-back that keeps out at or under -1 dBTP. g = 1 wherever
    the ceiling is not threatened (the usual case), so the change is untouched there."""
    from synth.effects import _forward_min, _release
    info = {"ceiling_dbtp": CEIL_DBTP}
    out = m + D
    tp0 = tp(out)
    info["true_peak_before_dbtp"] = round(tp0, 2)
    if tp0 <= CEIL_DBTP:
        info["applied"] = False
        return D, info
    c = 10 ** ((CEIL_DBTP - 0.1) / 20)
    L = smp(0.003)
    rel = math.exp(-1 / (0.060 * SR))
    for p in range(8):
        req = np.ones(len(m))
        y = m + D
        over = np.abs(y) > c
        idx = np.where(over.any(axis=1))[0]
        for ch in range(2):
            i = idx
            mm, dd = m[i, ch], D[i, ch]
            with np.errstate(divide="ignore", invalid="ignore"):
                g_hi = np.where(dd > 0, (c - mm) / dd, (-c - mm) / dd)
            g_hi = np.where(np.abs(mm + dd) > c, np.clip(g_hi, 0, 1), 1.0)
            req[i] = np.minimum(req[i], g_hi)
        h = _forward_min(req, L)
        h = _release(h, rel)
        g = np.convolve(np.concatenate([np.full(L - 1, h[0]), h]), np.ones(L) / L, mode="valid")
        g = np.minimum(g, 1.0)
        g[g > 1 - 1e-12] = 1.0
        D2 = D * g[:, None]
        t2 = tp(m + D2)
        if t2 <= CEIL_DBTP + 0.005:
            break
        c *= 10 ** ((CEIL_DBTP - t2 - 0.05) / 20)
    info.update({"applied": True, "passes": p + 1, "true_peak_after_dbtp": round(t2, 2),
                 "samples_pulled_back": int((g < 1).sum()), "seconds_pulled_back": round(float((g < 1).sum()) / SR, 3),
                 "min_change_gain": round(float(g.min()), 3),
                 "seconds_below_0.9": round(float((g < 0.9).sum()) / SR, 3),
                 "seconds_below_0.75": round(float((g < 0.75).sum()) / SR, 3),
                 "seconds_below_0.5": round(float((g < 0.5).sum()) / SR, 3),
                 "mean_gain_where_pulled": round(float(g[g < 1].mean()), 3) if (g < 1).any() else 1.0,
                 "rule": "g <= 1 on the Choroboros change only (3 ms look-ahead, 60 ms release); the master under it is never touched"})
    return D2, info


# --------------------------------------------------------------------------------------------- spans

def on_spans(d, t_lo=None):
    """The demo's ON spans (full mix, minus bypass spans, from the first full-Mix moment for Mix turns)."""
    a = d["t0"]
    if follows_mix(d) or any(g.get("param") == "mix" for g in d.get("gestures", [])):
        _, ramps = knob_curve(d, "mix")
        a = max(b for _, b, _, _ in ramps)
    spans = [(a, d["t1"])]
    for bp_ in d.get("bypass", []):
        out = []
        for s, e in spans:
            if bp_["t1"] <= s or bp_["t0"] >= e:
                out.append((s, e))
                continue
            if bp_["t0"] > s:
                out.append((s, bp_["t0"]))
            if bp_["t1"] < e:
                out.append((bp_["t1"], e))
        spans = out
    return spans


def full_bars(spans):
    out = []
    for n in range(1, 105):
        a, b = bar_line(n), bar_line(n + 1)
        if any(s <= a + 1e-3 and b <= e + 1e-3 for s, e in spans):
            out.append((n, a, b))
    return out


def cat(x, spans, t_origin):
    return np.concatenate([x[smp(s - t_origin):smp(e - t_origin)] for s, e in spans])


# --------------------------------------------------------------------------------------------- build

class Film:
    def __init__(self, name, spec, master, nd, bp):
        self.name = name
        self.spec = spec
        self.t_a, self.t_b = spec["span"]
        self.ia, self.ib = smp(self.t_a), smp(self.t_b)
        self.m = master[self.ia:self.ib]
        self.nd = nd[self.ia:self.ib]
        self.bp = bp[self.ia:self.ib]
        self.demos = spec["demos"]
        self.log = {"demos": {}, "joins": []}

    def loc(self, t):
        return min(max(smp(t) - self.ia, 0), self.ib - self.ia)

    # processed signal of demo d over [ra, rb) master time, given its wet render
    def proc(self, wet, ra):
        i = smp(ra) - self.ia
        n = len(wet)
        lo, hi = max(i, 0), min(i + n, len(self.m))
        P = np.full((len(self.m), 2), np.nan)
        P[lo:hi] = self.m[lo:hi] - self.bp[lo:hi] + wet[lo - i:hi - i]
        return P


def solve_trim(m, bp, y0, spans, t_origin, gain_curve=None):
    """Constant trim (dB, rounded 0.1) so LUFS(master - bp + g*y0) == LUFS(master) over spans."""
    M = cat(m, spans, t_origin)
    B = cat(bp, spans, t_origin)
    Y = cat(y0, spans, t_origin)
    target = lufs(M)
    lo, hi = -12.0, 6.0
    for _ in range(30):
        mid = (lo + hi) / 2
        L = lufs(M - B + Y * 10 ** (mid / 20))
        if L > target:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 1), target


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(QC, exist_ok=True)
    spec = json.load(open(DEMOS))
    master, sr = sf.read(MASTER, dtype="float64", always_2d=True)
    assert sr == SR
    nd, sr2 = sf.read(ND, dtype="float64", always_2d=True)
    assert sr2 == SR and len(nd) == len(master)
    drums = master - nd
    sos = signal.butter(4, [BP_LO, BP_HI], btype="bandpass", fs=SR, output="sos")
    bp = signal.sosfiltfilt(sos, nd, axis=0).astype(np.float32).astype(np.float64)  # what the renderer is fed
    log = {"version": "v5", "spec": "film/v5/demos.json + film/v5/TREATMENT.md s3, s7", "sr": SR,
           "method": {"formula": "out = master - BP(nd) + choro_trim(BP(nd))",
                      "bp": f"Butterworth band-pass {BP_LO:.0f} Hz to {BP_HI:.0f} Hz, 4th order per edge, sosfiltfilt (zero phase)",
                      "preroll_s": PREROLL, "tail_s": TAIL, "block": BLOCK, "renderer": "choro-render (called by path)",
                      "limiter_on_song": "none"},
           "null_tests": {}, "films": {}}

    # ---------------------------------------------------------------- null tests (first)
    nt = {}
    # 1. renderer at Mix 0 vs its input, one per engine/hq, over 6 s of the band with 3 s of pre-roll
    seg0, seg1 = 60.0, 69.0
    for eng, hq in (("green", 0), ("blue", 0), ("red", 0), ("red", 1), ("purple", 1), ("black", 1)):
        d = {"engine": eng, "hq": hq, "knobs_at_t0": {"rate_hz": 0.62, "depth_pct": 30, "offset_deg": 90,
                                                         "width_pct": 100, "color_pct": 40, "mix_pct": 0},
             "gestures": []}
        y, _ = render(f"null_{eng}{hq}", bp, d, [(seg0, seg1, 0.0)], seg0, seg1)
        x = bp[smp(seg0):smp(seg1)]
        k = smp(PREROLL)
        res = np.abs(y[k:] - x[k:]).max()
        nt[f"mix0_{eng}_hq{hq}"] = {"max_abs_residual": float(res), "dbfs": round(db(res), 1),
                                    "first_10ms_after_start_dbfs": round(db(np.abs(y[:480] - x[:480]).max()), 1),
                                    "pass": bool(db(res) < -100)}
    # 2. the split recombined without processing vs the master (the BP path at unity)
    rec = master - bp + bp
    nt["split_recombined_vs_master"] = {"max_abs_diff": float(np.abs(rec - master).max()),
                                        "dbfs": round(db(np.abs(rec - master).max()), 1),
                                        "pass": bool(db(np.abs(rec - master).max()) < -100)}
    # 3. fitted drums + non-drum part = master
    nt["drums_plus_nondrums_vs_master"] = {"max_abs_diff": float(np.abs(drums + nd - master).max())}
    # 4. the band-pass alone (what the BP path replaces) and a complementary check: master - bp is the
    #    exact complement of the fed band, so the path needs no crossover.
    log["null_tests"] = nt
    print("null tests:", json.dumps({k: v.get("dbfs", v.get("max_abs_diff")) for k, v in nt.items()}))
    path_ok = all(v.get("pass", True) for v in nt.values())
    log["method"]["path"] = "BP" if path_ok else "fallback_parallel"

    # ---------------------------------------------------------------- films
    results = {}
    for fname in ("main", "tiktok"):
        results[fname] = build_film(fname, spec["films"][fname], master, nd, bp, drums, log)

    write_outputs(results, master, log)
    json.dump(log, open(LOG, "w"), indent=1, default=float)
    print("log:", LOG)


def build_film(fname, fspec, master, nd, bp, drums, log):
    F = Film(fname, fspec, master, nd, bp)
    flog = {"span": fspec["span"], "demos": {}, "joins": [], "renders": {}}
    demos = fspec["demos"]
    ranges = [(max(d["t0"] - PREROLL, -PREROLL), d["t1"] + TAIL) for d in demos]

    # pass 1: trim 0 renders (in parallel)
    with ThreadPoolExecutor(WORKERS) as ex:
        y0s = list(ex.map(lambda k: render(f"{fname}_{demos[k]['id']}_p1", bp, demos[k],
                                           [(demos[k]["t0"], demos[k]["t1"], 0.0)], ranges[k][0], ranges[k][1])[0],
                          range(len(demos))))

    def full(y, r0):
        """a render placed on the film timeline (NaN outside)"""
        P = np.full((len(F.m), 2), np.nan)
        i = smp(r0) - F.ia
        lo, hi = max(i, 0), min(i + len(y), len(F.m))
        P[lo:hi] = y[lo - i:hi - i]
        return P

    # level match: per demo trim, split at failing bars, true-peak rule
    trims = {}
    green_trim = None
    order = sorted(range(len(demos)), key=lambda k: follows_mix(demos[k]) and demos[k]["t0"] > F.t_a + 1)
    for k in order:
        d = demos[k]
        y0 = full(y0s[k], ranges[k][0])
        spans = on_spans(d)
        spans = [(max(s, F.t_a), min(e, F.t_b)) for s, e in spans if min(e, F.t_b) - max(s, F.t_a) > 0.05]
        span_len = sum(e - s for s, e in spans)
        dl = {"on_spans": [[round(s, 4), round(e, 4)] for s, e in spans]}
        if span_len < 0.4 and follows_mix(d) and green_trim is not None:
            parts = [(d["t0"], d["t1"], green_trim)]
            dl["trim_rule"] = f"the ON span is {span_len:.2f} s (too short to gate); Trim = the same Green settings' measured trim"
        else:
            tr, _ = solve_trim(F.m, F.bp, y0, spans, F.t_a)
            parts = [(d["t0"], d["t1"], tr)]
            for _it in range(8):
                bad = None
                new_parts = []
                for (pa, pb, ptr) in parts:
                    psp = [(max(s, pa), min(e, pb)) for s, e in spans if min(e, pb) > max(s, pa)]
                    fb = full_bars(psp)
                    for n, a, b in fb:
                        o = F.m[F.loc(a):F.loc(b)] - F.bp[F.loc(a):F.loc(b)] + y0[F.loc(a):F.loc(b)] * 10 ** (ptr / 20)
                        dlu = lufs(o) - lufs(F.m[F.loc(a):F.loc(b)])
                        if abs(dlu) > 0.45 and len(fb) > 1:
                            bad = (pa, pb, n, a, b)
                            break
                    if bad:
                        break
                if not bad:
                    break
                pa, pb, n, a, b = bad
                cut = a if a > pa + 0.5 else b
                new_parts = []
                for (qa, qb, qtr) in parts:
                    if (qa, qb) == (pa, pb):
                        for sa, sb in ((qa, cut), (cut, qb)):
                            psp = [(max(s, sa), min(e, sb)) for s, e in spans if min(e, sb) > max(s, sa)]
                            t2, _ = solve_trim(F.m, F.bp, y0, psp, F.t_a) if psp else (qtr, 0)
                            new_parts.append((sa, sb, t2))
                    else:
                        new_parts.append((qa, qb, qtr))
                parts = new_parts
            # the demo as a whole within +-0.2 LU: after a split, shift every part by one common offset
            # when the integrated (gated) measure of the whole demo drifts, as long as every bar stays inside +-0.45
            if len(parts) > 1:
                def demo_delta(pp):
                    o = F.m.copy()
                    for (pa, pb, ptr) in pp:
                        sl = slice(F.loc(pa), F.loc(pb))
                        o[sl] = F.m[sl] - F.bp[sl] + y0[sl] * 10 ** (ptr / 20)
                    fe = min(F.spec["ending"]["from"], F.t_b)
                    sp2 = [(s_, min(e_, fe)) for s_, e_ in spans if min(e_, fe) > s_]
                    return lufs(cat(o, sp2, F.t_a)) - lufs(cat(F.m, sp2, F.t_a)), o, sp2
                dd, o, sp2 = demo_delta(parts)
                if abs(dd) > 0.12:
                    cand = [(pa, pb, round(ptr - dd, 1)) for pa, pb, ptr in parts]
                    dd2, o2, _ = demo_delta(cand)
                    worst = max((abs(lufs(o2[F.loc(a):F.loc(b)]) - lufs(F.m[F.loc(a):F.loc(b)])) for _, a, b in full_bars(sp2)), default=0.0)
                    if abs(dd2) < abs(dd) and worst <= 0.45:
                        parts = cand
                        dl["demo_shift_db"] = round(-dd, 1)
        trims[k] = parts
        if d["engine"] == "green" and not follows_mix(d) and d["knobs_at_t0"]["mix_pct"] == 40:
            green_trim = green_trim if green_trim is not None else parts[0][2]
        if follows_mix(d) and green_trim is None:
            green_trim = parts[0][2]
        dl["trim_parts"] = [{"t0": round(a, 4), "t1": round(b, 4), "trim_db": t} for a, b, t in parts]
        flog["demos"][d["id"]] = dl

    # pass 2: final renders with the plug-in's own Output Trim
    with ThreadPoolExecutor(WORKERS) as ex:
        finals = list(ex.map(lambda k: render(f"{fname}_{demos[k]['id']}", bp, demos[k], trims[k],
                                              ranges[k][0], ranges[k][1]), range(len(demos))))
    wets = []
    for k, d in enumerate(demos):
        y, meta = finals[k]
        wet = full(y, ranges[k][0])
        ok = np.isfinite(wet[:, 0])
        dk = np.zeros_like(wet)
        # the Choroboros change, band-limited (zero-phase FIR, see DIFF_LP): what the demo adds to the master
        dk[ok] = band_limit(wet[ok] - F.bp[ok])
        dk[~ok] = np.nan
        wets.append(dk)
        # plausibility: the trimmed render vs the trim-0 render times the trim gain (constant-trim demos)
        if len(trims[k]) == 1 and not follows_mix(d):
            y0 = y0s[k]
            g = 10 ** (trims[k][0][2] / 20)
            kk = smp(PREROLL)
            meta["trim_is_output_gain_max_dev_dbfs"] = round(db(np.abs(y[kk:] - g * y0[kk:]).max()), 1)
        flog["renders"][d["id"]] = meta
        flog["demos"][d["id"]].update({
            "engine": d["engine"], "core": d["core"], "hq": d["hq"], "knobs_at_t0": d["knobs_at_t0"],
            "gestures": d.get("gestures", []), "hq_switch": d.get("hq_switch"), "bypass": d.get("bypass", []),
            "render_span": [round(ranges[k][0], 4), round(ranges[k][1], 4)],
            "preroll": "3.0 s of real input (zeros before the first sample of the song)"})

    # ---------------------------------------------------------------- timeline and joins
    # segments: (t_start, source) where source is ("M",) or ("D", k); transitions carry xfade windows
    segs = []   # (t_switch, src, (w0, w1), kind)
    for k, d in enumerate(demos):
        si = d["switch_in"]
        kind = si["kind"]
        t = si.get("t", d["t0"])
        if kind == "start":
            segs.append((F.t_a, ("D", k), None, "start"))
        elif kind == "on-hit":
            segs.append((t, ("D", k), (t - si["xfade_ms"] / 1000, t), "on-hit 20 ms equal-power ending at the hit"))
        elif kind == "bar-line":
            segs.append((t, ("D", k), (t - si["xfade_ms"] / 2000, t + si["xfade_ms"] / 2000), "bar-line 20 ms equal-power centred"))
        for bpz in d.get("bypass", []):
            segs.append((bpz["t0"], ("M",), (bpz["t0"] - 0.010, bpz["t0"]), "bypass toggle 10 ms, midpoint 5 ms before the hit"))
            segs.append((bpz["t1"], ("D", k), (bpz["t1"] - 0.010, bpz["t1"]), "bypass toggle 10 ms, midpoint 5 ms before the hit"))
    for bpz in fspec.get("bypass_spans", []):
        segs.append((bpz["t0"], ("M",), (bpz["t0"] - 0.010, bpz["t0"]), "bypass span 10 ms, midpoint 5 ms before the hit"))
        # the demo that resumes at bpz.t1 switches in with the bypass toggle rule (10 ms)
        for i, s in enumerate(segs):
            if s[0] == bpz["t1"] or (s[1][0] == "D" and abs(demos[s[1][1]]["t0"] - bpz["t1"]) < 1e-6):
                segs[i] = (bpz["t1"], s[1], (bpz["t1"] - 0.010, bpz["t1"]), "bypass span end 10 ms, midpoint 5 ms before the hit")
    segs.sort(key=lambda s: s[0])

    def diff_of(src):
        return None if src[0] == "M" else wets[src[1]]

    # out = master + D, where D is the Choroboros change of the demo that is on. Joins crossfade D
    # (equal-power, the two engines' changes are uncorrelated); the master under it (drums, bass, air)
    # is never faded, so a join can neither dip nor bump the drums.
    D = np.zeros_like(F.m)
    state = np.zeros(len(F.m), dtype=np.int16) - 1   # -1 master, k demo (for the scope and QC)
    cur = None
    for i, (t, src, win, kind) in enumerate(segs):
        t_next = segs[i + 1][2][0] if i + 1 < len(segs) and segs[i + 1][2] else (segs[i + 1][0] if i + 1 < len(segs) else F.t_b)
        a = F.loc(t if win is None else win[1])
        b = min(F.loc(t_next), len(F.m))
        dn = diff_of(src)
        D[a:b] = 0.0 if dn is None else dn[a:b]
        state[a:b] = -1 if src[0] == "M" else src[1]
        if win is not None and cur is not None:
            w0, w1 = F.loc(win[0]), F.loc(win[1])
            u = ((np.arange(w0, w1) - w0 + 0.5) / (w1 - w0) * (np.pi / 2))[:, None]
            dp = diff_of(cur)
            D[w0:w1] = (0.0 if dp is None else dp[w0:w1] * np.cos(u)) + (0.0 if dn is None else dn[w0:w1] * np.sin(u))
            state[w0:w1] = -2                     # a join window
            flog["joins"].append({"t": round(t, 4), "window": [round(win[0], 4), round(win[1], 4)], "kind": kind,
                                  "from": "master" if cur[0] == "M" else demos[cur[1]]["id"],
                                  "to": "master" if src[0] == "M" else demos[src[1]]["id"]})
        cur = src
    assert np.isfinite(D).all(), "a render does not cover its span"
    # peak control at -1 dBTP, only where needed: pull the Choroboros change back towards the master
    # (whose own true peak is under the ceiling) around the few peaks that pass it. Drums untouched.
    D, pk = peak_control(F.m, D)
    flog["peak_control"] = pk
    out = F.m + D
    master_state = state == -1
    out[master_state] = F.m[master_state]          # outside the demos and in bypass: the master, bit for bit
    band_heard = F.bp + D

    # ---------------------------------------------------------------- ending
    pre_fade = out.copy()
    fade = np.ones(len(out))
    end = fspec["ending"]
    fa, fb = F.loc(end["from"]), F.loc(end["to"])
    u = (np.arange(fa, fb) - fa + 0.5) / (fb - fa)
    fade[fa:fb] = np.cos(u * np.pi / 2)
    fade[fb:] = 0.0
    fade_in = None
    if fname == "tiktok":
        n_in = smp(0.001)
        fade_in = n_in
        fade[:n_in] *= np.sin((np.arange(n_in) + 0.5) / n_in * np.pi / 2)
    out = out * fade[:, None]
    flog["ending"] = {"type": "equal-power fade (cos)", "from": end["from"], "to": end["to"],
                      "then": f"digital silence to {F.t_b}", "fade_in_samples": fade_in}

    return {"F": F, "out": out, "pre_fade": pre_fade, "fade": fade, "band_heard": band_heard, "state": state,
            "wets": wets, "trims": trims, "log": flog, "drums": drums[F.ia:F.ib], "demos": demos}


# ------------------------------------------------------------------------------------------- outputs / QC

def env(x, hop=240):
    """5 ms RMS envelope of a (mono-summed) signal."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    n = len(m) // hop
    return np.sqrt((m[:n * hop].reshape(n, hop) ** 2).mean(axis=1))


def spectro_png(path, title, pairs, sr=SR):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pairs = list(pairs) + [("CHANGE (out - master), +20 dB", (pairs[1][1] - pairs[0][1]) * 10.0)]
    fig, axs = plt.subplots(2, 3, figsize=(20, 7), sharex=True, sharey=True)
    for c, (lab, x) in enumerate(pairs):
        for r, (nm, s) in enumerate((("MID (L+R)/2", (x[:, 0] + x[:, 1]) / 2), ("SIDE (L-R)/2", (x[:, 0] - x[:, 1]) / 2))):
            f, t, S = signal.spectrogram(s, sr, nperseg=4096, noverlap=4096 - 512, window="hann")
            Sdb = 10 * np.log10(S + 1e-14)
            ax = axs[r, c]
            ax.pcolormesh(t, f, Sdb, vmin=-130, vmax=-40, shading="auto", cmap="magma")
            ax.set_yscale("log")
            ax.set_ylim(80, 8000)
            ax.set_title(f"{lab}: {nm}", fontsize=10)
            if c == 0:
                ax.set_ylabel("Hz")
            if r == 1:
                ax.set_xlabel("s from demo start")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def scope_frames(x, gain, nframes):
    n = nframes * SPF
    w = np.zeros((n, 2))
    w[:min(n, len(x))] = x[:n]
    mid = (w[:, 0] + w[:, 1]) / 2
    side = (w[:, 0] - w[:, 1]) / 2
    mid = mid.reshape(-1, 2).mean(axis=1) * gain
    side = side.reshape(-1, 2).mean(axis=1) * gain
    buf = np.empty((len(mid), 2), dtype=np.int16)
    buf[:, 0] = np.round(np.clip(mid, -1, 1) * 32767)
    buf[:, 1] = np.round(np.clip(side, -1, 1) * 32767)
    return buf


def write_outputs(R, master, log):
    import shutil
    main, tt = R["main"], R["tiktok"]
    report = {"A1": {}, "A2": log["null_tests"], "A3": {}, "A4": {}, "A5": {}, "A6": {}, "musicality": {}}

    for fname, res in (("main", main), ("tiktok", tt)):
        F, out, pre, st = res["F"], res["out"], res["pre_fade"], res["state"]
        flog = res["log"]
        demos = res["demos"]
        n_expected = {"main": 4378368, "tiktok": 720000}[fname]
        assert len(out) == n_expected, (fname, len(out))
        a1 = {"samples": len(out), "expected": n_expected}
        # bit identity where the state is master (outside demos, bypass spans), away from the fades
        fade = res["fade"]
        mask = (st == -1) & (fade == 1.0)
        # exclude the crossfade windows (state was set to the incoming side inside windows)
        for j in flog["joins"]:
            mask[F.loc(j["window"][0]):F.loc(j["window"][1])] = False
        diff = np.abs(out[mask] - F.m[mask]).max() if mask.any() else 0.0
        a1["master_state_samples"] = int(mask.sum())
        a1["master_state_seconds"] = round(mask.sum() / SR, 3)
        a1["max_abs_diff_vs_master_float"] = float(diff)
        a1["bit_identical_float"] = bool(diff == 0.0)
        # lag per bar (cross-correlation of out vs master, +-5 ms)
        lags = []
        for n in range(1, 105):
            a, b = bar_line(n), bar_line(n + 1)
            if a < F.t_a or b > min(F.t_b, F.spec["ending"]["from"]):
                continue
            o = out[F.loc(a):F.loc(b)].mean(axis=1)
            m = F.m[F.loc(a):F.loc(b)].mean(axis=1)
            c = signal.correlate(o, m, mode="full", method="fft")
            mid = len(m) - 1
            wnd = c[mid - 240:mid + 241]
            lags.append((n, int(np.argmax(wnd)) - 240))
        a1["xcorr_lag_per_bar_samples"] = {"bars": len(lags), "max_abs_lag": max(abs(l) for _, l in lags) if lags else None,
                                           "nonzero": [[n, l] for n, l in lags if l != 0]}
        report["A1"][fname] = a1

        # A3 band: out - master above 6.5 kHz (pre-fade), measured in the spectrum (Welch, Blackman-Harris,
        # 8192 points) so that the strong band content just under 6.5 kHz cannot leak into the measure
        dff = pre - F.m
        f_, P_ = signal.welch(dff, SR, window="blackmanharris", nperseg=8192, axis=0, scaling="spectrum")
        hi = f_ >= 6500
        p_hi = P_[hi].sum(axis=0)          # mean-square power above 6.5 kHz per channel
        p_all = P_.sum(axis=0)
        report["A3"][fname] = {"rms_dbfs_above_6k5": round(10 * np.log10(max(p_hi.max(), 1e-30)), 1),
                               "rms_dbfs_diff_fullband": round(10 * np.log10(max(p_all.max(), 1e-30)), 1),
                               "method": "Welch power spectrum of out - master over the whole film (before the ending fade), Blackman-Harris 8192; energy summed above 6.5 kHz, worst channel"}
        report["A3"][fname]["pass_rms_below_-90"] = bool(report["A3"][fname]["rms_dbfs_above_6k5"] < -90)

        # A4 drums untouched: envelope correlation of (out - master) with the fitted drums
        on = st != -1
        e_d = env(dff * on[:, None])
        e_dr = env(res["drums"])
        e_m = env(F.m)
        n = min(len(e_d), len(e_dr))
        onm = env(on[:, None].astype(float) * np.ones((1, 2)))[:n] > 0.5
        c_env = float(np.corrcoef(e_d[:n][onm], e_dr[:n][onm])[0, 1])
        # transient (onset) envelopes: half-wave rectified first difference of the log envelope
        def onset(e):
            le = np.log10(e + 1e-6)
            return np.maximum(np.diff(le, prepend=le[0]), 0)
        c_on = float(np.corrcoef(onset(e_d[:n])[onm], onset(e_dr[:n])[onm])[0, 1])
        c_ref = float(np.corrcoef(onset(e_m[:n])[onm], onset(e_dr[:n])[onm])[0, 1])
        e_b = env(F.bp)
        c_band = float(np.corrcoef(e_b[:n][onm], e_dr[:n][onm])[0, 1])
        report["A4"][fname] = {"envelope_corr": round(c_env, 4), "onset_envelope_corr": round(c_on, 4),
                               "reference_master_vs_drums_onset_corr": round(c_ref, 4),
                               "reference_dry_band_vs_drums_envelope_corr": round(c_band, 4),
                               "note": "envelope_corr: 5 ms RMS envelopes of (out - master) and the fitted drums over the Choroboros-on time; onset_envelope_corr: their half-wave rectified log-envelope differences (drum transients). The dry guitar band itself correlates with the drums at reference_dry_band_vs_drums_envelope_corr, because the band plays with them",
                               "pass_onset_below_0.05": c_on < 0.05, "pass_envelope_below_0.05": c_env < 0.05}

        # A5 level per bar and per demo, true peak per bar; A6 mono; musicality per demo
        measured = {}
        for k, d in enumerate(demos):
            dl = flog["demos"][d["id"]]
            spans = [(max(s, F.t_a), min(e, F.t_b)) for s, e in on_spans(d) if min(e, F.t_b) - max(s, F.t_a) > 0.05]
            # exclude the final fade from level judgement
            fe = F.spec["ending"]["from"]
            spans_l = [(s, min(e, fe)) for s, e in spans if min(e, fe) - s > 0.05]
            bars = []
            for n_, a, b in full_bars(spans_l):
                sl = slice(F.loc(a), F.loc(b))
                bars.append({"bar": n_, "t0": round(a, 3), "delta_lu": round(lufs(out[sl]) - lufs(F.m[sl]), 3),
                             "tp_dbtp": round(tp(out[sl]), 2), "tp_over_master_db": round(tp(out[sl]) - tp(F.m[sl]), 2)})
            partial = []
            for s, e in spans_l:
                for n_ in range(1, 105):
                    a, b = max(s, bar_line(n_)), min(e, bar_line(n_ + 1))
                    if b - a > 0.45 and not any(x["bar"] == n_ for x in bars):
                        sl = slice(F.loc(a), F.loc(b))
                        partial.append({"bar": n_, "span": [round(a, 3), round(b, 3)],
                                        "delta_lu": round(lufs(out[sl]) - lufs(F.m[sl]), 3),
                                        "tp_dbtp": round(tp(out[sl]), 2), "tp_over_master_db": round(tp(out[sl]) - tp(F.m[sl]), 2)})
            if spans_l and sum(e - s for s, e in spans_l) >= 0.4:
                O = cat(out, spans_l, F.t_a)
                Mm = cat(F.m, spans_l, F.t_a)
                demo_delta = round(lufs(O) - lufs(Mm), 3)
                demo_tp = round(tp(O) - tp(Mm), 2)
            else:
                demo_delta, demo_tp = None, None
            bar_pass = all(abs(x["delta_lu"]) <= 0.5 for x in bars)
            tp_pass = all(x["tp_dbtp"] <= CEIL_DBTP + 0.01 for x in bars + partial)
            tp_rel_pass = all(x["tp_over_master_db"] <= 0.1 for x in bars + partial)
            demo_pass = demo_delta is not None and abs(demo_delta) <= 0.2
            # mono (A6): processed band vs dry band over the ON span
            W = cat(res["band_heard"], spans_l or spans, F.t_a)
            D = cat(F.bp, spans_l or spans, F.t_a)
            def fold_loss(x):
                mono = np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1)
                return lufs(x) - lufs(mono)
            def corr(x):
                return float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])
            loss_w, loss_d = fold_loss(W), fold_loss(D)
            mono = {"fold_loss_wet_lu": round(loss_w, 3), "fold_loss_dry_lu": round(loss_d, 3),
                    "extra_loss_lu": round(loss_w - loss_d, 3), "lr_corr_wet": round(corr(W), 3),
                    "lr_corr_dry": round(corr(D), 3)}
            mono["pass"] = (loss_w - loss_d) <= 0.6 and corr(W) > 0.1
            report["A6"].setdefault(fname, {})[d["id"]] = mono
            lm = {"trim_db": dl["trim_parts"][0]["trim_db"] if len(dl["trim_parts"]) == 1 else None,
                  "trim_parts": dl["trim_parts"], "trim_rule": dl.get("trim_rule", "-(LUFS(out) - LUFS(master)) over the ON span, 0.1 dB"),
                  "on_spans": dl["on_spans"], "bars": bars, "partial_bars": partial,
                  "demo_delta_lu": demo_delta, "demo_tp_over_master_db": demo_tp,
                  "bars_pass": bar_pass, "demo_pass": demo_pass if demo_delta is not None else None,
                  "tp_pass": tp_pass, "tp_rule": "every bar at or under -1 dBTP (the delivery ceiling)",
                  "tp_within_master_plus_0.1_every_bar": tp_rel_pass,
                  "mono": mono}
            lm["level_matched"] = bool(bar_pass and (demo_pass or (demo_delta is None and follows_mix(d))) and tp_pass)
            measured[d["id"]] = lm
            dl["level_match"] = {kk: lm[kk] for kk in ("bars", "partial_bars", "demo_delta_lu", "demo_tp_over_master_db",
                                                      "bars_pass", "demo_pass", "tp_pass", "tp_within_master_plus_0.1_every_bar", "level_matched")}
            dl["mono"] = mono
            # musicality: side/mid energy, spectrogram
            a_, b_ = max(d["t0"], F.t_a), min(d["t1"], F.t_b)
            sl = slice(F.loc(a_), F.loc(b_))
            def sm(x):
                mid = (x[:, 0] + x[:, 1]) / 2
                side = (x[:, 0] - x[:, 1]) / 2
                return round(10 * np.log10((side ** 2).sum() / max((mid ** 2).sum(), 1e-20)), 2)
            mus = {"side_mid_db_master": sm(F.m[sl]), "side_mid_db_out": sm(pre[sl]),
                   "side_mid_db_band_dry": sm(F.bp[sl]), "side_mid_db_band_wet": sm(res["band_heard"][sl])}
            png = os.path.join(QC, f"{fname}_{d['id']}.png")
            spectro_png(png, f"{fname} {d['id']} ({d['engine']} {d['core']}), {a_:.3f}-{b_:.3f} s master time; "
                        f"side/mid {mus['side_mid_db_master']} -> {mus['side_mid_db_out']} dB",
                        [("BEFORE (master)", F.m[sl]), ("AFTER (out)", pre[sl])])
            mus["spectrogram"] = png
            report["musicality"].setdefault(fname, {})[d["id"]] = mus
            dl["musicality"] = mus
        report["A5"][fname] = {k: {"bars_pass": v["bars_pass"], "demo_pass": v["demo_pass"], "tp_pass": v["tp_pass"],
                                   "worst_bar_lu": max([abs(b["delta_lu"]) for b in v["bars"]], default=None),
                                   "demo_delta_lu": v["demo_delta_lu"]} for k, v in measured.items()}

        # joins: level jump and clicks
        dff_full = out - F.m
        for j in flog["joins"]:
            w0, w1 = F.loc(j["window"][0]), F.loc(j["window"][1])
            n4 = smp(0.4)
            def dl_(a, b):
                return lufs(out[a:b]) - lufs(F.m[a:b])
            before = dl_(max(w0 - n4, 0), w0)
            after = dl_(w1, min(w1 + n4, len(out)))
            j["level_jump_lu"] = round(abs(after - before), 3)
            nb = smp(BAR)
            j["level_jump_lu_bar_windows"] = round(abs(dl_(w1, min(w1 + nb, len(out))) - dl_(max(w0 - nb, 0), w0)), 3)
            # the same 400 ms measure inside the incoming demo (0.8 s and 1.2 s after the join): the chorus's own
            # momentary loudness movement, for scale
            base = []
            for off in (0.8, 1.2):
                c0 = w1 + smp(off)
                if c0 + n4 < len(out) and st[c0 - n4:c0 + n4].min() >= 0:
                    base.append(round(abs(dl_(c0, c0 + n4) - dl_(c0 - n4, c0)), 3))
            j["same_measure_inside_demo_lu"] = base
            s0, s1 = max(w0 - 240, 1), min(w1 + 240, len(out))
            j["max_step_out"] = round(float(np.abs(np.diff(out[s0 - 1:s1], axis=0)).max()), 5)
            j["max_step_master"] = round(float(np.abs(np.diff(F.m[s0 - 1:s1], axis=0)).max()), 5)
            j["max_step_out_minus_master"] = round(float(np.abs(np.diff(dff_full[s0 - 1:s1], axis=0)).max()), 6)
            ref0, ref1 = min(w1 + 240, len(out) - 1), min(w1 + smp(0.2), len(out))
            j["ref_step_out_minus_master_next_200ms"] = round(float(np.abs(np.diff(dff_full[ref0 - 1:ref1], axis=0)).max()), 6) if ref1 - ref0 > 2 else None
        report.setdefault("joins", {})[fname] = {"max_level_jump_lu": max(j["level_jump_lu"] for j in flog["joins"]),
                                                 "all_under_0.5": all(j["level_jump_lu"] <= 0.5 for j in flog["joins"]),
                                                 "joins": flog["joins"]}
        res["measured"] = measured

    # ---------------------------------------------------------------- write audio
    mo = main["out"]
    tt_u = tt["out"]
    sf.write(os.path.join(V5, "master_v5.wav"), mo.astype(np.float64), SR, subtype="PCM_24")
    L_t = lufs(tt_u)
    g = 10 ** ((-14.0 - L_t) / 20)
    tn = tt_u * g
    lim_info = None
    if tp(tn) > -1.0:
        tn, lim_info = limiter(tn, ceiling_dbtp=-1.0, sr=SR)
    sf.write(os.path.join(V5, "tiktok_v5.wav"), tn, SR, subtype="PCM_24")
    sf.write(os.path.join(V5, "tiktok_v5_unity.wav"), tt_u, SR, subtype="PCM_24")
    # proof after PCM 24 quantisation: the written file vs the master written the same way
    mw, _ = sf.read(os.path.join(V5, "master_v5.wav"), dtype="float64", always_2d=True)
    Fm = main["F"]
    tmp = os.path.join(WORK, "master_ref_pcm24.wav")
    sf.write(tmp, Fm.m, SR, subtype="PCM_24")
    mref, _ = sf.read(tmp, dtype="float64", always_2d=True)
    mask = (main["state"] == -1) & (main["fade"] == 1.0)
    for j in main["log"]["joins"]:
        mask[Fm.loc(j["window"][0]):Fm.loc(j["window"][1])] = False
    report["A1"]["main"]["pcm24_file_vs_master_pcm24_max_abs_diff"] = float(np.abs(mw[mask] - mref[mask]).max())
    report["A1"]["main"]["pcm24_file_vs_master_float_max_abs_diff"] = float(np.abs(mw[mask] - Fm.m[mask]).max())
    report["A1"]["main"]["silent_after"] = {"t": Fm.spec["ending"]["to"],
                                            "max_abs": float(np.abs(mw[Fm.loc(Fm.spec["ending"]["to"]):]).max())}
    tw, _ = sf.read(os.path.join(V5, "tiktok_v5_unity.wav"), dtype="float64", always_2d=True)
    Ft = tt["F"]
    n20 = smp(0.02)
    report["A1"]["tiktok"]["first_20ms_null_vs_prefade_db"] = round(
        db(np.sqrt(((tw[:n20] - tt["pre_fade"][:n20]) ** 2).mean()) / max(np.sqrt((Ft.m[:n20] ** 2).mean()), 1e-12)), 1)
    report["A1"]["tiktok"]["first_20ms_null_vs_source_db_note"] = "Choroboros (T01 Red) is on from the first sample, so the guitar band differs from the source by design; the drums (crash + kick 123.649) are the master's"
    report["A1"]["tiktok"]["first_20ms_null_vs_source_db"] = round(
        db(np.sqrt(((tw[:n20] - Ft.m[:n20]) ** 2).mean()) / max(np.sqrt((Ft.m[:n20] ** 2).mean()), 1e-12)), 1)
    loud = {
        "main": {"lufs": round(lufs(mo), 2), "true_peak_dbtp": round(tp(mo), 2),
                 "master_same_span_lufs": round(lufs(Fm.m), 2), "master_same_span_tp": round(tp(Fm.m), 2),
                 "limiter": "none on the mix; peak control at -1 dBTP on the Choroboros change only, where needed (see films.main.peak_control)"},
        "tiktok": {"lufs": round(lufs(tn), 2), "true_peak_dbtp": round(tp(tn), 2),
                   "normalize_gain_db": round(20 * math.log10(g), 2), "limiter": lim_info or "not needed",
                   "unity_lufs": round(L_t, 2), "unity_true_peak_dbtp": round(tp(tt_u), 2),
                   "master_same_span_lufs": round(lufs(Ft.m), 2)},
    }
    report["loudness"] = loud

    # ---------------------------------------------------------------- scope data
    def stems_for(res):
        F = res["F"]
        fade = res["fade"][:, None]
        guitar = (F.nd + (res["pre_fade"] - F.m)) * fade     # the non-drum part as heard
        return {"guitar": guitar, "mix": res["out"], "dry": F.bp * fade, "wet": res["band_heard"] * fade}

    S_main = stems_for(main)
    # one fixed data gain: the guitar trace's typical per-frame extent lands at SCOPE_FILL of the circle
    gtr = S_main["guitar"]
    nfr = len(gtr) // SPF
    w = gtr[:nfr * SPF]
    mid = ((w[:, 0] + w[:, 1]) / 2).reshape(-1, 2).mean(axis=1).reshape(nfr, PTS)
    side = ((w[:, 0] - w[:, 1]) / 2).reshape(-1, 2).mean(axis=1).reshape(nfr, PTS)
    ext = np.sqrt(mid ** 2 + side ** 2).max(axis=1)
    active = ext > 10 ** (-40 / 20)
    typical = float(np.median(ext[active]))
    r_data = math.atanh(SCOPE_FILL) / DISPLAY_GAIN
    gain = round(r_data / typical, 6)
    scope_log = {"gain": gain, "typical_guitar_frame_extent": round(typical, 5), "target_display_fraction": SCOPE_FILL,
                 "display_gain": DISPLAY_GAIN}

    for fname, res, S, dirs in (("main", main, S_main, [os.path.join(V5, "data", "scope")]),
                                ("tiktok", tt, stems_for(tt), [os.path.join(V5, "data-tiktok", "scope")])):
        F = res["F"]
        nframes = F.spec["frames"]
        sdir = dirs[0]
        os.makedirs(sdir, exist_ok=True)
        for stem, x in S.items():
            scope_frames(x, gain, nframes).tofile(os.path.join(sdir, f"{stem}.i16"))
        # typical fill check (display fraction) for the guitar
        buf = np.fromfile(os.path.join(sdir, "guitar.i16"), dtype=np.int16).reshape(nframes, PTS, 2) / 32767
        r = np.sqrt((buf ** 2).sum(axis=2)).max(axis=1)
        disp = np.tanh(DISPLAY_GAIN * r)
        act = r > 10 ** (-40 / 20) * gain
        scope_log[f"{fname}_guitar_display_extent_median"] = round(float(np.median(disp[act])), 3)
        scope_log[f"{fname}_guitar_display_extent_p90"] = round(float(np.percentile(disp[act], 90)), 3)
        idx = {
            "format": "int16 little-endian, interleaved (mid, side) per point",
            "fps": FPS, "sample_rate": SR, "samples_per_frame": SPF, "points_per_frame": PTS, "frames": nframes,
            "bytes_per_frame": PTS * 4, "duration_s": nframes / FPS,
            "indexed_by": "FILM time (main: master time; TikTok: tau = master - 123.648)" if fname == "main"
                          else "TikTok time tau = master - 123.648 (frame 0 = master 123.648)",
            "frame_f_covers_samples": "[800 f, 800 f + 800)",
            "mid_side": "mid = (L + R) / 2, side = (L - R) / 2; x = side, y = mid, so mono is a vertical line",
            "decimation": "800 samples -> 400 points, mean of each sample pair",
            "gain": gain,
            "gain_rule": f"one fixed data gain for both films: the guitar trace's median per-frame extent lands at {SCOPE_FILL:.0%} of the circle after scope.js DISPLAY_GAIN {DISPLAY_GAIN} and its tanh knee",
            "value": "round(clamp(x * gain, -1, 1) * 32767)", "decode": "x_display = value / 32767",
            "files": {"guitar": "guitar.i16", "gtr": "guitar.i16", "mix": "mix.i16", "dry": "dry.i16", "wet": "wet.i16"},
            "stems": ["guitar", "gtr", "mix", "dry", "wet"],
            "stem_source": {
                "guitar": "the non-drum part as heard: nd + (out - master) (processed inside the demos; in the guitar-alone windows this is the master itself), with the ending fade",
                "gtr": "alias of guitar (scope.js default stem name)",
                "mix": "the film's audio as heard" + (" at the master's level (the delivered TikTok wav is this x %.4f)" % g if fname == "tiktok" else ""),
                "dry": "BP(nd): the guitar band before Choroboros",
                "wet": "the guitar band as heard: choro_trim(BP(nd)) inside demos, BP(nd) in bypass spans and outside demos"},
        }
        json.dump(idx, open(os.path.join(sdir, "index.json"), "w"), indent=1)
        # meter.json: per frame, the processed band's peak dBFS after trim
        wb = S["wet"]
        n = nframes * SPF
        wpad = np.zeros((n, 2))
        wpad[:min(n, len(wb))] = wb[:n]
        pk = np.abs(wpad).max(axis=1).reshape(nframes, SPF).max(axis=1)
        pkdb = np.maximum(20 * np.log10(np.maximum(pk, 1e-12)), -120.0)
        st = res["state"]
        demos = res["demos"]
        json.dump({"fps": FPS, "frames": nframes, "unit": "dBFS peak of the processed guitar band after the Output Trim",
                   "peak_dbfs": [round(float(v), 1) for v in pkdb]}, open(os.path.join(sdir, "meter.json"), "w"))
        meas = {"about": "Level match results per demo (film/v5/demos.json level_match). The picture shows LEVEL MATCHED only where level_matched is true.",
                "film": fname, "demos": res["measured"]}
        json.dump(meas, open(os.path.join(sdir, "measured.json"), "w"), indent=1)
        # the spec's paths (TREATMENT s3): /home/user/build/v5/audio/scope[-tiktok] -> the same folders
        alias = os.path.join(V5, "audio", "scope" if fname == "main" else "scope-tiktok")
        os.makedirs(os.path.dirname(alias), exist_ok=True)
        if os.path.islink(alias) or os.path.exists(alias):
            if os.path.islink(alias):
                os.unlink(alias)
            else:
                shutil.rmtree(alias)
        os.symlink(sdir, alias)
        # tell the page the scope exists (film.sh prep writes the same file)
        ap = os.path.join(os.path.dirname(sdir), "available.json")
        try:
            av = json.load(open(ap))
        except Exception:
            av = {}
        av["scope"] = True
        av["scopeStems"] = idx["stems"]
        json.dump(av, open(ap, "w"), indent=1)
    report["scope"] = scope_log

    # ---------------------------------------------------------------- log
    log["films"] = {k: {kk: vv for kk, vv in R[k]["log"].items()} for k in R}
    log["loudness"] = loud
    log["scope"] = scope_log
    log["qc"] = {k: report[k] for k in ("A1", "A3", "A4", "A5", "A6", "joins")}
    log["musicality"] = report["musicality"]
    log["outputs"] = {"master": os.path.join(V5, "master_v5.wav"), "tiktok": os.path.join(V5, "tiktok_v5.wav"),
                      "tiktok_unity": os.path.join(V5, "tiktok_v5_unity.wav"),
                      "scope_main": os.path.join(V5, "data", "scope"), "scope_tiktok": os.path.join(V5, "data-tiktok", "scope"),
                      "qc": QC, "report": os.path.join(V5, "audio", "report.json")}
    os.makedirs(os.path.join(V5, "audio"), exist_ok=True)
    json.dump(report, open(os.path.join(V5, "audio", "report.json"), "w"), indent=1, default=float)
    print(json.dumps({"loudness": loud, "A1": {k: {kk: v[kk] for kk in v if kk != "xcorr_lag_per_bar_samples"} for k, v in report["A1"].items()},
                      "A3": report["A3"], "A4": report["A4"], "scope": scope_log,
                      "joins_max_jump": {k: v["max_level_jump_lu"] for k, v in report["joins"].items()}}, indent=1, default=float))
    for fname in ("main", "tiktok"):
        for k, v in R[fname]["measured"].items():
            print(fname, k, "trim", [p["trim_db"] for p in v["trim_parts"]], "bars", [b["delta_lu"] for b in v["bars"]],
                  "demo", v["demo_delta_lu"], "tp", v["tp_pass"], "mono", v["mono"]["extra_loss_lu"], v["mono"]["lr_corr_wet"],
                  "LM", v["level_matched"])


if __name__ == "__main__":
    main()
