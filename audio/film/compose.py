#!/usr/bin/env python3
"""Compose and render the dry mono stems of "Still Life" (treatment section 7).

Every stem is mono, dry, 48 kHz float32 and exactly film length, so each
Choroboros render is aligned to film time. Bar n starts at 2 (n - 1) s.

Stems (build dir, stems/):
  gtr    the take (T1 T3 T4), strums, motifs M_G / M_A, block P pasted at
         16 20 24 28 32 50 58 (sample-identical), payoff, final strum, last note
  ep     EP comp, bars 28-31
  pad    pad chords (all internal motion off), bars 19-35 and 38-41
  lead   lead guitar, bars 30-31
  pluck  FM pluck 16ths, bars 30-31
  bells  17 rising FM bells, bar 19 (dry, no Choroboros)
  bass   pluck bass (dry)
  drums  kick, snare, hats, rim, shaker, crash (dry); sub-stems in stems/drums_*.wav
  fx     risers, impacts, reverse guitar swell, four smear swishes (dry)
All stems carry the three hard digital silences (7.85-8.00, 49.85-50.00,
69.50-70.00) with a 3 ms fade to zero before each.

Usage: python3 audio/film/compose.py [--only gtr,pad] [--png]
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from common import SR, Film, bar_t, dual, hard_silence, jdump, smp, stats, todb, write
from instruments import (FMBell, FilmEPiano, FilmGuitar, MonoCrash, PAD_EQ, Shaker, comp_pedal, fold_pad, impact,
                         mono_pad, ceiling_control, peak_control, render_events, reverse_guitar, riser, swish)
from synth import Bass, HiHat, Kick, Rim, Snare
from synth.filters import eq
from synth.instrument import NoteEvent

# ----------------------------------------------------------------- harmony (treatment 7.3, 7.4)

OPEN = (40, 45, 50, 55, 59, 64)            # E2 A2 D3 G3 B3 E4
# guitar / pad voicing, low to high, and the (string, fret) each note is played on
VOICE = {
    "D": [50, 57, 61, 64, 66],             # Dmaj9    D3 A3 C#4 E4 F#4
    "Bm": [47, 54, 57, 62, 64],            # Bm11     B2 F#3 A3 D4 E4
    "G": [43, 50, 54, 57, 61],             # Gmaj9#11 G2 D3 F#3 A3 C#4
    "A": [45, 52, 54, 59, 64],             # A6sus2   A2 E3 F#3 B3 E4
}
FINGER = {   # one string per chord tone so every note rings until its string is replayed
    "D": {50: (1, 5), 57: (2, 7), 61: (3, 6), 64: (5, 0), 66: (4, 7)},
    "Bm": {47: (1, 2), 54: (2, 4), 57: (3, 2), 62: (4, 3), 64: (5, 0)},
    "G": {43: (0, 3), 50: (1, 5), 54: (2, 4), 57: (3, 2), 61: (4, 2)},
    "A": {45: (0, 5), 52: (1, 7), 54: (2, 4), 59: (3, 4), 64: (4, 5)},
}
MOTIF = {   # eight eighths per bar
    "D": [50, 57, 61, 64, 66, 64, 61, 57],     # M_D
    "Bm": [47, 54, 57, 62, 64, 62, 57, 54],    # M_Bm
    "G": [43, 50, 54, 57, 61, 57, 54, 50],     # M_G
    "A": [45, 52, 54, 59, 64, 59, 54, 52],     # M_A
}
EP_VOICE = {"D": [54, 57, 61, 64], "Bm": [57, 62, 64, 66], "G": [59, 61, 66, 69], "A": [64, 66, 69, 71]}
BASS_ROOT = {"D": 38, "Bm": 35, "G": 31, "A": 33}          # D2 B1 G1 A1
FINAL_STRUM = [(50, 0, 10), (57, 1, 12), (61, 2, 11), (64, 3, 9), (66, 4, 7), (69, 5, 5)]  # D3 A3 C#4 E4 F#4 A4

# bar -> chord (treatment 7.6)
MAIN_CHORDS = {1: "D", 2: "D", 3: "Bm", 4: "A", 5: "D", 6: "Bm", 7: "G", 8: "A"}
for _b in range(9, 19):
    MAIN_CHORDS[_b] = "D" if _b % 2 == 1 else "Bm"
MAIN_CHORDS.update({19: "G", 20: "A", 21: "Bm", 22: "G", 23: "A", 24: "G", 25: "A", 26: "D", 27: "Bm",
                    28: "G", 29: "A", 30: "D", 31: "Bm", 32: "G", 33: "A", 34: "G", 35: "A", 36: "D",
                    37: "Bm", 38: "G", 39: "A", 40: "D", 41: "D", 42: "D"})

VEL_ONE, VEL_ELSE = 100 / 127, 78 / 127    # treatment 7.2: velocity 100 on beat 1, 78 elsewhere
TAKE_SEED = 1954                            # the one fixed seed of the take
SILENCES = [(7.85, 8.00), (49.85, 50.00), (69.50, 70.00)]


def hum(rng, t_ms=4.0, v_pct=0.06):
    """Fixed-seed humanise: timing SD t_ms/2 clipped to +-t_ms, velocity SD
    v_pct/2 clipped to +-v_pct."""
    dt = float(np.clip(rng.normal(0, t_ms / 2000.0), -t_ms / 1000.0, t_ms / 1000.0))
    dv = float(np.clip(rng.normal(0, v_pct / 2), -v_pct, v_pct))
    return dt, dv


def cut_after(y, t, fade_s=0.003):
    """Hard cut at t: raised-cosine fade to exactly zero ending at t, zero after."""
    y = np.array(y, dtype=np.float64, copy=True)
    a = smp(t)
    k = max(1, smp(fade_s))
    lo = max(0, a - k)
    g = 0.5 + 0.5 * np.cos(np.pi * (np.arange(k) + 1) / k)
    seg = y[lo:a]
    y[lo:a] = seg * g[k - len(seg):]
    y[a:] = 0.0
    return y


def render_split(make, evs, n, silences=None):
    """Render events in groups separated by the hard silences: each group is
    rendered on its own (per-event seeds keep every note identical) and cut at
    the start of the next silence, so no tail survives a digital silence."""
    silences = SILENCES if silences is None else silences
    edges = [0.0] + [b for (_, b) in silences]
    cuts = [a for (a, _) in silences] + [None]
    y = np.zeros(n)
    for lo, cut in zip(edges, cuts):
        grp = [e for e in evs if e.start_s >= lo - 1e-9 and (cut is None or e.start_s < cut)]
        if not grp:
            continue
        g = render_events(make(), grp, n)
        y += cut_after(g, cut) if cut is not None else g
    return y


# ----------------------------------------------------------------- guitar

def take():
    """The take: T1 (M_D), T3 (M_Bm), T4 (M_A), one fixed seed. Returns
    {name: [(t_rel, pitch, vel, string, fret, note_seed), ...]}. The first
    note of T1 is never early, so a block starting on T1 starts on its sample."""
    rng = np.random.default_rng(TAKE_SEED)
    out = {}
    for k, (name, ch) in enumerate((("T1", "D"), ("T3", "Bm"), ("T4", "A"))):
        evs = []
        for i, p in enumerate(MOTIF[ch]):
            dt, dv = hum(rng)
            if name == "T1" and i == 0:
                dt = abs(dt)
            v = (VEL_ONE if i == 0 else VEL_ELSE) * (1 + dv)
            s, f = FINGER[ch][p]
            evs.append((i * 0.25 + dt, p, v, s, f, TAKE_SEED * 10 + k * 100 + i))
        out[name] = evs
    return out


def motif(ch, t0, seed):
    """One bar of a motif (M_G, M_A, ...) humanised with its own seed."""
    rng = np.random.default_rng(seed)
    evs = []
    for i, p in enumerate(MOTIF[ch]):
        dt, dv = hum(rng)
        v = (VEL_ONE if i == 0 else VEL_ELSE) * (1 + dv)
        s, f = FINGER[ch][p]
        evs.append((t0 + i * 0.25 + dt, p, v, s, f, seed * 10 + i))
    return evs


def take_at(name, t0):
    return [(t0 + t, p, v, s, f, sd) for (t, p, v, s, f, sd) in take()[name]]


def strum_bar(ch, t0, seed):
    """Bars 5-6 rhythm: dotted quarter on 1 (down), dotted quarter on 2-and
    (down), eighth on 4 (up, top strings), all strings muted on 4-and."""
    rng = np.random.default_rng(seed)
    evs = []
    tones = VOICE[ch]
    hits = [(0.0, "down", VEL_ONE, tones), (0.75, "down", 92 / 127, tones), (1.5, "up", 70 / 127, tones[2:])]
    for h, (tb, kind, vel, notes) in enumerate(hits):
        dt, dv = hum(rng)
        order = list(notes) if kind == "down" else list(notes)[::-1]
        spread = 0.012 if kind == "down" else 0.009
        for j, p in enumerate(order):
            s, f = FINGER[ch][p]
            v = vel * (1 + dv) * (1 - 0.05 * j)
            evs.append((t0 + tb + max(dt, -0.002 if tb == 0 else -0.004) + j * spread, p, v, s, f,
                        seed * 10 + h * 10 + j))
    return evs


def to_events(rows, gate_end, short=None):
    """rows -> NoteEvents that ring until gate_end (or until their string is
    replayed: FilmGuitar chokes by string). short: {index: dur_s}."""
    evs = []
    for i, (t, p, v, s, f, sd) in enumerate(rows):
        dur = gate_end - t
        if short and i in short:
            dur = short[i]
        evs.append(NoteEvent(max(0.0, t), int(p), float(np.clip(v, 0.02, 1.0)), max(0.02, dur),
                             {"string": s, "fret": f, "seed": int(sd)}))
    return evs


def render_guitar(evs, t_start, t_end, fade_out_s=0.004, ceiling=None, **kw):
    """Render a segment of guitar events with its own instrument, keep only
    [t_start, t_end) of film time (the segment is damped or cut there) and return
    (offset_sample, audio). ceiling: pick-attack control of the DI (dBTP, scalar
    or a function of segment time), see GTR_CEIL."""
    g = FilmGuitar(**kw)
    rel = [NoteEvent(e.start_s - t_start, e.pitch, e.vel, e.dur_s, e.meta) for e in evs]
    n = smp(t_end - t_start)
    y = render_events(g, rel, n + smp(6.0))
    if ceiling is not None:
        c = ceiling(np.arange(len(y)) / SR) if callable(ceiling) else ceiling
        y = ceiling_control(y, c)
    y = y[:n]
    k = smp(fade_out_s)
    if k:
        y[-k:] *= 0.5 + 0.5 * np.cos(np.pi * (np.arange(k) + 1) / k)
    return smp(t_start), y


GTR_LEVEL = 0.17        # FilmGuitar level: take peaks about -13 dBFS into the plugin
# Pick-attack control of the guitar DI (dBTP ceilings, before Choroboros). One
# absolute ceiling for all arpeggio material (take, P, motifs, lead-in), so the
# same notes are treated the same everywhere; the strums and the final chord
# get their own ceilings a few dB above.
GTR_CEIL = {"arp": -15.5, "strum": -11.5, "final": -10.5}
LEAD_LEVEL = 0.19

P_PASTES = [16.0, 20.0, 24.0, 28.0, 32.0, 50.0, 58.0]


def main_guitar(n):
    y = np.zeros(n)
    segs = []
    # bars 1-4: T1 | T1 (copy) | T3 | T4, ringing, cut at 7.85
    rows = take_at("T1", 0.0) + take_at("T1", 2.0) + take_at("T3", 4.0) + take_at("T4", 6.0)
    segs.append(render_guitar(to_events(rows, 8.0), 0.0, 7.85, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    # bars 5-6 strums, bars 7-8 M_G M_A, all strings damped at 15.94
    rows = strum_bar("D", bar_t(5), 5105) + strum_bar("Bm", bar_t(6), 5106)
    evs = []
    for r in rows:
        bar0 = bar_t(5) if r[0] < bar_t(6) - 0.01 else bar_t(6)
        evs += to_events([r], bar0 + 1.75)                 # all strings muted on 4-and (the 4 is an eighth)
    rows = motif("G", bar_t(7), 5107) + motif("A", bar_t(8), 5108)
    evs += to_events(rows, 15.94)
    segs.append(render_guitar(evs, 8.0, 16.0, level=GTR_LEVEL,
                              ceiling=lambda t: np.where(t < 4.0, GTR_CEIL["strum"], GTR_CEIL["arp"])))
    # block P, rendered once, pasted sample-identical
    P = p_block_cached()
    for t in P_PASTES:
        segs.append((smp(t), P))
    # bars 22-25: M_G M_A M_G M_A, cut at 49.85
    rows = motif("G", bar_t(22), 5122) + motif("A", bar_t(23), 5123) + motif("G", bar_t(24), 5124) + \
        motif("A", bar_t(25), 5125)
    segs.append(render_guitar(to_events(rows, 50.0), 42.0, 49.85, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    # bars 28-29 (trial): M_G M_A, damped at 57.94 so P at 58 starts from silence
    rows = motif("G", bar_t(28), 5128) + motif("A", bar_t(29), 5129)
    segs.append(render_guitar(to_events(rows, 57.94), 54.0, 58.0, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    # payoff: T1 | T3 (same notes, velocities, seed), M_G, M_A, final strum, one note
    rows = take_at("T1", bar_t(36)) + take_at("T3", bar_t(37)) + motif("G", bar_t(38), 5138) + \
        motif("A", bar_t(39), 5139)
    evs = to_events(rows, bar_t(40) + 0.2)
    # 78.00 final Dmaj9, down strum 40 ms per string, mf, clean attack exactly on the bar
    for j, (p, s, f) in enumerate(FINAL_STRUM):
        evs.append(NoteEvent(bar_t(40) + 0.040 * j, p, 0.80 * (1 - 0.035 * j), 12.0,
                             {"string": s, "fret": f, "seed": 51400 + j}))
    # 82.00 one F#4, pp
    evs.append(NoteEvent(bar_t(42), 66, 0.36, 6.0, {"string": 4, "fret": 7, "seed": 51420}))
    segs.append(render_guitar(evs, 70.0, 86.0, fade_out_s=0.0, level=GTR_LEVEL,
                              ceiling=lambda t: np.where(t < 8.0 - 0.003, GTR_CEIL["arp"], GTR_CEIL["final"])))
    for off, a in segs:
        y[off:off + len(a)] += a[: max(0, n - off)]
    return y


_P_CACHE = {}


def p_block_cached():
    """Block P = T1 | T3 from silent strings, last eighth played short, all
    strings damped at +3.94 s (60 ms release). Exactly 4.000 s, rendered once."""
    if "P" not in _P_CACHE:
        rows = take_at("T1", 0.0) + take_at("T3", 2.0)
        evs = to_events(rows, 3.94, short={len(rows) - 1: 0.14})
        _, y = render_guitar(evs, 0.0, 4.0, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL)
        _P_CACHE["P"] = y
    return _P_CACHE["P"]


def reverse_swell(t_end=7.85, length_s=1.1):
    """Reversed dry guitar D3 swelling into t_end (FX stem, not the gtr stem)."""
    g = FilmGuitar(level=GTR_LEVEL, pick_noise=0.0)
    y = render_events(g, [NoteEvent(0.0, 50, 0.85, 3.0, {"string": 2, "fret": 0, "seed": 777})], smp(3.2))
    return reverse_guitar(y, length_s)


# ----------------------------------------------------------------- lead, EP, pad, pluck, bells

def main_lead(n):
    b30, b31 = bar_t(30), bar_t(31)
    line = [(b30, 78, 1.0), (b30 + 1.0, 76, 1.0), (b31, 74, 1.0), (b31 + 1.0, 73, 0.5), (b31 + 1.5, 69, 0.45)]
    rng = np.random.default_rng(3030)
    evs = []
    for i, (t, p, d) in enumerate(line):
        dt, dv = hum(rng)
        # laid back 20 ms behind the beat, like a singer (and off the kick/bass/pluck attacks)
        evs.append(NoteEvent(t + 0.020 + dt, p, 0.86 * (1 + dv), d, {"string": 5, "fret": p - 64,
                                                                       "seed": 30300 + i}))
    g = FilmGuitar(level=LEAD_LEVEL, sustain_s=9.0, brightness=0.55, pluck=0.2, pick_noise=0.04)
    rel = [NoteEvent(e.start_s - 56.0, e.pitch, e.vel, e.dur_s, e.meta) for e in evs]
    a = render_events(g, rel, smp(8.0))
    y = np.zeros(n)
    y[smp(56.0):smp(56.0) + len(a)] += a
    return comp_pedal(y)


def ep_bars(bars_chords, seed=2828):
    """EP comp: beat 1 (dotted quarter), 2-and tied through 3, beat 4 staccato
    eighth. Small roll between the notes of each chord."""
    rng = np.random.default_rng(seed)
    evs = []
    for b, ch, skip_before in bars_chords:
        t0 = bar_t(b)
        for tb, d, vel in ((0.0, 0.70, 0.62), (0.75, 0.72, 0.56), (1.5, 0.13, 0.50)):
            if skip_before is not None and tb < skip_before:
                continue
            dt, dv = hum(rng)
            for j, p in enumerate(EP_VOICE[ch]):
                roll = 0.004 * j + abs(rng.normal(0, 0.002))
                evs.append(NoteEvent(t0 + tb + dt + roll, p, vel * (1 + dv) * (1 - 0.03 * j), d - roll,
                                     {"seed": int(rng.integers(1 << 30))}))
    return evs


def main_ep(n):
    evs = ep_bars([(28, "G", None), (29, "A", None), (30, "D", None), (31, "Bm", None)])
    y = render_events(FilmEPiano(level=0.1, bark=1.0, tine=0.75), evs, n)
    return peak_control(y, 6.0, lookahead_ms=2.0, release_ms=80.0)


def pad_events(bar_chords, t_end, vel=0.75):
    """Pad chords with common tones tied across bar lines (no re-attack)."""
    evs = []
    open_notes = {}
    for b, ch in bar_chords:
        t0 = bar_t(b)
        cur = set(VOICE[ch])
        for p in list(open_notes):
            if p not in cur:
                s = open_notes.pop(p)
                evs.append((s, p, t0 + 0.05 - s))       # tiny legato overlap
        for p in VOICE[ch]:
            if p not in open_notes:
                open_notes[p] = t0
    for p, s in open_notes.items():
        evs.append((s, p, t_end - s))
    return [NoteEvent(s, p, vel, d, {"seed": 3000 + int(s * 100) + p}) for s, p, d in sorted(evs)]


def render_pad(evs, n, attack, release=1.8, env_amount=1.4):
    inst = mono_pad(attack=attack, release=release, env_amount=env_amount)
    return fold_pad(render_events(inst, evs, n))


def main_pad(n):
    y = np.zeros(n)
    # bars 19-25: slow attack (breakdown, looks, build), cut at 49.85
    y += cut_after(render_pad(pad_events([(b, MAIN_CHORDS[b]) for b in range(19, 26)], 49.85), n, attack=0.9), 49.85)
    # bars 26-35: faster attack so the pad lands with the impact at 50.00; cut at 69.50
    y += cut_after(render_pad(pad_events([(b, MAIN_CHORDS[b]) for b in range(26, 36)], 69.5), n, attack=0.3,
                              env_amount=1.0), 69.5)
    # bars 38-40: end card; released from 81.00
    y += render_pad(pad_events([(38, "G"), (39, "A"), (40, "D")], 81.0), n, attack=0.9)
    return peak_control(eq(y, PAD_EQ, SR), 3.0, 3.0, 120.0)


def main_pluck(n):
    pat = {"D": [81, 85, 88, 90, 93, 90, 88, 85], "Bm": [83, 86, 88, 90, 93, 90, 88, 86]}
    rng = np.random.default_rng(3131)
    evs = []
    for b in (30, 31):
        ch = MAIN_CHORDS[b]
        for k in range(16):
            p = pat[ch][k % 8]
            dt, dv = hum(rng, 3.0, 0.06)
            vel = (0.62 if k == 8 else 0.8 if k % 4 == 0 else 0.62 if k % 2 == 0 else 0.5) * (1 + dv)
            evs.append(NoteEvent(bar_t(b) + k * 0.125 + dt, p, vel, 0.1, {"seed": 31000 + b * 20 + k}))
    return peak_control(render_events(FMBell(level=0.14), evs, n), 4.0, 1.5, 50.0)


BELL_NOTES_A = [67, 69, 71, 73, 74, 76, 78, 81, 83, 85]      # G4 A4 B4 C#5 D5 E5 F#5 A5 B5 C#6 (ten)
BELL_NOTES_B = [86, 88, 90, 93, 95, 97, 98]                  # D6 E6 F#6 A6 B6 C#7 D7 (seven)


def bells_events(t_a, t_b):
    evs = []
    for k, p in enumerate(BELL_NOTES_A):
        evs.append(NoteEvent(t_a + 0.125 * k, p, 0.7, 0.1, {"seed": 36000 + k}))
    for k, p in enumerate(BELL_NOTES_B):
        evs.append(NoteEvent(t_b + 0.125 * k, p, 0.7, 0.1, {"seed": 36100 + k}))
    return evs


BELL_PEAK_DB = -24.0


def main_bells(n):
    y = render_events(FMBell(level=0.3, ring=0.35), bells_events(36.0, 37.25), n)
    # every bell about -24 dBFS: normalise each bell's own peak
    return normalise_hits(y, [36.0 + 0.125 * k for k in range(10)] + [37.25 + 0.125 * k for k in range(7)],
                          BELL_PEAK_DB)


def normalise_hits(y, times, peak_db):
    """Scale so the loudest hit peaks at peak_db (the bells are already even)."""
    pk = max(np.abs(y[smp(t):smp(t) + smp(0.125)]).max() for t in times)
    return y * (10 ** (peak_db / 20) / max(pk, 1e-9))


# ----------------------------------------------------------------- bass

def bass_note(t, p, d, v, seed):
    return NoteEvent(t, p, v, d, {"seed": seed})


def groove_a_bass(bar, ch, seed, stop_at=None):
    t0 = bar_t(bar)
    r = BASS_ROOT[ch]
    notes = [(0.0, r, 0.68, 0.9), (0.75, r, 0.22, 0.7), (1.0, r, 0.9, 0.8)]
    rng = np.random.default_rng(seed)
    out = []
    for k, (tb, p, d, v) in enumerate(notes):
        dt, dv = hum(rng, 3.0, 0.05)
        t = t0 + tb + dt
        if stop_at is not None:
            if t >= stop_at:
                continue
            d = min(d, stop_at - t)
        out.append(bass_note(t, p, d, v * (1 + dv), seed * 10 + k))
    return out


def groove_b_bass(bar, ch, seed):
    t0 = bar_t(bar)
    r = BASS_ROOT[ch]
    fifth = r + 7
    notes = [(0.0, r, 0.45, 0.92), (0.75, r + 12, 0.2, 0.72), (1.0, r, 0.45, 0.85), (1.75, fifth, 0.2, 0.7)]
    rng = np.random.default_rng(seed)
    out = []
    for k, (tb, p, d, v) in enumerate(notes):
        dt, dv = hum(rng, 3.0, 0.05)
        out.append(bass_note(t0 + tb + dt, p, d, v * (1 + dv), seed * 10 + k))
    return out


def whole_bass(bar, ch, seed, dur=1.9, v=0.75):
    return [bass_note(bar_t(bar), BASS_ROOT[ch], dur, v, seed)]


def tour_block_bass(t_block, stop=False):
    """Bars 9-10 of groove A, identical in every tour pass (same offsets, same
    per-note seeds). stop=True is Black's pass: nothing after beat 4 of bar 2."""
    evs = groove_a_bass(9, "D", 6109) + groove_a_bass(10, "Bm", 6110, stop_at=(bar_t(10) + 1.5) if stop else None)
    return [NoteEvent(e.start_s - bar_t(9) + t_block, e.pitch, e.vel, e.dur_s, dict(e.meta)) for e in evs]


def main_bass_events():
    evs = []
    for b in range(5, 9):
        evs += groove_a_bass(b, MAIN_CHORDS[b], 6000 + b)
    for k, t in enumerate((16.0, 20.0, 24.0, 28.0, 32.0)):
        evs += tour_block_bass(t, stop=(k == 4))
    for b, ch in ((19, "G"), (20, "A"), (21, "Bm"), (22, "G"), (23, "A"), (24, "G")):
        evs += whole_bass(b, ch, 6000 + b, v=0.7)
    t = bar_t(25)
    evs += [bass_note(t, 45, 0.45, 0.8, 60250), bass_note(t + 0.5, 47, 0.45, 0.85, 60251),
            bass_note(t + 1.0, 49, 0.85, 0.9, 60252)]                                # A2 B2 C#3
    for b in range(26, 32):
        evs += groove_b_bass(b, MAIN_CHORDS[b], 6000 + b)
    for b in range(32, 36):
        evs += whole_bass(b, MAIN_CHORDS[b], 6000 + b, v=0.7)
    evs += whole_bass(38, "G", 6038, v=0.62) + whole_bass(39, "A", 6039, v=0.62)
    evs += [bass_note(bar_t(40), 38, 3.0, 0.7, 6040)]                                 # D2, released 81.00
    return evs


def make_bass():
    return Bass(SR, 4, kind="pluck", cutoff=150.0, env_octaves=1.9, decay_s=0.2, resonance=0.18, sub_level=0.6,
                release_s=0.09, level=0.42)


def main_bass(n):
    y = render_split(make_bass, main_bass_events(), n)
    return peak_control(eq(y, [("lowpass", 2500, 0, 0.7)], SR), 5.0, 3.0, 80.0)


# ----------------------------------------------------------------- drums

GM = {"kick": 36, "rim": 37, "snare": 38, "chh": 42, "ohh": 46, "shaker": 70, "crash": 49}
ACC = {"X": 1.0, "x": 0.8, "o": 0.55, "g": 0.32}


def grid(pattern, t0, step=0.125):
    out = []
    k = 0
    for ch in pattern:
        if ch in " |":
            continue
        if ch in ACC:
            out.append((t0 + k * step, ACC[ch]))
        k += 1
    return out


def drum_hits(kind, hits, seed, t_ms=2.0, v_pct=0.05):
    rng = np.random.default_rng(seed)
    evs = []
    for k, (t, v) in enumerate(hits):
        dt, dv = hum(rng, t_ms, v_pct)
        evs.append((kind, max(0.0, t + dt), float(np.clip(v * (1 + dv), 0.05, 1.0)), seed * 100 + k))
    return evs


def groove_a_bar(t0, seed, fill=False, flam=False, stop_at=None):
    ev = []
    ev += drum_hits("kick", grid("X.....x.........", t0), seed + 1)
    ev += drum_hits("snare", grid("........X.......", t0), seed + 2)
    ev += drum_hits("chh", grid("x.o.x.o.x.o.x.o." if not fill else "x.o.x.o.x.o.....", t0), seed + 3, 2.5, 0.08)
    if fill:
        ev += drum_hits("snare", grid("............goxX", t0), seed + 4)
    elif flam:
        ev += drum_hits("snare", [(t0 + 1.5 - 0.028, 0.34), (t0 + 1.5, 0.92)], seed + 6, 0.5)
    else:
        ev += drum_hits("rim", grid("............o...", t0), seed + 7)
    if stop_at is not None:
        ev = [e for e in ev if e[1] < stop_at - 1e-6]
    return ev


def groove_b_bar(t0, seed, fill=False, crash=False):
    ev = []
    ev += drum_hits("kick", grid("X.....x.o.....x.", t0), seed + 1)       # the kick on 3 is lighter
    ev += drum_hits("snare", grid("....X.......X...", t0), seed + 2)
    hats = "xgogxgogxgogxgO" if not fill else "xgogxgogxgog...."
    hh = []
    k = 0
    for ch in hats:
        if ch in ACC:
            hh.append(("chh", t0 + k * 0.125, ACC[ch]))
        elif ch == "O":
            hh.append(("ohh", t0 + k * 0.125, 0.62))
        k += 1
    if not fill:
        hh.append(("chh", t0 + 15 * 0.125, 0.4))
    rng = np.random.default_rng(seed + 3)
    for j, (kind, t, v) in enumerate(hh):
        dt, dv = hum(rng, 2.5, 0.08)
        ev.append((kind, t + dt, v * (1 + dv), (seed + 3) * 100 + j))
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxoxgx", t0), seed + 4, 3.0, 0.1)
    if fill:
        ev += drum_hits("snare", grid("............ooxX", t0), seed + 5)
    if crash:
        ev += drum_hits("crash", [(t0, 0.85)], seed + 6, 0.5)
    return ev


def tour_block_drums(t_block, stop=False):
    ev = groove_a_bar(bar_t(9), 7109) + groove_a_bar(bar_t(10), 7110, fill=not stop,
                                                     stop_at=(bar_t(10) + 1.5) if stop else None)
    return [(k, t - bar_t(9) + t_block, v, s) for (k, t, v, s) in ev]


def main_drum_events():
    ev = []
    ev += groove_a_bar(bar_t(5), 7005) + groove_a_bar(bar_t(6), 7006, fill=True)
    ev += groove_a_bar(bar_t(7), 7007) + groove_a_bar(bar_t(8), 7008, flam=True)
    for k, t in enumerate((16.0, 20.0, 24.0, 28.0, 32.0)):
        ev += tour_block_drums(t, stop=(k == 4))
    ev += drum_hits("kick", [(bar_t(20), 0.5)], 7020)
    for b in range(21, 25):
        ev += drum_hits("kick", [(bar_t(b), 0.62)], 7000 + b * 3)
        ev += drum_hits("rim", [(bar_t(b) + 1.0, 0.6)], 7001 + b * 3)
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxoxgx" * 2, bar_t(23)), 7023, 3.0, 0.1)
    t = bar_t(25)
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxox", t), 7025, 3.0, 0.1)
    ev += drum_hits("kick", [(t, 0.8), (t + 1.0, 0.8)], 7026)
    build = [(t + 0.25 * k, 0.32 + 0.05 * k) for k in range(4)] + \
            [(t + 1.0 + 0.125 * k, 0.55 + 0.06 * k) for k in range(7)]
    ev += drum_hits("snare", build, 7027, 1.5)
    for b in range(26, 32):
        ev += groove_b_bar(bar_t(b), 7000 + b * 10, fill=(b == 31), crash=(b in (26, 28, 30)))
    for b in range(32, 36):
        ev += drum_hits("kick", [(bar_t(b), 0.7)], 7000 + b * 10)
    ev += drum_hits("kick", [(bar_t(40), 0.55)], 7400)
    ev += drum_hits("crash", [(bar_t(40), 0.45)], 7401, 0.5)
    return ev


DRUM_KITS = {
    "kick": lambda: Kick(SR, 10, f_start=150.0, f_end=50.0, pitch_tau=0.03, decay_s=0.19, click=0.32, drive=1.5,
                         level=0.7),
    "snare": lambda: Snare(SR, 11, tone_hz=(190.0, 335.0), tone_decay=0.075, noise_decay=0.14, level=0.55),
    "chh": lambda: HiHat(SR, 13, tune=1.5, brightness_hz=7200.0, closed_decay=0.03, level=0.3),
    "rim": lambda: Rim(SR, 14, level=0.35),
    "shaker": lambda: Shaker(606, level=0.3),
    "crash": lambda: MonoCrash(707, level=0.3),
}
DRUM_EQ = {
    "kick": [("peak", 60, 1.0, 1.0), ("peak", 350, -2.0, 1.0), ("lowpass", 9000, 0, 0.7)],
    "snare": [("highpass", 90, 0, 0.7), ("peak", 200, 1.0, 1.2), ("peak", 5200, -2.5, 1.0), ("lowpass", 10000, 0, 0.7)],
    "chh": [("highshelf", 10000, -3.0, 0.7)],
    "rim": [],
    "shaker": [],
    "crash": [],
}
# transient control per drum (dB off the top of each sub-stem, 1.5 ms look-ahead)
DRUM_PEAK = {"kick": 4.5, "snare": 4.5}
# balance inside the DRUMS stem (dB)
DRUM_BAL = {"kick": -10.0, "snare": -12.0, "chh": -14.0, "rim": -18.0, "shaker": -21.0, "crash": -14.0}


def render_drums(ev, n, silences=None):
    parts = {}
    for kind in ("kick", "snare", "chh", "rim", "shaker", "crash"):
        rows = [e for e in ev if (e[0] == kind or (kind == "chh" and e[0] == "ohh"))]
        evs = [NoteEvent(t, 46 if k == "ohh" else GM[k], v, 0.1, {"seed": s}) for (k, t, v, s) in rows]
        y = render_split(DRUM_KITS[kind], evs, n, silences)
        if DRUM_EQ[kind]:
            y = eq(y, DRUM_EQ[kind], SR)
        if kind in DRUM_PEAK:
            y = peak_control(y, DRUM_PEAK[kind], 1.5, 50.0)
        parts[kind] = y * 10 ** (DRUM_BAL[kind] / 20)
    return parts


# ----------------------------------------------------------------- FX

def main_fx(n):
    y = np.zeros(n)

    def put(a, t_start):
        s = smp(t_start)
        y[s:s + len(a)] += a[: max(0, n - s)]

    put(riser(0.85, db0=-30, db1=-14, seed=711), 7.00)
    put(reverse_swell(7.85, 1.1) * 10 ** (-6 / 20), 7.85 - 1.1)
    put(impact(seed=721, level=10 ** (-7 / 20)), 8.00)
    for k, t in enumerate((20.0, 24.0, 28.0, 32.0)):
        put(swish(seed=731 + k, dur=0.5, peak_db=-30.0), t - 0.25)
    put(riser(1.85, db0=-30, db1=-13, seed=741), 48.00)
    put(impact(seed=751, level=10 ** (-10 / 20)), 50.00)
    return y


# ----------------------------------------------------------------- build

def apply_silences(x, silences=SILENCES):
    for a, b in silences:
        x = hard_silence(x, a, b)
    return x


def build_main(only=None, png=False):
    film = Film("main")
    n = film.n
    t_all = time.time()
    builders = {
        "gtr": main_guitar, "lead": main_lead, "ep": main_ep, "pad": main_pad, "pluck": main_pluck,
        "bells": main_bells, "bass": main_bass, "fx": main_fx,
    }
    meta = {}
    for name, fn in builders.items():
        if only and name not in only:
            continue
        t0 = time.time()
        y = apply_silences(fn(n))
        write(film.stem_path(name), y)
        meta[name] = {"seconds": round(time.time() - t0, 1), "peak_dbfs": round(float(todb(np.abs(y).max())), 2)}
        print(f"  {name:6s} {meta[name]}", flush=True)
    if not only or "drums" in only:
        t0 = time.time()
        parts = render_drums(main_drum_events(), n)
        tot = np.zeros(n)
        for k, v in parts.items():
            v = apply_silences(v)
            write(film.stem_path(f"drums_{k}"), v)
            tot += v
        write(film.stem_path("drums"), tot)
        meta["drums"] = {"seconds": round(time.time() - t0, 1), "peak_dbfs": round(float(todb(np.abs(tot).max())), 2)}
        print(f"  drums  {meta['drums']}", flush=True)
    print(f"compose done in {time.time() - t_all:.1f} s")
    return meta


def score_json():
    """Machine-readable summary of the composition (for the README and QC)."""
    t = take()
    return {
        "take_seed": TAKE_SEED,
        "take": {k: [{"t": round(r[0], 4), "pitch": r[1], "vel": round(r[2], 4), "string": r[3], "fret": r[4]}
                     for r in v] for k, v in t.items()},
        "p_pastes": P_PASTES,
        "bells": {"A": BELL_NOTES_A, "B": BELL_NOTES_B, "t_a": 36.0, "t_b": 37.25},
        "chords": MAIN_CHORDS,
        "silences": SILENCES,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = set(x for x in a.only.split(",") if x)
    build_main(only or None)
    jdump(Film("main").p("stems", "score.json"), score_json())
