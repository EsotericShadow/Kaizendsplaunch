"""FM electric piano in the style of the DX7 "E.PIANO 1" family.

Three two-operator stacks (carrier <- modulator), phase modulation:
  body  : C 1.00 <- M 1.00, index rises with velocity (the "bark"), decays slowly
  tine  : C 1.00 <- M 14.0, short bright index burst (the metallic tine attack)
  warmth: C 1.00 <- M 1.00 at low index, slightly detuned for a softer core
Index is scaled down for high keys to keep sidebands below Nyquist, and every
voice is rendered at 2x then decimated. Tremolo is off; the output is mono.
"""
from __future__ import annotations

import math

import numpy as np

from .core import SR, dc_block, midi_to_hz
from .filters import eq
from .instrument import Instrument
from .osc import decimate


def _carrier_env(n, sr, pitch, attack_s, gate_n, release_s):
    t = np.arange(n) / sr
    key = (pitch - 60) / 12.0
    fast = 0.55 * 2 ** (-0.35 * key)
    slow = 4.2 * 2 ** (-0.55 * key)
    env = 0.55 * np.exp(-t / fast) + 0.45 * np.exp(-t / slow)
    na = max(2, int(attack_s * sr))
    env[:na] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(na) / na)
    # damper: exponential release from gate end, reaching zero at the end
    if gate_n < n:
        nr = n - gate_n
        tr = np.arange(nr) / sr
        tau = release_s / 5.0
        shape = (np.exp(-tr / tau) - math.exp(-release_s / tau)) / (1 - math.exp(-release_s / tau))
        env[gate_n:] *= np.clip(shape, 0, 1)
    return env


class EPiano(Instrument):
    """Parameters
    bark: scales the velocity-driven body index (0.6 soft .. 1.4 aggressive).
    tine: level of the 14:1 tine attack.
    detune_cents: tiny static detune of the warmth stack (0 = none).
    release_s: damper release time.
    """

    name = "epiano"

    def __init__(self, sr=SR, seed=2, bark=1.0, tine=1.0, detune_cents=0.7, release_s=0.35,
                 level=0.28, oversample=2):
        super().__init__(sr, seed)
        self.bark, self.tine, self.detune = bark, tine, detune_cents
        self.release_s, self.level, self.os = release_s, level, oversample

    def voice(self, pitch, vel, dur_s, meta):
        sr = self.sr * self.os
        v = float(np.clip(vel, 0.05, 1.0))
        f = float(midi_to_hz(pitch))
        gate_n = int(dur_s * sr)
        key = (pitch - 60) / 12.0
        slow = 4.2 * 2 ** (-0.55 * key)
        n = gate_n + int(self.release_s * sr)
        n = min(n, int((slow * 3.2 + 0.05) * sr))  # carrier is below -60 dB by then
        gate_n = min(gate_n, n)
        t = np.arange(n) / sr
        tw = 2 * math.pi * t
        ph = self.rng.uniform(0, 2 * math.pi, 3)

        # key scaling for the indices
        ks_body = float(np.clip(2 ** (-0.45 * key), 0.35, 1.3))
        ks_tine = float(np.clip(2 ** (-0.9 * key), 0.12, 1.6))

        # body stack
        i_body = (0.35 + 2.1 * v ** 1.7) * self.bark * ks_body
        env_ib = 0.35 + 0.65 * np.exp(-t / (0.25 + 0.25 * (1 - v)))
        mod = np.sin(tw * f + ph[0])
        body = np.sin(tw * f + i_body * env_ib * mod)

        # tine stack: 14:1 modulator, very short index envelope
        i_tine = (0.15 + 1.9 * v ** 2) * self.tine * ks_tine
        env_it = np.exp(-t / (0.018 + 0.012 * v))
        mod = np.sin(tw * f * 14.0 + ph[1])
        tine = np.sin(tw * f * 2 ** (1.2 / 1200) + i_tine * env_it * mod)

        # warmth stack
        mod = np.sin(tw * f + ph[2])
        warm = np.sin(tw * f * 2 ** (-self.detune / 1200) + 0.35 * v * mod)

        env = _carrier_env(n, sr, pitch, 0.0015, gate_n, self.release_s)
        tine_env = np.exp(-t / 0.9) * env
        y = env * (0.62 * body + 0.33 * warm) + 0.30 * tine_env * tine
        amp = (0.25 + 0.75 * v ** 1.3)
        y = decimate(y * amp, self.os)
        nf = min(len(y), int(0.004 * self.sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        return y * self.level

    def post(self, x):
        # preamp warmth and a softened top, like a sampled Rhodes-style DI
        y = eq(x, [("lowshelf", 220, 1.5, 0.7), ("peak", 1200, -1.0, 0.9), ("highshelf", 7000, -2.5, 0.7)], self.sr)
        y = np.tanh(1.3 * y) / 1.3
        return dc_block(y, 12.0, self.sr)
