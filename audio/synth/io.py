"""WAV input/output and ffmpeg helpers."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from .core import SR


def ffmpeg_exe() -> str:
    exe = os.environ.get("FFMPEG")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def write_wav(path, x, sr=SR, subtype="FLOAT"):
    """Write float32 WAV (default). Mono stays mono, (n, 2) is stereo."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    if not np.all(np.isfinite(x)):
        raise ValueError(f"non-finite samples in {path}")
    sf.write(path, x.astype(np.float32), sr, subtype=subtype)
    return path


def read_wav(path):
    """Returns (float64 array, sr). Mono files come back 1-D."""
    x, sr = sf.read(path, dtype="float64", always_2d=False)
    return x, sr


def decode(path, sr=None, channels=None):
    """Decode any audio/video file's first audio stream with ffmpeg to float64.
    Keeps the native rate unless sr is given. Returns (array (n, ch), sr)."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "a.wav")
        cmd = [ffmpeg_exe(), "-v", "error", "-y", "-i", path, "-vn", "-map", "0:a:0", "-c:a", "pcm_f32le"]
        if sr:
            cmd += ["-ar", str(sr)]
        if channels:
            cmd += ["-ac", str(channels)]
        subprocess.run(cmd + [out], check=True)
        x, rate = sf.read(out, dtype="float64", always_2d=True)
    return x, rate


def has_audio(path) -> bool:
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", path], capture_output=True, text=True)
    return "Audio:" in r.stderr


def ffmpeg_loudness(path):
    """Cross-check with ffmpeg: ebur128 (true peak) and loudnorm JSON."""
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", path, "-vn",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    get = lambda pat: float(re.search(pat, s, re.S).group(1)) if re.search(pat, s, re.S) else None
    res = {"ebur128_I": get(r"I:\s+(-?[\d.]+) LUFS"), "ebur128_LRA": get(r"LRA:\s+(-?[\d.]+) LU"),
           "ebur128_TP": get(r"True peak:.*?Peak:\s+(-?[\d.]+) dBFS")}
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", path, "-vn",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if m:
        j = json.loads(m.group(0))
        res.update(loudnorm_I=float(j["input_i"]), loudnorm_TP=float(j["input_tp"]),
                   loudnorm_LRA=float(j["input_lra"]))
    return res


def encode_preview(wav_path, out_path, bitrate="256k"):
    """AAC preview (for listening on a phone or dropping into an edit)."""
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", wav_path, "-c:a", "aac", "-b:a", bitrate,
                    out_path], check=True)
    return out_path
