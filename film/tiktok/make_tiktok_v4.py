"""15.8-second 9:16 teaser, v4: one continuous stretch of the owner's track (bars 8-17, the engine tour).

The song is not cut: the audio is the film master from bar 8 to bar 18, and the picture is the same
stretch of the film, placed in a 1080x608 band with large captions. The last bar carries the
Buy Choroboros button and the URL. Reuses the drawing helpers in make_tiktok15.py.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("TIKTOK_V3", "1")
import make_tiktok15 as tk  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "audio"))
from synth import meter  # noqa: E402
from synth.effects import limiter  # noqa: E402

GRID = os.environ.get("SONG_GRID", "/home/user/build/track/grid.json")
VIDEO = os.environ.get("TIKTOK_VIDEO", "/home/user/build/film/out/v4-preview.mp4")
MASTER = os.environ.get("TIKTOK_AUDIO", "/home/user/build/film/v3/master.wav")
OUT = os.environ.get("TIKTOK_OUT_FILE", os.path.join(tk.BUILD, "choroboros-tiktok-v4.mp4"))
ENGINES = ["green", "blue", "red", "purple", "black"]


def main():
    bars = json.load(open(GRID))["bars"]
    t0, t1 = bars[8], bars[18]
    B = (t1 - t0) / 10
    dur = t1 - t0
    L = lambda n: os.path.join(tk.BUILD, "layers", n)
    os.makedirs(os.path.join(tk.BUILD, "layers"), exist_ok=True)

    # audio: the master from bar 8 to bar 18, untouched except short edge fades and loudness to -14 LUFS
    x, sr = sf.read(MASTER, dtype="float64", always_2d=True)
    a = x[int(round(t0 * sr)):int(round(t1 * sr))].copy()
    fi, fo = int(0.02 * sr), int(0.35 * sr)
    a[:fi] *= np.linspace(0, 1, fi)[:, None]
    a[-fo:] *= np.cos(np.linspace(0, np.pi / 2, fo))[:, None] ** 2
    a = a * 10 ** ((-14.0 - meter.integrated_lufs(a, sr)) / 20)
    a, _ = limiter(a, ceiling_dbtp=-1.0, sr=sr)
    wav = os.path.join(tk.BUILD, "audio-v4.wav")
    sf.write(wav, a.astype(np.float32), sr, subtype="FLOAT")

    # layers
    bgs = {"neutral": tk.background(), **{k: tk.background(tk.HUES[k]) for k in tk.HUES}}
    for k, im in bgs.items():
        im.save(L(f"bg-{k}.png"))
    top = tk.cap_engines_top()
    from PIL import ImageDraw
    d = ImageDraw.Draw(top)
    tk.eyebrow(d, 250, "SOUND ON")
    top.save(L("v4-top.png"))
    overlays = [("v4-top.png", 0.0, dur)]
    bg_windows = []
    for k, e in enumerate(ENGINES):
        w0, w1 = 2 * k * B, 2 * (k + 1) * B
        if e == "black":
            w1 = 9 * B                      # the last bar is the call to action
        tk.cap_engine(e).save(L(f"eng-{e}.png"))
        overlays.append((f"eng-{e}.png", w0, w1))
        bg_windows.append((f"bg-{e}.png", 2 * k * B, 2 * (k + 1) * B))
    # call to action on the last bar: button + URL (same art as the main teaser's end)
    end = tk.cap_end()
    # keep only the lower part (button and URL): clear the top caption area of that layer
    import numpy as _np
    arr = _np.array(end)
    arr[:1200, :, 3] = 0
    from PIL import Image
    Image.fromarray(arr).save(L("v4-cta.png"))
    overlays.append(("v4-cta.png", 9 * B, dur))
    for i, f in enumerate(np.linspace(0, 1, 12)):
        tk.ring(None, f).save(L(f"ring-{i:02d}.png"))
        overlays.append((f"ring-{i:02d}.png", 9 * B + i * 0.06, 9 * B + (i + 1) * 0.06))

    ff = tk.ffmpeg()
    uniq = sorted(set([p for p, _, _ in bg_windows + overlays]))
    args = [ff, "-y", "-v", "error", "-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", VIDEO, "-i", wav]
    for png in uniq:
        args += ["-loop", "1", "-framerate", str(tk.FPS), "-t", f"{dur:.3f}", "-i", L(png)]
    idx = {png: i + 2 for i, png in enumerate(uniq)}
    fc = [f"[0:v]setpts=PTS-STARTPTS,fps={tk.FPS},scale={tk.BAND_W}:{tk.BAND_H}:flags=lanczos,setsar=1[band]"]
    cur = "base"
    fc.append(f"[{idx[bg_windows[0][0]]}:v]format=rgb24,setsar=1[{cur}]")
    for j, (png, w0, w1) in enumerate(bg_windows[1:]):
        nxt = f"b{j}"
        fc.append(f"[{cur}][{idx[png]}:v]overlay=0:0:enable='between(t,{w0:.4f},{w1 - 1e-4:.4f})'[{nxt}]")
        cur = nxt
    fc.append(f"[{cur}][band]overlay=0:{tk.BAND_Y}:shortest=1[v0]")
    cur = "v0"
    for j, (png, w0, w1) in enumerate(overlays):
        nxt = f"o{j}"
        fc.append(f"[{cur}][{idx[png]}:v]overlay=0:0:enable='between(t,{w0:.4f},{w1 - 1e-4:.4f})'[{nxt}]")
        cur = nxt
    fc.append(f"[{cur}]format=yuv420p[vout]")
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "1:a",
             "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", f"{dur:.3f}", "-movflags", "+faststart", OUT]
    subprocess.run(args, check=True)
    print(OUT, round(dur, 3))


if __name__ == "__main__":
    main()
