"""Synthesised drums. Each class is an Instrument, so a drum part is just a
list of notes (pitch is ignored except where noted). Every hit gets small
random variations so repeated hits never sound identical.

Kick   : pitch-swept sine + beater click, gentle saturation
Snare  : two-mode tone body with pitch drop + band-limited noise wires
Clap   : four noise bursts then a diffuse tail, band-passed
HiHat  : six-square metallic cluster (808-style ratios) + noise, high-passed.
         pitch 42 = closed, 46 = open, 44 = pedal; closed/pedal choke open.
"""
from __future__ import annotations

import math

import numpy as np

from .core import SR, dc_block, exp_decay, fade_curve
from .filters import biquad, eq, svf
from .instrument import Instrument
from .osc import square

GM = {"kick": 36, "snare": 38, "clap": 39, "closed_hat": 42, "pedal_hat": 44, "open_hat": 46}


class Kick(Instrument):
    name = "kick"

    def __init__(self, sr=SR, seed=10, f_start=170.0, f_end=47.0, pitch_tau=0.032, decay_s=0.26,
                 click=0.5, drive=1.6, level=0.7):
        super().__init__(sr, seed)
        self.f_start, self.f_end, self.pitch_tau = f_start, f_end, pitch_tau
        self.decay_s, self.click, self.drive, self.level = decay_s, click, drive, level

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng = self.sr, self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        n = int((self.decay_s * 7.0) * sr)
        t = np.arange(n) / sr
        fs = self.f_start * (0.85 + 0.25 * v) * (1 + rng.normal(0, 0.01))
        f = self.f_end + (fs - self.f_end) * np.exp(-t / self.pitch_tau)
        ph = np.concatenate([[0.0], np.cumsum(f[:-1]) / sr])
        body = np.sin(2 * np.pi * ph)
        amp = np.exp(-t / self.decay_s) * (1 - np.exp(-t / 0.0004))
        body *= amp
        # beater click: short high-passed noise + raised-cosine pulse
        nc = int(0.006 * sr)
        cl = rng.uniform(-1, 1, nc) * np.exp(-np.arange(nc) / (0.0012 * sr))
        cl = biquad(cl, "highpass", 2500, sr, 0.7)
        np_ = int(0.0012 * sr)
        cl[:np_] += 0.8 * np.hanning(np_ + 2)[1:-1]
        body[:nc] += self.click * v * 0.35 * cl
        y = np.tanh(self.drive * body) / math.tanh(self.drive)
        y = dc_block(y, 18.0, sr)
        y *= fade_curve(n, 0, int(0.05 * sr))
        return y * self.level * (0.35 + 0.65 * v)


class Snare(Instrument):
    name = "snare"

    def __init__(self, sr=SR, seed=11, tone_hz=(185.0, 330.0), tone_decay=0.07, noise_decay=0.16,
                 tone_level=0.55, noise_level=0.65, level=0.55):
        super().__init__(sr, seed)
        self.tone_hz, self.tone_decay, self.noise_decay = tone_hz, tone_decay, noise_decay
        self.tone_level, self.noise_level, self.level = tone_level, noise_level, level

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng = self.sr, self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        n = int(0.6 * sr)
        t = np.arange(n) / sr
        tone = np.zeros(n)
        for k, (f0, lv) in enumerate(zip(self.tone_hz, (1.0, 0.55))):
            f = f0 * (1 + 0.35 * np.exp(-t / 0.012))
            ph = np.cumsum(f) / sr + rng.uniform()
            tone += lv * np.sin(2 * np.pi * ph) * exp_decay(n, self.tone_decay / (1 + 0.4 * k), sr, 0.0003)
        nz = rng.uniform(-1, 1, n)
        nz = eq(nz, [("highpass", 1600, 0, 0.7), ("peak", 5200, 4.0, 1.0), ("lowpass", 9500, 0, 0.7)], sr)
        nd = self.noise_decay * (0.75 + 0.4 * v) * (1 + rng.normal(0, 0.05))
        nz *= exp_decay(n, nd, sr, 0.0004)
        y = self.tone_level * tone + self.noise_level * nz * (0.6 + 0.4 * v)
        y = np.tanh(1.4 * y) / math.tanh(1.4)
        y = dc_block(y, 30.0, sr) * fade_curve(n, 0, int(0.1 * sr))
        return y * self.level * (0.3 + 0.7 * v)


class Clap(Instrument):
    name = "clap"

    def __init__(self, sr=SR, seed=12, centre_hz=1150.0, tail_s=0.11, level=0.5):
        super().__init__(sr, seed)
        self.centre_hz, self.tail_s, self.level = centre_hz, tail_s, level

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng = self.sr, self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        n = int(0.5 * sr)
        t = np.arange(n) / sr
        env = np.zeros(n)
        offsets = np.cumsum([0.0] + list(rng.uniform(0.007, 0.012, 3)))
        for k, o in enumerate(offsets):
            tt = t - o
            m = tt >= 0
            env[m] += (0.8 + 0.2 * k / 3) * np.exp(-tt[m] / 0.0035) * (1 - np.exp(-tt[m] / 0.0002))
        tt = t - offsets[-1]
        m = tt >= 0
        env[m] += 0.55 * np.exp(-tt[m] / (self.tail_s * (0.8 + 0.3 * v))) * (1 - np.exp(-tt[m] / 0.001))
        nz = rng.uniform(-1, 1, n)
        y = svf(nz, self.centre_hz * (1 + rng.normal(0, 0.03)), 1.1, "bp", sr)
        y = y + 0.35 * biquad(nz, "highpass", 2500, sr, 0.7) * 0.4
        y *= env
        y = biquad(y, "highpass", 450, sr, 0.7) * fade_curve(n, 0, int(0.08 * sr))
        y /= max(np.abs(y).max(), 1e-9)
        return y * self.level * (0.3 + 0.7 * v)


HAT_RATIOS = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0])


def metallic(n, sr, rng, tune=1.0):
    """Six detuned band-limited squares (the TR-808 cymbal/hat cluster)."""
    x = np.zeros(n)
    for f in HAT_RATIOS * tune:
        x += square(f * (1 + rng.normal(0, 0.002)), n, sr, rng.uniform())
    return x / 6.0


class HiHat(Instrument):
    name = "hihat"

    def __init__(self, sr=SR, seed=13, tune=1.55, closed_decay=0.035, open_decay=0.33, noise_mix=0.45,
                 brightness_hz=8200.0, level=0.3):
        super().__init__(sr, seed)
        self.tune, self.cd, self.od, self.noise_mix = tune, closed_decay, open_decay, noise_mix
        self.bright, self.level = brightness_hz, level

    def prepare(self, events):
        # closed or pedal hat chokes a ringing open hat
        last_open = None
        for ev in events:
            if ev.pitch == GM["open_hat"]:
                last_open = ev
            elif ev.pitch in (GM["closed_hat"], GM["pedal_hat"]) and last_open is not None:
                last_open.meta["choke_at"] = ev.start_s - last_open.start_s
                last_open = None
        return events

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng = self.sr, self.rng
        v = float(np.clip(vel, 0.05, 1.0))
        is_open = pitch == GM["open_hat"]
        decay = (self.od if is_open else self.cd * (0.8 + 0.5 * v)) * (1 + rng.normal(0, 0.06))
        if pitch == GM["pedal_hat"]:
            decay = self.cd * 0.7
        n = int(min(decay * 7, 2.0) * sr)
        met = metallic(n, sr, rng, self.tune)
        nz = rng.uniform(-1, 1, n)
        x = (1 - self.noise_mix) * met + self.noise_mix * nz
        x = svf(x, self.bright * (0.92 + 0.12 * v), 0.9, "bp", sr) + 0.5 * biquad(x, "highpass", 9000, sr, 0.7)
        env = exp_decay(n, decay, sr, 0.0002)
        choke = meta.get("choke_at")
        if choke is not None and choke * sr < n:
            k = int(choke * sr)
            nr = int(0.012 * sr)
            g = np.ones(n)
            g[k:k + nr] = np.linspace(1, 0, len(g[k:k + nr]))
            g[k + nr:] = 0
            env *= g
        # high-pass after the envelope so the onset click carries no low end
        y = eq(x * env, [("highpass", 6500, 0, 0.7), ("highpass", 6500, 0, 0.7), ("lowpass", 14000, 0, 0.7)], sr)
        y *= fade_curve(n, 0, int(0.004 * sr))
        y /= max(np.abs(y).max(), 1e-9)
        return y * self.level * (0.25 + 0.75 * v)


class Rim(Instrument):
    """Short woody rim click, handy for sparse intros."""
    name = "rim"

    def __init__(self, sr=SR, seed=14, level=0.35):
        super().__init__(sr, seed)
        self.level = level

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng = self.sr, self.rng
        n = int(0.12 * sr)
        t = np.arange(n) / sr
        y = (np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.008) + 0.6 * np.sin(2 * np.pi * 510 * t) * np.exp(-t / 0.012))
        y += 0.3 * biquad(rng.uniform(-1, 1, n), "bandpass", 3500, sr, 1.5) * np.exp(-t / 0.004)
        y *= 1 - np.exp(-t / 0.0002)
        y = dc_block(y, 40.0, sr) * fade_curve(n, 0, int(0.02 * sr))
        return y / max(np.abs(y).max(), 1e-9) * self.level * float(np.clip(vel, 0.05, 1.0))
