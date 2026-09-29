"""Shared paths and helpers for the v5 audio forensics (song map, grid, hits).

Inputs are the owner's files in the upload folder; outputs are written under /home/user/build/v5 (audio,
never committed) and film/v5 (timing data only). Master time t = 0 is the first sample of the master mp3
as decoded gapless (LAME encoder delay and decoder delay removed).
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf

UP = os.environ.get("SONG_UPLOADS", "/root/.claude/uploads/f63a1200-0746-5eb0-86a7-2113896bbccf")
OUT = os.environ.get("V5_OUT", "/home/user/build/v5")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FILM_V5 = os.path.join(REPO, "film", "v5")
SR = 48000


def _up(suffix):
    """Name of the uploaded file ending with suffix. The upload names carry a working title that stays
    out of the repo, so files are found by their stem suffix."""
    names = sorted(f for f in os.listdir(UP) if f.endswith(suffix))
    if not names:
        raise FileNotFoundError(f"no upload ending with {suffix} in {UP}")
    return names[-1]


MASTER_MP3 = os.path.join(UP, _up("_copy.mp3"))
OTHER_MP3 = os.path.join(UP, _up("_thisone.mp3"))
STEMS = {  # name in v5 -> uploaded file
    "kick": _up("_Kick_In.wav"),
    "snare": _up("_Snare.wav"),
    "hihat": _up("_Hi_Hat.wav"),
    "racktom": _up("_Rack_Tom.wav"),
    "floortom": _up("_Floor_Tom.wav"),
    "ohl": _up("_Overhead_Left.wav"),
    "ohr": _up("_Overhead_Right.wav"),
}
DRUMS = list(STEMS)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def decode_mp3(path, out_wav, gapless=True):
    """Decode with ffmpeg to float WAV. gapless=True applies the LAME/Xing delay+padding trim."""
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y"]
    if not gapless:
        cmd += ["-flags2", "+skip_manual"]
    cmd += ["-i", path, "-c:a", "pcm_f32le", out_wav]
    subprocess.run(cmd, check=True)
    x, _ = sf.read(out_wav, dtype="float64", always_2d=True)
    return x


def load(path):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    return x, sr


def master():
    x, sr = load(os.path.join(OUT, "master_src.wav"))
    assert sr == SR
    return x


def stem(name):
    x, sr = load(os.path.join(OUT, "stems", f"{name}.wav"))
    assert sr == SR
    return x


def write_json(path, obj, indent=None):
    with open(path, "w") as f:
        json.dump(obj, f, indent=indent, separators=(",", ":") if indent is None else None)
        f.write("\n")


def db(x, floor=1e-12):
    return 20 * np.log10(np.maximum(np.abs(x), floor))
