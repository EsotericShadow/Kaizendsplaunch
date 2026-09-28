"""Bass: a clean sub (sine plus a touch of harmonics) or a pluck bass
(saw + square through a ladder with a fast filter envelope, layered with a sine
sub so the fundamental stays solid)."""
from __future__ import annotations

import numpy as np

from .core import SR, adsr, dc_block, midi_to_hz, pad_to
from .filters import eq, ladder
from .instrument import Instrument
from .osc import decimate, saw, sine, square, upsample


class Bass(Instrument):
    """kind: "sub" or "pluck".
    cutoff, env_octaves, decay_s: pluck filter (base cutoff, envelope depth, decay).
    sub_level: sine layer level in pluck mode. glide_semitones: small pitch drop
    at the attack (0 = none)."""

    name = "bass"

    def __init__(self, sr=SR, seed=4, kind="pluck", cutoff=180.0, env_octaves=3.2, decay_s=0.16,
                 resonance=0.28, sub_level=0.55, glide_semitones=0.0, release_s=0.07, level=0.42,
                 oversample=2):
        super().__init__(sr, seed)
        self.kind, self.cutoff, self.env_oct, self.decay = kind, cutoff, env_octaves, decay_s
        self.res, self.sub_level, self.glide = resonance, sub_level, glide_semitones
        self.release_s, self.level, self.os = release_s, level, oversample

    def voice(self, pitch, vel, dur_s, meta):
        sr, os_ = self.sr, self.os
        v = float(np.clip(vel, 0.05, 1.0))
        attack = 0.003 if self.kind == "pluck" else 0.009
        env = adsr(dur_s, attack, 0.35, 0.78, self.release_s, sr, curve=4.0)
        n = len(env)
        t = np.arange(n) / sr
        f0 = float(midi_to_hz(pitch))
        freq = f0 * 2 ** (self.glide * np.exp(-t / 0.025) / 12)
        ph = self.rng.uniform()
        sub = sine(freq, n, sr, ph)
        if self.kind == "sub":
            y = np.tanh(1.8 * sub) / np.tanh(1.8)  # adds odd harmonics, keeps peak at 1
        else:
            osc = 0.6 * saw(freq, n, sr, ph, 12000.0) + 0.4 * square(freq, n, sr, ph, 12000.0)
            fenv = np.exp(-t / (self.decay * (0.7 + 0.6 * v)))
            cutoff = self.cutoff * 2 ** (self.env_oct * (0.5 + 0.5 * v) * fenv + (pitch - 36) / 24)
            x2 = upsample(osc, os_)
            c2 = np.interp(np.arange(len(x2)) / os_, np.arange(n), np.minimum(cutoff, 0.45 * sr))
            y = pad_to(decimate(ladder(x2, c2, self.res, 1.5, 0.6, sr * os_), os_), n)
            y = y + self.sub_level * sub
        y = y * env * (0.55 + 0.45 * v)
        nf = min(len(y), int(0.004 * sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        return y * self.level

    def post(self, x):
        y = eq(x, [("highpass", 32, 0, 0.7)], self.sr)
        return dc_block(y, 12.0, self.sr)
