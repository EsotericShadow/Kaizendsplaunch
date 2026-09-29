#!/usr/bin/env python3
"""Compose and render the dry mono stems of "Still Life" (production pass).

Section times, bar lines, the three hard silences, the two impacts, gesture
times and the Choroboros render plan are locked to the picture (cues.json).
Inside that grid the score is written around one 2-bar HOOK (the take):

  T1 (Dmaj9):  D3 . A3 . . F#4 . . C#4 E4 . .     top line F#4 -> E4
  T3 (Bm11):   B2 . F#3 . . E4 . . A3 D4 A3        E4 -> D4: sus4 -> b3, a pull-off on the B string
  (1, 1&, 2&, 3&, 4; the 4& A3 of T3 is a pickup, played short in block P)
  T4 (A7sus4 -> A7): A2 . E3 . . D4 . . G3 C#4    D4 -> C#4 on beat 4: the dominant before a drop

Five notes a bar instead of eight, with let-ring sustains on 2& and 4 where the
chorus is heard. The hook is heard dry (0.00), through all five engines in the
tour (block P, sample-identical), in full at the offer peak with the lead
answering it, and alone at the payoff (70.00, same notes, velocities, seed).

Tension and release: A7sus4 -> A7 before the drops at 8.00 and 50.00 (and
before 16.00, 58.00 and 78.00); an A pedal under G/A and A7sus4 -> A7 in the
build with the pad and arp filters opening; Gmaj9#11 floats the breakdown;
the final Dmaj9 at 78.00 is the deepest release, then space, then F#4 at 82.00.

Stems (build dir, stems/, mono dry 48 kHz float32, exactly film length):
  gtr      the featured guitar (the only guitar that goes through Choroboros)
  gtr_oct  a quiet octave double, only outside the honesty zones (dry, gets verb)
  ep       EP comp + a quiet FM bell layer, gentle tape
  pad      Juno pad + a soft choir layer (no vibrato, no unison), gentle tape
  lead     lead guitar answering the hook (price card), compressor pedal
  pluck    FM pluck 16ths (price card)
  arp      analog-style arp pluck (title, breakdown, build, offer), dry
  bells    17 FM bells (bar 19)
  bass     layered bass (sub sine + saturated mid)
  drums    layered kick, snare (+clap, +tail), hats, rim, shaker, crash; sub-stems
           drums_<kind>.wav and steady-state tour loops drums_<kind>_loopN/_loopS.wav
  fx       risers, impacts, downlifters, reverse swells, smear swishes
Honesty zones (0.00-8.00, 16.00-36.00): only gtr is processed by Choroboros and
only gain follows it; the backing there (drums, bass, fx) carries no
modulation and the tour backing is pasted sample-identical in every pass.

Usage: python3 audio/film/compose.py [--only gtr,pad]
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import SR, Film, bar_t, hard_silence, jdump, smp, todb, write
from instruments import (FMBell, FilmEPiano, FilmGuitar, LayeredBass, LayeredKick, LayeredSnare, ArpPluck,
                         ChoirLayer, MonoCrash, PAD_EQ, RealGuitar, Shaker, ceiling_control, comp_pedal,
                         downlifter, fold_pad, impact, mono_pad, peak_control, render_events, render_events_pre,
                         reverse_crash, reverse_guitar, riser, swish, tape)
from synth import HiHat, Rim
from synth.filters import eq, svf
from synth.instrument import NoteEvent

# ----------------------------------------------------------------- harmony

OPEN = (40, 45, 50, 55, 59, 64)            # E2 A2 D3 G3 B3 E4
VOICE = {                                  # pad / strum voicings (treatment 7.3 + dominants)
    "D": [50, 57, 61, 64, 66],             # Dmaj9     D3 A3 C#4 E4 F#4
    "Bm": [47, 54, 57, 62, 64],            # Bm11      B2 F#3 A3 D4 E4
    "G": [43, 50, 54, 57, 61],             # Gmaj9#11  G2 D3 F#3 A3 C#4
    "A": [45, 52, 54, 59, 64],             # A6sus2    A2 E3 F#3 B3 E4
    "GA": [43, 50, 54, 57, 61],            # G/A: Gmaj9#11 over an A pedal (A11)
    "A7s4": [45, 52, 55, 59, 62],          # A7sus4(9) A2 E3 G3 B3 D4
    "A7": [45, 52, 55, 59, 61],            # A9        A2 E3 G3 B3 C#4  (only D4 -> C#4 moves)
}
EP_VOICE = {"D": [54, 57, 61, 64], "Bm": [57, 62, 64, 66], "G": [59, 61, 66, 69], "A": [64, 66, 69, 71],
            "A7s4": [62, 64, 67, 69], "A7": [61, 64, 67, 71], "GA": [59, 61, 66, 69]}
BASS_ROOT = {"D": 38, "Bm": 35, "G": 31, "A": 33, "GA": 33, "A7s4": 33, "A7": 33}
ARP_CELL = {"D": [74, 81, 78, 76], "Bm": [71, 78, 74, 76], "G": [67, 74, 78, 73], "A": [69, 76, 71, 78],
            "GA": [69, 74, 78, 73], "A7s4": [69, 76, 74, 79], "A7": [69, 76, 73, 79]}
FINAL_STRUM = [(50, 0, 10), (57, 1, 12), (61, 2, 11), (64, 3, 9), (66, 4, 7), (69, 5, 5)]  # D3 A3 C#4 E4 F#4 A4

# bar -> [(beat offset s, chord)], chords may change inside a bar (bar lines are locked)
H = {1: [(0, "D")], 2: [(0, "D")], 3: [(0, "Bm")], 4: [(0, "A7s4"), (1.5, "A7")],
     5: [(0, "D")], 6: [(0, "Bm")], 7: [(0, "G")], 8: [(0, "A7s4"), (1.5, "A7")]}
for _b in range(9, 19):
    H[_b] = [(0, "D" if _b % 2 == 1 else "Bm")]
H.update({19: [(0, "G")], 20: [(0, "G")], 21: [(0, "Bm")], 22: [(0, "G")], 23: [(0, "A")], 24: [(0, "GA")],
          25: [(0, "A7s4"), (1.5, "A7")], 26: [(0, "D")], 27: [(0, "Bm")], 28: [(0, "G")],
          29: [(0, "A7s4"), (1.5, "A7")], 30: [(0, "D")], 31: [(0, "Bm")], 32: [(0, "G")], 33: [(0, "A")],
          34: [(0, "G")], 35: [(0, "A")], 36: [(0, "D")], 37: [(0, "Bm")], 38: [(0, "G")],
          39: [(0, "A7s4"), (1.5, "A7")], 40: [(0, "D")], 41: [(0, "D")], 42: [(0, "D")]})


def chord_at(t):
    b = int(t // 2.0) + 1
    ch = H.get(b, [(0, "D")])
    cur = ch[0][1]
    for off, c in ch:
        if t - bar_t(b) >= off - 1e-9:
            cur = c
    return cur


SILENCES = [(7.85, 8.00), (49.85, 50.00), (69.50, 70.00)]
HONESTY = [(0.0, 8.0), (16.0, 36.0)]


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
    """Render events in groups separated by the hard silences; each group is
    cut at the start of the next silence, so no tail survives a digital silence."""
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


def swing16(t, amount=0.54, t0=0.0):
    """Swing the off 16ths: 54% = the second 16th of each pair 10 ms late at 120 BPM."""
    k = int(round((t - t0) / 0.125))
    if abs((t - t0) - k * 0.125) < 1e-6 and k % 2 == 1:
        return t + (amount - 0.5) * 2 * 0.125
    return t


# ----------------------------------------------------------------- the hook (the take)

VEL_SHAPE = [100, 72, 92, 66, 86, 60]      # 1, 1&, 2&, 3&, 4, 4& (MIDI velocity)
CELL_T = [0.0, 0.25, 0.75, 1.25, 1.5, 1.75]
FIG = {   # (pitch, string, fret) per cell position
    "T1": [(50, 1, 5), (57, 2, 7), (66, 4, 7), (61, 3, 6), (64, 4, 5)],
    "T3": [(47, 1, 2), (54, 2, 4), (64, 4, 5), (57, 3, 2), (62, 4, 3), (57, 3, 2)],
    "T4": [(45, 0, 5), (52, 1, 7), (62, 4, 3), (55, 3, 0), (61, 4, 2)],
    "M_G": [(43, 0, 3), (50, 1, 5), (61, 4, 2), (54, 2, 4), (59, 4, 0)],
    "M_A": [(45, 0, 5), (52, 1, 7), (59, 4, 0), (54, 2, 4), (64, 5, 0)],
    "M_A7": [(45, 0, 5), (52, 1, 7), (62, 4, 3), (55, 3, 0), (61, 4, 2)],
}
SQUEAK = {"T3": 0, "T4": 0, "M_A7": 0}     # fret-hand shift before these figures' first note
TAKE_SEED = 1954


def take():
    """The take: T1, T3, T4 with one fixed seed. {name: [(t, pitch, vel, string, fret, seed, squeak)]}.
    T1's first note is never early, so a block starting on T1 starts on its sample."""
    rng = np.random.default_rng(TAKE_SEED)
    out = {}
    for k, name in enumerate(("T1", "T3", "T4")):
        rows = []
        for i, (p, s, f) in enumerate(FIG[name]):
            dt, dv = hum(rng)
            if i == 0:
                dt = abs(dt)
            v = VEL_SHAPE[i] / 127 * (1 + dv)
            rows.append((CELL_T[i] + dt, p, v, s, f, TAKE_SEED * 10 + k * 100 + i, SQUEAK.get(name) == i))
        out[name] = rows
    return out


_TAKE = take()


def take_at(name, t0):
    return [(t0 + t, p, v, s, f, sd, sq) for (t, p, v, s, f, sd, sq) in _TAKE[name]]


def motif(name, t0, seed, vel_scale=1.0, octave=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i, (p, s, f) in enumerate(FIG[name]):
        dt, dv = hum(rng)
        v = VEL_SHAPE[i] / 127 * (1 + dv) * vel_scale
        rows.append((t0 + CELL_T[i] + dt, p + 12 * octave, v, s, f, seed * 10 + i, SQUEAK.get(name) == i))
    return rows


def strum_bar(ch, t0, seed):
    """Title strums: dotted quarter on 1 (down), dotted quarter on 2& (down),
    eighth on 4 (up, top strings), all strings muted on 4&."""
    rng = np.random.default_rng(seed)
    fing = {"D": [(50, 1, 5), (57, 2, 7), (61, 3, 6), (66, 4, 7), (64, 5, 0)],
            "Bm": [(47, 1, 2), (54, 2, 4), (57, 3, 2), (62, 4, 3), (64, 5, 0)]}[ch]
    rows = []
    hits = [(0.0, "down", 100 / 127, fing), (0.75, "down", 90 / 127, fing), (1.5, "up", 68 / 127, fing[2:])]
    for h, (tb, kind, vel, notes) in enumerate(hits):
        dt, dv = hum(rng)
        order = list(notes) if kind == "down" else list(notes)[::-1]
        spread = 0.012 if kind == "down" else 0.009
        for j, (p, s, f) in enumerate(order):
            v = vel * (1 + dv) * (1 - 0.05 * j)
            rows.append((t0 + tb + max(dt, -0.002 if tb == 0 else -0.004) + j * spread, p, v, s, f,
                         seed * 10 + h * 10 + j, False))
    return rows


def to_events(rows, gate_end, short=None, octave=0):
    evs = []
    for i, r in enumerate(rows):
        t, p, v, s, f, sd, sq = r
        dur = gate_end - t
        if short and i in short:
            dur = short[i]
        meta = {"string": s, "fret": f, "seed": int(sd)}
        if sq:
            meta["squeak"] = True
        evs.append(NoteEvent(max(0.0, t), int(p + 12 * octave), float(np.clip(v, 0.02, 1.0)), max(0.02, dur), meta))
    return evs


GTR_LEVEL = 0.17
LEAD_LEVEL = 0.19
GTR_CEIL = {"arp": -15.5, "strum": -11.5, "final": -10.5}


def render_guitar(evs, t_start, t_end, fade_out_s=0.004, ceiling=None, inst=RealGuitar, **kw):
    """Render a guitar segment with its own instrument; keep [t_start, t_end)
    (damped or cut there). ceiling: pick-attack control of the DI (dBTP)."""
    g = inst(**kw)
    rel = [NoteEvent(e.start_s - t_start, e.pitch, e.vel, e.dur_s, dict(e.meta)) for e in evs]
    n = smp(t_end - t_start)
    y = render_events_pre(g, rel, n + smp(6.0))
    if ceiling is not None:
        c = ceiling(np.arange(len(y)) / SR) if callable(ceiling) else ceiling
        y = ceiling_control(y, c)
    y = y[:n]
    k = smp(fade_out_s)
    if k:
        y[-k:] *= 0.5 + 0.5 * np.cos(np.pi * (np.arange(k) + 1) / k)
    return smp(t_start), y


P_PASTES = [16.0, 20.0, 24.0, 28.0, 32.0, 50.0, 58.0]
_P = {}


def p_block():
    """Block P = T1 | T3 from silent strings, the 4& pickup played short, all
    strings damped at +3.94 s (60 ms release). Exactly 4.000 s, rendered once."""
    if "P" not in _P:
        rows = take_at("T1", 0.0) + take_at("T3", 2.0)
        evs = to_events(rows, 3.94, short={len(rows) - 1: 0.12})
        _P["P"] = render_guitar(evs, 0.0, 4.0, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL)[1]
    return _P["P"]


def main_guitar(n):
    y = np.zeros(n)
    segs = []
    rows = take_at("T1", 0.0) + take_at("T1", 2.0) + take_at("T3", 4.0) + take_at("T4", 6.0)
    segs.append(render_guitar(to_events(rows, 8.0), 0.0, 7.85, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    evs = []
    for r in strum_bar("D", bar_t(5), 5105) + strum_bar("Bm", bar_t(6), 5106):
        bar0 = bar_t(5) if r[0] < bar_t(6) - 0.01 else bar_t(6)
        evs += to_events([r], bar0 + 1.75)
    evs += to_events(motif("M_G", bar_t(7), 5107) + motif("M_A7", bar_t(8), 5108), 15.94)
    segs.append(render_guitar(evs, 8.0, 16.0, level=GTR_LEVEL,
                              ceiling=lambda t: np.where(t < 4.0, GTR_CEIL["strum"], GTR_CEIL["arp"])))
    P = p_block()
    for t in P_PASTES:
        segs.append((smp(t), P))
    rows = motif("M_G", bar_t(22), 5122) + motif("M_A", bar_t(23), 5123) + motif("M_G", bar_t(24), 5124) + \
        motif("M_A7", bar_t(25), 5125)
    segs.append(render_guitar(to_events(rows, 50.0), 42.0, 49.85, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    rows = motif("M_G", bar_t(28), 5128) + motif("M_A7", bar_t(29), 5129)
    segs.append(render_guitar(to_events(rows, 57.94), 54.0, 58.0, ceiling=GTR_CEIL["arp"], level=GTR_LEVEL))
    rows = take_at("T1", bar_t(36)) + take_at("T3", bar_t(37)) + motif("M_G", bar_t(38), 5138) + \
        motif("M_A7", bar_t(39), 5139)
    evs = to_events(rows, bar_t(40) + 0.2)
    for j, (p, s, f) in enumerate(FINAL_STRUM):
        evs.append(NoteEvent(bar_t(40) + 0.040 * j, p, 0.80 * (1 - 0.035 * j), 12.0,
                             {"string": s, "fret": f, "seed": 51400 + j}))
    evs.append(NoteEvent(bar_t(42), 66, 0.36, 6.0, {"string": 4, "fret": 7, "seed": 51420}))
    segs.append(render_guitar(evs, 70.0, 86.0, fade_out_s=0.0, level=GTR_LEVEL,
                              ceiling=lambda t: np.where(t < 8.0 - 0.003, GTR_CEIL["arp"], GTR_CEIL["final"])))
    for off, a in segs:
        y[off:off + len(a)] += a[: max(0, n - off)]
    return y


def main_gtr_oct(n):
    """Quiet octave double, only outside the honesty zones: a second, slightly
    later performance of the motifs and the hook, brighter pluck position."""
    y = np.zeros(n)
    kw = dict(level=GTR_LEVEL * 0.55, pluck=0.12, brightness=0.6, pick_noise=0.04)

    def seg(rows, t0, t1, gate):
        rows = [(t + 0.008, p, v * 0.8, s, f, sd + 7, False) for (t, p, v, s, f, sd, sq) in rows]
        off, a = render_guitar(to_events(rows, gate, octave=1), t0, t1, ceiling=GTR_CEIL["arp"] + 3, **kw)
        y[off:off + len(a)] += a[: max(0, n - off)]

    seg(motif("M_G", bar_t(7), 6107) + motif("M_A7", bar_t(8), 6108), 12.0, 15.94, 15.9)
    seg(motif("M_G", bar_t(22), 6122) + motif("M_A", bar_t(23), 6123) + motif("M_G", bar_t(24), 6124) +
        motif("M_A7", bar_t(25), 6125), 42.0, 49.85, 49.8)
    for t in (50.0, 58.0):
        seg(motif("T1", t, 6200 + int(t)) + motif("T3", t + 2.0, 6300 + int(t)), t, t + 3.98, t + 3.94)
    seg(motif("M_G", bar_t(28), 6128) + motif("M_A7", bar_t(29), 6129), 54.0, 57.98, 57.94)
    seg(motif("M_G", bar_t(38), 6138) + motif("M_A7", bar_t(39), 6139), 74.0, 78.2, 78.1)
    return y


# ----------------------------------------------------------------- lead, EP, pad, pluck, bells, arp

def main_lead(n):
    """The lead answers the hook in its gaps (price card): A5 F#5 E5 | D5 C#5 A4,
    laid back 15 ms, compressor pedal."""
    b30, b31 = bar_t(30), bar_t(31)
    line = [(b30 + 1.0, 81, 0.22), (b30 + 1.25, 78, 0.55), (b30 + 1.875, 76, 0.55), (b31 + 0.5, 74, 0.45),
            (b31 + 1.0, 73, 0.45), (b31 + 1.5, 69, 0.42)]
    rng = np.random.default_rng(3030)
    evs = []
    for i, (t, p, d) in enumerate(line):
        dt, dv = hum(rng)
        evs.append(NoteEvent(t + 0.015 + dt, p, (0.9 if i in (1, 3) else 0.8) * (1 + dv), d,
                             {"string": 5, "fret": p - 64, "seed": 30300 + i}))
    g = RealGuitar(level=LEAD_LEVEL, sustain_s=9.0, brightness=0.55, pluck=0.2, pick_noise=0.04)
    rel = [NoteEvent(e.start_s - 56.0, e.pitch, e.vel, e.dur_s, e.meta) for e in evs]
    a = render_events_pre(g, rel, smp(8.0))
    y = np.zeros(n)
    y[smp(56.0):smp(56.0) + len(a)] += a
    return comp_pedal(y)


def ep_bars(bars, seed=2828):
    """EP comp: 1 (dotted quarter), 2& (tied through 3), 4 (staccato eighth).
    Chord per hit from the harmony map (so A7sus4 -> A7 lands on beat 4)."""
    rng = np.random.default_rng(seed)
    evs = []
    for b in bars:
        t0 = bar_t(b)
        for tb, d, vel in ((0.0, 0.70, 0.62), (0.75, 0.72, 0.55), (1.5, 0.13, 0.50)):
            dt, dv = hum(rng)
            ch = chord_at(t0 + tb + 0.01)
            for j, p in enumerate(EP_VOICE[ch]):
                roll = 0.004 * j + abs(rng.normal(0, 0.002))
                evs.append(NoteEvent(t0 + tb + dt + roll, p, vel * (1 + dv) * (1 - 0.03 * j), d - roll,
                                     {"seed": int(rng.integers(1 << 30)), "hit": tb}))
    return evs


def ep_with_bell(evs, n, bell_db=-17.0):
    y = render_events(FilmEPiano(level=0.1, bark=1.0, tine=0.75), evs, n)
    bell = [NoteEvent(e.start_s, e.pitch + 12, e.vel * 0.8, 0.1, {"seed": e.meta["seed"] + 1})
            for e in evs if e.meta.get("hit") == 0.0]
    y += render_events(FMBell(level=0.1, ring=0.3, lp_hz=7000.0), bell, n) * 10 ** (bell_db / 20) * 3.0
    y = tape(y, drive_db=9.0, bias=0.05, hf_db=-0.5)
    return peak_control(y, 6.0, lookahead_ms=2.0, release_ms=80.0)


def main_ep(n):
    return ep_with_bell(ep_bars([28, 29, 30, 31]), n)


def pad_events(bar_list, t_end, vel=0.75):
    """Pad chords (with in-bar changes) with common tones tied (no re-attack)."""
    evs, open_notes = [], {}
    changes = []
    for b in bar_list:
        for off, ch in H[b]:
            changes.append((bar_t(b) + off, ch))
    for t0, ch in changes:
        cur = set(VOICE[ch])
        for p in list(open_notes):
            if p not in cur:
                s = open_notes.pop(p)
                evs.append((s, p, t0 + 0.05 - s))
        for p in VOICE[ch]:
            if p not in open_notes:
                open_notes[p] = t0
    for p, s in open_notes.items():
        evs.append((s, p, t_end - s))
    return [NoteEvent(s, p, vel, d, {"seed": 3000 + int(s * 100) + p}) for s, p, d in sorted(evs)]


def render_pad(evs, n, attack, release=1.8, env_amount=1.4, cutoff=800.0, choir_db=-7.0):
    inst = mono_pad(attack=attack, release=release, env_amount=env_amount, cutoff=cutoff)
    y = fold_pad(render_events(inst, evs, n))
    ch = [NoteEvent(e.start_s, e.pitch + (12 if e.pitch < 50 else 0), e.vel, e.dur_s,
                    {"seed": e.meta["seed"] + 5, "attack": attack * 1.5 + 0.2}) for e in evs]
    y += render_events(ChoirLayer(level=0.1, release=release), ch, n) * 10 ** (choir_db / 20) * 2.0
    return y


def sweep_lp(y, t0, t1, f0, f1, q=0.9):
    """Opening low-pass sweep between t0 and t1 (exponential), open after t1."""
    n = len(y)
    t = np.arange(n) / SR
    u = np.clip((t - t0) / (t1 - t0), 0, 1)
    fc = f0 * (f1 / f0) ** (u ** 1.5)
    fc[t > t1] = f1
    return svf(y, np.minimum(fc, 0.45 * SR), q, "lp", SR)


def main_pad(n):
    y = np.zeros(n)
    y += cut_after(render_pad(pad_events(range(19, 25), 48.0), n, attack=0.9), 49.85)
    # the build: A7sus4 -> A7 over the A pedal, filter opening from 700 Hz to 9 kHz
    b = render_pad(pad_events([25], 49.85), n, attack=0.35, cutoff=2600.0, env_amount=0.6)
    y += cut_after(sweep_lp(b, 48.0, 49.8, 700.0, 9000.0), 49.85)
    y += cut_after(render_pad(pad_events(range(26, 36), 69.5), n, attack=0.3, env_amount=1.0), 69.5)
    y += render_pad(pad_events([38, 39, 40], 81.0), n, attack=0.9)
    y = tape(eq(y, PAD_EQ, SR), drive_db=6.0, bias=0.04, hf_db=-0.5)
    return peak_control(y, 3.0, 3.0, 120.0)


def main_pluck(n):
    pat = {"D": [81, 85, 88, 90, 93, 90, 88, 85], "Bm": [83, 86, 88, 90, 93, 90, 88, 86]}
    rng = np.random.default_rng(3131)
    evs = []
    for b in (30, 31):
        ch = H[b][0][1]
        for k in range(16):
            dt, dv = hum(rng, 3.0, 0.06)
            vel = (0.62 if k == 8 else 0.8 if k % 4 == 0 else 0.62 if k % 2 == 0 else 0.5) * (1 + dv)
            evs.append(NoteEvent(swing16(bar_t(b) + k * 0.125, 0.54, bar_t(b)) + dt, pat[ch][k % 8], vel, 0.1,
                                 {"seed": 31000 + b * 20 + k}))
    return peak_control(render_events(FMBell(level=0.14), evs, n), 4.0, 1.5, 50.0)


BELL_NOTES_A = [67, 69, 71, 73, 74, 76, 78, 81, 83, 85]      # G4 A4 B4 C#5 D5 E5 F#5 A5 B5 C#6 (ten)
BELL_NOTES_B = [86, 88, 90, 93, 95, 97, 98]                  # D6 E6 F#6 A6 B6 C#7 D7 (seven)
BELL_PEAK_DB = -24.0


def bells_events(t_a, t_b):
    evs = [NoteEvent(t_a + 0.125 * k, p, 0.7, 0.1, {"seed": 36000 + k}) for k, p in enumerate(BELL_NOTES_A)]
    evs += [NoteEvent(t_b + 0.125 * k, p, 0.7, 0.1, {"seed": 36100 + k}) for k, p in enumerate(BELL_NOTES_B)]
    return evs


def main_bells(n):
    y = render_events(FMBell(level=0.3, ring=0.35), bells_events(36.0, 37.25), n)
    pk = max(np.abs(y[smp(t):smp(t) + smp(0.125)]).max()
             for t in [36.0 + 0.125 * k for k in range(10)] + [37.25 + 0.125 * k for k in range(7)])
    return y * (10 ** (BELL_PEAK_DB / 20) / max(pk, 1e-9))


def arp_run(t0, t1, step, cutoff, vel, seed, accent_every=4, swing=0.54, cell_shift=0, decay_mul=1.0):
    """Arpeggio over the harmony map between t0 and t1 (step 0.125 = 16ths,
    0.375 = dotted 8ths); cutoff may be a function of time (filter sweeps)."""
    rng = np.random.default_rng(seed)
    evs = []
    k = 0
    t = t0
    while t < t1 - 1e-9:
        ch = chord_at(t + 0.001)
        p = ARP_CELL[ch][(k + cell_shift) % 4]
        dt, dv = hum(rng, 2.5, 0.08)
        v = (vel(t) if callable(vel) else vel) * (1.18 if k % accent_every == 0 else 1.0) * (1 + dv)
        c = cutoff(t) if callable(cutoff) else cutoff
        tt = swing16(t, swing, 0.0) if step == 0.125 else t
        evs.append(NoteEvent(tt + dt, p, float(np.clip(v, 0.05, 1.0)), 0.1,
                             {"seed": seed * 1000 + k, "cutoff": c, "decay_mul": decay_mul}))
        k += 1
        t += step
    return evs


def main_arp(n):
    evs = []
    evs += arp_run(8.0, 15.9, 0.375, 1100.0, 0.52, 4101)                       # title + lineup: dotted 8ths
    evs += arp_run(40.0, 48.0, 0.375, lambda t: 650.0 + 45.0 * (t - 40.0), 0.45, 4102, decay_mul=1.4)
    evs += arp_run(48.0, 49.8, 0.125, lambda t: 700.0 * (9.0 ** ((t - 48.0) / 1.8)),     # build: opens up
                   lambda t: 0.4 + 0.3 * (t - 48.0) / 1.8, 4103)
    evs += arp_run(50.0, 54.0, 0.125, 1900.0, 0.55, 4104)                      # free: 16ths
    evs += arp_run(54.0, 58.0, 0.125, 1500.0, 0.5, 4105)                       # trial
    evs += arp_run(58.0, 61.9, 0.375, 2100.0, 0.42, 4106)                      # price: dotted 8ths under the pluck
    y = render_split(lambda: ArpPluck(level=0.22), evs, n)
    return peak_control(y, 3.0, 1.5, 50.0)


# ----------------------------------------------------------------- bass

def bass_note(t, p, d, v, seed):
    return NoteEvent(t, p, v, d, {"seed": seed})


def groove_a_bass(bar, seed, stop_at=None, pickup=None):
    t0 = bar_t(bar)
    r = BASS_ROOT[chord_at(t0 + 0.01)]
    notes = [(0.0, r, 0.68, 0.9), (0.75, r, 0.22, 0.7), (1.0, r, 0.7, 0.8)]
    if pickup is not None:
        notes.append((1.75, pickup, 0.2, 0.62))
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


def groove_b_bass(bar, seed, pickup=None):
    t0 = bar_t(bar)
    r = BASS_ROOT[chord_at(t0 + 0.01)]
    notes = [(0.0, r, 0.45, 0.92), (0.75, r + 12, 0.2, 0.72), (1.0, r, 0.4, 0.85), (1.75, r + 7, 0.2, 0.7)]
    if pickup is not None:
        notes[-1] = (1.75, pickup, 0.2, 0.72)
    rng = np.random.default_rng(seed)
    out = []
    for k, (tb, p, d, v) in enumerate(notes):
        dt, dv = hum(rng, 3.0, 0.05)
        out.append(bass_note(t0 + tb + dt, p, d, v * (1 + dv), seed * 10 + k))
    return out


def whole_bass(bar, seed, dur=1.9, v=0.75, root=None):
    return [bass_note(bar_t(bar), root or BASS_ROOT[chord_at(bar_t(bar) + 0.01)], dur, v, seed)]


def tour_block_bass(t_block, stop=False):
    """Bars 9-10 of groove A (identical in every pass). stop: Black's pass, nothing
    after beat 4 of bar 2."""
    evs = groove_a_bass(9, 6109) + groove_a_bass(10, 6110, stop_at=(bar_t(10) + 1.5) if stop else None)
    return [NoteEvent(e.start_s - bar_t(9) + t_block, e.pitch, e.vel, e.dur_s, dict(e.meta)) for e in evs]


def main_bass_events(include_tour=True):
    evs = []
    evs += groove_a_bass(5, 6005, pickup=37) + groove_a_bass(6, 6006, pickup=42)     # C#2 -> B1, F#2 -> G1
    evs += groove_a_bass(7, 6007, pickup=44) + groove_a_bass(8, 6008)                # G#2 -> A1
    if include_tour:
        for k, t in enumerate((16.0, 20.0, 24.0, 28.0, 32.0)):
            evs += tour_block_bass(t, stop=(k == 4))
    for b in (19, 20, 21, 22, 23):
        evs += whole_bass(b, 6000 + b, v=0.7)
    evs += whole_bass(24, 6024, v=0.7, root=33)                                      # the A pedal starts (G/A)
    t = bar_t(25)
    evs += [bass_note(t + 0.25 * k, 33, 0.2, 0.62 + 0.04 * k, 60250 + k) for k in range(7)]   # pulsing A pedal
    for b in range(26, 32):
        evs += groove_b_bass(b, 6000 + b, pickup={27: 42, 29: 44}.get(b))
    for b in range(32, 36):
        evs += whole_bass(b, 6000 + b, v=0.7)
    evs += whole_bass(38, 6038, v=0.62) + whole_bass(39, 6039, v=0.62, root=33)
    evs += [bass_note(bar_t(40), 38, 3.0, 0.7, 6040)]
    return evs


def make_bass():
    return LayeredBass(seed=4, level=0.42)


def bass_chain(y):
    return peak_control(eq(y, [("lowshelf", 75, -2.0, 0.7), ("peak", 140, 1.5, 1.0), ("lowpass", 3000, 0, 0.7)], SR),
                        4.0, 3.0, 80.0)


def main_bass(n):
    return bass_chain(render_split(make_bass, main_bass_events(), n))


# ----------------------------------------------------------------- drums

GM = {"kick": 36, "rim": 37, "snare": 38, "chh": 42, "ohh": 46, "shaker": 70, "crash": 49}
ACC = {"X": 1.0, "x": 0.8, "o": 0.55, "g": 0.3}


def grid(pattern, t0, step=0.125, swing=None):
    out = []
    k = 0
    for ch in pattern:
        if ch in " |":
            continue
        if ch in ACC:
            t = t0 + k * step
            if swing:
                t = swing16(t, swing, t0)
            out.append((t, ACC[ch]))
        k += 1
    return out


def drum_hits(kind, hits, seed, t_ms=2.0, v_pct=0.05):
    rng = np.random.default_rng(seed)
    evs = []
    for k, (t, v) in enumerate(hits):
        dt, dv = hum(rng, t_ms, v_pct)
        evs.append((kind, max(0.0, t + dt), float(np.clip(v * (1 + dv), 0.05, 1.0)), seed * 100 + k))
    return evs


def groove_a_bar(t0, seed, fill=False, flam=False, stop_at=None, lift=False):
    """Half-time groove A: kick 1 and 2&, snare 3 with ghost notes, closed hats
    on 8ths (accented) with a 16th pickup, soft rim on 4, open-hat lift on 4& (lift)."""
    ev = []
    ev += drum_hits("kick", grid("X.....x.........", t0), seed + 1)
    ev += drum_hits("snare", grid("........X.......", t0), seed + 2)
    ev += drum_hits("snare", grid(".......g.....g..", t0, swing=0.54), seed + 8, 2.5, 0.15)   # ghosts
    hats = "x.o.x.ogx.o.x.o." if not fill else "x.o.x.ogx.o....."
    if lift:
        hats = "x.o.x.ogx.o.x..."
    ev += drum_hits("chh", grid(hats, t0, swing=0.54), seed + 3, 2.5, 0.1)
    if lift:
        ev += [("ohh", t0 + 1.75, 0.6, (seed + 9) * 100)]
    if fill:
        ev += drum_hits("snare", grid("............goxX", t0, swing=0.54), seed + 4)
    elif flam:
        ev += drum_hits("snare", [(t0 + 1.5 - 0.028, 0.34), (t0 + 1.5, 0.92)], seed + 6, 0.5)
    else:
        ev += drum_hits("rim", grid("............o...", t0), seed + 7)
    if stop_at is not None:
        ev = [e for e in ev if e[1] < stop_at - 1e-6]
    return ev


def groove_b_bar(t0, seed, fill=None, crash=False):
    """Full groove B: kick 1, 2&, 3 (light), 4&; snare 2 and 4 with ghosts; 16th
    hats with accents and swing; open hat on 4&; shaker 16ths; fills: 'small'
    (beat 4 pickup), 'roll' (beat 4 roll + open hat), 'full' (beat 4 16ths)."""
    ev = []
    ev += drum_hits("kick", grid("X.....x.o.....x.", t0), seed + 1)
    ev += drum_hits("snare", grid("....X.......X...", t0), seed + 2)
    ev += drum_hits("snare", grid("..g....g..g.....", t0, swing=0.54), seed + 7, 2.5, 0.15)
    hats = "XgogxgogXgogxgO." if fill is None else "Xgogxgogxgog...."
    k = 0
    rng = np.random.default_rng(seed + 3)
    for ch in hats:
        t = swing16(t0 + k * 0.125, 0.54, t0)
        if ch in ACC:
            dt, dv = hum(rng, 2.5, 0.1)
            ev.append(("chh", t + dt, ACC[ch] * (1 + dv), (seed + 3) * 100 + k))
        elif ch == "O":
            ev.append(("ohh", t, 0.62, (seed + 3) * 100 + k))
        k += 1
    if fill is None:
        ev.append(("chh", t0 + 2.0 - 0.001, 0.25, (seed + 3) * 100 + 99))     # chokes the open hat
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxoxgx", t0, swing=0.54), seed + 4, 3.0, 0.1)
    if fill == "small":
        ev += drum_hits("snare", grid("..............ox", t0, swing=0.54), seed + 5)
    elif fill == "roll":
        ev += drum_hits("snare", grid("............ooxx", t0, swing=0.54), seed + 5)
        ev += [("ohh", t0 + 1.5, 0.5, (seed + 5) * 100 + 50)]
    elif fill == "full":
        ev += drum_hits("snare", grid("............goxX", t0, swing=0.54), seed + 5)
    if crash:
        ev += drum_hits("crash", [(t0, 0.85)], seed + 6, 0.5)
    return ev


def tour_block_drums(t_block, stop=False):
    ev = groove_a_bar(bar_t(9), 7109) + groove_a_bar(bar_t(10), 7110, fill=not stop,
                                                     stop_at=(bar_t(10) + 1.5) if stop else None)
    return [(k, t - bar_t(9) + t_block, v, s) for (k, t, v, s) in ev]


def main_drum_events(include_tour=True):
    ev = []
    ev += groove_a_bar(bar_t(5), 7005) + groove_a_bar(bar_t(6), 7006, fill=True)
    ev += groove_a_bar(bar_t(7), 7007) + groove_a_bar(bar_t(8), 7008, flam=True, lift=True)
    if include_tour:
        for k, t in enumerate((16.0, 20.0, 24.0, 28.0, 32.0)):
            ev += tour_block_drums(t, stop=(k == 4))
    ev += drum_hits("kick", [(bar_t(20), 0.5)], 7020)
    for b in range(21, 25):
        ev += drum_hits("kick", [(bar_t(b), 0.62)], 7000 + b * 3)
        ev += drum_hits("rim", [(bar_t(b) + 1.0, 0.6)], 7001 + b * 3)
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxoxgx" * 2, bar_t(23), swing=0.54), 7023, 3.0, 0.1)
    t = bar_t(25)
    ev += drum_hits("shaker", grid("oxgxoxgxoxgxox", t, swing=0.54), 7025, 3.0, 0.1)
    ev += drum_hits("kick", [(t + 0.5 * k, 0.62 + 0.06 * k) for k in range(4)], 7026)
    roll = [(t + 0.25 * k, 0.3 + 0.05 * k) for k in range(4)] + [(t + 1.0 + 0.125 * k, 0.52 + 0.06 * k)
                                                                 for k in range(7)]
    ev += drum_hits("snare", roll, 7027, 1.5)
    for b in range(26, 32):
        ev += groove_b_bar(bar_t(b), 7000 + b * 10, fill={27: "small", 29: "roll", 31: "full"}.get(b),
                           crash=(b in (26, 28, 30)))
    for b in range(32, 36):
        ev += drum_hits("kick", [(bar_t(b), 0.7)], 7000 + b * 10)
    ev += drum_hits("kick", [(bar_t(40), 0.55)], 7400)
    ev += drum_hits("crash", [(bar_t(40), 0.45)], 7401, 0.5)
    return ev


DRUM_KITS = {
    "kick": lambda: LayeredKick(seed=10, level=0.7),
    "snare": lambda: LayeredSnare(seed=11, level=0.55),
    "chh": lambda: HiHat(SR, 13, tune=1.5, brightness_hz=7200.0, closed_decay=0.03, level=0.3),
    "rim": lambda: Rim(SR, 14, level=0.35),
    "shaker": lambda: Shaker(606, level=0.3),
    "crash": lambda: MonoCrash(707, level=0.3),
}
DRUM_EQ = {
    "kick": [("lowshelf", 60, -1.5, 0.7), ("peak", 110, 1.0, 1.0), ("peak", 350, -2.0, 1.0), ("lowpass", 9000, 0, 0.7)],
    "snare": [("highpass", 90, 0, 0.7), ("peak", 200, 1.0, 1.2), ("peak", 5200, -2.0, 1.0), ("lowpass", 11000, 0, 0.7)],
    "chh": [("highshelf", 10000, -3.0, 0.7)],
    "rim": [],
    "shaker": [],
    "crash": [],
}
DRUM_PEAK = {"kick": 5.0, "snare": 5.0}
DRUM_BAL = {"kick": -10.0, "snare": -12.0, "chh": -14.0, "rim": -18.0, "shaker": -21.0, "crash": -14.0}
KINDS = ("kick", "snare", "chh", "rim", "shaker", "crash")


def render_drums(ev, n, silences=None, peak_ref=None):
    """peak_ref: {kind: dB} absolute ceilings for the transient control (so the
    tour loops get exactly the treatment of the full stems)."""
    parts = {}
    for kind in KINDS:
        rows = [e for e in ev if (e[0] == kind or (kind == "chh" and e[0] == "ohh"))]
        evs = [NoteEvent(t, 46 if k == "ohh" else GM[k], v, 0.1, {"seed": s}) for (k, t, v, s) in rows]
        y = render_split(DRUM_KITS[kind], evs, n, silences)
        if DRUM_EQ[kind]:
            y = eq(y, DRUM_EQ[kind], SR)
        if kind in DRUM_PEAK and np.abs(y).max() > 0:
            ceil = peak_ref[kind] if peak_ref else float(todb(np.abs(y).max())) - DRUM_PEAK[kind]
            y = ceiling_control(y, ceil, 1.5, 50.0)
            parts[f"_{kind}_ceiling"] = ceil
        parts[kind] = y * 10 ** (DRUM_BAL[kind] / 20)
    return parts


def tour_loops(peak_ref, bass_ref):
    """Steady-state tour backing: loopN = three identical 2-bar blocks, loopS =
    one block then Black's stop block (+1 s). The mix runs these through the same
    drum-bus chain and pastes block 2 of N (passes 1-4) and block 2 of S (pass
    5), so the backing is sample-identical in every pass, after processing too."""
    out = {}
    for name, blocks in (("N", [False, False, False]), ("S", [False, True])):
        n = smp(4.0 * len(blocks) + 1.0)
        dev, bev = [], []
        for i, stop in enumerate(blocks):
            dev += tour_block_drums(4.0 * i, stop=stop)
            bev += tour_block_bass(4.0 * i, stop=stop)
        parts = render_drums(dev, n, silences=[], peak_ref=peak_ref)
        b = render_split(make_bass, bev, n, silences=[])
        out[name] = {"drums": parts, "bass": bass_chain_abs(b, bass_ref)}
    return out


BASS_CEIL = {}


def bass_chain_abs(y, ceil):
    y = eq(y, [("lowshelf", 75, -2.0, 0.7), ("peak", 140, 1.5, 1.0), ("lowpass", 3000, 0, 0.7)], SR)
    return ceiling_control(y, ceil, 3.0, 80.0)


# ----------------------------------------------------------------- FX

def reverse_swell(t_end=7.85, length_s=1.1, pitch=50, string=2, fret=0, seed=777):
    g = FilmGuitar(level=GTR_LEVEL, pick_noise=0.0)
    y = render_events(g, [NoteEvent(0.0, pitch, 0.85, 3.0, {"string": string, "fret": fret, "seed": seed})], smp(3.2))
    return reverse_guitar(y, length_s)


def main_fx(n):
    y = np.zeros(n)

    def put(a, t_start):
        s = smp(t_start)
        y[s:s + len(a)] += a[: max(0, n - s)]

    put(riser(0.85, db0=-30, db1=-14, seed=711), 7.00)
    put(reverse_swell(7.85, 1.1) * 10 ** (-6 / 20), 7.85 - 1.1)
    put(impact(seed=721, level=10 ** (-7 / 20)), 8.00)
    put(downlifter(2.2, 761, -27.0), 8.05)
    put(reverse_crash(1.4, 772, -26.0), 16.0 - 1.4)
    for k, t in enumerate((20.0, 24.0, 28.0, 32.0)):
        put(swish(seed=731 + k, dur=0.5, peak_db=-30.0), t - 0.25)
    put(reverse_swell(42.0, 1.2, pitch=66, string=4, fret=7, seed=778) * 10 ** (-14 / 20), 42.0 - 1.2)
    put(riser(1.85, db0=-32, db1=-18, seed=741), 48.00)
    put(reverse_crash(1.5, 773, -23.0), 49.85 - 1.5)
    put(impact(seed=751, level=10 ** (-10 / 20)), 50.00)
    put(downlifter(2.6, 762, -24.0), 50.05)
    put(reverse_crash(1.0, 774, -25.0), 58.0 - 1.0)
    put(reverse_crash(1.5, 775, -23.0), 78.0 - 1.5)
    return y


# ----------------------------------------------------------------- build

def apply_silences(x, silences=SILENCES):
    for a, b in silences:
        x = hard_silence(x, a, b)
    return x


def build_main(only=None):
    film = Film("main")
    n = film.n
    t_all = time.time()
    builders = {"gtr": main_guitar, "gtr_oct": main_gtr_oct, "lead": main_lead, "ep": main_ep, "pad": main_pad,
                "pluck": main_pluck, "bells": main_bells, "arp": main_arp, "fx": main_fx}
    meta = {}
    for name, fn in builders.items():
        if only and name not in only:
            continue
        t0 = time.time()
        y = apply_silences(fn(n))
        write(film.stem_path(name), y)
        meta[name] = {"seconds": round(time.time() - t0, 1), "peak_dbfs": round(float(todb(np.abs(y).max())), 2)}
        print(f"  {name:7s} {meta[name]}", flush=True)
    if not only or "drums" in only or "bass" in only:
        t0 = time.time()
        braw = eq(render_split(make_bass, main_bass_events(), n),
                  [("lowshelf", 75, -2.0, 0.7), ("peak", 140, 1.5, 1.0), ("lowpass", 3000, 0, 0.7)], SR)
        bceil = float(todb(np.abs(braw).max())) - 4.0
        bass = apply_silences(ceiling_control(braw, bceil, 3.0, 80.0))
        write(film.stem_path("bass"), bass)
        parts = render_drums(main_drum_events(), n)
        refs = {k[1:-8]: v for k, v in parts.items() if k.startswith("_")}
        tot = np.zeros(n)
        for k in KINDS:
            v = apply_silences(parts[k])
            write(film.stem_path(f"drums_{k}"), v)
            tot += v
        write(film.stem_path("drums"), tot)
        loops = tour_loops(refs, bceil)
        for name, d in loops.items():
            for k in KINDS:
                write(film.stem_path(f"drums_{k}_loop{name}"), d["drums"][k])
            write(film.stem_path(f"bass_loop{name}"), d["bass"])
        meta["drums"] = {"seconds": round(time.time() - t0, 1), "peak_dbfs": round(float(todb(np.abs(tot).max())), 2),
                         "ceilings_db": refs, "bass_ceiling_db": bceil}
        print(f"  drums+bass {meta['drums']}", flush=True)
    print(f"compose done in {time.time() - t_all:.1f} s")
    return meta


def score_json():
    return {
        "take_seed": TAKE_SEED,
        "take": {k: [{"t": round(r[0], 4), "pitch": r[1], "vel": round(r[2], 4), "string": r[3], "fret": r[4],
                      "squeak": r[6]} for r in v] for k, v in _TAKE.items()},
        "figures": FIG, "harmony": {str(b): v for b, v in H.items()}, "p_pastes": P_PASTES,
        "bells": {"A": BELL_NOTES_A, "B": BELL_NOTES_B, "t_a": 36.0, "t_b": 37.25},
        "silences": SILENCES, "honesty_zones": HONESTY,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = set(x for x in a.only.split(",") if x)
    build_main(only or None)
    jdump(Film("main").p("stems", "score.json"), score_json())
