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


PAD_EQ = [("highpass", 125, 0, 0.707), ("highpass", 100, 0, 0.707), ("peak", 320, -1.5, 0.9), ("highshelf", 6000, -2.0, 0.7)]


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


def comp_pedal(x, threshold_below_peak_db=14.0, ratio=4.0, attack_ms=3.0, release_ms=140.0, attack_ctrl_db=6.0):
    """Guitar compressor pedal on a mono source (peak detector, soft knee),
    followed by a peak control for the pick attack."""
    from synth.effects import compressor
    x = np.asarray(x, dtype=np.float64)
    pk = 20 * np.log10(max(np.abs(x).max(), 1e-12))
    y = compressor(np.stack([x, x], 1), threshold_db=pk - threshold_below_peak_db, ratio=ratio,
                   attack_ms=attack_ms, release_ms=release_ms, knee_db=6.0, sidechain_hp=0,
                   detector="peak")[:, 0]
    return peak_control(y, attack_ctrl_db)


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


# =================================================================== production pass (owner direction)
# Realism layers. Still no modulation effect anywhere: no vibrato, no detuned
# unison, no chorus; the only motion effect in the film is Choroboros.

from synth.core import jit  # noqa: E402
from synth.filters import ladder  # noqa: E402
from synth.guitar import OPEN_STRINGS, PICKUP_MM, SCALE_MM, string_and_fret, tune_loop  # noqa: E402
from synth.osc import pulse as osc_pulse, saw as osc_saw, sine as osc_sine  # noqa: E402
from synth.drums import Clap  # noqa: E402


@jit
def _string_loop_eta(exc, M, eta, a0, gain, n_out):
    """Karplus-Strong loop with a per-sample allpass coefficient (pitch drift)."""
    y = np.zeros(n_out)
    a1 = 1.0 - 2.0 * a0
    f_prev = 0.0
    ap_prev = 0.0
    ne = len(exc)
    for n in range(n_out):
        d0 = y[n - M] if n >= M else 0.0
        d1 = y[n - M - 1] if n >= M + 1 else 0.0
        d2 = y[n - M - 2] if n >= M + 2 else 0.0
        f = a0 * d0 + a1 * d1 + a0 * d2
        e_ = eta[n]
        ap = e_ * f + f_prev - e_ * ap_prev
        f_prev = f
        ap_prev = ap
        e = exc[n] if n < ne else 0.0
        y[n] = e + gain[n] * ap
    return y


class RealGuitar(FilmGuitar):
    """FilmGuitar plus two realism details of a real string (not effects):
    - pitch drift on the attack: a plucked string starts a few cents sharp
      (tension modulation) and settles within about 60 ms (2 + 4 v cents);
    - fret-hand squeak before notes marked meta["squeak"] (a short gliding
      band of noise, about -30 dB under the note)."""

    def __init__(self, drift_cents=(2.0, 4.0), drift_tau=0.06, **kw):
        super().__init__(**kw)
        self.drift_cents, self.drift_tau = drift_cents, drift_tau

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng, hz = self.sr, self.rng, self.humanize
        f0 = float(midi_to_hz(pitch)) * 2 ** (rng.normal(0, 0.8 * hz) / 1200)
        M, eta0, P = tune_loop(f0, sr)
        string, fret = meta.get("string"), meta.get("fret")
        if string is None:
            string, fret = string_and_fret(pitch)
        if fret is None:
            fret = pitch - OPEN_STRINGS[string]
        v = float(np.clip(vel, 0.05, 1.0))
        ne = max(8, int(round(P)))
        noise = rng.uniform(-1, 1, ne)
        fc1 = (self.pick_hz[0] + (self.pick_hz[1] - self.pick_hz[0]) * v ** 1.5)
        a1 = math.exp(-2 * math.pi * fc1 / sr)
        exc = signal.lfilter([1 - a1], [1, -a1], noise)
        b, a = signal.butter(2, min(3500.0 + 6000.0 * v, 0.45 * sr), fs=sr)
        exc = signal.lfilter(b, a, exc)
        exc *= np.hanning(ne + 2)[1:-1] ** 0.25
        nk = max(3, int(0.0006 * sr))
        exc[:nk] += np.hanning(nk + 2)[1:-1] * (0.25 + 0.6 * v)
        beta = float(np.clip(self.pluck * (1 + rng.normal(0, 0.12 * hz)), 0.05, 0.45))
        kd = max(1, int(round(beta * P)))
        exc = exc - np.concatenate([np.zeros(kd), exc[:-kd]]) if kd < ne else exc
        exc *= v ** 1.2 / max(np.abs(exc).max(), 1e-9)
        t60 = self.sustain_s * (82.4 / f0) ** 0.5
        bright = float(np.clip(self.brightness + rng.normal(0, 0.05 * hz), 0.05, 0.98))
        a0 = 0.25 * (1 - bright) ** 1.5
        w0 = 2 * math.pi * f0 / sr
        fir_mag = 1 - 2 * a0 * (1 - math.cos(w0))
        r = 10 ** (-3 * P / (sr * t60))
        g_sus = min(r / fir_mag, 0.99995)
        g_rel = min(10 ** (-3 * P / (sr * self.release_s)) / fir_mag, 0.999)
        n_gate = int(dur_s * sr)
        n_out = n_gate + int(self.release_s * 1.4 * sr) + ne
        n_out = min(n_out, int((t60 * 1.1 + 0.05) * sr) + ne)
        gain = np.full(n_out, g_sus)
        if n_gate < n_out:
            nr = max(2, int(0.012 * sr))
            ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(nr) / nr)
            seg = gain[n_gate:n_gate + nr]
            seg[:] = g_sus + (g_rel - g_sus) * ramp[:len(seg)]
            gain[n_gate + nr:] = g_rel
        # pitch drift: loop period shorter at the attack by c(t) cents, c -> 0
        d0 = P - 1.0 - M
        c0 = (self.drift_cents[0] + self.drift_cents[1] * v) * (1 + rng.normal(0, 0.15))
        t = np.arange(n_out) / sr
        dP = P * (1 - 2 ** (-(c0 * np.exp(-t / self.drift_tau)) / 1200))
        d = np.clip(d0 - dP, 0.08, 1.49)
        thiran = lambda dd: (1 - dd) / (1 + dd)
        eta = thiran(d) + (eta0 - thiran(d0))
        y = _string_loop_eta(exc, M, np.ascontiguousarray(eta), a0, gain, n_out)
        L = SCALE_MM * 2 ** (-fret / 12)
        gamma = min(PICKUP_MM[self.pickup] / L, 0.45)
        kp = max(1, int(round(gamma * P)))
        y = y - np.concatenate([np.zeros(kp), y[:-kp]])
        nf = min(len(y), int(0.01 * sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        y = y * self.level
        # pick scrape
        if self.pick_noise > 0:
            nk2 = int(0.005 * sr)
            nz = rng.uniform(-1, 1, nk2)
            nz = eq(nz, [("highpass", 1500, 0, 0.7), ("lowpass", 6000, 0, 0.7)], sr)
            env = np.exp(-np.arange(nk2) / (0.0012 * sr)) * (1 - np.exp(-np.arange(nk2) / (0.0002 * sr)))
            pk = max(np.abs(y[: int(0.02 * sr)]).max(), 1e-9)
            y[:nk2] += nz * env / max(np.abs(nz * env).max(), 1e-9) * pk * self.pick_noise * (0.4 + 0.6 * v)
        if meta.get("squeak"):
            ns = int(0.05 * sr)
            nz = rng.uniform(-1, 1, ns)
            fc = np.linspace(4200, 2400, ns)
            sq = svf(nz, fc, 3.0, "bp", sr) * np.sin(np.pi * np.arange(ns) / ns) ** 2
            sq = sq / max(np.abs(sq).max(), 1e-9) * max(np.abs(y).max(), 1e-9) * 10 ** (-30 / 20)
            pre = int(0.035 * sr)
            y = np.concatenate([np.zeros(pre), y])
            y[:ns] += sq
            meta["_pre_s"] = pre / sr
        return y


def render_events_pre(inst, events, n, post=True):
    """render_events that honours voices which start before their onset
    (meta['_pre_s'], e.g. a fret squeak ahead of the note)."""
    events = inst.prepare(sorted(events, key=lambda e: (e.start_s, e.pitch)))
    out = np.zeros((n, 2)) if inst.stereo else np.zeros(n)
    for ev in events:
        if "seed" in ev.meta:
            inst.rng = np.random.default_rng(int(ev.meta["seed"]))
        v = inst.voice(ev.pitch, ev.vel, ev.dur_s, ev.meta)
        if inst.stereo and v.ndim == 1:
            v = np.stack([v, v], 1)
        pre = ev.meta.pop("_pre_s", 0.0)
        add_at(out, v, int(round((ev.start_s - pre) * SR)))
    return inst.post(out) if post else out


# ----------------------------------------------------------------- layered drums with round robin

class LayeredKick:
    """Kick = synth body + sub tail (sine around 50 Hz, longer decay) + click
    (short high-passed tick). Every hit varies its synthesis a little (round
    robin): body pitch sweep, decays, click level and tone."""

    stereo = False
    name = "kick"

    def __init__(self, seed=10, level=0.7, sub=0.45, click=0.22, f_end=50.0):
        self.rng = np.random.default_rng(seed)
        self.level, self.sub, self.click, self.f_end, self.sr = level, sub, click, f_end, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        rng = self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        body = Kick(SR, int(rng.integers(1 << 30)), f_start=150.0 * (1 + rng.normal(0, 0.02)), f_end=self.f_end,
                    pitch_tau=0.03 * (1 + rng.normal(0, 0.06)), decay_s=0.17 * (1 + rng.normal(0, 0.06)),
                    click=0.25, drive=1.4, level=1.0).voice(36, v, 0.1, {})
        n = max(len(body), int(0.9 * SR))
        t = np.arange(n) / SR
        fs = self.f_end * (1 + 0.6 * np.exp(-t / 0.02))
        sub = np.sin(2 * np.pi * np.cumsum(fs) / SR) * np.exp(-t / (0.32 * (1 + rng.normal(0, 0.08)))) * \
            (1 - np.exp(-t / 0.003))
        nc = int(0.004 * SR)
        ck = rng.uniform(-1, 1, nc) * np.exp(-np.arange(nc) / (0.0006 * SR))
        ck = eq(ck, [("highpass", 3000 * (1 + rng.normal(0, 0.1)), 0, 0.7), ("lowpass", 9000, 0, 0.7)], SR)
        ck = ck / max(np.abs(ck).max(), 1e-9)
        y = np.zeros(n)
        y[:len(body)] += body
        y += self.sub * sub * (0.6 + 0.4 * v)
        y[:nc] += self.click * ck * v * (1 + rng.normal(0, 0.1))
        y = dc_block(y, 25.0, SR) * fade_curve(n, 0, int(0.08 * SR))
        return y * self.level * (0.35 + 0.65 * v)

    def post(self, x):
        return x


class LayeredSnare:
    """Snare = synth body + clap layer (a few ms late) + a noise tail, each hit
    varied (round robin). Ghost notes (low velocity) keep mostly the body."""

    stereo = False
    name = "snare"

    def __init__(self, seed=11, level=0.55, clap=0.35, tail=0.3):
        self.rng = np.random.default_rng(seed)
        self.level, self.clap, self.tail, self.sr = level, clap, tail, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        rng = self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        body = Snare(SR, int(rng.integers(1 << 30)), tone_hz=(190.0 * (1 + rng.normal(0, 0.015)), 335.0),
                     tone_decay=0.075 * (1 + rng.normal(0, 0.08)), noise_decay=0.13 * (1 + rng.normal(0, 0.08)),
                     level=1.0).voice(38, v, 0.1, {})
        n = int(0.7 * SR)
        y = np.zeros(n)
        y[:len(body)] += body
        cl = Clap(SR, int(rng.integers(1 << 30)), centre_hz=1200 * (1 + rng.normal(0, 0.05)), tail_s=0.09,
                  level=1.0).voice(39, v, 0.1, {})
        off = int((0.003 + 0.004 * rng.random()) * SR)
        w = self.clap * v ** 1.5
        y[off:off + len(cl)] += w * cl[: n - off]
        t = np.arange(n) / SR
        nz = rng.uniform(-1, 1, n)
        nz = eq(nz, [("highpass", 3500, 0, 0.7), ("lowpass", 11000, 0, 0.7)], SR)
        nz *= np.exp(-t / (0.22 * (1 + rng.normal(0, 0.1)))) * (1 - np.exp(-t / 0.002))
        y += self.tail * v ** 1.3 * nz / max(np.abs(nz).max(), 1e-9) * 0.5
        y = dc_block(y, 60.0, SR) * fade_curve(n, 0, int(0.1 * SR))
        return y * self.level * (0.3 + 0.7 * v)

    def post(self, x):
        return x


# ----------------------------------------------------------------- bass: sub sine + saturated mid layer

class LayeredBass:
    """Bass = clean sub sine (the weight) + a mid layer (synth.Bass pluck,
    high-passed at 110 Hz and tube-saturated for harmonics that read on phone
    speakers). Mono, dry."""

    stereo = False
    name = "bass"

    def __init__(self, seed=4, level=0.42, mid=0.55, drive=2.4):
        self.rng = np.random.default_rng(seed)
        self.level, self.mid, self.drive, self.sr = level, mid, drive, SR
        self.pluck = Bass(SR, seed, kind="pluck", cutoff=260.0, env_octaves=1.6, decay_s=0.22, resonance=0.2,
                          sub_level=0.0, release_s=0.08, level=1.0)

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        self.pluck.rng = self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        mid = self.pluck.voice(pitch, v, dur_s, meta)
        n = len(mid)
        t = np.arange(n) / SR
        f0 = float(midi_to_hz(pitch))
        env = np.minimum(1.0, t / 0.006) * np.where(t < dur_s, 1.0, np.exp(-(t - dur_s) / 0.03))
        env *= 0.85 + 0.15 * np.exp(-t / 0.25)
        sub = np.sin(2 * np.pi * f0 * t + self.rng.uniform(0, 2 * np.pi)) * env
        mid = eq(mid, [("highpass", 110, 0, 0.7)], SR)
        mid = np.tanh(self.drive * mid / max(np.abs(mid).max(), 1e-9)) / math.tanh(self.drive)
        y = 0.9 * sub + self.mid * mid * (0.5 + 0.5 * v)
        y *= fade_curve(n, 0, int(0.006 * SR))
        return y * self.level * (0.55 + 0.45 * v)

    def post(self, x):
        return dc_block(eq(x, [("lowpass", 3000, 0, 0.7)], SR), 20.0, SR)


# ----------------------------------------------------------------- arp synth pluck

class ArpPluck:
    """Analog-style pluck for the arpeggios: saw + pulse (alias-free additive)
    through a 4-pole ladder with a fast filter envelope. meta['cutoff'] sets the
    base cutoff per note, so a filter sweep is just a cutoff ramp across notes.
    No modulation: static pulse width, no detune, no vibrato."""

    stereo = False
    name = "arp"

    def __init__(self, seed=808, level=0.22, decay=0.26, env_oct=2.6, res=0.3):
        self.rng = np.random.default_rng(seed)
        self.level, self.decay, self.env_oct, self.res, self.sr = level, decay, env_oct, res, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        v = float(np.clip(vel, 0.05, 1.0))
        f = float(midi_to_hz(pitch))
        dec = self.decay * meta.get("decay_mul", 1.0)
        n = int((dec * 6 + 0.05) * SR)
        t = np.arange(n) / SR
        base = float(meta.get("cutoff", 900.0))
        cutoff = np.minimum(base * 2 ** (self.env_oct * v * np.exp(-t / 0.07)), 0.45 * SR)
        fmax = min(16000.0, 5.66 * float(cutoff.max()))
        x = 0.6 * osc_saw(f, n, SR, self.rng.uniform(), fmax) + 0.4 * osc_pulse(f, n, SR, 0.3, self.rng.uniform(), fmax)
        y = ladder(x, cutoff, self.res, 1.3, 0.5, SR)
        amp = np.exp(-t / dec) * (1 - np.exp(-t / 0.0015))
        y = y * amp * fade_curve(n, 0, int(0.03 * SR))
        return y * self.level * (0.3 + 0.7 * v)

    def post(self, x):
        return dc_block(eq(x, [("highpass", 180, 0, 0.7)], SR), 20.0, SR)


# ----------------------------------------------------------------- pad layer: soft choir / strings

class ChoirLayer:
    """Soft 'aah' layer under the pad: one saw per note (no unison, no
    vibrato) through three vowel formants and a gentle low-pass, slow attack."""

    stereo = False
    name = "choir"

    def __init__(self, seed=909, level=0.1, attack=1.2, release=2.0):
        self.rng = np.random.default_rng(seed)
        self.level, self.attack, self.release, self.sr = level, attack, release, SR

    def prepare(self, events):
        return events

    def voice(self, pitch, vel, dur_s, meta):
        a = float(meta.get("attack", self.attack))
        env = adsr_env(dur_s, a, 0.8, 0.9, self.release)
        n = len(env)
        f = float(midi_to_hz(pitch))
        x = osc_saw(f, n, SR, self.rng.uniform(), 6000.0)
        y = (svf(x, 720, 5.0, "bp", SR) + 0.7 * svf(x, 1150, 6.0, "bp", SR) + 0.25 * svf(x, 2700, 8.0, "bp", SR)
             + 0.35 * svf(x, 350, 2.0, "lp", SR))
        y = y * env
        return y * self.level * (0.6 + 0.4 * float(vel))

    def post(self, x):
        return dc_block(eq(x, [("highpass", 140, 0, 0.7), ("lowpass", 5000, 0, 0.7)], SR), 20.0, SR)


def adsr_env(gate_s, a, d, s, r):
    from synth.core import adsr
    return adsr(gate_s, a, d, s, r, SR, curve=3.0)


# ----------------------------------------------------------------- saturation

def tape(x, drive_db=4.0, bias=0.08, hf_db=-1.0):
    """Tape/tube-style saturation: asymmetric tanh (even plus odd harmonics)
    with unity small-signal gain (a fixed curve, so identical input always gives
    identical output), then a gentle head-bump and HF roll. drive_db is the
    input gain into the curve relative to full scale."""
    x = np.asarray(x, dtype=np.float64)
    d = 10 ** (drive_db / 20)
    sech2 = 1 - math.tanh(bias) ** 2
    y = (np.tanh(d * x + bias) - math.tanh(bias)) / (d * sech2)
    y = dc_block(y, 15.0, SR)
    return eq(y, [("peak", 90, 0.8, 0.9), ("highshelf", 9000, hf_db, 0.7)], SR)


# ----------------------------------------------------------------- more FX (mono)

def downlifter(dur=2.2, seed=761, peak_db=-24.0):
    """Mono downlifter after an impact: low-passed noise sweeping 6 kHz -> 200 Hz."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    fc = 6000 * (200 / 6000) ** (u ** 0.7)
    y = svf(rng.uniform(-1, 1, n), fc, 1.2, "lp", SR)
    y *= (1 - u) ** 1.6 * (1 - np.exp(-np.arange(n) / (0.01 * SR)))
    y = dc_block(y, 40.0, SR)
    return y / max(np.abs(y).max(), 1e-9) * 10 ** (peak_db / 20)


def reverse_crash(dur=1.5, seed=771, peak_db=-20.0):
    """Mono reversed crash swelling into its last sample."""
    c = MonoCrash(seed, level=1.0, decay_s=1.2).voice(49, 0.8, 0.1, {})
    y = c[::-1][-int(dur * SR):]
    y = y * fade_curve(len(y), int(0.1 * SR), int(0.004 * SR))
    return y / max(np.abs(y).max(), 1e-9) * 10 ** (peak_db / 20)
