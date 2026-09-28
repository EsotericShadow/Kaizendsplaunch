"""Spectrogram and waveform PNGs drawn with Pillow only (no matplotlib)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import signal

from .core import SR, ensure_stereo

# magma-like colour ramp
_RAMP = np.array([
    (0, 0, 4), (28, 16, 68), (79, 18, 123), (129, 37, 129), (181, 54, 122),
    (229, 80, 100), (251, 135, 97), (254, 194, 135), (252, 253, 191)], dtype=float)


def _colormap(v):
    v = np.clip(v, 0, 1) * (len(_RAMP) - 1)
    i = np.minimum(v.astype(int), len(_RAMP) - 2)
    f = (v - i)[..., None]
    return (_RAMP[i] * (1 - f) + _RAMP[i + 1] * f).astype(np.uint8)


def _font(size=12):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def spectrogram_png(x, path, sr=SR, *, title="", width=1400, height=460, fmin=30.0,
                    fmax=20000.0, db_range=90.0, n_fft=4096, markers=None):
    """Log-frequency spectrogram of the mid signal, plus a strip below showing the
    mid (grey) and side (orange) peak envelopes. markers: list of (time_s, label)."""
    st = ensure_stereo(np.asarray(x, dtype=np.float64))
    mid = 0.5 * (st[:, 0] + st[:, 1])
    side = 0.5 * (st[:, 0] - st[:, 1])
    dur = len(mid) / sr
    left, right, top, strip = 64, 16, 34 if title else 12, 110
    plot_w = width - left - right
    hop = max(64, int(len(mid) / plot_w))
    f, t, Z = signal.stft(mid, sr, nperseg=n_fft, noverlap=max(0, n_fft - hop), boundary="even")
    mag = 20 * np.log10(np.abs(Z) * 2 / (np.hanning(n_fft).sum() / n_fft) / n_fft + 1e-12)
    ref = mag.max()
    rows = height
    fmax = min(fmax, sr / 2)
    freqs = np.geomspace(fmin, fmax, rows)[::-1]
    # interpolate each column onto the log axis
    img = np.empty((rows, mag.shape[1]))
    for c in range(mag.shape[1]):
        img[:, c] = np.interp(freqs, f, mag[:, c])
    v = (img - (ref - db_range)) / db_range
    rgb = _colormap(v)
    spec = Image.fromarray(rgb, "RGB").resize((plot_w, height), Image.BILINEAR)

    H = top + height + strip + 26
    canvas = Image.new("RGB", (width, H), (14, 14, 18))
    canvas.paste(spec, (left, top))
    d = ImageDraw.Draw(canvas)
    font, small = _font(13), _font(11)
    if title:
        d.text((left, 8), title, fill=(235, 235, 240), font=font)
    # frequency axis
    for fl, lab in ((50, "50"), (100, "100"), (200, "200"), (500, "500"), (1000, "1k"),
                    (2000, "2k"), (5000, "5k"), (10000, "10k"), (20000, "20k")):
        if fl < fmin or fl > fmax:
            continue
        y = top + int((1 - math.log(fl / fmin) / math.log(fmax / fmin)) * (height - 1))
        d.line([(left - 5, y), (left, y)], fill=(200, 200, 200))
        d.line([(left, y), (left + plot_w, y)], fill=(60, 60, 70))
        d.text((6, y - 7), lab + " Hz" if fl < 1000 else lab, fill=(200, 200, 200), font=small)
    # time axis
    step = _nice_step(dur)
    tt = 0.0
    while tt <= dur + 1e-9:
        xpx = left + int(tt / dur * (plot_w - 1))
        d.line([(xpx, top + height), (xpx, top + height + strip + 4)], fill=(80, 80, 90))
        d.text((xpx - 8, top + height + strip + 8), f"{tt:g}s", fill=(200, 200, 200), font=small)
        tt += step
    # envelope strip
    y0 = top + height + 4
    hh = strip - 8
    n = len(mid)
    edges = np.linspace(0, n, plot_w + 1).astype(int)
    for kind, sig_, col in (("mid", mid, (170, 170, 180)), ("side", side, (255, 140, 60))):
        for i in range(plot_w):
            seg = sig_[edges[i]:max(edges[i + 1], edges[i] + 1)]
            pk = float(np.abs(seg).max()) if len(seg) else 0.0
            h = int(min(1.0, pk) * hh / 2)
            cx = left + i
            cy = y0 + hh // 2
            d.line([(cx, cy - h), (cx, cy + h)], fill=col)
    d.text((6, y0 + 4), "mid", fill=(170, 170, 180), font=small)
    d.text((6, y0 + 20), "side", fill=(255, 140, 60), font=small)
    for tm, label in (markers or []):
        xpx = left + int(tm / dur * (plot_w - 1))
        d.line([(xpx, top), (xpx, top + height)], fill=(120, 220, 255))
        d.text((xpx + 3, top + 3), label, fill=(120, 220, 255), font=small)
    canvas.save(path)
    return path


def _nice_step(dur):
    for s in (0.1, 0.25, 0.5, 1, 2, 4, 5, 10, 15, 30, 60):
        if dur / s <= 16:
            return s
    return 120


def bar_chart_png(values: dict, path, *, title="", width=700, height=300, lo=-40.0, hi=0.0):
    """Simple bar chart, e.g. octave-band levels."""
    canvas = Image.new("RGB", (width, height), (14, 14, 18))
    d = ImageDraw.Draw(canvas)
    font = _font(12)
    d.text((10, 6), title, fill=(235, 235, 240), font=font)
    keys = list(values)
    n = len(keys)
    x0, y0, x1, y1 = 50, 30, width - 10, height - 30
    for db in np.arange(lo, hi + 1e-9, 10):
        y = y1 - (db - lo) / (hi - lo) * (y1 - y0)
        d.line([(x0, y), (x1, y)], fill=(50, 50, 60))
        d.text((8, y - 7), f"{db:.0f}", fill=(180, 180, 190), font=font)
    bw = (x1 - x0) / n
    for i, k in enumerate(keys):
        v = float(np.clip(values[k], lo, hi))
        y = y1 - (v - lo) / (hi - lo) * (y1 - y0)
        d.rectangle([x0 + i * bw + 4, y, x0 + (i + 1) * bw - 4, y1], fill=(120, 200, 140))
        d.text((x0 + i * bw + 4, y1 + 6), str(k), fill=(200, 200, 200), font=font)
    canvas.save(path)
    return path
