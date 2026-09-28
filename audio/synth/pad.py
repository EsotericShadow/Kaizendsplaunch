"""Juno-style polysynth pad.

Per voice:
  DCO: additive (alias-free) saw + PWM pulse + sub square (-1 oct) + a little
       noise, with slow random pitch drift of a cent or two
  -> 2-pole high-pass (the Juno HPF)
  -> 4-pole ZDF ladder low-pass with its own ADSR, key tracking and a slow LFO
     (run at 2x so its saturation does not alias)
  -> VCA ADSR
Voices are spread across the stereo field by pitch (``spread``), so the pad is
genuinely stereo without any detune or chorus of its own.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from .core import SR, adsr, dc_block, midi_to_hz, pad_to, pan
from .filters import biquad, ladder
from .instrument import Instrument
from .osc import decimate, pulse, saw, square, upsample


def _drift(n, sr, rng, cents, rate_hz=0.4):
    """Smoothed random pitch drift in cents (band-limited random walk)."""
    k = max(4, int(n / sr * rate_hz * 4) + 4)
    pts = rng.normal(0, cents, k)
    x = np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
    b, a = signal.butter(1, rate_hz, fs=sr)
    return signal.lfilter(b, a, x, zi=[x[0]])[0]


class JunoPad(Instrument):
    """Parameters (times in seconds, cutoff in Hz)
    saw, pulse_level, sub, noise: oscillator mix.
    pwm_depth, pwm_rate: pulse width modulation (width 0.5 +- depth).
    hpf: high-pass corner. cutoff: ladder base cutoff. resonance 0..1.
    env_amount: filter envelope depth in octaves. keytrack 0..1.
    amp_adsr, filt_adsr: (a, d, s, r).
    spread: stereo spread of voices by pitch (0 = mono).
    drift_cents: analogue pitch drift (keep small so the chorus is the star).
    """

    name = "pad"
    stereo = True

    def __init__(self, sr=SR, seed=3, saw=0.55, pulse_level=0.45, sub=0.25, noise=0.015,
                 pwm_depth=0.18, pwm_rate=0.35, hpf=110.0, cutoff=700.0, resonance=0.18,
                 env_amount=1.6, keytrack=0.5, lfo_filter_oct=0.12, lfo_rate=0.18, drive=1.2,
                 amp_adsr=(0.9, 1.5, 0.85, 1.8), filt_adsr=(1.2, 2.5, 0.45, 1.8), spread=0.55,
                 drift_cents=1.2, level=0.16, oversample=2, fmax=18000.0):
        super().__init__(sr, seed)
        self.p = dict(saw=saw, pulse=pulse_level, sub=sub, noise=noise, pwm_depth=pwm_depth,
                      pwm_rate=pwm_rate, hpf=hpf, cutoff=cutoff, res=resonance, env_amount=env_amount,
                      keytrack=keytrack, lfo_oct=lfo_filter_oct, lfo_rate=lfo_rate, drive=drive,
                      amp=amp_adsr, filt=filt_adsr, spread=spread, drift=drift_cents)
        self.level, self.os, self.fmax = level, oversample, fmax

    def voice(self, pitch, vel, dur_s, meta):
        p, rng, sr, os_ = self.p, self.rng, self.sr, self.os
        a, d, s, r = p["amp"]
        amp_env = adsr(dur_s, a, d, s, r, sr, curve=3.0)
        n = len(amp_env)
        fa, fd, fs_, fr = p["filt"]
        f_env = adsr(dur_s, fa, fd, fs_, fr, sr, curve=3.0)
        f_env = np.concatenate([f_env, np.full(max(0, n - len(f_env)), f_env[-1])])[:n]
        t = np.arange(n) / sr
        f0 = float(midi_to_hz(pitch))
        freq = f0 * 2 ** (_drift(n, sr, rng, p["drift"]) / 1200)
        width = 0.5 + p["pwm_depth"] * np.sin(2 * np.pi * p["pwm_rate"] * t + rng.uniform(0, 2 * np.pi))
        fmax = self.fmax
        x = (p["saw"] * saw(freq, n, sr, rng.uniform(), fmax) +
             p["pulse"] * pulse(freq, n, sr, width, rng.uniform(), fmax) +
             p["sub"] * square(freq / 2, n, sr, rng.uniform(), fmax) +
             p["noise"] * rng.uniform(-1, 1, n))
        x = biquad(x, "highpass", p["hpf"], sr, 0.6)
        lfo = np.sin(2 * np.pi * p["lfo_rate"] * t + rng.uniform(0, 2 * np.pi))
        v = float(np.clip(vel, 0.05, 1.0))
        octs = (p["env_amount"] * (0.6 + 0.4 * v) * f_env + p["keytrack"] * (pitch - 60) / 12
                + p["lfo_oct"] * lfo)
        cutoff = np.minimum(p["cutoff"] * 2 ** octs, 0.45 * sr)
        x2 = upsample(x, os_)
        c2 = np.interp(np.arange(len(x2)) / os_, np.arange(n), cutoff)
        y = pad_to(decimate(ladder(x2, c2, p["res"], p["drive"], 0.5, sr * os_), os_), n)
        y *= amp_env * (0.5 + 0.5 * v)
        nf = min(len(y), int(0.005 * sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        pos = p["spread"] * float(np.clip((pitch - meta.get("centre", 62)) / 10.0, -1, 1))
        pos += rng.normal(0, 0.08 * p["spread"])
        return pan(y * self.level, float(np.clip(pos, -1, 1)))

    def post(self, x):
        return dc_block(x, 12.0, self.sr)
