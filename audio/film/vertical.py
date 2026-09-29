#!/usr/bin/env python3
"""Vertical cutdown soundtrack (28.0 s, 14 bars, treatment section 9), production pass.

Its own arrangement from the same instruments, the same take (the hook) and
seeds and the same Choroboros settings (same flags, gesture times shifted), not
an edit of the main mix. Writes film/cues-vertical.json (same schema as
cues.json), the vertical stems, renders, level-match log, mix, master and scope:

  /home/user/build/film/audio/vertical/...          stems, renders, edit, mix
  /home/user/build/film/audio/vertical-master.wav   48 kHz 24-bit
  /home/user/build/film/data/scope-vertical/        1680 frames + index.json
  audio/logs/level-match-vertical.json, qc-vertical.json, arc-vertical.json, render-meta/*-vertical.json

Honesty zone 0.00-14.00 (the Mix turn and the five engine blocks): the featured
guitar is Choroboros plus gain only, the backing there (drums, bass, FX) has no
modulation, the stereo returns are gated off. Production after 14.00.

Bars (bar n starts at 2 (n - 1) s):
 1 Dmaj9  hook T1 dry, Mix turn 1.00-1.50        8 Gmaj9#11  free: M_G (Green), pad Purple, groove B, arp
 2 Bm11   T3 Green, impact, groove A             9 A7sus4>A7 M_A7; trial from 17.00: Blue gtr, Red EP, Black pad
 3 Dmaj9  T1 Green, Depth 5.00-5.50             10 Gmaj9#11  M_G Blue, EP, pad, arp
 4 Bm11   T3 Blue, Offset 7.00-7.50             11 Dmaj9     hook T1 + the lead answering + all five engines
 5 Dmaj9  T1 Red, HQ at 9.00                    12 A7sus4>A7 under T1 alone, moving (Green) - the dominant
 6 Bm11   T3 Purple, Rate 11.00-11.50           13 Dmaj9     final strum at 24.00, pad Green (b), bass D2
 7 Dmaj9  T1 Black, Color 13.00-13.50, fill,    14           ring; fade 27.00-28.00
          riser into the drop at 14.00

Usage: python3 audio/film/vertical.py [--skip-compose]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time

import numpy as np

import compose as C
from common import HERE, REPO, SR, Film, bar_t, smp, todb, write
from instruments import (FMBell, PAD_EQ, RealGuitar, comp_pedal, downlifter, impact, peak_control, render_events,
                         render_events_pre, reverse_crash, riser, swish, tape, ceiling_control)
from synth.filters import eq
from synth.instrument import NoteEvent

DUR = 28.0
VH = {1: [(0, "D")], 2: [(0, "Bm")], 3: [(0, "D")], 4: [(0, "Bm")], 5: [(0, "D")], 6: [(0, "Bm")], 7: [(0, "D")],
      8: [(0, "G")], 9: [(0, "A7s4"), (1.5, "A7")], 10: [(0, "G")], 11: [(0, "D")],
      12: [(0, "A7s4"), (1.0, "A7")], 13: [(0, "D")], 14: [(0, "D")]}
HONESTY_V = [(0.0, 14.0)]

# ----------------------------------------------------------------- mix plan (used by mix.py --film vertical)

PLAN_VERTICAL = {
    "honesty": HONESTY_V,
    "tour": None,
    "faders": {
        "gtr": [(0.0, 3.0), (14.0, 5.0), (17.0, 4.8), (20.0, 4.4), (22.0, 3.4)],
        "gtr_oct": [(0.0, 1.0)],
        "pad": [(0.0, 0.0), (14.0, 2.0), (17.0, 1.5), (20.0, 0.5), (22.0, -6.0), (24.0, -6.0)],
        "ep": [(0.0, 0.5)],
        "lead": [(0.0, 9.0)],
        "pluck": [(0.0, -1.0)],
        "arp": [(0.0, 1.5), (20.0, -1.0)],
        "bells": [(0.0, 0.0)],
        "bass": [(0.0, -12.0), (14.0, -10.5), (22.0, -17.5), (24.0, -15.5)],
        "drums": [(0.0, 1.0), (14.0, 2.0), (20.0, 1.5), (22.0, -4.0)],
        "fx": [(0.0, 0.0)],
    },
    "sends": {
        "gtr": {"plate": [(0.0, -19.0)], "hall": [(0.0, -24.0)]},
        "gtr_oct": {"plate": [(0.0, -10.0)], "hall": [(0.0, -14.0)]},
        "ep": {"plate": [(0.0, -15.0)], "hall": [(0.0, -20.0)]},
        "lead": {"plate": [(0.0, -13.0)], "hall": [(0.0, -17.0)]},
        "pluck": {"plate": [(0.0, -17.0)], "hall": [(0.0, -16.0)]},
        "pad": {"hall": [(0.0, -11.0)]},
        "arp": {"hall": [(0.0, -12.0)], "delay": [(0.0, -15.0)]},
        "snare": {"plate": [(0.0, -17.0)]},
        "fx": {"hall": [(0.0, -22.0)]},
    },
    "throws": {
        "gtr": [(15.5, 15.85, -9.0), (19.5, 19.85, -9.0), (21.5, 21.95, -7.0), (23.5, 23.95, -9.0)],
        "arp": [(16.6, 17.0, -9.0), (19.6, 20.0, -9.0)],
        "lead": [(21.5, 21.95, -6.0)],
    },
    "returns": {"plate": 0.0, "hall": 0.0, "delay": -3.0},
    "room": {"send_db": -15.0, "return_db": 0.0},
    "low_end": {"shelf_hz": 80.0, "gain_db": -3.0, "q": 0.8},      # the same sub shelf as the main film
    "sidechain": {"targets": ["pad", "arp"], "span": (14.0, 22.0), "depth_db": 3.5},
    "glue": {"target_mean_gr_db": 2.5, "target_span": (14.0, 22.0), "ratio": 2.0, "attack_ms": 20.0,
             "release_ms": 160.0, "threshold_offsets": [(0.0, 2.0), (14.0, 0.0), (22.0, 4.0)]},
    "zones": [(0.0, 14.0), (14.0, 17.0), (17.0, 20.0), (20.0, 22.0), (22.0, 24.0), (24.0, 28.0)],
    "zone_level": {(0.0, 14.0): -4.0, (14.0, 17.0): 1.5, (17.0, 20.0): -1.5, (20.0, 22.0): -2.5, (22.0, 24.0): -3.5,
                   (24.0, 28.0): -1.0},
    "fade": (27.00, 28.00),
}


# ----------------------------------------------------------------- cues-vertical.json

def vertical_cues():
    main = json.load(open(os.path.join(REPO, "film", "cues.json")))
    renders = copy.deepcopy(main["renders"])
    for rid, r in renders.items():
        for k in ("preroll", "swoosh_t"):
            r.pop(k, None)
    renders["R05"]["preroll_sweep"] = {"range": [0.0, 8.25], "step": 0.25, "window": [10.25, 10.85],
                                       "section_start": 10.0, "clear_until": 11.0}
    roles = {"R01": "Green (a) guitar; Mix turn at 1.00-1.50 (V1), V2, V8, V10, V11",
             "R02": "Green block V3, Depth gesture", "R03": "Blue block V4, Offset gesture; trial guitar (V9)",
             "R04": "Red block V5, BBD then Tape at 9.00", "R05": "Purple block V6 (Orbit), Rate gesture; pre-roll swept",
             "R06": "Black block V7 (Ensemble), Color gesture", "R07": "Pad, Green (b) Lagrange 5th, V11 and the final chord",
             "R08": "Pad, Purple (a) Orbit, free card (V8)", "R09": "Pad, Black (b), Width gesture at 17.00-18.00 (V9)",
             "R09ref": "Level reference for R09 (Width fixed 100%)", "R10": "EP, Red (b) Tape (V9, V10)",
             "R11": "Lead guitar, Blue (b) Thiran (V10)", "R12": "FM pluck, Purple (a) Orbit (V10)"}
    for rid, role in roles.items():
        renders[rid]["role"] = role
    gestures = [
        {"render": "R01", "param": "mix", "t0": 1.00, "t1": 1.50, "from": 0, "to": 45, "ease": "sine.inOut",
         "ring": "mix", "caption": None},
        {"render": "R02", "param": "depth", "t0": 5.00, "t1": 5.50, "from": 20, "to": 35, "ease": "sine.inOut",
         "ring": "depth", "caption": "Depth."},
        {"render": "R03", "param": "offset", "t0": 7.00, "t1": 7.50, "from": 0, "to": 90, "ease": "sine.inOut",
         "ring": "offset", "caption": "Offset."},
        {"render": "R04", "param": "hq", "t0": 9.00, "t1": 9.42, "from": 0, "to": 1, "ease": "step", "ring": "hq",
         "caption": None},
        {"render": "R05", "param": "rate", "t0": 11.00, "t1": 11.50, "from": 0.12, "to": 1.5, "ease": "sine.inOut",
         "ring": "rate", "caption": "Rate."},
        {"render": "R06", "param": "color", "t0": 13.00, "t1": 13.50, "from": 20, "to": 60, "ease": "sine.inOut",
         "ring": "color", "caption": "Color."},
        {"render": "R09", "param": "width", "t0": 17.00, "t1": 18.00, "from": 100, "to": 170, "ease": "sine.inOut",
         "ring": "width", "caption": None},
    ]
    sections = [
        {"t0": 0.00, "t1": 2.00, "shot": "V1", "name": "mix-turn", "audio": {"gtr": "R01"}},
        {"t0": 2.00, "t1": 4.00, "shot": "V2", "name": "title", "audio": {"gtr": "R01"}},
        {"t0": 4.00, "t1": 6.00, "shot": "V3", "name": "green", "audio": {"gtr": "R02"},
         "plate": {"engine": "green", "render": "R02"}},
        {"t0": 6.00, "t1": 8.00, "shot": "V4", "name": "blue", "audio": {"gtr": "R03"},
         "plate": {"engine": "blue", "render": "R03"}},
        {"t0": 8.00, "t1": 10.00, "shot": "V5", "name": "red", "audio": {"gtr": "R04"},
         "plate": {"engine": "red", "render": "R04"}},
        {"t0": 10.00, "t1": 12.00, "shot": "V6", "name": "purple", "audio": {"gtr": "R05"},
         "plate": {"engine": "purple", "render": "R05"}},
        {"t0": 12.00, "t1": 14.00, "shot": "V7", "name": "black", "audio": {"gtr": "R06"},
         "plate": {"engine": "black", "render": "R06"}},
        {"t0": 14.00, "t1": 17.00, "shot": "V8", "name": "free", "audio": {"gtr": "R01", "pad": "R08"}},
        {"t0": 17.00, "t1": 20.00, "shot": "V9", "name": "trial", "audio": {"gtr": "R03", "ep": "R10", "pad": "R09"}},
        {"t0": 20.00, "t1": 22.00, "shot": "V10", "name": "price",
         "audio": {"gtr": "R01", "ep": "R10", "pad": "R09", "lead": "R11", "pluck": "R12"}},
        {"t0": 22.00, "t1": 28.00, "shot": "V11", "name": "endcard", "audio": {"gtr": "R01", "pad": "R07"}},
    ]
    scope = copy.deepcopy(main["scope"])
    scope["dir"] = "/data/scope-vertical"
    scope["frames"] = int(round(DUR * 60))
    scope["featured"] = [{"t0": 0.00, "t1": 2.00, "stem": "gtr"}, {"t0": 4.00, "t1": 14.00, "stem": "gtr"},
                         {"t0": 14.00, "t1": 17.00, "stems": {"green": "gtr", "purple": "pad"}},
                         {"t0": 17.00, "t1": 20.00, "stems": {"blue": "gtr", "red": "ep", "black": "pad"}},
                         {"t0": 22.00, "t1": 24.00, "stem": "gtr"}]
    return {
        "title": "Still Life (vertical cutdown)", "fps": 60, "bpm": 120, "sr": SR, "block": 128, "duration": DUR,
        "note": "Vertical cutdown timings (treatment 9), same schema as cues.json. Same take (the hook), instruments, "
                "seeds and Choroboros settings as the main film, gestures shifted. Honesty zone 0.00-14.00. "
                "Written by audio/film/vertical.py.",
        "renders": renders, "gestures": gestures, "position_maps": main["position_maps"], "sections": sections,
        "bars": {str(b): v for b, v in VH.items()},
        "honesty_zones": HONESTY_V,
        "scope": scope,
        "levelmatch": {"sections": [[0, 14, "dry"], [17, 22, "R09ref"]], "tolerance_lu": 0.3,
                       "log": "audio/logs/level-match-vertical.json"},
        "master": main["master"],
    }


def dump_cues(obj, path):
    """Write in the same hand layout as cues.json (one render, gesture, section
    or featured entry per line)."""
    j = lambda o: json.dumps(o, ensure_ascii=False)
    L = ["{"]
    for k in ("title", "fps", "bpm", "sr", "block", "duration", "note"):
        L.append(f'  "{k}": {j(obj[k])},')
    L.append("")
    L.append('  "renders": {')
    items = list(obj["renders"].items())
    for i, (rid, r) in enumerate(items):
        L.append(f'    "{rid}": {j(r)}' + ("," if i < len(items) - 1 else ""))
    L.append("  },")
    L.append("")
    L.append('  "gestures": [')
    for i, g in enumerate(obj["gestures"]):
        L.append(f"    {j(g)}" + ("," if i < len(obj["gestures"]) - 1 else ""))
    L.append("  ],")
    L.append("")
    L.append('  "position_maps": {')
    pm = list(obj["position_maps"].items())
    for i, (k, v) in enumerate(pm):
        L.append(f'    "{k}": {j(v)}' + ("," if i < len(pm) - 1 else ""))
    L.append("  },")
    L.append("")
    L.append('  "sections": [')
    for i, s in enumerate(obj["sections"]):
        L.append(f"    {j(s)}" + ("," if i < len(obj["sections"]) - 1 else ""))
    L.append("  ],")
    L.append("")
    L.append(f'  "bars": {j(obj["bars"])},')
    L.append(f'  "honesty_zones": {j(obj["honesty_zones"])},')
    L.append("")
    sc = dict(obj["scope"])
    feat = sc.pop("featured")
    L.append('  "scope": {')
    for k, v in sc.items():
        L.append(f'    "{k}": {j(v)},')
    L.append('    "featured": [')
    for i, f in enumerate(feat):
        L.append(f"      {j(f)}" + ("," if i < len(feat) - 1 else ""))
    L.append("    ]")
    L.append("  },")
    L.append("")
    L.append(f'  "levelmatch": {j(obj["levelmatch"])},')
    L.append("")
    L.append(f'  "master": {j(obj["master"])}')
    L.append("}")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    json.load(open(path))


# ----------------------------------------------------------------- arrangement (compose helpers on the vertical map)

def v_guitar(n):
    rows = []
    for b in range(1, 8):
        rows += C.take_at("T1" if b % 2 == 1 else "T3", bar_t(b))
    rows += C.motif("M_G", bar_t(8), 5128) + C.motif("M_A7", bar_t(9), 5129) + C.motif("M_G", bar_t(10), 5138)
    rows += C.take_at("T1", bar_t(11)) + C.take_at("T1", bar_t(12))
    evs = C.to_events(rows, bar_t(13) + 0.2)
    for j, (p, s, f) in enumerate(C.FINAL_STRUM):
        evs.append(NoteEvent(bar_t(13) + 0.040 * j, p, 0.80 * (1 - 0.035 * j), 12.0,
                             {"string": s, "fret": f, "seed": 51400 + j}))
    off, y = C.render_guitar(evs, 0.0, DUR, fade_out_s=0.0, level=C.GTR_LEVEL,
                             ceiling=lambda t: np.where(t < bar_t(13) - 0.003, C.GTR_CEIL["arp"],
                                                        C.GTR_CEIL["final"]))
    out = np.zeros(n)
    out[:len(y)] = y[:n]
    return out


def v_gtr_oct(n):
    y = np.zeros(n)
    kw = dict(level=C.GTR_LEVEL * 0.55, pluck=0.12, brightness=0.6, pick_noise=0.04)
    rows = C.motif("M_G", bar_t(8), 6128) + C.motif("M_A7", bar_t(9), 6129) + C.motif("M_G", bar_t(10), 6138) + \
        C.motif("T1", bar_t(11), 6211)
    rows = [(t + 0.008, p, v * 0.8, s, f, sd + 7, False) for (t, p, v, s, f, sd, sq) in rows]
    off, a = C.render_guitar(C.to_events(rows, bar_t(12) - 0.06, octave=1), 14.0, bar_t(12),
                             ceiling=C.GTR_CEIL["arp"] + 3, **kw)
    y[off:off + len(a)] += a[: max(0, n - off)]
    return y


def v_pad(n):
    y = C.cut_after(C.render_pad(C.pad_events([8, 9, 10, 11], bar_t(12)), n, attack=0.3, env_amount=1.0),
                    bar_t(12) + 1.9)
    y += C.render_pad(C.pad_events([12, 13], bar_t(13) + 2.6), n, attack=0.35, env_amount=1.0)
    y = tape(eq(y, PAD_EQ, SR), drive_db=6.0, bias=0.04, hf_db=-0.5)
    return peak_control(y, 3.0, 3.0, 120.0)


def v_ep(n):
    rng = np.random.default_rng(2929)
    evs = []
    t0 = bar_t(9)
    for tb, d, vel in ((1.0, 0.45, 0.58), (1.5, 0.13, 0.5)):          # enters at 17.00 (beat 3), then beat 4
        dt, dv = C.hum(rng)
        ch = C.chord_at(t0 + tb + 0.01)
        for j, p in enumerate(C.EP_VOICE[ch]):
            roll = 0.004 * j + abs(rng.normal(0, 0.002))
            evs.append(NoteEvent(t0 + tb + max(dt, 0.0) + roll, p, vel * (1 + dv) * (1 - 0.03 * j), d - roll,
                                 {"seed": int(rng.integers(1 << 30)), "hit": 0.0 if tb == 1.0 else tb}))
    evs += C.ep_bars([10, 11], seed=2930)
    return C.ep_with_bell(evs, n)


def v_lead(n):
    b = bar_t(11)
    line = [(b + 1.0, 81, 0.22), (b + 1.25, 78, 0.55), (b + 1.875, 76, 0.1)]
    rng = np.random.default_rng(3030)
    evs = []
    for i, (t, p, d) in enumerate(line):
        dt, dv = C.hum(rng)
        evs.append(NoteEvent(t + 0.015 + dt, p, (0.9 if i == 1 else 0.8) * (1 + dv), d,
                             {"string": 5, "fret": p - 64, "seed": 30300 + i}))
    g = RealGuitar(level=C.LEAD_LEVEL, sustain_s=9.0, brightness=0.55, pluck=0.2, pick_noise=0.04)
    y = render_events_pre(g, evs, n)
    y = C.cut_after(y, bar_t(12) - 0.02, 0.03)
    return comp_pedal(y)


def v_pluck(n):
    pat = [81, 85, 88, 90, 93, 90, 88, 85]
    rng = np.random.default_rng(3131)
    evs = []
    for k in range(16):
        dt, dv = C.hum(rng, 3.0, 0.06)
        vel = (0.62 if k == 8 else 0.8 if k % 4 == 0 else 0.62 if k % 2 == 0 else 0.5) * (1 + dv)
        evs.append(NoteEvent(C.swing16(bar_t(11) + k * 0.125, 0.54, bar_t(11)) + dt, pat[k % 8], vel, 0.1,
                             {"seed": 31000 + 30 * 20 + k}))
    return peak_control(render_events(FMBell(level=0.14), evs, n), 4.0, 1.5, 50.0)


def v_arp(n):
    evs = []
    evs += C.arp_run(14.0, 20.0, 0.125, 1800.0, 0.55, 4204)
    evs += C.arp_run(20.0, 21.9, 0.375, 2100.0, 0.42, 4206)
    from instruments import ArpPluck
    y = C.render_split(lambda: ArpPluck(level=0.22), evs, n, silences=[])
    return peak_control(y, 3.0, 1.5, 50.0)


def v_bass(n):
    evs = []
    for b in range(2, 8):
        evs += C.groove_a_bass(b, 6100 + b, pickup=(44 if b == 7 else None))
    for b in range(8, 12):
        evs += C.groove_b_bass(b, 6100 + b)
    evs += [C.bass_note(bar_t(12), 33, 1.9, 0.6, 6112), C.bass_note(bar_t(13), 38, 2.5, 0.7, 6113)]
    y = eq(C.render_split(C.make_bass, evs, n, silences=[]),
           [("lowshelf", 75, -2.0, 0.7), ("peak", 140, 1.5, 1.0), ("lowpass", 3000, 0, 0.7)], SR)
    return ceiling_control(y, float(todb(np.abs(y).max())) - 4.0, 3.0, 80.0)


def v_drum_events():
    ev = []
    for b in range(2, 8):
        ev += C.groove_a_bar(bar_t(b), 7700 + b * 10, fill=(b == 7))
    for b in range(8, 12):
        ev += C.groove_b_bar(bar_t(b), 7700 + b * 10, fill=("full" if b == 11 else None), crash=(b in (8, 11)))
    ev += C.drum_hits("crash", [(17.0, 0.75)], 7790, 0.5)                 # the trial card cut (beat 3)
    ev += C.drum_hits("kick", [(bar_t(13), 0.55)], 7791)
    ev += C.drum_hits("crash", [(bar_t(13), 0.45)], 7792, 0.5)
    return ev


def v_fx(n):
    y = np.zeros(n)

    def put(a, t):
        s = smp(t)
        y[s:s + len(a)] += a[: max(0, n - s)]

    put(impact(seed=721, level=10 ** (-8 / 20)), 2.00)
    put(downlifter(1.8, 761, -28.0), 2.05)
    for k, t in enumerate((6.0, 8.0, 10.0, 12.0)):
        put(swish(seed=731 + k, dur=0.5, peak_db=-30.0), t - 0.25)
    put(riser(0.97, db0=-32, db1=-19, seed=781), 13.0)
    put(reverse_crash(1.0, 782, -24.0), 14.0 - 1.0)
    put(downlifter(2.0, 762, -26.0), 14.05)
    put(reverse_crash(1.5, 775, -24.0), 24.0 - 1.5)
    return y


def compose_vertical(film):
    n = film.n
    t0 = time.time()
    saved = C.H
    C.H = VH                                   # the compose helpers read the harmony map from C.H
    try:
        for name, fn in (("gtr", v_guitar), ("gtr_oct", v_gtr_oct), ("pad", v_pad), ("ep", v_ep), ("lead", v_lead),
                         ("pluck", v_pluck), ("arp", v_arp), ("bass", v_bass), ("fx", v_fx)):
            y = fn(n)
            write(film.stem_path(name), y)
            print(f"  {name:7s} peak {todb(np.abs(y).max()):6.2f} dBFS", flush=True)
        write(film.stem_path("bells"), np.zeros(n))
        parts = C.render_drums(v_drum_events(), n, silences=[])
        tot = np.zeros(n)
        for k in C.KINDS:
            write(film.stem_path(f"drums_{k}"), parts[k])
            tot += parts[k]
        write(film.stem_path("drums"), tot)
        print(f"  drums   peak {todb(np.abs(tot).max()):6.2f} dBFS")
    finally:
        C.H = saved
    print(f"vertical compose {time.time() - t0:.1f} s")


def run(mod, *args):
    cmd = [sys.executable, os.path.join(HERE, mod), "--film", "vertical", *args]
    print("$", os.path.basename(mod), " ".join(cmd[2:]), flush=True)
    subprocess.run(cmd, check=True, cwd=HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compose", action="store_true")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    path = os.path.join(REPO, "film", "cues-vertical.json")
    obj = vertical_cues()
    if os.path.exists(path):            # keep a pre-roll already chosen by an earlier sweep
        old = json.load(open(path))
        for k in ("preroll", "swoosh_t"):
            if k in old["renders"].get("R05", {}):
                obj["renders"]["R05"][k] = old["renders"]["R05"][k]
    dump_cues(obj, path)
    film = Film("vertical")
    if not a.skip_compose:
        compose_vertical(film)
    run("render_dsp.py", "--sweep", "--jobs", str(a.jobs))
    run("levelmatch.py")
    run("mix.py")
    run("scope.py")
    run("qc.py")


if __name__ == "__main__":
    main()
