"""Mixer: channels with gain, pan, width, EQ, compression, inserts and sends;
return buses (reverb, delay); a master chain (bus compressor, loudness target,
true-peak-safe limiter); stem export and a metrics report."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .core import SR, balance, db_to_amp, ensure_stereo, ms_width, pad_to, pan as pan_mono
from .effects import compressor, limiter
from .filters import eq as eq_apply
from . import io, meter


@dataclass
class Channel:
    name: str
    audio: np.ndarray
    gain_db: float = 0.0
    pan: float = 0.0
    width: float = 1.0
    eq: list | None = None
    comp: dict | None = None
    inserts: list[Callable] = field(default_factory=list)
    sends: dict = field(default_factory=dict)   # bus name -> send level dB (post-fader)
    mute: bool = False


@dataclass
class Bus:
    name: str
    processor: Callable
    gain_db: float = 0.0
    eq: list | None = None


@dataclass
class MixResult:
    master: np.ndarray
    premaster: np.ndarray
    stems: dict
    returns: dict
    info: dict
    sr: int = SR

    def export(self, folder, prefix="", master_name="mix"):
        """Write stems, returns and master as 48 kHz float32 stereo WAV, plus
        mix_info.json. Returns the list of paths."""
        os.makedirs(folder, exist_ok=True)
        paths = []
        for kind, d in (("stem", self.stems), ("return", self.returns)):
            for k, v in d.items():
                p = os.path.join(folder, f"{prefix}{kind}_{k}.wav")
                io.write_wav(p, v, self.sr)
                paths.append(p)
        p = os.path.join(folder, f"{prefix}{master_name}.wav")
        io.write_wav(p, self.master, self.sr)
        paths.append(p)
        with open(os.path.join(folder, f"{prefix}mix_info.json"), "w") as fh:
            json.dump(self.info, fh, indent=1, default=float)
        return paths


class Mixer:
    def __init__(self, sr=SR):
        self.sr = sr
        self.channels: list[Channel] = []
        self.buses: dict[str, Bus] = {}

    def track(self, name, audio, gain_db=0.0, pan=0.0, width=1.0, eq=None, comp=None, sends=None,
              inserts=None, mute=False):
        """Add a channel. Mono audio is panned with the -3 dB law; stereo audio
        uses a balance control. comp is a dict of effects.compressor kwargs."""
        self.channels.append(Channel(name, np.asarray(audio, dtype=np.float64), gain_db, pan, width, eq, comp,
                                     list(inserts or []), dict(sends or {}), mute))
        return self

    def bus(self, name, processor, gain_db=0.0, eq=None):
        self.buses[name] = Bus(name, processor, gain_db, eq)
        return self

    def _channel_out(self, ch: Channel, n: int):
        x = ch.audio
        for fx in ch.inserts:
            x = fx(x)
        if ch.eq:
            x = eq_apply(x, ch.eq, self.sr)
        if ch.comp:
            y = compressor(x, sr=self.sr, **ch.comp)
            x = y if x.ndim == 2 else y[:, 0]
        if x.ndim == 1:
            x = pan_mono(x, ch.pan)
        else:
            x = balance(ensure_stereo(x), ch.pan)
        if ch.width != 1.0:
            x = ms_width(x, ch.width)
        return pad_to(x * db_to_amp(ch.gain_db), n)

    def render(self, master_comp: dict | None = None, target_lufs: float | None = -16.0,
               ceiling_dbtp: float = -1.0, limiter_kw: dict | None = None, length: int | None = None):
        n = length or max(len(c.audio) for c in self.channels)
        stems, sends = {}, {b: np.zeros((n, 2)) for b in self.buses}
        for ch in self.channels:
            if ch.mute:
                continue
            y = self._channel_out(ch, n)
            stems[ch.name] = y
            for b, lvl in ch.sends.items():
                if b not in sends:
                    raise KeyError(f"no bus named {b!r}")
                sends[b] += y * db_to_amp(lvl)
        returns = {}
        for b, bus in self.buses.items():
            w = pad_to(ensure_stereo(bus.processor(sends[b])), n)
            if bus.eq:
                w = eq_apply(w, bus.eq, self.sr)
            returns[b] = w * db_to_amp(bus.gain_db)
        pre = sum(stems.values()) + (sum(returns.values()) if returns else 0)
        x = pre
        info = {"premaster": _brief(pre, self.sr)}
        if master_comp:
            x, gr = compressor(x, sr=self.sr, return_gr=True, **master_comp)
            info["bus_comp_max_gr_db"] = round(float(-gr.min()), 2)
            info["bus_comp_mean_gr_db"] = round(float(-gr[np.abs(pre).max(axis=1) > 1e-4].mean()), 2)
        gain = 0.0
        if target_lufs is not None:
            gain = target_lufs - meter.integrated_lufs(x, self.sr)
            for _ in range(4):   # limiting lowers loudness a little: converge on the target
                y, lim = limiter(x * db_to_amp(gain), ceiling_dbtp, sr=self.sr, **(limiter_kw or {}))
                err = target_lufs - meter.integrated_lufs(y, self.sr)
                if abs(err) < 0.05:
                    break
                gain += err
            x = y
            info["limiter"] = lim
        else:
            x, lim = limiter(x, ceiling_dbtp, sr=self.sr, **(limiter_kw or {}))
            info["limiter"] = lim
        info["master_gain_db"] = round(gain, 2)
        info["master"] = meter.report(x, self.sr, tempo=False, key=False)
        info["stems"] = {k: _brief(v, self.sr) for k, v in stems.items()}
        info["returns"] = {k: _brief(v, self.sr) for k, v in returns.items()}
        # stems scaled by the master gain so they sum to the pre-limiter master
        g = db_to_amp(gain)
        return MixResult(x, pre * g, {k: v * g for k, v in stems.items()},
                         {k: v * g for k, v in returns.items()}, info, self.sr)


def _brief(x, sr):
    return {"lufs": round(meter.integrated_lufs(x, sr), 2), "sample_peak_dbfs": round(meter.sample_peak(x), 2),
            "rms_dbfs": round(meter.rms_db(x), 2)}
