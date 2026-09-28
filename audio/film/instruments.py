"""Instruments for "Still Life", built on audio/synth. Every source is mono and
dry: no reverb, delay, panning, widening or internal modulation (all motion in
the film comes from Choroboros).

- FilmGuitar: synth.Guitar (extended Karplus-Strong, pluck-position comb,
  pickup-position comb, per-string choke) plus a subtle pick scrape and a clean
  amp/body voicing: coil resonance, 70 Hz high-pass, a little low warmth, a
  small low-mid dip, gentle 2.5 kHz presence and a roll-off above about 6 kHz.
- FilmEPiano: synth.EPiano with every detune at zero (the stock tine stack has a
  fixed 1.2 cent offset, removed here so the EP has no beating of its own).
- mono_pad(): synth.JunoPad with spread, PWM, drift and filter LFO at zero,
  folded to mono.
- FMBell: 2-operator FM, carrier:modulator 1:3.5, rendered at 4x, used for the
  price-card pluck and the 17 core bells.
- Shaker, MonoCrash and the FX functions (riser, impact, swish, reverse guitar).

Per-event seeds: render_events() can reseed an instrument's RNG for each note
(event.meta["seed"]), so a repeated note or drum hit is sample-identical
wherever it appears (the tour backing and the guitar take rely on this).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from common import SR
from synth import Bass, EPiano, Guitar, HiHat, JunoPad, Kick, Rim, Snare  # noqa: F401
from synth.core import add_at, dc_block, fade_curve, midi_to_hz
from synth.drums import metallic
from synth.filters import biquad, eq, svf
from synth.instrument import NoteEvent
from synth.osc import decimate, upsample


# ----------------------------------------------------------------- rendering

def render_events(inst, events, n, post=True):
    """Render NoteEvents into a mono (or stereo) buffer of n samples. If an
    event has meta['seed'], the instrument RNG is reseeded before that voice so
    the note is reproducible regardless of what else is in the list."""
    events = inst.prepare(sorted(events, key=lambda e: (e.start_s, e.pitch)))
    out = np.zeros((n, 2)) if inst.stereo else np.zeros(n)
    for ev in events:
        if "seed" in ev.meta:
            inst.rng = np.random.default_rng(int(ev.meta["seed"]))
        v = inst.voice(ev.pitch, ev.vel, ev.dur_s, ev.meta)
        if inst.stereo and v.ndim == 1:
            v = np.stack([v, v], 1)
        add_at(out, v, int(round(ev.start_s * SR)))
    return inst.post(out) if post else out


# ----------------------------------------------------------------- guitar

GTR_EQ = [
    ("highpass", 70, 0, 0.707),     # below the low E: no rumble into the chorus
    ("lowshelf", 160, 1.0, 0.7),    # a little warmth
    ("peak", 420, -1.2, 1.0),       # clear the boxy low mids slightly
    ("peak", 2500, 1.5, 0.9),       # gentle presence (with the coil: about +2.2 dB at 2-3 kHz)
    ("lowpass", 7500, 0, 0.707),    # amp/cab roll-off: -3 dB near 5 kHz, -7 dB at 6 kHz, -16 dB at 8 kHz
    ("lowpass", 12000, 0, 0.6),
]


class FilmGuitar(Guitar):
    """Clean electric guitar DI with an amp/body voicing (still mono and dry)."""

    def __init__(self, seed=101, brightness=0.5, sustain_s=5.5, pluck=0.17, level=0.35,
                 pick_noise=0.06, release_s=0.06, pickup="neck", eq_bands=None):
        super().__init__(SR, seed, tone="di", pickup=pickup, brightness=brightness, sustain_s=sustain_s,
                         pluck=pluck, humanize=1.0, choke=True, release_s=release_s, level=level,
                         pick_hz=(300.0, 2200.0))
        self.pick_noise = pick_noise
        self.eq_bands = GTR_EQ if eq_bands is None else eq_bands

    def voice(self, pitch, vel, dur_s, meta):
        y = super().voice(pitch, vel, dur_s, meta)
        if self.pick_noise > 0:
            # pick scrape: 5 ms of band-limited noise (1.5-6 kHz), outside the string
            nk = int(0.005 * SR)
            nz = self.rng.uniform(-1, 1, nk)
            nz = eq(nz, [("highpass", 1500, 0, 0.7), ("lowpass", 6000, 0, 0.7)], SR)
            env = np.exp(-np.arange(nk) / (0.0012 * SR)) * (1 - np.exp(-np.arange(nk) / (0.0002 * SR)))
            pk = max(np.abs(y[: int(0.02 * SR)]).max(), 1e-9)
            v = float(np.clip(vel, 0.05, 1.0))
            y[:nk] += nz * env / max(np.abs(nz * env).max(), 1e-9) * pk * self.pick_noise * (0.4 + 0.6 * v)
        return y

    def post(self, x):
        sr = self.sr
        res = {"neck": (4200, 1.0), "middle": (4600, 1.1), "bridge": (5000, 1.2)}[self.pickup]
        y = eq(x, [("lowpass", res[0], 0, res[1])], sr)
        y = eq(y, self.eq_bands, sr)
        return dc_block(y, 12.0, sr)


# ----------------------------------------------------------------- electric piano

class FilmEPiano(EPiano):
    """EPiano with every detune at zero (no beating of its own), no tremolo."""

    def __init__(self, seed=202, bark=0.85, tine=0.8, release_s=0.3, level=0.28):
        super().__init__(SR, seed, bark=bark, tine=tine, detune_cents=0.0, release_s=release_s, level=level,
                         oversample=2)

    def voice(self, pitch, vel, dur_s, meta):
        # same structure as synth.EPiano.voice with the tine carrier at exactly 1:1
        from synth.epiano import _carrier_env
        sr = self.sr * self.os
        v = float(np.clip(vel, 0.05, 1.0))
        f = float(midi_to_hz(pitch))
        gate_n = int(dur_s * sr)
        key = (pitch - 60) / 12.0
        slow = 4.2 * 2 ** (-0.55 * key)
        n = gate_n + int(self.release_s * sr)
        n = min(n, int((slow * 3.2 + 0.05) * sr))
        gate_n = min(gate_n, n)
        t = np.arange(n) / sr
        tw = 2 * math.pi * t
        ph = self.rng.uniform(0, 2 * math.pi, 3)
        ks_body = float(np.clip(2 ** (-0.45 * key), 0.35, 1.3))
        ks_tine = float(np.clip(2 ** (-0.9 * key), 0.12, 1.6))
        i_body = (0.35 + 2.1 * v ** 1.7) * self.bark * ks_body
        env_ib = 0.35 + 0.65 * np.exp(-t / (0.25 + 0.25 * (1 - v)))
        body = np.sin(tw * f + i_body * env_ib * np.sin(tw * f + ph[0]))
        i_tine = (0.15 + 1.9 * v ** 2) * self.tine * ks_tine
        env_it = np.exp(-t / (0.018 + 0.012 * v))
        tine = np.sin(tw * f + i_tine * env_it * np.sin(tw * f * 14.0 + ph[1]))
        warm = np.sin(tw * f + 0.35 * v * np.sin(tw * f + ph[2]))
        env = _carrier_env(n, sr, pitch, 0.0015, gate_n, self.release_s)
        tine_env = np.exp(-t / 0.9) * env
        y = env * (0.62 * body + 0.33 * warm) + 0.30 * tine_env * tine
        y = decimate(y * (0.25 + 0.75 * v ** 1.3), self.os)
        nf = min(len(y), int(0.004 * self.sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        return y * self.level

    def post(self, x):
        y = eq(x, [("highpass", 90, 0, 0.7), ("lowshelf", 220, 1.0, 0.7), ("peak", 1200, -1.0, 0.9),
                   ("highshelf", 6000, -3.0, 0.7), ("lowpass", 11000, 0, 0.7)], self.sr)
        y = np.tanh(1.2 * y) / 1.2
        return dc_block(y, 12.0, self.sr)


# ----------------------------------------------------------------- pad

def mono_pad(seed=303, attack=0.9, release=1.8, cutoff=800.0, level=0.12, env_amount=1.4):
    """JunoPad with all internal motion off; render() output must be folded
    with fold_pad() (the class is stereo, both channels identical)."""
    return JunoPad(SR, seed, spread=0.0, pwm_depth=0.0, drift_cents=0.0, lfo_filter_oct=0.0, sub=0.1,
                   amp_adsr=(attack, 1.5, 0.85, release), filt_adsr=(attack * 1.3, 2.5, 0.45, release),
                   cutoff=cutoff, resonance=0.15, env_amount=env_amount, level=level)


def fold_pad(x):
    x = np.asarray(x)
    if x.ndim == 1:
        return x
    assert np.max(np.abs(x[:, 0] - x[:, 1])) < 1e-12, "pad voices are not centred"
    return x[:, 0] * math.sqrt(2.0)   # undo the -3 dB centre pan law


PAD_EQ = [("highpass", 150, 0, 0.707), ("highpass", 110, 0, 0.707), ("peak", 320, -1.5, 0.9), ("highshelf", 6000, -2.0, 0.7)]


# ----------------------------------------------------------------- FM bell / pluck

class FMBell:
    """2-operator FM bell, carrier:modulator 1:3.5, 4x oversampled. Main decay
    about 400 ms (-17 dB at 0.4 s) with a quiet ring after it."""

    stereo = False

    def __init__(self, seed=404, index=2.2, level=0.3, ring=0.28, lp_hz=9000.0):
        self.rng = np.random.default_rng(seed)
        self.index, self.level, self.ring, self.lp_hz = index, level, ring, lp_hz
        self.sr = SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        os_ = 4
        sr = SR * os_
        v = float(np.clip(vel, 0.05, 1.0))
        f = float(midi_to_hz(pitch))
        dur = 2.2
        n = int(dur * sr)
        t = np.arange(n) / sr
        key = (pitch - 72) / 12.0
        ks = float(np.clip(2 ** (-0.6 * key), 0.3, 1.4))       # less index up high (no aliasing, less glare)
        idx = self.index * ks * (0.5 + 0.5 * v) * (0.25 + 0.75 * np.exp(-t / 0.16))
        ph = self.rng.uniform(0, 2 * np.pi)
        y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 3.5 * f * t + ph))
        amp = (1 - self.ring) * np.exp(-t / 0.12) + self.ring * np.exp(-t / 0.45)
        amp *= 1 - np.exp(-t / 0.0015)
        y = decimate(y * amp, os_)
        y *= fade_curve(len(y), 0, int(0.05 * SR))
        return y * self.level * (0.3 + 0.7 * v)

    def post(self, x):
        return dc_block(eq(x, [("lowpass", self.lp_hz, 0, 0.707), ("highpass", 200, 0, 0.707)], SR), 20.0, SR)


# ----------------------------------------------------------------- drums extras

class Shaker:
    """Noise band-passed around 5 kHz, soft 6 ms attack, 45 ms decay."""

    stereo = False
    name = "shaker"

    def __init__(self, seed=505, level=0.3):
        self.rng = np.random.default_rng(seed)
        self.level, self.sr = level, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        v = float(np.clip(vel, 0.05, 1.0))
        n = int(0.16 * SR)
        t = np.arange(n) / SR
        nz = self.rng.uniform(-1, 1, n)
        y = svf(nz, 5000 * (1 + self.rng.normal(0, 0.04)), 1.3, "bp", SR)
        y = biquad(y, "highpass", 2500, SR, 0.7)
        att = 0.006 * (1 + self.rng.normal(0, 0.1))
        dec = 0.045 * (0.8 + 0.4 * v) * (1 + self.rng.normal(0, 0.08))
        env = (1 - np.exp(-t / att)) * np.exp(-t / dec)
        y = y * env * fade_curve(n, 0, int(0.02 * SR))
        y /= max(np.abs(y).max(), 1e-9)
        return y * self.level * (0.2 + 0.8 * v)

    def post(self, x):
        return eq(x, [("lowpass", 10000, 0, 0.7)], SR)


class MonoCrash:
    """Mono crash: 808-style metallic cluster plus noise, bright band-pass,
    softened top so it never glares."""

    stereo = False
    name = "crash"

    def __init__(self, seed=606, level=0.3, decay_s=1.6):
        self.rng = np.random.default_rng(seed)
        self.level, self.decay_s, self.sr = level, decay_s, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        v = float(np.clip(vel, 0.05, 1.0))
        dec = self.decay_s * (0.7 + 0.4 * v)
        n = int(dec * 5 * SR)
        t = np.arange(n) / SR
        met = metallic(n, SR, self.rng, 2.3)
        nz = self.rng.uniform(-1, 1, n)
        x = 0.25 * met + 0.75 * nz
        x = svf(x, 6500, 0.6, "bp", SR) + 0.5 * biquad(x, "highpass", 3500, SR, 0.7)
        x = eq(x, [("highpass", 2800, 0, 0.7), ("highpass", 2800, 0, 0.7)], SR)   # no clangy low partials
        env = (0.6 * np.exp(-t / (0.12 * dec)) + 0.4 * np.exp(-t / dec)) * (1 - np.exp(-t / 0.0008))
        y = x * env * fade_curve(n, 0, int(0.2 * SR))
        y = eq(y, [("highshelf", 9000, -4.0, 0.7), ("lowpass", 13000, 0, 0.7)], SR)
        y /= max(np.abs(y).max(), 1e-9)
        return y * self.level * (0.25 + 0.75 * v)

    def post(self, x):
        return x


# ----------------------------------------------------------------- source dynamics (before Choroboros)

def peak_control(x, reduce_db, lookahead_ms=2.0, release_ms=60.0):
    """Source-side transient control for a mono dry source: a look-ahead
    peak limiter whose ceiling sits reduce_db under the source's own peak (part
    of the instrument's sound, like a DI preamp or drum-bus limiter; nothing
    after Choroboros is processed)."""
    from synth.effects import limiter
    x = np.asarray(x, dtype=np.float64)
    pk = np.abs(x).max()
    if pk <= 0:
        return x
    y, _ = limiter(np.stack([x, x], 1), ceiling_dbtp=float(20 * np.log10(pk)) - reduce_db,
                   lookahead_ms=lookahead_ms, release_ms=release_ms)
    return y[:, 0]


def ceiling_control(x, ceiling_db, lookahead_ms=2.0, release_ms=70.0):
    """Look-ahead true-peak limiter with an absolute ceiling (dBTP), scalar or
    per-sample array, for a mono dry source. Same algorithm as
    synth.effects.limiter; the ceiling does not depend on the signal, so the
    same notes get the same treatment wherever they occur."""
    from synth import meter
    from synth.effects import _forward_min, _release
    x = np.asarray(x, dtype=np.float64)
    L = max(1, int(lookahead_ms * SR / 1000))
    rel = math.exp(-1 / (release_ms * SR / 1000))
    ceil = 10 ** (np.asarray(ceiling_db, dtype=np.float64) / 20)
    pk = meter.true_peak_envelope(np.stack([x, x], 1), SR)
    req = np.minimum(1.0, ceil / np.maximum(pk, 1e-12))
    h = _release(_forward_min(req, L), rel)
    g = np.convolve(np.concatenate([np.full(L - 1, h[0]), h]), np.ones(L) / L, mode="valid")
    return x * g


def comp_pedal(x, threshold_below_peak_db=14.0, ratio=4.0, attack_ms=3.0, release_ms=140.0):
    """Guitar compressor pedal on a mono source (peak detector, soft knee),
    followed by a 3 dB peak control for the pick attack."""
    from synth.effects import compressor
    x = np.asarray(x, dtype=np.float64)
    pk = 20 * np.log10(max(np.abs(x).max(), 1e-12))
    y = compressor(np.stack([x, x], 1), threshold_db=pk - threshold_below_peak_db, ratio=ratio,
                   attack_ms=attack_ms, release_ms=release_ms, knee_db=6.0, sidechain_hp=0,
                   detector="peak")[:, 0]
    return peak_control(y, 3.0)


# ----------------------------------------------------------------- FX (mono)

def riser(duration_s, f0=400.0, f1=6000.0, db0=-30.0, db1=-14.0, seed=701, q=2.2):
    """Band-passed noise sweeping f0 -> f1, RMS level ramping db0 -> db1 dBFS
    (measured in 50 ms windows), ending on its last sample."""
    rng = np.random.default_rng(seed)
    n = int(round(duration_s * SR))
    u = np.linspace(0, 1, n)
    fc = f0 * (f1 / f0) ** (u ** 1.2)
    nz = rng.uniform(-1, 1, n)
    y = svf(nz, fc, q, "bp", SR)
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-12)
    # flatten the band-pass level variation with a running RMS, then impose the ramp
    w = int(0.05 * SR)
    rms = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, mode="same") + 1e-12)
    y = y / rms
    y = np.tanh(1.6 * y) / np.sqrt(np.mean(np.tanh(1.6 * y) ** 2))     # noise crest about 7 dB, not 12
    target = db0 + (db1 - db0) * u ** 1.6
    y = y * 10 ** (target / 20)
    y *= fade_curve(n, int(0.03 * SR), 0)
    return dc_block(y, 30.0, SR)


def impact(seed=702, level=0.5, sub_from=55.0, sub_to=32.0, dur=2.4):
    """Mono impact: sub drop sub_from -> sub_to Hz over 0.6 s plus a noise burst."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    tau = 0.6 / 4.0
    f = sub_to + (sub_from - sub_to) * np.exp(-t / tau)
    ph = np.cumsum(f) / SR
    sub = np.sin(2 * np.pi * ph) * np.exp(-t / 0.9) * (1 - np.exp(-t / 0.002))
    sub = np.tanh(1.4 * sub) / math.tanh(1.4)
    nz = rng.uniform(-1, 1, n)
    burst = eq(nz, [("lowpass", 3200, 0, 0.7), ("highpass", 120, 0, 0.7)], SR)
    burst *= np.exp(-t / 0.07) * (1 - np.exp(-t / 0.0006))
    burst /= max(np.abs(burst).max(), 1e-9)
    low = eq(nz, [("lowpass", 160, 0, 0.7), ("highpass", 35, 0, 0.7)], SR) * np.exp(-t / 0.5) * (1 - np.exp(-t / 0.01))
    low /= max(np.abs(low).max(), 1e-9)
    y = 0.85 * sub + 0.32 * burst + 0.18 * low
    y *= fade_curve(n, 0, int(0.4 * SR))
    y = dc_block(y, 22.0, SR)
    return y / max(np.abs(y).max(), 1e-9) * level


def swish(seed=703, dur=0.5, peak_db=-30.0):
    """Mono noise swish for the chorus smear: band-pass sweeping up then down
    around the bar line, sin^2 envelope, dur seconds centred on the cut."""
    rng = np.random.default_rng(seed)
    n = int(round(dur * SR))
    u = np.linspace(0, 1, n)
    fc = 900 * (5500 / 900) ** np.sin(np.pi * u)
    nz = rng.uniform(-1, 1, n)
    y = svf(nz, fc, 1.6, "bp", SR) + 0.3 * svf(nz, fc * 1.7, 0.8, "bp", SR)
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-12)
    env = np.sin(np.pi * u) ** 2
    y = y * env
    y = y / max(np.abs(y).max(), 1e-9) * 10 ** (peak_db / 20)
    return dc_block(y, 60.0, SR)


def reverse_guitar(note_events_audio, length_s):
    """Reverse a rendered dry guitar note and keep the last length_s seconds, so
    the swell peaks on the final sample."""
    y = note_events_audio[::-1]
    k = int(round(length_s * SR))
    nz = np.nonzero(np.abs(y) > 1e-6)[0]
    y = y[nz[0]:] if len(nz) else y
    y = y[-k:] if len(y) >= k else np.concatenate([np.zeros(k - len(y)), y])
    y = y * fade_curve(len(y), int(0.15 * SR), 0)
    return y
