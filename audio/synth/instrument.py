"""Instrument base class: turns note events into audio by summing voices."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .core import SR, add_at, ensure_stereo


@dataclass
class NoteEvent:
    """A note in absolute time, as produced by the sequencer."""
    start_s: float
    pitch: int
    vel: float
    dur_s: float
    meta: dict = field(default_factory=dict)


class Instrument:
    """Subclasses implement ``voice`` (one note, mono or stereo, starting at the
    note onset and including its release tail) and optionally ``post`` (track
    level processing applied to the summed voices, e.g. amp and cabinet)."""

    stereo = False
    name = "instrument"

    def __init__(self, sr=SR, seed=0):
        self.sr = sr
        self.rng = np.random.default_rng(seed)

    # -- to override -------------------------------------------------------
    def voice(self, pitch: int, vel: float, dur_s: float, meta: dict) -> np.ndarray:
        raise NotImplementedError

    def post(self, x: np.ndarray) -> np.ndarray:
        return x

    def prepare(self, events: list[NoteEvent]) -> list[NoteEvent]:
        """Hook to edit the event list before rendering (e.g. hi-hat choke)."""
        return events

    # -- rendering ---------------------------------------------------------
    def render(self, events: list[NoteEvent], length: int) -> np.ndarray:
        """Render events into a buffer of ``length`` samples. Returns (length, 2)
        if the instrument is stereo, else (length,)."""
        events = self.prepare(sorted(events, key=lambda e: e.start_s))
        out = np.zeros((length, 2)) if self.stereo else np.zeros(length)
        for ev in events:
            v = self.voice(ev.pitch, ev.vel, ev.dur_s, ev.meta)
            if self.stereo:
                v = ensure_stereo(v)
            add_at(out, v, int(round(ev.start_s * self.sr)))
        return self.post(out)
