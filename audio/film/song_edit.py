"""Still Life v3: re-cut the film to the owner's track.

The owner's mixed track replaces the synthesized score. The picture keeps its 25 shots; a piecewise-linear
time map (film time -> composition time) moves every cut onto the song's bar lines. Engine demos use the
track summed to mono and run through the real Choroboros processor (choro-render), level matched per bar
against the same mono source. Everywhere else the owner's stereo mix plays as it is.

Writes (outside the repo): /home/user/build/film/v3/  master.wav, demo renders, scope data (indexed by
composition frame), and warp.json; the warp is also copied to film/warp.json for the composition.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "audio"))
from synth import meter  # noqa: E402
from synth.effects import limiter  # noqa: E402

CHORO = os.environ.get("CHORO_RENDER", "/home/user/build/choro-render/build/choro-render")
SONG = os.environ.get("SONG_WAV", "/home/user/build/track/superfuck.wav")
GRID = os.environ.get("SONG_GRID", "/home/user/build/track/grid.json")
OUT = os.environ.get("V3_OUT", "/home/user/build/film/v3")
KAIZEN_PUBLIC = "/home/user/kaizendsp/public"
SR = 48000
FPS = 60
COMP_DUR = 86.0
BLOCK = 128

grid = json.load(open(GRID))
BARS = np.array(grid["bars"])
B = float(np.median(np.diff(BARS[:100])))  # one bar in seconds


def bar(i):
    return float(BARS[i])


# ---------- film structure (film seconds) ----------
P = 36 * B + 8.0          # payoff start, after the family section (7.5 s) and 0.5 s of silence
END = P + 9 * B
STOP = 0.15

# composition time -> film time anchors (the renderer seeks comp = W(film))
ANCHORS = [
    (0.00, 0.0), (2.00, 1 * B), (3.00, 2 * B), (7.85, 4 * B - STOP), (8.00, 4 * B),
    (12.00, 6 * B), (16.00, 8 * B), (20.00, 10 * B), (24.00, 12 * B), (28.00, 14 * B),
    (32.00, 16 * B), (36.00, 18 * B), (40.00, 21 * B), (46.00, 24 * B),
    (49.85, 28 * B - STOP), (50.00, 28 * B), (54.00, 31 * B), (58.00, 34 * B), (62.00, 36 * B),
    (69.50, 36 * B + 7.5), (70.00, P), (74.00, P + 2 * B), (78.00, P + 4 * B), (86.00, END),
]
COMP = np.array([a for a, _ in ANCHORS])
FILM = np.array([b for _, b in ANCHORS])


def film_of_comp(c):
    return np.interp(c, COMP, FILM)


def comp_of_film(f):
    return np.interp(f, FILM, COMP)


# ---------- helpers ----------

def load_song():
    x, sr = sf.read(SONG, dtype="float64", always_2d=True)
    assert sr == SR, sr
    return x


def smp(t):
    return int(round(t * SR))


def seg(x, t0, t1):
    return x[smp(t0):smp(t1)].copy()


def mono(x):
    m = x.mean(axis=1)
    return np.stack([m, m], axis=1)


def place(dst, src, t):
    i = smp(t)
    n = min(len(src), len(dst) - i)
    dst[i:i + n] += src[:n]


def fade(x, fi=0.0, fo=0.0):
    x = x.copy()
    if fi > 0:
        n = smp(fi); x[:n] *= np.sin(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    if fo > 0:
        n = smp(fo); x[-n:] *= np.cos(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    return x


def sine_inout(u):
    return -(np.cos(np.pi * np.clip(u, 0, 1)) - 1) / 2


def rate_to_p(hz):
    return ((hz - 0.005) / 19.995) ** (1 / 4.35)


def p_to_rate(p):
    return 0.005 + 19.995 * p ** 4.35


def gesture_points(t0, t1, v0, v1, param, n=None):
    """Sample the eased knob position every 10 ms and convert to display units."""
    ts = np.arange(t0, t1 + 1e-9, 0.01)
    u = sine_inout((ts - t0) / (t1 - t0))
    if param == "rate":
        p = rate_to_p(v0) + (rate_to_p(v1) - rate_to_p(v0)) * u
        vals = p_to_rate(p)
    else:
        vals = v0 + (v1 - v0) * u
    return [[round(float(t), 4), round(float(v), 4)] for t, v in zip(ts, vals)]


def choro(in_wav, out_wav, engine, hq, knobs, automation=None, preroll=2.0, tail=1.0):
    args = [CHORO, "--in", in_wav, "--out", out_wav, "--engine", engine, "--hq", str(hq),
            "--rate", f"{knobs['rate']}", "--depth", f"{knobs['depth']}%", "--offset", f"{knobs['offset']}",
            "--width", f"{knobs['width']}%", "--color", f"{knobs['color']}%", "--mix", f"{knobs['mix']}%",
            "--block", str(BLOCK), "--preroll", f"{preroll}", "--tail", f"{tail}", "--quiet",
            "--meta", out_wav.replace(".wav", ".json")]
    if automation:
        ap = out_wav.replace(".wav", ".automation.json")
        json.dump(automation, open(ap, "w"))
        args += ["--automation", ap]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    y, sr = sf.read(out_wav, dtype="float64", always_2d=True)
    return y


def lufs(x):
    return meter.integrated_lufs(x, SR)


def match_bars(proc, ref, t_bars):
    """Constant gain per bar (20 ms ramps) so each bar of proc matches ref loudness. Returns (y, log)."""
    g = np.ones(len(proc))
    log = []
    edges = list(t_bars)
    gains = []
    for a, b in zip(edges[:-1], edges[1:]):
        lp, lr = lufs(proc[smp(a):smp(b)]), lufs(ref[smp(a):smp(b)])
        gains.append((a, b, 10 ** ((lr - lp) / 20), lr, lp))
    for i, (a, b, gg, lr, lp) in enumerate(gains):
        g[smp(a):smp(b)] = gg
    # smooth steps with 20 ms ramps
    k = smp(0.02)
    ker = np.ones(k) / k
    g = np.convolve(g, ker, mode="same")
    y = proc * g[:, None]
    for a, b, gg, lr, lp in gains:
        la = lufs(y[smp(a) + k:smp(b) - k])
        log.append({"t0": round(a, 3), "t1": round(b, 3), "ref_lufs": round(lr, 2), "proc_lufs": round(lp, 2),
                    "gain_db": round(20 * np.log10(gg), 2), "after_lufs": round(la, 2),
                    "residual_lu": round(la - lufs(ref[smp(a) + k:smp(b) - k]), 3)})
    return y, log


TOUR = [  # engine, hq, knobs, gesture (param, from, to) at the second bar
    ("green", 0, dict(rate=0.60, depth=20, offset=90, width=130, color=35, mix=45), ("depth", 20, 35)),
    ("blue", 0, dict(rate=0.80, depth=15, offset=0, width=140, color=45, mix=40), ("offset", 0, 90)),
    ("red", 0, dict(rate=0.55, depth=35, offset=90, width=120, color=30, mix=50), ("hq", 0, 1)),
    ("purple", 1, dict(rate=0.12, depth=60, offset=90, width=140, color=25, mix=35), ("rate", 0.12, 1.5)),
    ("black", 1, dict(rate=0.50, depth=30, offset=120, width=170, color=20, mix=55), ("color", 20, 60)),
]
GREEN_A = dict(rate=0.60, depth=20, offset=90, width=130, color=35, mix=45)


def main():
    os.makedirs(os.path.join(OUT, "r"), exist_ok=True)
    song = load_song()
    n = smp(END)
    mix = np.zeros((n, 2))
    feat = np.zeros((n, 2))       # what the scope shows: the audio being demonstrated (full mix elsewhere)
    log = {"bar_s": B, "bpm": 240 / B, "anchors": ANCHORS, "end": END, "levelmatch": {}, "renders": {}}

    # A. opening: 4 bars of the intro, summed to mono, Choroboros Green (a) with the Mix turn
    a_src = mono(seg(song, bar(0), bar(4)))
    sf.write(os.path.join(OUT, "r", "A_in.wav"), a_src.astype(np.float32), SR, subtype="FLOAT")
    t_turn0, t_turn1 = film_of_comp(2.25), film_of_comp(2.75)
    auto = {"mix": gesture_points(t_turn0, t_turn1, 0, 45, "mix")}
    auto["mix"] = [[0.0, 0.0]] + auto["mix"]
    kn = dict(GREEN_A); kn["mix"] = 0
    a_out = choro(os.path.join(OUT, "r", "A_in.wav"), os.path.join(OUT, "r", "A_green.wav"), "green", 0, kn, auto)
    a_out = a_out[:len(a_src)]
    a_out, lm = match_bars(a_out, a_src, [0, 1 * B, 2 * B, 3 * B, 4 * B - STOP])
    log["levelmatch"]["opening"] = lm
    a_out[smp(4 * B - STOP):] = 0
    a_out = fade(a_out, fi=0.02)
    a_out[smp(4 * B - STOP) - smp(0.003):smp(4 * B - STOP)] *= np.linspace(1, 0, smp(0.003))[:, None]
    place(mix, a_out, 0.0); place(feat, a_out, 0.0)

    # B. title and lineup: the song, bars 8-11, as mixed
    b_src = seg(song, bar(8), bar(12))
    place(mix, fade(b_src, fo=0.012), 4 * B); place(feat, b_src, 4 * B)

    # C. engine tour: the same two breakdown bars (16-17), mono, through each engine
    c_src = mono(seg(song, bar(16), bar(18)))
    sf.write(os.path.join(OUT, "r", "C_in.wav"), c_src.astype(np.float32), SR, subtype="FLOAT")
    for k, (eng, hq, kn, (param, v0, v1)) in enumerate(TOUR):
        t_blk = 8 * B + 2 * k * B
        g0 = film_of_comp(16 + 4 * k + 2.0) - t_blk          # second-bar downbeat, block-relative
        g1 = film_of_comp(16 + 4 * k + 2.5) - t_blk
        if param == "hq":
            auto = {"hq": [[0.0, 0], [round(g0, 4), 1]]}
        else:
            auto = {param: [[0.0, v0]] + gesture_points(g0, g1, v0, v1, param)}
        out = choro(os.path.join(OUT, "r", "C_in.wav"), os.path.join(OUT, "r", f"C_{eng}.wav"), eng, hq, kn, auto)
        out = out[:len(c_src)]
        out, lm = match_bars(out, c_src, [0, B, 2 * B])
        log["levelmatch"][f"tour_{eng}"] = lm
        out = fade(out, fi=0.008, fo=0.008)
        place(mix, out, t_blk); place(feat, out, t_blk)
        log["renders"][eng] = {"hq": hq, "knobs": kn, "gesture": [param, v0, v1, round(g0, 3), round(g1, 3)]}

    # D. cores and Create: the breakdown from its start (bars 14-19), as mixed
    d_src = seg(song, bar(14), bar(20))
    place(mix, fade(d_src, fi=0.01, fo=0.012), 18 * B); place(feat, d_src, 18 * B)

    # E. looks and build: bars 26-29, as mixed, hard stop 0.15 s before the drop
    e_src = seg(song, bar(26), bar(30))
    e_src[smp(4 * B - STOP):] = 0
    e_src[smp(4 * B - STOP) - smp(0.003):smp(4 * B - STOP)] *= np.linspace(1, 0, smp(0.003))[:, None]
    place(mix, fade(e_src, fi=0.01), 24 * B); place(feat, e_src, 24 * B)

    # F. drop, free, trial, price: bars 30-37 as mixed
    f_src = seg(song, bar(30), bar(38))
    place(mix, fade(f_src, fo=0.03), 28 * B); place(feat, f_src, 28 * B)

    # G. more from Kaizen DSP: each product's own clip, song muted
    g0 = 36 * B
    FF = subprocess.run([sys.executable, "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
                        capture_output=True, text=True).stdout.strip()

    def clip(src, t_in, t_out):
        p = os.path.join(OUT, "r", os.path.basename(src) + f".{t_in}.wav")
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t_in}", "-to", f"{t_out}", "-i", src, "-ac", "2",
                        "-ar", str(SR), "-c:a", "pcm_f32le", p], check=True)
        y, _ = sf.read(p, dtype="float64", always_2d=True)
        y = fade(y, fi=0.04, fo=0.04)
        target = -15.0
        return y * 10 ** ((target - lufs(y)) / 20)

    cues = json.load(open(os.path.join(REPO, "film", "cues.json")))
    sec = {s["name"]: s for s in cues["sections"]}
    for name, src, at in [("fold", f"{KAIZEN_PUBLIC}/fold/fold-motion-sound.mp4", 62.25),
                          ("echolalia", f"{KAIZEN_PUBLIC}/film/echolalia/time-sound-preview.mp4", 64.75),
                          ("stovetop", f"{KAIZEN_PUBLIC}/stovetop/slow-drip-after.wav", 67.0)]:
        s = sec[name]
        ci = s.get("clip_in", {"fold": 1.0, "echolalia": 9.5, "stovetop": 3.005}[name])
        co = s.get("clip_out", {"fold": 3.25, "echolalia": 11.75, "stovetop": 5.505}[name])
        y = clip(src, ci, co)
        place(mix, y, film_of_comp(at)); place(feat, y, film_of_comp(at))

    # H. payoff: the same intro bars 0-1, mono, now through Choroboros from the downbeat; then bars 95-96
    h_src = mono(seg(song, bar(0), bar(2)))
    sf.write(os.path.join(OUT, "r", "H_in.wav"), h_src.astype(np.float32), SR, subtype="FLOAT")
    h_out = choro(os.path.join(OUT, "r", "H_in.wav"), os.path.join(OUT, "r", "H_green.wav"), "green", 0, GREEN_A)
    h_out = h_out[:len(h_src)]
    h_out, lm = match_bars(h_out, h_src, [0, B, 2 * B])
    log["levelmatch"]["payoff"] = lm
    place(mix, fade(h_out, fi=0.01, fo=0.012), P); place(feat, h_out, P)
    h2 = seg(song, bar(95), bar(97))
    place(mix, fade(h2, fi=0.012, fo=0.012), P + 2 * B); place(feat, h2, P + 2 * B)

    # I. end card: the outro from bar 97 (the landing under the Buy button), 5 bars, fade out
    i_src = seg(song, bar(97), bar(102))
    i_src = fade(i_src, fi=0.012, fo=1.6)
    place(mix, i_src, P + 4 * B); place(feat, i_src, P + 4 * B)

    # master: gentle gain so the loudest passages sit under a -1 dBTP true-peak limiter
    raw_lufs = lufs(mix)
    y, lim_info = limiter(mix, ceiling_dbtp=-1.0, sr=SR)
    master_path = os.path.join(OUT, "master.wav")
    sf.write(master_path, y.astype(np.float32), SR, subtype="PCM_24")
    log["master"] = {"lufs_before_limiter": round(raw_lufs, 2), "lufs": round(lufs(y), 2),
                     "true_peak_dbtp": round(float(meter.true_peak(y, SR)), 2), "duration": round(len(y) / SR, 3), "limiter": lim_info}

    # scope data indexed by COMPOSITION frame (the scope reads comp time): 400 (mid, side) points per frame
    frames = int(round(COMP_DUR * FPS))
    gain = 1.7915
    featp = feat.copy()
    lim_g = 1.0
    buf = np.zeros((frames, 400, 2), dtype=np.int16)
    for f in range(frames):
        tf = film_of_comp(f / FPS)
        i0 = smp(tf)
        w = featp[i0:i0 + 800] if i0 + 800 <= len(featp) else np.zeros((800, 2))
        if len(w) < 800:
            w = np.vstack([w, np.zeros((800 - len(w), 2))])
        m = (w[:, 0] + w[:, 1]) / 2 * gain * lim_g
        s = (w[:, 0] - w[:, 1]) / 2 * gain * lim_g
        buf[f, :, 0] = (np.clip(m[::2], -1, 1) * 32767).astype(np.int16)
        buf[f, :, 1] = (np.clip(s[::2], -1, 1) * 32767).astype(np.int16)
    sdir = os.path.join(OUT, "scope")
    os.makedirs(sdir, exist_ok=True)
    for stem in ["gtr", "pad", "ep", "lead", "pluck", "mix"]:
        buf.tofile(os.path.join(sdir, f"{stem}.i16"))
    json.dump({"fps": FPS, "points_per_frame": 400, "frames": frames, "gain": gain, "layout": "mid,side int16",
               "indexed_by": "composition frame (film time mapped through warp.json)",
               "stems": {s: {"file": f"{s}.i16"} for s in ["gtr", "pad", "ep", "lead", "pluck", "mix"]}},
              open(os.path.join(sdir, "index.json"), "w"), indent=1)

    warp = {"note": "Film time -> composition time. The renderer asks for film time t; the page seeks comp = interp(t, film, comp).",
            "film": [round(float(v), 6) for v in FILM], "comp": [round(float(v), 6) for v in COMP],
            "film_duration": round(END, 6), "bar_s": B}
    json.dump(warp, open(os.path.join(OUT, "warp.json"), "w"), indent=1)
    json.dump(warp, open(os.path.join(REPO, "film", "warp.json"), "w"), indent=1)
    os.makedirs(os.path.join(REPO, "audio", "logs"), exist_ok=True)
    json.dump(log, open(os.path.join(REPO, "audio", "logs", "v3-song-edit.json"), "w"), indent=1, default=float)
    print(json.dumps(log["master"]), "levelmatch worst residual",
          max(abs(b["residual_lu"]) for v in log["levelmatch"].values() for b in v))


if __name__ == "__main__":
    main()
