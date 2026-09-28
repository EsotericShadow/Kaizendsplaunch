"""Original-music toolkit for the Kaizen DSP launch video.

Small numpy/scipy synthesis package (numba optional, strongly recommended):
instruments suited to showing off a chorus, a beat-based sequencer, a mixer with
sends and a master chain, and loudness/true-peak metering. See
docs/brief/audio.md for the API and examples/dreamy_demo.py for a full song.
"""
from .core import (SR, HAVE_NUMBA, adsr, amp_to_db, db_to_amp, ensure_stereo, midi_to_hz, note,
                   note_name, pan)
from .instrument import Instrument, NoteEvent
from .guitar import Guitar
from .epiano import EPiano
from .pad import JunoPad
from .bass import Bass
from .drums import GM, Clap, HiHat, Kick, Rim, Snare
from . import fx
from .effects import Reverb, StereoDelay, compressor, duck, limiter, normalize_lufs, saturate
from .sequencer import Humanize, Note, Song, arpeggio, chord, drum_grid, repeat, shift, strum
from .mixer import Mixer, MixResult
from . import meter, io, viz, filters, osc

__all__ = [
    "SR", "HAVE_NUMBA", "adsr", "amp_to_db", "db_to_amp", "ensure_stereo", "midi_to_hz", "note", "note_name",
    "pan", "Instrument", "NoteEvent", "Guitar", "EPiano", "JunoPad", "Bass", "GM", "Clap", "HiHat", "Kick",
    "Rim", "Snare", "fx", "Reverb", "StereoDelay", "compressor", "duck", "limiter", "normalize_lufs", "saturate",
    "Humanize", "Note", "Song", "arpeggio", "chord", "drum_grid", "repeat", "shift", "strum", "Mixer",
    "MixResult", "meter", "io", "viz", "filters", "osc",
]
