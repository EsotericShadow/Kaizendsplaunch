"""Sequencer: tempo, bars and note events in beats, humanisation, and pattern
helpers (chords, arpeggios, strums, drum grids)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

from .core import SR, ensure_stereo, note as note_num
from .instrument import Instrument, NoteEvent


@dataclass
class Note:
    start: float          # beats from the start of the song (0 = bar 1, beat 1)
    dur: float            # beats
    pitch: int            # MIDI note number (60 = C4)
    vel: float = 0.8      # 0..1
    meta: dict = field(default_factory=dict)


@dataclass
class Humanize:
    """timing_ms: Gaussian timing spread (SD). velocity: SD of a velocity multiplier.
    swing: delay of off-grid notes as a fraction of the grid (0.33 = triplet feel).
    grid: swing grid in beats (0.25 = 16ths). push_ms: constant offset
    (negative plays ahead). seed: makes every render identical."""
    timing_ms: float = 0.0
    velocity: float = 0.0
    swing: float = 0.0
    grid: float = 0.25
    push_ms: float = 0.0
    seed: int = 0


class Song:
    def __init__(self, bpm=104.0, bars=16, beats_per_bar=4, sr=SR, tail_s=3.0):
        self.bpm, self.bars, self.bpb, self.sr, self.tail_s = float(bpm), bars, beats_per_bar, sr, tail_s

    @property
    def spb(self):
        return 60.0 / self.bpm

    def beats(self, bar, beat=0.0):
        """Beat position of a 0-based bar plus beat offset."""
        return bar * self.bpb + beat

    def seconds(self, beats):
        return beats * self.spb

    def sample(self, beats):
        return int(round(self.seconds(beats) * self.sr))

    @property
    def duration_s(self):
        return self.bars * self.bpb * self.spb

    @property
    def length(self):
        return int(round((self.duration_s + self.tail_s) * self.sr))

    def events(self, notes, humanize: Humanize | None = None):
        h = humanize or Humanize()
        rng = np.random.default_rng(h.seed)
        out = []
        for n in notes:
            b = n.start
            if h.swing and h.grid:
                pos = b / h.grid
                if abs(pos - round(pos)) < 1e-6 and int(round(pos)) % 2 == 1:
                    b += h.swing * h.grid
            t = self.seconds(b) + (h.push_ms + rng.normal(0, h.timing_ms) if h.timing_ms else h.push_ms) / 1000.0
            v = n.vel * (1 + rng.normal(0, h.velocity)) if h.velocity else n.vel
            out.append(NoteEvent(max(0.0, t), int(n.pitch), float(np.clip(v, 0.02, 1.0)),
                                 self.seconds(n.dur), copy.deepcopy(n.meta)))
        return out

    def render(self, instrument: Instrument, notes, humanize: Humanize | None = None, stereo=True):
        """Render a part to a buffer covering the whole song plus tail."""
        y = instrument.render(self.events(notes, humanize), self.length)
        return ensure_stereo(y) if stereo else y

    def place(self, audio, at_beats, length=None):
        """Place a one-shot (e.g. an FX from fx.py) at a beat position. Negative
        offsets are allowed for audio that must end on a downbeat."""
        from .core import add_at
        audio = ensure_stereo(audio)
        buf = np.zeros((length or self.length, 2))
        return add_at(buf, audio, self.sample(at_beats))


# ----------------------------------------------------------------- chords

_QUALITIES = {
    "": (0, 4, 7), "maj": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "5": (0, 7),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9), "69": (0, 4, 7, 9, 14),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "m7b5": (0, 3, 6, 10),
    "7sus4": (0, 5, 7, 10), "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
    "m11": (0, 3, 7, 10, 14, 17), "maj7#11": (0, 4, 7, 11, 18), "6sus4": (0, 5, 7, 9),
}


def chord(symbol: str, octave: int = 3):
    """'Gmaj7' -> [55, 59, 62, 66]; slash chords 'C/E' put E below. Close position
    from the root in the given octave."""
    bass = None
    if "/" in symbol:
        symbol, bass = symbol.split("/")
    i = 1
    if len(symbol) > 1 and symbol[1] in "#b":
        i = 2
    root = note_num(symbol[:i] + str(octave))
    q = symbol[i:]
    if q not in _QUALITIES:
        raise ValueError(f"unknown chord quality {q!r}")
    notes = [root + k for k in _QUALITIES[q]]
    if bass:
        b = note_num(bass + str(octave))
        while b >= notes[0]:
            b -= 12
        notes = [b] + notes
    return notes


# ----------------------------------------------------------------- patterns

def drum_grid(pattern: str, pitch: int, start: float = 0.0, step: float = 0.25, accents=None):
    """Notes from a step string. 'X' loud, 'x' normal, 'o' soft, 'g' ghost,
    '.' or '-' rest; spaces and '|' are ignored."""
    vel = accents or {"X": 1.0, "x": 0.8, "o": 0.55, "g": 0.3}
    out = []
    k = 0
    for ch in pattern:
        if ch in " |":
            continue
        if ch in vel:
            out.append(Note(start + k * step, step, pitch, vel[ch]))
        k += 1
    return out


def arpeggio(pitches, order, start, step=0.5, gate=1.0, vel=0.75, accent_every=0, accent=0.12, meta=None):
    """Play pitches[order[i]] every step beats. gate is the note length in steps
    (values > 1 let notes ring over the next ones)."""
    out = []
    for i, idx in enumerate(order):
        if idx is None:
            continue
        v = vel + (accent if accent_every and i % accent_every == 0 else 0.0)
        out.append(Note(start + i * step, step * gate, pitches[idx], min(v, 1.0), dict(meta or {})))
    return out


def strum(pitches, start, dur, bpm, vel=0.75, spread_ms=14.0, down=True, vel_taper=0.08):
    """Chord with the notes spread in time like a pick stroke (down = low to high)."""
    order = list(pitches) if down else list(pitches)[::-1]
    spb = 60.0 / bpm
    out = []
    for i, p in enumerate(order):
        off = i * spread_ms / 1000.0 / spb
        out.append(Note(start + off, max(dur - off, 0.05), p, max(0.05, vel * (1 - vel_taper * i))))
    return out


def repeat(notes, times, every):
    out = []
    for k in range(times):
        for n in notes:
            out.append(Note(n.start + k * every, n.dur, n.pitch, n.vel, dict(n.meta)))
    return out


def shift(notes, beats=0.0, semitones=0, vel_scale=1.0):
    return [Note(n.start + beats, n.dur, n.pitch + semitones, min(1.0, n.vel * vel_scale), dict(n.meta))
            for n in notes]
