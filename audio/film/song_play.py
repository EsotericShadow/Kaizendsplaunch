"""Still Life v4: the owner's track plays straight through; the film is timed to it.

Film time equals song time from the first sample. Nothing is cut, looped or muted. The picture's 25
shots are placed on the song's bar lines through film/warp.json (film time -> composition time).
Choroboros processes the song in place, in stereo, only during the demos: the Mix turn in the intro
(Green), then one engine per two bars from bar 8 to bar 17, each with its knob move on the second bar.
Processed bars are level matched to the same bars of the original mix, and every change of engine or
return to the original mix is a 20 ms equal-power crossfade ending on the bar line. Everywhere else
the original mix plays as it is. The film ends with a fade in the song's quiet section after bar 53.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import song_edit as se  # noqa: E402  (shared helpers: grid, choro(), match_bars(), gesture_points())

OUT = os.environ.get("V4_OUT", "/home/user/build/film/v3")   # same paths the picture already mounts
SR, FPS, COMP_DUR = se.SR, se.FPS, se.COMP_DUR
bar, B, smp = se.bar, se.B, se.smp

END = bar(57) - 0.2          # fade out in the quiet section, before the song re-enters at bar 57
FADE = 2.4
EPS = 0.0005                 # the two black stops collapse to (almost) nothing: the music does not stop

ANCHORS = [
    (0.00, 0.0), (2.00, bar(1)), (3.00, bar(2)), (7.85, bar(4) - EPS), (8.00, bar(4)),
    (12.00, bar(6)), (16.00, bar(8)), (20.00, bar(10)), (24.00, bar(12)), (28.00, bar(14)),
    (32.00, bar(16)), (36.00, bar(18)), (40.00, bar(22)), (46.00, bar(26)),
    (49.85, bar(30) - EPS), (50.00, bar(30)), (54.00, bar(33)), (58.00, bar(36)), (62.00, bar(38)),
    (69.50, bar(43) - B / 4), (70.00, bar(43)), (74.00, bar(48)), (78.00, bar(53)), (86.00, END),
]
COMP = np.array([a for a, _ in ANCHORS])
FILM = np.array([b for _, b in ANCHORS])


def film_of_comp(c):
    return float(np.interp(c, COMP, FILM))


# engine blocks: (engine, hq, knobs, gesture, first bar). Green also covers the intro from the Mix turn.
BLOCKS = [
    ("green", 0, dict(rate=0.60, depth=20, offset=90, width=130, color=35, mix=45), ("depth", 20, 35), 8),
    ("blue", 0, dict(rate=0.80, depth=15, offset=0, width=140, color=45, mix=40), ("offset", 0, 90), 10),
    ("red", 0, dict(rate=0.55, depth=35, offset=90, width=120, color=30, mix=50), ("hq", 0, 1), 12),
    ("purple", 1, dict(rate=0.12, depth=60, offset=90, width=140, color=25, mix=35), ("rate", 0.12, 1.5), 14),
    ("black", 1, dict(rate=0.50, depth=30, offset=120, width=170, color=20, mix=55), ("color", 20, 60), 16),
]
PROC_END = bar(18)            # back to the original mix at bar 18 (inside the breakdown)
WARM = 2                      # bars of the song rendered before each block so delay lines and LFOs run


def xfade_join(dst, src, t, dur=0.020):
    """Replace dst from t on with src (same timeline), equal-power crossfade ending at t."""
    i1 = smp(t); i0 = i1 - smp(dur)
    u = np.linspace(0, np.pi / 2, i1 - i0)[:, None]
    dst[i0:i1] = dst[i0:i1] * np.cos(u) + src[i0:i1] * np.sin(u)
    dst[i1:] = src[i1:]


def main():
    os.makedirs(os.path.join(OUT, "r4"), exist_ok=True)
    song = se.load_song()
    n = smp(END)
    orig = song[:n].copy()
    log = {"version": "v4 play-through", "bar_s": B, "bpm": 240 / B, "anchors": ANCHORS, "end": END,
           "levelmatch": {}, "renders": {}}

    # Each processed region is rendered from the song with some warm-up, then placed back on the
    # song's own timeline. Timeline pieces: [0, turn) original; [turn, bar 10) Green; then one engine
    # per two bars; [bar 18, end) original.
    t_turn0, t_turn1 = film_of_comp(2.25), film_of_comp(2.75)
    pieces = []  # (t_start, t_end, stereo array on the film timeline slice)

    def render_span(name, eng, hq, knobs, auto, t0, t1, warm_from):
        """Render song[warm_from:t1] through the engine; automation times are relative to warm_from."""
        src = song[smp(warm_from):smp(t1)]
        p_in = os.path.join(OUT, "r4", f"{name}_in.wav")
        sf.write(p_in, src.astype(np.float32), SR, subtype="FLOAT")
        rel = {}
        for k, pts in (auto or {}).items():
            rel[k] = [[round(t - warm_from, 4), v] for t, v in pts]
        y = se.choro(p_in, os.path.join(OUT, "r4", f"{name}.wav"), eng, hq, knobs, rel or None, preroll=1.0, tail=0.5)
        y = y[:len(src)]
        full = np.zeros_like(orig)
        full[smp(warm_from):smp(warm_from) + len(y)] = y
        return full

    # Green: from the Mix turn through its tour block (bars 8-9), Mix 0 -> 45 at the turn, Depth 20 -> 35 at bar 9
    eng, hq, kn, (param, v0, v1), b0 = BLOCKS[0]
    g0, g1 = film_of_comp(18.0), film_of_comp(18.5)
    auto = {"mix": [[0.0, 0.0]] + se.gesture_points(t_turn0, t_turn1, 0, 45, "mix"),
            "depth": [[0.0, v0], [g0, v0]] + se.gesture_points(g0, g1, v0, v1, "depth")}
    kn0 = dict(kn); kn0["mix"] = 0
    green = render_span("green", eng, hq, kn0, auto, 0.0, bar(10), 0.0)
    log["renders"]["green"] = {"span": [t_turn0, bar(10)], "mix_turn": [t_turn0, t_turn1], "depth_gesture": [g0, g1]}

    procs = [("green", green, t_turn0, bar(10))]
    for k, (eng, hq, kn, (param, v0, v1), b0) in enumerate(BLOCKS[1:], start=1):
        t0, t1 = bar(b0), bar(b0 + 2)
        c0 = 16 + 4 * k
        g0, g1 = film_of_comp(c0 + 2.0), film_of_comp(c0 + 2.5)
        warm_from = bar(b0 - WARM)
        if param == "hq":
            auto = {"hq": [[warm_from, 0], [g0, 1]]}
        else:
            auto = {param: [[warm_from, v0], [g0, v0]] + se.gesture_points(g0, g1, v0, v1, param)}
        y = render_span(eng, eng, hq, kn, auto, t0, t1, warm_from)
        procs.append((eng, y, t0, t1))
        log["renders"][eng] = {"span": [t0, t1], "gesture": [param, v0, v1, round(g0, 3), round(g1, 3)], "knobs": kn, "hq": hq}

    # level match every processed bar to the same bar of the original mix
    mix = orig.copy()
    for name, y, t0, t1 in procs:
        edges = [t0] + [bar(i) for i in range(len(se.BARS)) if t0 < bar(i) < t1] + [t1]
        seg_y, lm = se.match_bars(y[smp(t0):smp(t1)], orig[smp(t0):smp(t1)], [e - t0 for e in edges])
        log["levelmatch"][name] = lm
        y = y.copy(); y[smp(t0):smp(t1)] = seg_y
        xfade_join(mix, y, t0)          # into this engine (from the original or the previous engine)
    xfade_join(mix, orig, PROC_END)     # back to the original mix at bar 18

    # fade out at the end, in the quiet section
    nf = smp(FADE)
    mix[-nf:] *= np.cos(np.linspace(0, np.pi / 2, nf))[:, None] ** 2

    y, lim = se.limiter(mix, ceiling_dbtp=-1.0, sr=SR)
    sf.write(os.path.join(OUT, "master.wav"), y.astype(np.float32), SR, subtype="PCM_24")
    diff_outside = float(np.max(np.abs(y[smp(bar(18)) + smp(0.03):smp(END - FADE)] - orig[smp(bar(18)) + smp(0.03):smp(END - FADE)])))
    log["master"] = {"lufs": round(se.lufs(y), 2), "true_peak_dbtp": round(float(se.meter.true_peak(y, SR)), 2),
                     "duration": round(len(y) / SR, 3), "limiter": lim,
                     "max_abs_diff_vs_original_outside_demos": diff_outside}

    # scope data indexed by composition frame
    frames = int(round(COMP_DUR * FPS))
    gain = 1.7915
    buf = np.zeros((frames, 400, 2), dtype=np.int16)
    for f in range(frames):
        i0 = smp(film_of_comp_inv(f / FPS))
        w = y[i0:i0 + 800]
        if len(w) < 800:
            w = np.vstack([w, np.zeros((800 - len(w), 2))])
        m = (w[:, 0] + w[:, 1]) / 2 * gain
        s = (w[:, 0] - w[:, 1]) / 2 * gain
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

    warp = {"note": "v4: the song plays straight through; film time is song time. The page seeks comp = interp(t, film, comp).",
            "film": [round(float(v), 6) for v in FILM], "comp": [round(float(v), 6) for v in COMP],
            "film_duration": round(END, 6), "bar_s": B, "version": "v4"}
    json.dump(warp, open(os.path.join(OUT, "warp.json"), "w"), indent=1)
    json.dump(warp, open(os.path.join(se.REPO, "film", "warp.json"), "w"), indent=1)
    json.dump(log, open(os.path.join(se.REPO, "audio", "logs", "v4-song-play.json"), "w"), indent=1, default=float)
    print(json.dumps(log["master"]), "levelmatch worst",
          max(abs(b["residual_lu"]) for v in log["levelmatch"].values() for b in v))


def film_of_comp_inv(c):
    """Composition time -> film time (for the scope index)."""
    return float(np.interp(c, COMP, FILM))


if __name__ == "__main__":
    main()
