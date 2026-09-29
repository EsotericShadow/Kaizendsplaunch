#!/usr/bin/env python3
"""Mix and master "Still Life" (production pass; owner direction replaces
treatment 3.3 and 8.5 where they conflict).

HONESTY ZONES (main 0.00-8.00 and 16.00-36.00; vertical 0.00-14.00): the
featured guitar is its Choroboros render (section edit + level-match gain +
fader) and nothing else: no send, no reverb, delay, saturation or EQ after the
plugin, and the bus glue is bypassed (gain 1). The stereo reverb and delay
returns are gated to zero there. The backing in the zones (drums, bass, FX)
is produced (tape, parallel compression, a MONO room) with no modulation, and
in the main film's tour it is pasted from a steady-state render so it is
sample-identical in every pass.

EVERYWHERE ELSE: sends to a plate (1.6 s) and a hall (2.6 s), both 8-line FDNs
with pre-delay and damping and their modulation OFF (the only modulation
effect in the film is Choroboros), a tempo-synced ping-pong delay for throws
at phrase ends, drum-bus tape and parallel compression, bass tape, kick
sidechain on pad and arp in the offer peak, a gentle glue compressor on the
mix bus, then the master: gain to about -14 LUFS, true-peak limiter at
-1.1 dBTP (<= 1 dB gain reduction), fade, hard silences.

LOW END: a gentle low shelf (80 Hz, -3 dB) on the drum bus (before its
transient shave, whose ceiling is unchanged) and on the bass bus takes the
63 Hz octave band about 2 dB down against 125 Hz. It is linear and also runs
on the tour loops, so the pasted tour backing stays sample-identical.

PRODUCT CLIPS (main film): the clips stand alone. Every music stem and every
return is muted under them with 60 ms raised-cosine fades that end on the clip
start; under Fold (G major) and Echolalia (C major / A minor) only the bass
whole note and the soft kick stay (still ducked 6 dB), and under Stovetop (its
own key, 80 BPM) nothing stays until the digital silence at 69.50.

Outputs (<build>/): mix/stem_<name>.wav as heard (every gain in the chain
applied, so the stems and returns sum to the master), mix/mix.wav (float),
master.wav (24-bit), mix/mix_info.json.

Usage: python3 audio/film/mix.py [--film main|vertical]
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

import edit
from common import SR, Film, db, dual, hard_silence, jdump, lufs, read, sine_inout, smp, write
from instruments import tape
from synth import meter
from synth.effects import Reverb, StereoDelay, _forward_min, _release, compressor, duck
from synth.filters import eq

# ----------------------------------------------------------------- main film plan

PLAN_MAIN = {
    "honesty": [(0.0, 8.0), (16.0, 36.0)],
    "tour": {"blocks": [16.0, 20.0, 24.0, 28.0], "stop_block": 32.0, "end": 36.0},
    "faders": {   # (t, dB) steps; each change ramps over the 20 ms ending at t ((t, dB, s): over s seconds)
        "gtr": [(0.0, 3.0), (8.0, 3.6), (16.0, 4.6), (36.0, 4.6), (42.0, 2.2), (50.0, 4.5), (54.0, 4.8), (58.0, 4.4),
                (62.0, 4.4), (70.0, 3.0), (78.0, 0.5), (78.6, 3.0, 0.6), (81.5, 9.0)],
        # 78.00: the strum's attack sits 2.5 dB down and the ringing chord rides back up over 0.6 s (the zone's peak is
        # the strum attack, so this buys the whole final chord level); 81.5: the lone F#4 at 82.00 (the gtr is silent
        # from 81 to 82)
        "gtr_oct": [(0.0, 1.0)],
        "pad": [(0.0, 0.0), (36.0, -5.0), (46.0, -4.5), (48.0, -3.0), (50.0, 5.5), (54.0, 3.0), (58.0, 0.5),
                (62.0, -10.0), (70.0, -10.0), (74.0, -16.0), (78.0, -2.0), (81.0, -7.0, 2.0)],
        "ep": [(0.0, 0.5)],
        "lead": [(0.0, 9.0)],
        "pluck": [(0.0, -1.0)],
        "arp": [(0.0, 1.0), (40.0, 0.0), (48.0, 2.0), (50.0, 3.5), (58.0, -1.0)],
        "bells": [(0.0, 0.0)],
        "bass": [(0.0, -9.5), (8.0, -11.0), (16.0, -11.0), (36.0, -15.0), (46.0, -14.0), (48.0, -12.0), (50.0, -9.0),
                 (62.0, -15.0), (74.0, -18.0), (78.0, -8.0), (81.0, -14.0, 2.0)],
        "drums": [(0.0, 0.0), (8.0, 1.0), (16.0, 1.0), (36.0, -2.0), (48.0, 0.5), (50.0, 2.0), (58.0, 1.5),
                  (62.0, -2.0), (74.0, -4.0), (78.0, 3.0)],
        "fx": [(0.0, 0.0), (6.0, -1.5), (8.0, 0.0), (46.0, -3.0), (50.0, 0.0)],   # the risers sit under the hits
        "clips": [(0.0, 0.0)],
    },
    "sends": {    # stem -> bus -> [(t, dB)] (post-fader); gated to silence inside the honesty zones
        "gtr": {"plate": [(0.0, -19.0)], "hall": [(0.0, -24.0), (78.0, -18.0), (81.5, -24.0)]},
        "gtr_oct": {"plate": [(0.0, -10.0)], "hall": [(0.0, -14.0)]},
        "ep": {"plate": [(0.0, -15.0)], "hall": [(0.0, -20.0)]},
        "lead": {"plate": [(0.0, -13.0)], "hall": [(0.0, -17.0)]},
        "pluck": {"plate": [(0.0, -17.0)], "hall": [(0.0, -16.0)]},
        "pad": {"hall": [(0.0, -11.0)]},
        "bells": {"hall": [(0.0, -7.0)], "plate": [(0.0, -14.0)]},
        "arp": {"hall": [(0.0, -12.0)], "delay": [(0.0, -15.0)]},
        "snare": {"plate": [(0.0, -17.0)]},
        "fx": {"hall": [(0.0, -22.0)]},
    },
    "throws": {   # delay throws: stem -> [(t0, t1, dB)] windows where the delay send opens
        "gtr": [(9.5, 9.8, -8.0), (11.5, 11.8, -8.0), (43.5, 43.8, -9.0), (49.5, 49.8, -7.0), (53.5, 53.85, -9.0),
                (57.5, 57.85, -9.0), (61.5, 61.95, -6.0), (82.0, 82.6, -8.0)],
        "arp": [(15.5, 15.9, -8.0), (47.6, 48.0, -10.0), (53.6, 54.0, -9.0), (57.6, 58.0, -9.0)],
        "lead": [(61.5, 61.95, -6.0)],
    },
    "returns": {"plate": 0.0, "hall": 0.0, "delay": -3.0},
    "room": {"send_db": -15.0, "return_db": 0.0},
    # the sub: a gentle low shelf on the drum and bass buses (63 Hz band about 2 dB down, 125 Hz untouched)
    "low_end": {"shelf_hz": 80.0, "gain_db": -3.0, "q": 0.8},
    # the product clips stand alone: every music stem and return is muted under them (60 ms fades ending at
    # the clip start) except the ones kept per clip; Fold (G major) and Echolalia (C major / A minor) keep the
    # bass whole note and the soft kick, Stovetop (its own key, 80 BPM) keeps nothing
    "clip_bed": {"fade": 0.060, "bridge": 0.5, "keep": {"fold": ["bass", "drums"], "echolalia": ["bass", "drums"],
                                                        "stovetop": []}},
    "sidechain": {"targets": ["pad", "arp"], "span": (50.0, 62.0), "depth_db": 3.5},
    "glue": {"target_mean_gr_db": 2.5, "target_span": (50.0, 62.0), "ratio": 2.0, "attack_ms": 20.0,
             "release_ms": 160.0,
             "threshold_offsets": [(0.0, 2.0), (36.0, 4.0), (46.0, 3.0), (50.0, 0.0), (62.0, 4.0), (70.0, 4.0)]},
    "zones": [(0.0, 8.0), (8.0, 16.0), (16.0, 36.0), (36.0, 40.0), (40.0, 46.0), (46.0, 50.0), (50.0, 54.0),
              (54.0, 58.0), (58.0, 62.0), (62.0, 70.0), (70.0, 74.0), (74.0, 78.0), (78.0, 86.0)],
    "zone_level": {(0.0, 8.0): -5.8, (8.0, 16.0): -6.1, (16.0, 36.0): -4.4, (36.0, 40.0): -4.5, (40.0, 46.0): -6.6,
                   (46.0, 50.0): -7.5,
                   (50.0, 54.0): 1.5, (54.0, 58.0): -3.6, (58.0, 62.0): -7.9, (70.0, 74.0): -5.0, (74.0, 78.0): -5.8,
                   (78.0, 86.0): -6.5},
    "fade": (84.50, 86.00),
}

ABSOLUTE = ("fx", "bells", "clips")
DUCKED = ("pad", "bass", "drums")
DUCK_DB = -6.0
PROCESSED = ("gtr", "pad", "ep", "lead", "pluck")
MASTER_LUFS, CEILING, MAX_GR = -14.4, -1.1, 1.0      # inside the -14 +-0.5 gate, 0.1 LU margin
GR_BUDGET = 0.85

PLAN = PLAN_MAIN
PLANS = {"main": PLAN_MAIN}


def use_plan(name):
    global PLAN
    if name == "vertical":
        from vertical import PLAN_VERTICAL
        PLANS["vertical"] = PLAN_VERTICAL
    PLAN = PLANS[name]


# ----------------------------------------------------------------- curves

def fader_curve(n, plan, ramp=0.020):
    """dB curve from (t, dB) steps; each change ramps (sine in-out) over `ramp`
    s ending at t, or over its own ramp for a (t, dB, ramp_s) entry (a slow ride)."""
    g = np.zeros(n)
    for p in plan:
        g[smp(p[0]):] = p[1]
    for i in range(1, len(plan)):
        s = smp(plan[i][0])
        k = smp(plan[i][2] if len(plan[i]) > 2 else ramp)
        u = (np.arange(k) + 1) / k
        g0, g1 = plan[i - 1][1], plan[i][1]
        if g0 != g1 and s - k >= 0:
            g[s - k:s] = g0 + (g1 - g0) * sine_inout(u)
    return g


def gate_curve(n, zones, fade=0.04):
    """1 outside the honesty zones, 0 inside; fades end exactly on a zone start
    and begin exactly on a zone end (so the zones themselves are untouched)."""
    g = np.ones(n)
    k = smp(fade)
    u = (np.arange(k) + 1) / k
    for (a, b) in zones:
        s, e = smp(a), smp(b)
        g[s:e] = 0.0
        if s > 0:
            lo = max(0, s - k)
            g[lo:s] = np.minimum(g[lo:s], np.cos(0.5 * np.pi * u)[k - (s - lo):])
        if e < n:
            hi = min(n, e + k)
            g[e:hi] = np.minimum(g[e:hi], np.sin(0.5 * np.pi * u)[:hi - e])
    return g


def window_curve(n, windows, ramp=0.015):
    """Linear send gain: 0 outside the windows, the window level inside, 15 ms ramps."""
    lin = np.zeros(n)
    k = smp(ramp)
    u = sine_inout((np.arange(k) + 1) / k)
    for (a, b, dbv) in windows:
        s, e = smp(a), smp(b)
        w = np.zeros(n)
        w[s:e] = 1.0
        lo = max(0, s - k)
        w[lo:s] = u[k - (s - lo):]
        hi = min(n, e + k)
        w[e:hi] = 1 - u[:hi - e]
        lin = np.maximum(lin, w * db(dbv))
    return lin


def duck_curve(n, spans, depth_db=DUCK_DB, attack=0.040, release=0.150):
    env = np.zeros(n)
    t = np.arange(n) / SR
    for (a, b) in spans:
        on = np.clip((t - a) / attack, 0, 1)
        off = np.clip(1 - (t - b) / release, 0, 1)
        e = np.where(t < b, on, off)
        e[t < a] = 0
        env = np.maximum(env, sine_inout(e))
    return env * depth_db


def clip_bed_curves(n, cues, stems):
    """Linear gain per stem under the product clips (PLAN["clip_bed"]). Every
    stem except the clips and the ones kept for that clip is muted over the
    clip window: a raised-cosine fade of `fade` s ends exactly on the clip
    start, then silence to the clip end. Windows closer than `bridge` s are
    joined (the pad does not come back for the 0.25 s between two clips), and a
    window that runs into a hard silence stays shut to the silence's end (the
    next material starts hard there, as after any hard silence)."""
    cb = PLAN.get("clip_bed")
    if not cb:
        return {}
    wins = []
    for sec in cues["sections"]:
        if "clip_at" in sec:
            a = float(sec["clip_at"])
            wins.append((a, a + float(sec["clip_out"]) - float(sec["clip_in"]), set(cb["keep"].get(sec["name"], []))))
    if not wins:
        return {}
    sil = edit.silences(cues)
    k = smp(cb["fade"])
    u = (np.arange(k) + 1) / k
    out = {}
    for name in stems:
        if name == "clips":
            continue
        spans = sorted((a, b) for (a, b, keep) in wins if name not in keep)
        merged = []
        for a, b in spans:
            if merged and a - merged[-1][1] <= cb["bridge"] + 1e-9:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        if not merged:
            continue
        g = np.ones(n)
        for a, b in merged:
            for (s0, s1) in sil:
                if abs(s0 - b) < 1e-6:
                    b = s1
            sa, sb = smp(a), smp(b)
            g[sa:sb] = 0.0
            lo = max(0, sa - k)
            g[lo:sa] = np.minimum(g[lo:sa], (0.5 + 0.5 * np.cos(np.pi * u))[k - (sa - lo):])
            if not any(abs(s1 - b) < 1e-6 for (_, s1) in sil):
                hi = min(n, sb + k)
                g[sb:hi] = np.minimum(g[sb:hi], (0.5 - 0.5 * np.cos(np.pi * u))[:hi - sb])
        out[name] = g
    return out


# ----------------------------------------------------------------- processors (no modulation anywhere)

def plate():
    return Reverb(rt60=1.6, hf_ratio=0.5, size=0.85, predelay_ms=18.0, diffusion=0.72, mod_depth_ms=0.0,
                  low_cut=280.0, high_cut=7500.0, width=1.0)


def hall():
    return Reverb(rt60=2.6, hf_ratio=0.42, size=1.25, predelay_ms=34.0, diffusion=0.7, mod_depth_ms=0.0,
                  low_cut=220.0, high_cut=6500.0, width=1.0)


def room_mono(x):
    """Mono room for the backing (allowed in the honesty zones): short FDN,
    output folded to mono."""
    r = Reverb(rt60=0.65, hf_ratio=0.5, size=0.45, predelay_ms=7.0, diffusion=0.7, mod_depth_ms=0.0,
               low_cut=250.0, high_cut=7000.0)(dual(x))
    return 0.5 * (r[:, 0] + r[:, 1])


def delay_bus():
    return StereoDelay.synced(120.0, 0.75, 1.0, feedback=0.38, cross=0.65, lp_hz=4200.0, hp_hz=320.0)


def drum_bus(parts, ceiling_db=None, shave_db=6.0):
    """Drum bus on a dict of mono sub-stems: tape, parallel compression, mono
    room, then a look-ahead transient shave (a bus clipper's job, done cleanly)
    at an absolute ceiling. Deterministic: the same input and ceiling give the
    same output, so the tour loops match the full stem. Returns (bus, ceiling)."""
    from instruments import ceiling_control
    dry = sum(parts[k] for k in parts)
    sat = tape(dry, drive_db=10.0, bias=0.05, hf_db=-0.8)
    c = compressor(dual(sat), threshold_db=-34.0, ratio=6.0, attack_ms=3.0, release_ms=90.0, knee_db=6.0,
                   sidechain_hp=60.0, detector="peak")[:, 0]
    bus = sat + 0.4 * c * db(8.0)
    roomin = 0.35 * parts["kick"] + 1.0 * parts["snare"] + 0.6 * parts["chh"] + 0.8 * parts["rim"]
    bus = bus + room_mono(roomin) * db(PLAN["room"]["send_db"] + PLAN["room"]["return_db"])
    if ceiling_db is None:     # measured before the sub shelf, so the shelf never raises the drum-bus peak
        ceiling_db = float(20 * np.log10(np.abs(bus).max() + 1e-12)) - shave_db
    return ceiling_control(low_end(bus), ceiling_db, 1.5, 60.0), ceiling_db


def bass_bus(x):
    return low_end(tape(x, drive_db=8.0, bias=0.06, hf_db=0.0))


def low_end(x):
    """The sub: a gentle low shelf (PLAN["low_end"]) on the drum bus (before its
    transient shave) and at the end of the bass bus. Linear and time-invariant,
    and it runs on the tour loops too, so the pasted backing stays
    sample-identical in every pass."""
    le = PLAN.get("low_end")
    if not le:
        return x
    return eq(x, [("lowshelf", le["shelf_hz"], le["gain_db"], le["q"])], SR)


def paste_tour(full, loopN, loopS, tour, n, fade=0.020):
    """Replace the tour span of a processed stem by block 2 of the steady-state
    loops: passes 1-4 from loop N, pass 5 (Black's stop) from loop S, joined to
    the surrounding stem with 20 ms equal-power cross-fades outside the tour."""
    y = full.copy()
    blk = loopN[smp(4.0):smp(8.0)]
    for t in tour["blocks"]:
        y[smp(t):smp(t) + len(blk)] = blk
    s0 = smp(tour["stop_block"])
    blkS = loopS[smp(4.0):smp(9.0)]                    # the stop block plus 1 s of its tail
    k = smp(fade)
    e = smp(tour["end"])
    y[s0:e] = blkS[: e - s0]
    u = (np.arange(k) + 1) / k
    y[e:e + k] = full[e:e + k] * np.sin(0.5 * np.pi * u) + blkS[e - s0:e - s0 + k] * np.cos(0.5 * np.pi * u)
    a = smp(tour["blocks"][0])
    y[a - k:a] = full[a - k:a] * np.cos(0.5 * np.pi * u) + loopN[smp(4.0) - k:smp(4.0)] * np.sin(0.5 * np.pi * u)
    return y


# ----------------------------------------------------------------- build

def build(film, cues):
    n = film.n
    P = PLAN
    gate = gate_curve(n, P["honesty"])
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
        if s == "gtr":
            P["_gtr_pre_db"] = lg + fader_curve(n, P["faders"][s])
        stems[s] = y * db(lg + fader_curve(n, P["faders"][s]))[:, None]
    kinds = ("kick", "snare", "chh", "rim", "shaker", "crash")
    parts = {k: read(film.stem_path(f"drums_{k}")) for k in kinds}
    drums, dceil = drum_bus(parts)
    bass = bass_bus(read(film.stem_path("bass")))
    if P.get("tour"):
        lp = {nm: {k: read(film.stem_path(f"drums_{k}_loop{nm}")) for k in kinds} for nm in ("N", "S")}
        drums = paste_tour(drums, drum_bus(lp["N"], dceil)[0], drum_bus(lp["S"], dceil)[0], P["tour"], n)
        bass = paste_tour(bass, bass_bus(read(film.stem_path("bass_loopN"))),
                          bass_bus(read(film.stem_path("bass_loopS"))), P["tour"], n)
    for (a, b) in edit.silences(cues):
        drums = hard_silence(drums, a, b)
        bass = hard_silence(bass, a, b)
    stems["drums"] = dual(drums) * db(fader_curve(n, P["faders"]["drums"]))[:, None]
    stems["bass"] = dual(bass) * db(fader_curve(n, P["faders"]["bass"]))[:, None]
    for s in ("gtr_oct", "arp", "bells", "fx"):
        p = film.stem_path(s)
        if os.path.exists(p) and s in P["faders"]:
            stems[s] = dual(read(p)) * db(fader_curve(n, P["faders"][s]))[:, None]
    clips_p = film.p("edit", "clips.wav")
    if os.path.exists(clips_p) and "clips" in P["faders"]:
        stems["clips"] = read(clips_p)[:n] * db(fader_curve(n, P["faders"]["clips"]))[:, None]
        spans = [(sec["clip_at"], sec["clip_at"] + sec["clip_out"] - sec["clip_in"])
                 for sec in cues["sections"] if "clip_at" in sec]
        dk = db(duck_curve(n, spans))
        for s in DUCKED:
            stems[s] = stems[s] * dk[:, None]
    # honesty zones: nothing but the featured guitar and the (mono, unmodulated) backing
    for s in ("gtr_oct", "pad", "ep", "lead", "pluck", "arp", "bells", "clips"):
        if s in stems:
            stems[s] = stems[s] * gate[:, None]
    bed = clip_bed_curves(n, cues, list(stems) + ["plate", "hall", "delay"])
    for s, g in bed.items():
        if s in stems:
            stems[s] = stems[s] * g[:, None]
    if "gtr" in bed:
        P["_gtr_bed"] = bed["gtr"]
    sc = P.get("sidechain")
    if sc:
        a, b = smp(sc["span"][0]), smp(sc["span"][1])
        key = np.zeros(n)
        key[a:b] = read(film.stem_path("drums_kick"))[a:b]
        for s in sc["targets"]:
            if s in stems:
                stems[s] = duck(stems[s], dual(key), sc["depth_db"], attack_ms=3.0, release_ms=170.0)
    buses = {"plate": np.zeros((n, 2)), "hall": np.zeros((n, 2)), "delay": np.zeros((n, 2))}
    src = dict(stems)
    src["snare"] = dual(read(film.stem_path("drums_snare"))) * db(fader_curve(n, P["faders"]["drums"]))[:, None]
    for s, sends in P["sends"].items():
        if s not in src:
            continue
        for bus, plan in sends.items():
            buses[bus] += src[s] * (db(fader_curve(n, plan)) * gate)[:, None]
    for s, wins in P.get("throws", {}).items():
        if s in src:
            buses["delay"] += src[s] * (window_curve(n, wins) * gate)[:, None]
    rets = {"plate": plate()(buses["plate"]), "hall": hall()(buses["hall"]), "delay": delay_bus()(buses["delay"])}
    for k, r in rets.items():
        r = r * db(P["returns"][k]) * gate[:, None]
        if k in bed:
            r = r * bed[k][:, None]
        for (a, b) in edit.silences(cues):
            r = hard_silence(r, a, b)
        stems[k] = r
    return stems, gate


def glue_gain(mix, threshold_db, ratio, attack_ms, release_ms, knee_db=6.0, sc_hp=90.0):
    """Stereo-linked feed-forward bus compressor gain (dB) with a per-sample
    threshold (RMS detector 5 ms, soft knee, decoupled attack/release)."""
    from synth.effects import _smooth_gain
    from synth.filters import eq as _eq
    sc = _eq(mix, [("highpass", sc_hp, 0, 0.7)], SR)
    p = (sc ** 2).max(axis=1)
    a = math.exp(-1 / (5.0 * SR / 1000))
    from scipy import signal as _sig
    p = _sig.lfilter([1 - a], [1, -a], p)
    lvl = 10 * np.log10(np.maximum(p * 2, 1e-12))
    over = lvl - threshold_db
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, (1 / ratio - 1) * over,
                           (1 / ratio - 1) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    att = math.exp(-1 / (attack_ms * SR / 1000))
    rel = math.exp(-1 / (release_ms * SR / 1000))
    return _smooth_gain(gr, att, rel)


def glue_curve(stems, gate):
    """Bus glue on the music bus (the absolute-level stems, product clips, bells
    and FX, are not part of it): 2:1 soft knee, 12 ms attack, 160 ms release. The
    threshold follows the arc (lower in the offer peak so the drop is dense and
    loud, higher in the breakdown); its base is set so the mean gain reduction
    outside the honesty zones is about 1.8 dB. Forced to 0 dB (bypass) inside
    the honesty zones."""
    g = PLAN["glue"]
    n = len(gate)
    mix = sum(v for k, v in stems.items() if k not in ABSOLUTE)
    off = fader_curve(n, g.get("threshold_offsets", [(0.0, 0.0)]), ramp=0.2)
    m = gate > 0.999
    if "target_span" in g:
        m = np.zeros(n, bool)
        m[smp(g["target_span"][0]):smp(g["target_span"][1])] = True
    lo, hi = -60.0, 0.0
    for _ in range(16):
        th = 0.5 * (lo + hi)
        gdb = glue_gain(mix, th + off, g["ratio"], g["attack_ms"], g["release_ms"])
        if -gdb[m].mean() > g["target_mean_gr_db"]:
            lo = th
        else:
            hi = th
    PLAN["glue"]["threshold_db_used"] = round(th, 2)
    return gdb * gate


def tp_limiter(x, ceiling_dbtp=CEILING, lookahead_ms=5.0, release_ms=80.0, max_passes=6):
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


def trim_curve(n, trims, ramp=0.020):
    return fader_curve(n, [(z[0], trims[z]) for z in sorted(trims)], ramp)


def design_curve(n):
    return trim_curve(n, {z: PLAN["zone_level"].get(z, 0.0) for z in PLAN["zones"]})


def master_gain_for(stems, tcurve, lufs_target, iters=4):
    n = len(tcurve)
    design = db(-design_curve(n))
    rel = sum(v for k, v in stems.items() if k not in ABSOLUTE) * db(tcurve)[:, None]
    ab = sum((v for k, v in stems.items() if k in ABSOLUTE), np.zeros_like(rel)) * (db(tcurve) * design)[:, None]
    g = lufs_target - lufs(rel + ab)
    for _ in range(iters):
        g = g + (lufs_target - lufs((rel + ab * db(-g)) * db(g)))
    return g, (rel + ab * db(-g))


def in_honesty(z):
    return any(z[0] >= a - 1e-9 and z[1] <= b + 1e-9 for (a, b) in PLAN["honesty"])


def zone_trims(film, stems, lufs_target=MASTER_LUFS, budget=GR_BUDGET, iters=8):
    """Per-zone bus trims so no zone needs more than `budget` dB of limiting;
    honesty zones get no limiting at all (their peaks stay under the ceiling),
    so the featured guitar and the backing there are gain-only in the master."""
    n = film.n
    zones = PLAN["zones"]
    trims = {z: PLAN["zone_level"].get(z, 0.0) for z in zones}
    for it in range(iters):
        tc = trim_curve(n, trims)
        g, x = master_gain_for(stems, tc, lufs_target)
        env = meter.true_peak_envelope(x * db(g), SR)
        changed = False
        for z in zones:
            ceil_pre = CEILING - 0.1 if in_honesty(z) else CEILING + budget
            a, b = smp(z[0]), smp(z[1])
            pk = 20 * np.log10(max(env[a:b].max(), 1e-12))
            over = pk - ceil_pre
            if over > 0.02:
                trims[z] -= over + 0.05
                changed = True
        if not changed:
            break
    return trims


def master(film, stems, silences, lufs_target=MASTER_LUFS):
    n = film.n
    fade = PLAN["fade"]
    trims = zone_trims(film, stems, lufs_target)
    tcurve = trim_curve(n, trims)
    g_master, _ = master_gain_for(stems, tcurve, lufs_target)
    design = db(-design_curve(n))
    tc = db(tcurve)
    stems = {k: v * tc[:, None] * ((db(-g_master) * design)[:, None] if k in ABSOLUTE else 1.0)
             for k, v in stems.items()}
    pre = sum(stems.values())
    info = {"zone_levels_db": {f"{a:g}-{b:g}": round(v, 2) for (a, b), v in trims.items()},
            "zone_levels_design_db": {f"{a:g}-{b:g}": v for (a, b), v in PLAN["zone_level"].items()},
            "absolute_stems_compensated_db": round(-g_master, 3)}
    for it in range(4):
        x = pre * db(g_master)
        y, g_lim, linfo = tp_limiter(x)
        fcurve = np.ones(n)
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
    info.update(master_gain_db=round(g_master, 3), limiter=linfo, integrated_lufs=round(L, 3))
    total = db(g_master) * g_lim * fcurve
    out = {k: v * total[:, None] for k, v in stems.items()}
    for k in out:
        for (s0, s1) in silences:
            out[k] = hard_silence(out[k], s0, s1)
    info["_chain"] = tc * total          # linear gain after the glue, for the non-absolute stems
    info["_limiter_gain"] = g_lim
    return y, out, info


def per_bar(y, film):
    """Loudness, crest and onset density per bar (the arc)."""
    rows = []
    mono = 0.5 * (y[:, 0] + y[:, 1])
    on = meter.onset_times(y, SR, threshold=0.12, min_gap_s=0.06)
    nb = int(round(film.duration / 2.0))
    for b in range(1, nb + 1):
        a, e = smp(2.0 * (b - 1)), smp(2.0 * b)
        seg = y[a:e]
        L = lufs(seg)
        pk = float(np.abs(seg).max())
        rms = float(np.sqrt(np.mean(seg ** 2)))
        rows.append({"bar": b, "t0": 2.0 * (b - 1), "lufs": round(L, 2) if np.isfinite(L) else None,
                     "short_term_end": round(lufs(y[max(0, e - smp(3.0)):e]), 2),
                     "crest_db": round(20 * np.log10(pk / rms), 1) if rms > 0 else None,
                     "onsets": int(sum(1 for t in on if 2.0 * (b - 1) <= t < 2.0 * b)),
                     "mono_drop_lu": round(L - lufs(np.stack([mono[a:e]] * 2, 1)), 2) if np.isfinite(L) else None})
    return rows


def report(y, stems, cues, film):
    rep = {"integrated_lufs": round(lufs(y), 3), "true_peak_dbtp": round(meter.true_peak(y, SR), 3),
           "sample_peak_dbfs": round(meter.sample_peak(y), 3), "clipped_runs": meter.clipped_samples(y),
           "non_finite": int(np.sum(~np.isfinite(y))), "loudness_range_lu": round(meter.loudness_range(y, SR), 2)}
    mono = 0.5 * (y[:, 0] + y[:, 1])
    rep["mono_fold"] = {"integrated_lufs_mono_as_dual": round(lufs(np.stack([mono, mono], 1)), 3)}
    rep["mono_fold"]["drop_lu"] = round(rep["integrated_lufs"] - rep["mono_fold"]["integrated_lufs_mono_as_dual"], 3)
    bands = meter.octave_bands(y, SR)
    rep["octave_bands_db_rel"] = {str(k): round(v, 1) for k, v in bands.items()}
    rep["tilt_db_per_oct_125_8k"] = round(meter.spectral_tilt_db_per_oct(bands), 2)
    rep["crest_db"] = round(meter.crest_factor_db(y, SR)["sample_peak_to_rms_db"], 2)
    secs = []
    for s in cues["sections"]:
        t0, t1 = float(s["t0"]), float(s["t1"])
        if t1 - t0 < 1.0:
            continue
        seg = y[smp(t0):smp(t1)]
        m = 0.5 * (seg[:, 0] + seg[:, 1])
        secs.append({"shot": s["shot"], "name": s["name"], "t0": t0, "t1": t1, "lufs": round(lufs(seg), 2),
                     "short_term_at_end": round(lufs(y[max(0, smp(t1 - 3.0)):smp(t1)]), 2),
                     "mono_drop_lu": round(lufs(seg) - lufs(np.stack([m, m], 1)), 2),
                     "stems": {k: round(lufs(v[smp(t0):smp(t1)]), 1) for k, v in stems.items()
                               if np.abs(v[smp(t0):smp(t1)]).max() > 1e-6}})
    rep["sections"] = secs
    rep["bars"] = per_bar(y, film)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="main")
    a = ap.parse_args()
    use_plan(a.film)
    film = Film(a.film)
    cues = film.cues
    stems, gate = build(film, cues)
    gdb = glue_curve(stems, gate)
    stems = {k: (v * db(gdb)[:, None] if k not in ABSOLUTE else v) for k, v in stems.items()}
    y, out, info = master(film, stems, edit.silences(cues))
    chain = info.pop("_chain")
    g_lim = info.pop("_limiter_gain")
    # the featured guitar's whole post-plugin chain as one linear gain (QC proves gain-only)
    np.save(film.p("mix", "gtr_total_gain.npy"),
            db(PLAN.pop("_gtr_pre_db")) * PLAN.pop("_gtr_bed", 1.0) * db(gdb) * chain)
    np.save(film.p("mix", "limiter_gain.npy"), g_lim)
    info["glue"] = {"max_gain_reduction_db": round(float(-gdb.min()), 2),
                    "mean_gain_reduction_outside_zones_db": round(float(-gdb[gate > 0.999].mean()), 2),
                    "threshold_db_used": PLAN["glue"].get("threshold_db_used"),
                    "mean_gr_by_zone_db": {f"{a:g}-{b:g}": round(float(-gdb[smp(a):smp(b)].mean()), 2)
                                           for (a, b) in PLAN["zones"]}}
    rep = report(y, out, cues, film)
    info["report"] = rep
    for k, v in out.items():
        write(film.p("mix", f"stem_{k}.wav"), v)
    write(film.p("mix", "mix.wav"), y)
    mp = os.path.join(os.path.dirname(film.out) if a.film == "vertical" else film.out,
                      "vertical-master.wav" if a.film == "vertical" else "master.wav")
    write(mp, y, subtype="PCM_24")
    np.save(film.p("mix", "gate.npy"), gate)
    np.save(film.p("mix", "glue_db.npy"), gdb)
    info["files"] = {"master": mp, "mix_float": film.p("mix", "mix.wav"),
                     "stems": {k: film.p("mix", f"stem_{k}.wav") for k in out}}
    info["plan"] = {"honesty_zones": PLAN["honesty"], "faders": PLAN["faders"], "sends": PLAN["sends"],
                    "throws": PLAN.get("throws"), "sidechain": PLAN.get("sidechain"), "glue": PLAN["glue"],
                    "low_end": PLAN.get("low_end"), "clip_bed": PLAN.get("clip_bed")}
    jdump(film.p("mix", "mix_info.json"), info)
    print(json.dumps({k: info[k] for k in ("master_gain_db", "limiter", "integrated_lufs", "glue")}))
    print("TP", rep["true_peak_dbtp"], "LRA", rep["loudness_range_lu"], "mono drop", rep["mono_fold"]["drop_lu"],
          "tilt", rep["tilt_db_per_oct_125_8k"], "bands", rep["octave_bands_db_rel"])
    print("zones", info["zone_levels_db"])
    for r in rep["sections"]:
        print(f"{str(r['shot']):>3} {r['name']:11s} {r['t0']:6.2f}-{r['t1']:6.2f} L {r['lufs']:6.1f} ST_end "
              f"{r['short_term_at_end']:6.1f} mono -{r['mono_drop_lu']:.2f}  "
              + " ".join(f"{k}:{v}" for k, v in r["stems"].items()))


if __name__ == "__main__":
    main()
