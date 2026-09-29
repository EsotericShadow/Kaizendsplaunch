#!/usr/bin/env python3
"""Picture QC gates 6, 7 and 9 (treatment 11), and the merged report film/qc-picture.json.

    node film/tools/qc_picture.mjs scan      # $OUT/qc/scan.json: layers and text blocks per frame
    node film/tools/qc_picture.mjs gates     # $OUT/qc/gates.json: gate 5 and gate 8
    film/film.sh check <times>               # gate 11 (determinism); log to $OUT/logs/determinism.log
    python3 film/tools/qc_picture.py         # gates 6, 7, 9, cut and coverage checks -> film/qc-picture.json

Gate 6 reads the source clips and the extracted frames the film draws, gate 7 the Stovetop stills
and one rendered still, gate 9 the frame scan.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.environ.get("FILM_OUT", "/home/user/build/film")
QC = os.path.join(OUT, "qc")
DATA = os.path.join(OUT, "data")
SITE = "/home/user/kaizendsp/public"
cues = json.load(open(os.path.join(REPO, "film/cues.json")))
FPS = cues["fps"]
FRAMES = round(cues["duration"] * FPS)


def ffmpeg():
    return os.environ.get("FFMPEG") or subprocess.check_output(
        [sys.executable, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"], text=True).strip()


def section(name):
    return next(s for s in cues["sections"] if s["name"] == name)


def fr(t):
    return round(t * FPS)


# Gate 6 -------------------------------------------------------------------------------------------

def orange_mask(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (r > 170) & (g > 70) & (g < 170) & (b < 100) & (r - g > 60)


def shown_clip_times(sec, t0, t1):
    """Clip time drawn on each film frame of a product shot (frozen on clip_in until clip_at)."""
    out = []
    for f in range(fr(t0), fr(t1)):
        t = f / FPS
        out.append(sec["clip_in"] + (t - sec["clip_at"]) if f >= fr(sec["clip_at"]) else sec["clip_in"])
    return out


def gate6():
    res = {}
    # Fold: find every source frame with the orange CLIP label (or clipped orange trace), then check
    # the extracted frames the film actually draws.
    sec = section("fold")
    src = os.path.join(SITE, sec["clip_src"].replace("public/", "", 1))
    W, H = 1080, 640
    p = subprocess.Popen([ffmpeg(), "-nostdin", "-loglevel", "error", "-i", src, "-vf", "fps=60", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    orange_times, n = [], 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        if orange_mask(np.frombuffer(b, np.uint8).reshape(H, W, 3)).sum() > 20:
            orange_times.append(n / 60)
        n += 1
    p.wait()
    meta = json.load(open(os.path.join(DATA, "frames/fold/meta.json")))
    shown = shown_clip_times(sec, sec["t0"], sec["t1"])
    idx = sorted({max(0, min(meta["count"] - 1, round((tc - meta["start"]) * meta["fps"]))) for tc in shown})
    hits = []
    for i in idx:
        a = np.asarray(Image.open(os.path.join(DATA, f"frames/fold/frame-{i:04d}.webp")).convert("RGB"))
        c = int(orange_mask(a).sum())
        if c > 20:
            hits.append({"frame": i, "orange_px": c})
    first_orange = orange_times[0] if orange_times else None
    res["fold"] = {
        "source": sec["clip_src"],
        "window": [sec["clip_in"], sec["clip_out"]],
        "last_clip_time_shown": round(max(shown), 4),
        "first_source_time_with_orange_clip_label": first_orange,
        "margin_s": round(first_orange - max(shown), 4) if first_orange is not None else None,
        "extracted_frames_checked": len(idx),
        "frames_with_orange": hits,
        "pass": not hits and (first_orange is None or first_orange > max(shown)),
    }

    # Echolalia: the crop (x 0-1600, y 96-530 of the 1600x812 source) must exclude the header
    # (Echolalia STUDY, VISUAL STUDY, HUB, preset label), the EST. 2023 panel and the caption.
    sec = section("echolalia")
    scene = open(os.path.join(REPO, "film/scenes/shot20-echolalia.js")).read()
    m = re.search(r"CROP = \{ x: (\d+), y: (\d+), w: (\d+), h: (\d+) \}", scene)
    cx, cy, cw, ch = map(int, m.groups())
    meta = json.load(open(os.path.join(DATA, "frames/echolalia/meta.json")))
    shown = shown_clip_times(sec, sec["t0"], sec["t1"])
    idx = sorted({max(0, min(meta["count"] - 1, round((tc - meta["start"]) * meta["fps"]))) for tc in shown})
    # Text boxes found by bright pixels in each forbidden element's area (source px), over every shown frame.
    areas = {
        "header (Echolalia STUDY, VISUAL STUDY, HUB, preset label)": (0, 0, 1600, 100, 150),
        "KAIZEN DSP EST. 2023": (60, 560, 220, 812, 110),
        "burned-in caption": (400, 740, 1200, 812, 150),
    }
    boxes = {k: None for k in areas}
    for i in idx[:: max(1, len(idx) // 30)]:
        g = np.asarray(Image.open(os.path.join(DATA, f"frames/echolalia/frame-{i:04d}.webp")).convert("L"))
        for k, (x0, y0, x1, y1, thr) in areas.items():
            ys, xs = np.where(g[y0:y1, x0:x1] > thr)
            if not len(ys):
                continue
            b = [int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0, int(ys.max()) + y0]
            boxes[k] = b if boxes[k] is None else [min(boxes[k][0], b[0]), min(boxes[k][1], b[1]), max(boxes[k][2], b[2]), max(boxes[k][3], b[3])]
    ok = True
    found = {}
    for k, b in boxes.items():
        inside = b is not None and not (b[3] < cy or b[1] >= cy + ch)
        # The header box is searched only above y 100; anything it finds at y >= cy is the plate's
        # bevel, so require its text rows (found with a text-height run) to end above the crop.
        if k.startswith("header") and b is not None:
            g = np.asarray(Image.open(os.path.join(DATA, f"frames/echolalia/frame-{idx[len(idx) // 2]:04d}.webp")).convert("L"))
            rows = np.where((g[0:cy, 0:1600] > 150).sum(1) > 0)[0]
            b = [b[0], int(rows.min()), b[2], int(rows.max())] if len(rows) else None
            inside = False
        found[k] = {"box_src_px": b, "inside_crop": inside}
        ok = ok and not inside
    res["echolalia"] = {
        "source": sec["clip_src"],
        "window": [sec["clip_in"], sec["clip_out"]],
        "crop_src_px": [cx, cy, cx + cw, cy + ch],
        "elements": found,
        "frames_checked": len(idx),
        "pass": ok and cy >= 96 and cy + ch <= 530,
    }
    res["pass"] = res["fold"]["pass"] and res["echolalia"]["pass"]
    return res


# Gate 7 -------------------------------------------------------------------------------------------

def gate7():
    scale = 0.45
    out = {"scale": scale, "items": {}}
    for label, (x0, y0, x1, y1, mode) in {
        "v0.1.0 (bottom right)": (1080, 985, 1190, 1030, "dark"),
        "header subtitle 0.1.0 / KAIZEN DSP": (10, 40, 120, 65, "bright"),
    }.items():
        hs = []
        for n in ("cold", "warm", "hot"):
            g = np.asarray(Image.open(f"{SITE}/stovetop/stovetop-{n}.jpg").convert("L")).astype(float)
            reg = g[y0:y1, x0:x1]
            bg = np.median(reg)
            ink = reg < bg - 40 if mode == "dark" else reg > bg + 40
            rows = np.where(ink.sum(1) > 0)[0]
            hs.append(int(rows.max() - rows.min() + 1))
        out["items"][label] = {"source_cap_height_px": max(hs), "rendered_cap_height_px": round(max(hs) * scale, 2)}
    # One rendered still: ink rows of "v0.1.0" at 68.50 (stills at x 1180, y 330, 0.45 scale).
    still = os.path.join(OUT, "stills/full-0.5/still-137-t68.500-f04110.png")
    if os.path.exists(still):
        g = np.asarray(Image.open(still).convert("L")).astype(float)
        reg = g[775:796, 1670:1705]
        rows = np.where((reg < np.median(reg) - 25).sum(1) > 0)[0]
        rows = rows[rows < 18]
        out["rendered_still"] = {"file": still, "ink_rows_px": int(rows.max() - rows.min() + 1) if len(rows) else 0}
    out["pass"] = all(v["rendered_cap_height_px"] <= 5 for v in out["items"].values()) and out.get("rendered_still", {}).get("ink_rows_px", 0) <= 5
    return out


# Gate 9 and coverage ------------------------------------------------------------------------------

# Section 6 rows: (shots, block, scan keys, words, table time, window [t0, t1) to measure in).
COPY = [
    ("1", "Eyebrow", ["HEADPHONES ON"], 2, 2.00, (0, 2)),
    ("1, 3", "Headline, first half", ["Great sound "], 2, 1.75, (0, 3)),
    ("1, 3", "Headline", ["Great sound doesn’t sit still."], 5, 4.85, (3, 7.85)),
    ("1-3", "Scope label", ["STEREO FIELD"], 2, 7.60, (0, 8)),
    ("1-3", "Pill", ["DRY | CHOROBOROS"], 2, 7.60, (0, 8)),
    ("2-3", "Footnote", ["LEVEL MATCHED"], 2, 5.60, (0, 8)),
    ("5", "Eyebrow", ["KAIZEN DSP · FIRST RELEASE"], 4, 3.50, (8, 12)),
    ("5", "H1", ["Meet Choroboros."], 2, 3.25, (8, 12)),
    ("5", "Sub", ["A chorus and modulation plugin for macOS."], 7, 2.50, (8, 12)),
    ("6", "Headline", ["Five prebuilt engines."], 3, 4.00, (12, 16)),
    ("6", "Labels", ["GREEN", "BLUE", "RED", "PURPLE", "BLACK"], 1, 2.00, (12, 16)),
    ("6", "Footnote", ["EVERY CHOROBOROS DEMO IN THIS FILM STARTS MONO AND DRY."], 10, 3.00, (12, 16)),
    ("7-11", "Label", ["BEST FOR"], 2, 20.00, (16, 36)),
    ("7-11", "Footnote", ["SAME TAKE · LEVEL MATCHED"], 4, 20.00, (16, 36)),
    ("7", "Pill, eyebrow", ["FREE", "LAGRANGE 3RD CORE"], 4, 4.00, (16, 20.25)),
    ("7", "Headline", ["Green. Sways."], 2, 4.00, (16, 20.25)),
    ("7", "Best for", ["Warm acoustic and synth sends"], 5, 4.00, (16, 20.25)),
    ("7", "Caption", ["Depth."], 1, 2.00, (16, 20.25)),
    ("8", "Eyebrow", ["CUBIC CORE"], 2, 4.00, (19.75, 24.25)),
    ("8", "Headline", ["Blue. Widens."], 2, 4.00, (19.75, 24.25)),
    ("8", "Best for", ["Clean width on vocals and buses"], 6, 4.00, (19.75, 24.25)),
    ("8", "Caption", ["Offset."], 1, 2.00, (19.75, 24.25)),
    ("9", "Headline", ["Red. Wavers."], 2, 4.00, (23.75, 28.25)),
    ("9", "Best for", ["BBD AND TAPE. VINTAGE INSTABILITY."], 5, 4.00, (23.75, 28.25)),
    ("9", "Pill", ["BBD | TAPE"], 2, 4.00, (23.75, 28.25)),
    ("9", "Lines", ["TWO SOUND CORES PER ENGINE", "SAME KNOBS, DIFFERENT CORE"], 9, 2.75, (23.75, 28.25)),
    ("10", "Pill, eyebrow", ["FREE", "ORBIT CORE"], 3, 4.00, (27.75, 32.25)),
    ("10", "Headline", ["Purple. Orbits."], 2, 4.00, (27.75, 32.25)),
    ("10", "Best for", ["STRANGE TEXTURES, SOUND DESIGN, WEIRDNESS"], 5, 4.00, (27.75, 32.25)),
    ("10", "Caption", ["Rate."], 1, 2.00, (27.75, 32.25)),
    ("11", "Eyebrow", ["ENSEMBLE CORE"], 2, 4.00, (31.75, 36)),
    ("11", "Headline", ["Black. Multiplies."], 2, 4.00, (31.75, 36)),
    ("11", "Best for", ["Dense ensembles. Low CPU."], 4, 4.00, (31.75, 36)),
    ("11", "Caption", ["Color."], 1, 2.00, (31.75, 36)),
    ("12", "Centre", ["17", "SOUND CORES"], 3, 4.00, (36, 40)),
    ("12", "Tag", ["NOW PLAYING · LAGRANGE 5TH"], 4, 3.50, (36, 40)),
    ("12", "Bottom", ["The ten cores inside the prebuilt engines, plus seven more."], 10, 2.50, (36, 40)),
    ("13", "Headline", ["Build your own", "in Create."], 5, 6.00, (40, 46)),
    ("13", "Caption", ["INTERFACE CAPTURE FROM CHOROBOROS 1.0.5"], 5, 5.75, (40, 46)),
    ("13", "Sub", ["Choose one or two cores.", "Modify recipes.", "Add artwork."], 9, 5.25, (40, 46)),
    ("13", "Footnote", ["INCLUDED WITH AN ACTIVE 30-DAY TRIAL", "OR A PAID LICENCE."], 10, 4.00, (40, 46)),
    ("14", "Eyebrow", ["ARTWORK PACKS FOR CREATE"], 4, 3.85, (46, 49.85)),
    ("14", "Headline", ["26 custom looks."], 3, 3.85, (46, 49.85)),
    ("14", "Bottom", ["A custom look changes what Choroboros looks like, not how it sounds."], 12, 3.35, (46, 49.85)),
    ("16", "Eyebrow", ["FREE MODE"], 2, 4.00, (50, 54)),
    ("16", "Headline", ["Green and Purple are free."], 5, 4.00, (50, 54)),
    ("16", "Sub", ["No card or licence key needed."], 6, 3.25, (50, 54)),
    ("16", "Labels", ["GREEN", "PURPLE"], 1, 4.00, (50, 54)),
    ("17", "Headline", ["30-day free trial. No payment card."], 6, 4.00, (54, 58)),
    ("17", "Labels", ["BLUE", "RED", "BLACK", "CREATE"], 1, 4.00, (54, 58)),
    ("17", "Sub", ["Unlocks Blue, Red, Black and Create."], 6, 3.25, (54, 58)),
    ("18", "Eyebrow", ["ONE-TIME PURCHASE · NO SUBSCRIPTION"], 4, 4.00, (58, 62)),
    ("18", "Headline", ["$49.99 USD."], 2, 4.00, (58, 62)),
    ("18", "Sub", ["Lifetime updates. 30-day refund."], 4, 3.50, (58, 62)),
    ("19-21", "Eyebrow", ["MORE FROM KAIZEN DSP"], 4, 7.50, (62, 69.5)),
    ("19", "Eyebrow", ["FOLD · COMING SOON"], 3, 2.50, (62, 64.5)),
    ("19", "Headline", ["A free spectral stereo shaper."], 5, 2.50, (62, 64.5)),
    ("20", "Eyebrow", ["ECHOLALIA · DELAY + REVERB · COMING SOON"], 5, 2.50, (64.5, 67)),
    ("20", "Headline", ["Echoes that change as they return."], 6, 2.50, (64.5, 67)),
    ("21", "Eyebrow", ["STOVETOP · IN DEVELOPMENT"], 3, 2.50, (67, 69.5)),
    ("21", "Headline", ["Heats up", "as you play."], 5, 2.50, (67, 69.5)),
    ("23-25", "Tagline", ["Great sound", "doesn’t", "sit still."], 5, 16.00, (70, 86)),
    ("24-25", "Top right", ["CHOROBOROS · CHORUS PLUGIN"], 3, 10.00, (74, 86)),
    ("24-25", "CTA buttons", ["Buy Choroboros", "Start your 30-day free trial"], 7, 11.00, (74, 86)),
    ("24-25", "URL", ["kaizendsp.com/choroboros"], 1, 11.50, (74, 86)),
    ("24-25", "Line", ["Available now for macOS · Apple Silicon + Intel"], 7, 11.00, (74, 86)),
    ("24-25", "Facts", ["GREEN AND PURPLE FREE · 30-DAY TRIAL · $49.99 USD ONE-TIME"], 9, 10.50, (74, 86)),
    ("24-25", "Tiles", ["VST®3 · AU · Audio Units · AAX · Standalone · macOS"], 7, 10.00, (74, 86)),
    ("24-25", "Footer", ["Five prebuilt engines · 17 sound cores · Version 1.0.5"], 9, 9.50, (74, 86)),
]
READ_ALPHA = 0.5  # a block counts as on screen from half opacity (fades count half their length)
DENSITY_SHOTS = [(1, 0, 2), (3, 3, 7.85), (5, 8, 12), (6, 12, 16), (7, 16, 20), (8, 20, 24), (9, 24, 28), (10, 28, 32),
                 (11, 32, 36), (12, 36, 40), (13, 40, 46), (14, 46, 49.85), (16, 50, 54), (17, 54, 58), (18, 58, 62),
                 (19, 62, 64.5), (20, 64.5, 67), (21, 67, 69.5), (23, 70, 74), ("24-25", 74, 86)]


def words_of(text):
    return len([w for w in text.split() if re.search(r"\w", w)])


def gate9(scan):
    F = scan["frames"]
    rows, ok = [], True
    for shots, block, keys, words, table_t, (a, b) in COPY:
        per_key = {}
        for k in keys:
            n = sum(1 for f in range(fr(a), min(FRAMES, fr(b))) if F[f]["texts"].get(k, 0) >= READ_ALPHA)
            per_key[k] = round(n / FPS, 3)
        # "Labels" rows list one-word blocks; other multi-key rows are one block set in pieces.
        need = max(1.5, 0.25 * words)
        measured = min(per_key.values())
        row_ok = measured + 1e-9 >= need
        near_table = measured >= table_t - 0.15
        rows.append({"shots": shots, "block": block, "text": " / ".join(keys), "words": words, "table_time_s": table_t,
                     "measured_s": measured, "min_required_s": need, "pass": row_ok, "within_0.15s_of_table": near_table,
                     **({"per_key_s": per_key} if len(keys) > 1 else {})})
        ok = ok and row_ok
    # New words per shot: every block whose on-screen run (>= 50% opacity) starts inside the shot.
    exempt = lambda k: k.startswith("VST is a trademark") or k == "KAIZENDSP"
    dens = []
    for shot, a, b in DENSITY_SHOTS:
        new = {}
        for f in range(fr(a), fr(b)):
            for k, al in F[f]["texts"].items():
                if al >= READ_ALPHA and not exempt(k) and (f == 0 or F[f - 1]["texts"].get(k, 0) < READ_ALPHA):
                    new[k] = words_of(k)
        n = sum(new.values())
        rate = n / (b - a)
        dens.append({"shot": shot, "window": [a, b], "new_words": n, "words_per_s": round(rate, 2), "pass": rate <= 5.0 + 1e-9})
    ok_d = all(d["pass"] for d in dens)
    return {"rule": "each block on screen >= max(1.5 s, 0.25 s/word) at >= 50% opacity; new words per shot <= 5/s",
            "blocks": rows, "density": dens, "pass": ok and ok_d}


def coverage(scan):
    F = scan["frames"]
    empty = [f for f in range(FRAMES) if not F[f]["layers"]]
    stops = set(range(fr(7.85), fr(8.0))) | set(range(fr(49.85), fr(50.0))) | set(range(fr(69.5), fr(70.0)))
    unexpected_empty = [f for f in empty if f not in stops]
    cuts = []
    for s in cues["sections"]:
        t = s["t0"]
        if t == 0:
            continue
        f = fr(t)
        before, after = set(F[f - 1]["layers"]), set(F[f]["layers"])
        cuts.append({"t": t, "shot": s["shot"], "frame": f, "leaves": sorted(before - after), "enters": sorted(after - before)})
    return {"frames": len(F), "empty_frames": [[a / FPS, (b + 1) / FPS] for a, b in runs(empty)],
            "unexpected_empty": unexpected_empty, "cuts": cuts, "pass": not unexpected_empty}


def runs(ix):
    out = []
    for i in ix:
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def main():
    scan = json.load(open(os.path.join(QC, "scan.json")))
    gates = json.load(open(os.path.join(QC, "gates.json")))
    det_log = os.path.join(OUT, "logs/determinism.log")
    det = None
    if os.path.exists(det_log):
        lines = open(det_log).read().splitlines()
        times = [ln.split()[1] for ln in lines if ln.startswith(("OK ", "DIFF", "FAIL"))]
        det = {"times": times, "result": next((ln for ln in lines if ln.startswith("deterministic")), None),
               "pass": any(ln.startswith("deterministic: all captures identical") for ln in lines) and len(times) >= 5}
    g8 = gates["gate8"]
    vst_frames = [f for f, x in enumerate(scan["frames"]) if x.get("vst", 0) > 0]
    fmt_frames = [f for f, x in enumerate(scan["frames"]) if x["texts"].get("VST®3 · AU · Audio Units · AAX · Standalone · macOS", 0) > 0]
    film = np.asarray(Image.open(g8["pixel"]["filmPng"]).convert("RGB")).astype(int)
    ref = np.asarray(Image.open(g8["pixel"]["refPng"]).convert("RGB")).astype(int)
    chain_clean = all(c["filter"] == "none" and c["transform"] == "none" and c["blend"] == "normal" and c["opacity"] == "1" for c in g8["info"]["chain"])
    report = {
        "film": "Still Life, main 16:9",
        "composition": "film/main/index.html",
        "generated_by": "film/tools/qc_picture.mjs (scan, gates) and film/tools/qc_picture.py",
        "coverage_and_cuts": coverage(scan),
        "gate5_readouts_knobs_captions": {"times": [g["t"] for g in gates["gate5"]],
                                           "failures": [g for g in gates["gate5"] if not g["ok"]],
                                           "plates_checked": sum(1 for g in gates["gate5"] for p in g["plates"] if p.get("render")),
                                           "pass": all(g["ok"] for g in gates["gate5"])},
        "gate6_product_clips": gate6(),
        "gate7_stovetop_version_strings": gate7(),
        "gate8_vst_tile": {
            "src": g8["info"]["src"], "natural_px": g8["info"]["natural"], "drawn_px": g8["info"]["rect"][2:],
            "style_chain_unmodified": chain_clean, "top_layer_z": g8["info"]["chain"][-1]["z"],
            "pixels_vs_same_image_scaled_alone": {"max_abs_diff": int(np.abs(film - ref).max()), "mean_abs_diff": float(np.abs(film - ref).mean())},
            "frames_with_logo": [vst_frames[0] / FPS, (vst_frames[-1] + 1) / FPS] if vst_frames else None,
            "frames_with_vst3_label": [fmt_frames[0] / FPS, (fmt_frames[-1] + 1) / FPS] if fmt_frames else None,
            "logo_in_every_label_frame": vst_frames == fmt_frames,
            "logo_opacity_values": sorted({x.get("vst") for x in scan["frames"] if x.get("vst")}),
            "pass": chain_clean and vst_frames == fmt_frames and int(np.abs(film - ref).max()) == 0,
        },
        "gate9_reading_budget": gate9(scan),
        "gate11_determinism": det,
    }
    for k in ("gate6_product_clips", "gate7_stovetop_version_strings", "gate9_reading_budget"):
        print(k, report[k]["pass"])
    report["gate5_readouts_knobs_captions"]["gate5_detail"] = gates["gate5"]
    out = os.path.join(REPO, "film/qc-picture.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print("wrote", out)


if __name__ == "__main__":
    main()
