"""Clean electric guitar from an extended Karplus-Strong string model.

Signal path per note:
  pick excitation (velocity-dependent low-pass noise burst + pick click)
  -> pluck-position comb
  -> string loop: integer delay, 3-tap linear-phase damping FIR, first-order
     allpass for exact fractional tuning, loop gain from the target decay time
  -> pickup-position comb (depends on which string and fret plays the note)
Track level (``post``): pickup coil resonance, then either nothing (tone="di",
the mono DI to feed a chorus) or a clean amp and cabinet voicing.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, signal

from .core import SR, dc_block, jit, midi_to_hz
from .filters import eq
from .instrument import Instrument

OPEN_STRINGS = (40, 45, 50, 55, 59, 64)  # E2 A2 D3 G3 B3 E4
SCALE_MM = 648.0
PICKUP_MM = {"bridge": 41.0, "middle": 102.0, "neck": 162.0}


@jit
def _string_loop(exc, M, eta, a0, gain, n_out):
    y = np.zeros(n_out)
    a1 = 1.0 - 2.0 * a0
    f_prev = 0.0
    ap_prev = 0.0
    ne = len(exc)
    for n in range(n_out):
        d0 = y[n - M] if n >= M else 0.0
        d1 = y[n - M - 1] if n >= M + 1 else 0.0
        d2 = y[n - M - 2] if n >= M + 2 else 0.0
        f = a0 * d0 + a1 * d1 + a0 * d2          # linear phase, delay exactly 1 sample
        ap = eta * f + f_prev - eta * ap_prev     # fractional delay allpass
        f_prev = f
        ap_prev = ap
        e = exc[n] if n < ne else 0.0
        y[n] = e + gain[n] * ap
    return y


def _allpass_phase_delay(eta, w):
    z = np.exp(-1j * w)
    h = (eta + z) / (1 + eta * z)
    return -np.angle(h) / w


def tune_loop(f0, sr=SR):
    """Integer delay M and allpass coefficient eta so the loop period is exact at f0."""
    P = sr / f0
    M = int(math.floor(P - 1.0 - 0.5))
    d = P - 1.0 - M  # in [0.5, 1.5)
    w = 2 * math.pi * f0 / sr
    eta0 = (1 - d) / (1 + d)
    try:
        eta = optimize.brentq(lambda e: _allpass_phase_delay(e, w) - d, -0.95, 0.95)
    except ValueError:
        eta = eta0
    return M, float(eta), P


def string_and_fret(pitch):
    """Open-position fingering: the highest string that can play the note."""
    best = 0
    for i, o in enumerate(OPEN_STRINGS):
        if pitch >= o:
            best = i
    return best, pitch - OPEN_STRINGS[best]


class Guitar(Instrument):
    """Parameters
    tone: "di" (mono pickup signal, ideal chorus input) or "clean_amp".
    pickup: "neck", "middle" or "bridge" (sets the comb and coil resonance).
    brightness: 0..1 string damping (higher = brighter, longer highs).
    sustain_s: decay time (T60) of an open low E; higher notes decay faster.
    pluck: pluck position as a fraction of the string (0.08 near bridge .. 0.3).
    pick_hz: (soft, hard) corner of the pick excitation; velocity moves between them.
    humanize: per-note random spread of pluck position, brightness and tuning.
    choke: when True a new note on the same string stops the previous one.
    """

    name = "guitar"

    def __init__(self, sr=SR, seed=1, tone="di", pickup="neck", brightness=0.55, sustain_s=5.5,
                 pluck=0.16, humanize=1.0, choke=True, release_s=0.09, level=0.35, pick_hz=(300.0, 2200.0)):
        super().__init__(sr, seed)
        self.tone, self.pickup, self.brightness = tone, pickup, brightness
        self.sustain_s, self.pluck, self.humanize = sustain_s, pluck, humanize
        self.choke, self.release_s, self.level, self.pick_hz = choke, release_s, level, pick_hz

    def prepare(self, events):
        if not self.choke:
            return events
        last = {}
        for ev in events:
            s = ev.meta.get("string", string_and_fret(ev.pitch)[0])
            if s in last:
                prev = last[s]
                gap = ev.start_s - prev.start_s
                if prev.dur_s > gap:
                    prev.dur_s = max(0.02, gap)
            last[s] = ev
        return events

    def voice(self, pitch, vel, dur_s, meta):
        sr, rng, hz = self.sr, self.rng, self.humanize
        f0 = float(midi_to_hz(pitch)) * 2 ** (rng.normal(0, 0.8 * hz) / 1200)  # tiny intonation spread
        M, eta, P = tune_loop(f0, sr)
        string, fret = meta.get("string"), meta.get("fret")
        if string is None:
            string, fret = string_and_fret(pitch)
        if fret is None:
            fret = pitch - OPEN_STRINGS[string]
        v = float(np.clip(vel, 0.05, 1.0))

        # -- excitation: one period of noise, low-passed harder for soft picks
        ne = max(8, int(round(P)))
        noise = rng.uniform(-1, 1, ne)
        # plucked-string spectrum: -6 dB/oct above a velocity-dependent corner
        # (soft pick ~ 300 Hz, hard pick ~ 2 kHz), steeper above a second corner
        fc1 = (self.pick_hz[0] + (self.pick_hz[1] - self.pick_hz[0]) * v ** 1.5)
        a1 = math.exp(-2 * math.pi * fc1 / sr)
        exc = signal.lfilter([1 - a1], [1, -a1], noise)
        b, a = signal.butter(2, min(3500.0 + 6000.0 * v, 0.45 * sr), fs=sr)
        exc = signal.lfilter(b, a, exc)
        exc *= np.hanning(ne + 2)[1:-1] ** 0.25                 # soften burst edges
        # pick click: short raised-cosine pulse, louder when picked hard
        nk = max(3, int(0.0006 * sr))
        click = np.hanning(nk + 2)[1:-1] * (0.25 + 0.6 * v)
        exc[:nk] += click
        # pluck-position comb (also removes DC)
        beta = float(np.clip(self.pluck * (1 + rng.normal(0, 0.12 * hz)), 0.05, 0.45))
        kd = max(1, int(round(beta * P)))
        exc = exc - np.concatenate([np.zeros(kd), exc[:-kd]]) if kd < ne else exc
        exc *= v ** 1.2 / max(np.abs(exc).max(), 1e-9)

        # -- decay: T60 falls with pitch; damping FIR sets how fast highs die
        t60 = self.sustain_s * (82.4 / f0) ** 0.5
        bright = float(np.clip(self.brightness + rng.normal(0, 0.05 * hz), 0.05, 0.98))
        a0 = 0.25 * (1 - bright) ** 1.5
        w0 = 2 * math.pi * f0 / sr
        fir_mag = 1 - 2 * a0 * (1 - math.cos(w0))
        r = 10 ** (-3 * P / (sr * t60))
        g_sus = min(r / fir_mag, 0.99995)
        r_rel = 10 ** (-3 * P / (sr * self.release_s))
        g_rel = min(r_rel / fir_mag, 0.999)
        n_gate = int(dur_s * sr)
        n_out = n_gate + int(self.release_s * 1.4 * sr) + ne
        n_out = min(n_out, int((t60 * 1.1 + 0.05) * sr) + ne)  # stop once inaudible (-66 dB)
        gain = np.full(n_out, g_sus)
        if n_gate < n_out:
            nr = max(2, int(0.012 * sr))
            ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(nr) / nr)
            seg = gain[n_gate:n_gate + nr]
            seg[:] = g_sus + (g_rel - g_sus) * ramp[:len(seg)]
            gain[n_gate + nr:] = g_rel
        y = _string_loop(exc, M, eta, a0, gain, n_out)

        # -- pickup-position comb for the fretted string length
        L = SCALE_MM * 2 ** (-fret / 12)
        gamma = min(PICKUP_MM[self.pickup] / L, 0.45)
        kp = max(1, int(round(gamma * P)))
        y = y - np.concatenate([np.zeros(kp), y[:-kp]])
        # fade the very end to exact zero
        nf = min(len(y), int(0.01 * sr))
        y[-nf:] *= np.linspace(1, 0, nf)
        return y * self.level

    def post(self, x):
        sr = self.sr
        # pickup coil + cable resonance
        res = {"neck": (3600, 1.6), "middle": (4200, 1.8), "bridge": (4800, 1.9)}[self.pickup]
        y = eq(x, [("lowpass", res[0], 0, res[1]), ("lowpass", 11000, 0, 0.6)], sr)
        if self.tone == "clean_amp":
            y = eq(y, [("highpass", 75, 0, 0.7), ("peak", 130, 2.0, 1.0), ("peak", 450, -1.5, 1.0),
                       ("peak", 1800, 1.0, 0.9)], sr)
            # gentle, slightly asymmetric valve-like saturation
            drive = 1.6
            y = (np.tanh(drive * (y + 0.05)) - math.tanh(drive * 0.05)) / drive
            # 1x12 cabinet voicing
            y = eq(y, [("lowpass", 4800, 0, 0.85), ("lowpass", 7500, 0, 0.6), ("highpass", 70, 0, 0.6)], sr)
        return dc_block(y, 12.0, sr)
