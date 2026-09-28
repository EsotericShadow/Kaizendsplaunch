"""Run audio through an external command-line processor as a mixer insert.

Used to put the real Choroboros processor (the local ``choro-render`` build,
documented in docs/brief/dsp-renderer.md) on a dry stem. Nothing proprietary
lives here: this only writes a WAV, calls a program and reads the result. The
binary path comes from the CHORO_RENDER environment variable or an argument and
must stay outside this repository.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np

from .core import SR, ensure_stereo, pad_to
from . import io

DEFAULT_CHORO_RENDER = "/home/user/build/choro-render/build/choro-render"


class ExternalInsert:
    """cmd is a list with {in} and {out} placeholders, e.g.
    ["sox", "{in}", "{out}", "reverb"]. The output is trimmed or padded to the
    input length plus ``keep_tail_s``."""

    def __init__(self, cmd, sr=SR, keep_tail_s=0.0, mono_input=False):
        self.cmd, self.sr, self.keep_tail_s, self.mono_input = list(cmd), sr, keep_tail_s, mono_input

    def __call__(self, x):
        x = np.asarray(x, dtype=np.float64)
        with tempfile.TemporaryDirectory() as td:
            pin, pout = os.path.join(td, "in.wav"), os.path.join(td, "out.wav")
            src = x.mean(axis=1) if (self.mono_input and x.ndim == 2) else x
            io.write_wav(pin, src, self.sr)
            cmd = [c.replace("{in}", pin).replace("{out}", pout) for c in self.cmd]
            subprocess.run(cmd, check=True, capture_output=True)
            y, sr = io.read_wav(pout)
        if sr != self.sr:
            raise ValueError(f"external processor returned {sr} Hz, expected {self.sr}")
        return pad_to(ensure_stereo(y), len(x) + int(self.keep_tail_s * self.sr))


def choro_available(binary=None):
    b = binary or os.environ.get("CHORO_RENDER", DEFAULT_CHORO_RENDER)
    return b if os.path.isfile(b) and os.access(b, os.X_OK) else None


def choroboros(engine="green", hq=False, rate=None, depth=None, offset=None, width=None, color=None,
               mix=None, trim=None, automation=None, binary=None, sr=SR, tail_s=0.0):
    """Insert that runs the stem through Choroboros via choro-render.
    Knob units match the plugin UI: rate Hz, depth/width/color/mix in percent,
    offset in degrees, trim in dB. Unset knobs keep the engine's factory value."""
    b = choro_available(binary)
    if not b:
        raise FileNotFoundError("choro-render not found; set CHORO_RENDER")
    cmd = [b, "--in", "{in}", "--out", "{out}", "--engine", engine, "--hq", "1" if hq else "0",
           "--tail", str(max(tail_s, 0.0)), "--quiet"]
    for flag, val, unit in (("--rate", rate, ""), ("--depth", depth, "%"), ("--offset", offset, ""),
                            ("--width", width, "%"), ("--color", color, "%"), ("--mix", mix, "%"),
                            ("--trim", trim, "")):
        if val is not None:
            cmd += [flag, f"{val}{unit}"]
    if automation:
        cmd += ["--automation", automation]
    return ExternalInsert(cmd, sr, keep_tail_s=0.0)
