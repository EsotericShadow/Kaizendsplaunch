"""15-second 9:16 teaser cut from the Still Life preview render and master audio.

Picture: segments of the 16:9 film preview placed in a 1080x608 band, with large captions above and below.
Audio: the same segments cut from the film master on beat boundaries, with short equal-power joins.
Outputs go to /home/user/build/tiktok (outside the repo). Fonts: Fraunces and Inter TTF (OFL) in FONT_DIR.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BUILD = os.environ.get("TIKTOK_OUT", "/home/user/build/tiktok")
FONT_DIR = os.path.join(BUILD, "fonts")
VIDEO = os.environ.get("TIKTOK_VIDEO", "/home/user/build/film/out/lead-review-full.mp4")
MASTER = os.environ.get("TIKTOK_AUDIO", "/home/user/build/film/audio/master.wav")
W, H = 1080, 1920
BAND_W, BAND_H = 1080, 608
BAND_Y = (H - BAND_H) // 2  # 656
FPS = 30

# (source in, source out, key) in film time; output time is cumulative.
V3 = os.environ.get("TIKTOK_V3", "1") == "1"
if V3:
    # cut to the owner's track: film/warp.json gives the bar length; every cut sits on a bar line
    _w = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "warp.json")))
    B = _w["bar_s"]
    P = 36 * B + 8.0
    SEGMENTS = [(0.5 * B, 3 * B, "open")]
    for k, eng in enumerate(["green", "blue", "red", "purple", "black"]):
        a = 8 * B + 2 * k * B + B          # the second bar of each engine block (its knob move)
        SEGMENTS.append((a, a + B, eng))
    SEGMENTS += [(28 * B, 29 * B, "free"), (P + 4 * B, P + 5 * B, "end")]
    TURN = 1.974 - 0.5 * B                # Mix turn starts this far into the opening segment
    VIDEO = os.environ.get("TIKTOK_VIDEO", "/home/user/build/film/out/v3-preview.mp4")
    MASTER = os.environ.get("TIKTOK_AUDIO", "/home/user/build/film/v3/master.wav")
else:
    SEGMENTS = [
        (1.0, 4.0, "open"),
        (18.0, 19.0, "green"),
        (22.0, 23.0, "blue"),
        (25.5, 26.5, "red"),
        (30.0, 31.0, "purple"),
        (34.0, 35.0, "black"),
        (50.0, 52.0, "free"),
        (58.0, 60.0, "price"),
        (77.0, 80.0, "end"),
    ]
    TURN = 1.25

INK = (246, 244, 239, 255)
ACCENT = (208, 189, 255, 255)
PURPLE = (184, 140, 255, 255)
MUTED = (168, 167, 160, 255)
HUES = {"green": (126, 224, 160), "blue": (121, 184, 255), "red": (255, 138, 128),
        "purple": (201, 177, 255), "black": (154, 160, 166)}


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ---------- audio ----------

def build_audio(path_out):
    x, sr = sf.read(MASTER, dtype="float64", always_2d=True)
    xf = int(0.012 * sr)
    out = None
    for a, b, _ in SEGMENTS:
        seg = x[int(round(a * sr)):int(round(b * sr)) + xf].copy()
        if out is None:
            fi = int(0.03 * sr)
            seg[:fi] *= np.linspace(0, 1, fi)[:, None]
            out = seg
            continue
        # equal-power join centred on the cut: previous tail overlaps the new head
        t = np.linspace(0, np.pi / 2, xf)[:, None]
        tail = out[-xf:] * np.cos(t)
        head = seg[:xf] * np.sin(t)
        out = np.concatenate([out[:-xf], tail + head, seg[xf:]])
    total = int(round(sum(b - a for a, b, _ in SEGMENTS) * sr))
    out = out[:total]
    fo = int(0.6 * sr)
    out[-fo:] *= np.cos(np.linspace(0, np.pi / 2, fo))[:, None] ** 2
    sf.write(path_out, out.astype(np.float32), sr, subtype="FLOAT")
    return total / sr


# ---------- images ----------

def text_w(draw, s, f):
    l, t, r, b = draw.textbbox((0, 0), s, font=f)
    return r - l


def centered_line(draw, y, parts, spacing=0):
    """parts: list of (text, font, fill). Draws them on one line centred at x = W/2, baseline y."""
    widths = [text_w(draw, s, f) for s, f, _ in parts]
    total = sum(widths) + spacing * (len(parts) - 1)
    x = (W - total) / 2
    for (s, f, fill), w in zip(parts, widths):
        draw.text((x, y), s, font=f, fill=fill, anchor="ls")
        x += w + spacing


def eyebrow(draw, y, s, fill=PURPLE, size=30, track=0.3):
    f = font("Inter-700.ttf", size)
    chars = list(s)
    widths = [text_w(draw, c, f) if c != " " else size * 0.35 for c in chars]
    gap = size * track
    total = sum(widths) + gap * (len(chars) - 1)
    x = (W - total) / 2
    for c, w in zip(chars, widths):
        if c != " ":
            draw.text((x, y), c, font=f, fill=fill, anchor="ls")
        x += w + gap


def background(hue=None):
    img = Image.new("RGB", (W, H), (5, 5, 6))
    glow = Image.new("L", (W, H), 0)
    g = ImageDraw.Draw(glow)
    cx, cy = W // 2, BAND_Y + BAND_H // 2
    for r in range(900, 0, -12):
        v = int(70 * (1 - r / 900) ** 2)
        g.ellipse((cx - r, cy - r * 0.9, cx + r, cy + r * 0.9), fill=v)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    col = hue or (184, 140, 255)
    tint = Image.new("RGB", (W, H), col)
    img = Image.composite(tint, img, glow.point(lambda v: int(v * 0.55)))
    # fine grain to keep the gradient from banding
    rng = np.random.default_rng(7)
    arr = np.asarray(img).astype(np.int16) + rng.integers(-2, 3, (H, W, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def cap_open_a():
    im = layer(); d = ImageDraw.Draw(im)
    eyebrow(d, 250, "SOUND ON")
    centered_line(d, 470, [("Bypassed." if V3 else "A dry guitar.", font("Fraunces-600.ttf", 112), INK)])
    return im


def cap_open_b():
    im = layer(); d = ImageDraw.Draw(im)
    eyebrow(d, 250, "SOUND ON")
    centered_line(d, 420, [("Now add", font("Fraunces-600.ttf", 112), INK)])
    centered_line(d, 545, [("Choroboros.", font("Fraunces-400i.ttf", 124), ACCENT)])
    return im


def cap_engines_top():
    im = layer(); d = ImageDraw.Draw(im)
    centered_line(d, 420, [("Five prebuilt", font("Fraunces-600.ttf", 112), INK)])
    centered_line(d, 545, [("engines.", font("Fraunces-400i.ttf", 124), ACCENT)])
    return im


def cap_engine(name):
    im = layer(); d = ImageDraw.Draw(im)
    hue = HUES[name] + (255,)
    label = name.upper() if name != "red" else "RED  ·  BBD / TAPE"
    eyebrow(d, 1385, label, fill=hue, size=52, track=0.22)
    eyebrow(d, 1460, "SAME TAKE  ·  LEVEL MATCHED", fill=(246, 244, 239, 150), size=26, track=0.25)
    return im


def cap_free():
    im = layer(); d = ImageDraw.Draw(im)
    centered_line(d, 420, [("Green and Purple", font("Fraunces-600.ttf", 104), INK)])
    centered_line(d, 545, [("are ", font("Fraunces-600.ttf", 104), INK), ("free.", font("Fraunces-400i.ttf", 116), ACCENT)])
    centered_line(d, 1400, [("No card or licence key needed.", font("Inter-500.ttf", 46), MUTED)])
    return im


def cap_price():
    im = layer(); d = ImageDraw.Draw(im)
    centered_line(d, 520, [("$49.99 ", font("Fraunces-600.ttf", 150), INK), ("USD.", font("Fraunces-400i.ttf", 160), ACCENT)])
    centered_line(d, 1390, [("One-time purchase.", font("Inter-500.ttf", 48), INK)])
    centered_line(d, 1460, [("Lifetime updates. 30-day refund.", font("Inter-500.ttf", 44), MUTED)])
    return im


def cap_end():
    im = layer(); d = ImageDraw.Draw(im)
    centered_line(d, 420, [("Great sound", font("Fraunces-600.ttf", 108), INK)])
    centered_line(d, 545, [("doesn’t sit still.", font("Fraunces-400i.ttf", 118), ACCENT)])
    # primary site button: cream fill, dark label, arrow
    bw, bh = 700, 124
    bx, by = (W - bw) // 2, 1300
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=16, fill=(245, 242, 234, 255))
    f = font("Inter-700.ttf", 54)
    label = "Buy Choroboros"
    lw = text_w(d, label, f)
    ax = 46  # arrow width + gap
    x0 = bx + (bw - (lw + ax + 20)) / 2
    d.text((x0, by + bh / 2), label, font=f, fill=(23, 24, 23, 255), anchor="lm")
    axs = x0 + lw + 26
    ay = by + bh / 2
    d.line((axs, ay, axs + ax - 6, ay), fill=(23, 24, 23, 255), width=6)
    d.line((axs + ax - 22, ay - 16, axs + ax - 4, ay), fill=(23, 24, 23, 255), width=6)
    d.line((axs + ax - 22, ay + 16, axs + ax - 4, ay), fill=(23, 24, 23, 255), width=6)
    centered_line(d, 1500, [("kaizendsp.com/choroboros", font("Inter-600.ttf", 46), PURPLE)])
    return im


def ring(im_base, t_frac):
    """1 px lavender ring pulse around the button (drawn as a separate layer)."""
    im = layer(); d = ImageDraw.Draw(im)
    bw, bh = 700, 124
    bx, by = (W - bw) // 2, 1300
    pad = int(6 + 18 * t_frac)
    a = int(255 * (1 - t_frac))
    d.rounded_rectangle((bx - pad, by - pad, bx + bw + pad, by + bh + pad), radius=16 + pad, outline=(208, 189, 255, a), width=3)
    return im


def main():
    os.makedirs(os.path.join(BUILD, "layers"), exist_ok=True)
    L = lambda n: os.path.join(BUILD, "layers", n)
    dur = build_audio(os.path.join(BUILD, "audio.wav"))

    # output-time windows
    windows, t = [], 0.0
    for a, b, k in SEGMENTS:
        windows.append((t, t + (b - a), a, b, k))
        t += b - a

    bgs = {"neutral": background(), **{k: background(HUES[k]) for k in HUES}}
    for k, im in bgs.items():
        im.save(L(f"bg-{k}.png"))

    overlays = []  # (png, t0, t1)
    w = {k: (t0, t1) for t0, t1, _, _, k in windows}
    o0, o1 = w["open"]
    cap_open_a().save(L("open-a.png")); overlays.append(("open-a.png", o0, o0 + TURN))
    cap_open_b().save(L("open-b.png")); overlays.append(("open-b.png", o0 + TURN, o1))
    cap_engines_top().save(L("engines.png")); overlays.append(("engines.png", w["green"][0], w["black"][1]))
    for k in ["green", "blue", "red", "purple", "black"]:
        cap_engine(k).save(L(f"eng-{k}.png")); overlays.append((f"eng-{k}.png", *w[k]))
    cap_free().save(L("free.png")); overlays.append(("free.png", *w["free"]))
    if "price" in w:
        cap_price().save(L("price.png")); overlays.append(("price.png", *w["price"]))
    cap_end().save(L("end.png")); overlays.append(("end.png", *w["end"]))
    # ring pulse on the button when the final chord lands (film 78.00 = 1.0 s into the end segment)
    e0 = w["end"][0] + (0.0 if V3 else 1.0)
    for i, f in enumerate(np.linspace(0, 1, 12)):
        ring(None, f).save(L(f"ring-{i:02d}.png"))
        overlays.append((f"ring-{i:02d}.png", e0 + i * 0.06, e0 + (i + 1) * 0.06))

    bg_windows = [("bg-neutral.png", 0, w["green"][0])]
    for k in ["green", "blue", "red", "purple", "black"]:
        bg_windows.append((f"bg-{k}.png", *w[k]))
    bg_windows.append(("bg-neutral.png", w["black"][1], dur))

    # ffmpeg graph
    ff = ffmpeg()
    args = [ff, "-y", "-v", "error", "-i", VIDEO, "-i", os.path.join(BUILD, "audio.wav")]
    inputs = []
    for png, _, _ in bg_windows + overlays:
        inputs.append(png)
    uniq = sorted(set(inputs))
    for png in uniq:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", L(png)]
    idx = {png: i + 2 for i, png in enumerate(uniq)}

    fc = []
    segs = []
    for i, (t0, t1, a, b, k) in enumerate(windows):
        fc.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS,fps={FPS},"
                  f"scale={BAND_W}:{BAND_H}:flags=lanczos,setsar=1[s{i}]")
        segs.append(f"[s{i}]")
    fc.append("".join(segs) + f"concat=n={len(segs)}:v=1:a=0[band]")
    # start from the first background, then switch backgrounds by time
    cur = "base0"
    fc.append(f"[{idx['bg-neutral.png']}:v]format=rgb24,setsar=1[{cur}]")
    n = 0
    for png, t0, t1 in bg_windows[1:]:
        nxt = f"b{n}"; n += 1
        fc.append(f"[{cur}][{idx[png]}:v]overlay=0:0:enable='between(t,{t0:.4f},{t1 - 1e-4:.4f})'[{nxt}]")
        cur = nxt
    fc.append(f"[{cur}][band]overlay=0:{BAND_Y}:shortest=1[v0]")
    cur = "v0"
    for j, (png, t0, t1) in enumerate(overlays):
        nxt = f"o{j}"
        fc.append(f"[{cur}][{idx[png]}:v]overlay=0:0:enable='between(t,{t0:.4f},{t1 - 1e-4:.4f})'[{nxt}]")
        cur = nxt
    fc.append(f"[{cur}]format=yuv420p[vout]")
    out = os.path.join(BUILD, "choroboros-tiktok-15s-v3.mp4" if V3 else "choroboros-tiktok-15s.mp4")
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "1:a",
             "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17",
             "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", f"{dur:.3f}", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    json.dump({"windows": windows, "overlays": overlays, "duration": dur}, open(os.path.join(BUILD, "timeline.json"), "w"), indent=1)
    print(out, dur)


if __name__ == "__main__":
    sys.exit(main())
