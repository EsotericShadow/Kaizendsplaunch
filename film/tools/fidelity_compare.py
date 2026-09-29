#!/usr/bin/env python3
"""Compare the film's plate with renders of the real Choroboros editor (film/UI_FIDELITY.md).

  python3 film/tools/fidelity_compare.py <stills dir> <reference dir> <out dir> [tag]

<stills dir>: stills of film/gallery/fidelity.html (film.sh stills <name> 0.5,1.5,... that page).
<reference dir>: the editor renders (<state>.png, 1400 px wide, header included) named as in
/home/user/build/film/data/fidelity/states.json, in the same order as the page shows them.
For each state writes <out>/<tag>-<state>-side.png (reference | plate), -blend.png (50/50) and
-diff.png (absolute difference x4), plus <out>/<tag>-report.json with the mean absolute error of
the whole window, the header strip and the body, per state.
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

W = 1400
H = 847  # 386 editor px x 1400/638
HEADER = round(56 * W / 638)


def load(p, size=(W, H)):
    im = Image.open(p).convert("RGB")
    if im.size != size:
        im = im.crop((0, 0, size[0], size[1]))
    return im


def main():
    stills_dir, ref_dir, out_dir = sys.argv[1:4]
    tag = sys.argv[4] if len(sys.argv) > 4 else "cmp"
    os.makedirs(out_dir, exist_ok=True)
    states = json.load(open("/home/user/build/film/data/fidelity/states.json"))
    stills = sorted(f for f in os.listdir(stills_dir) if f.startswith("still-"))
    report = {}
    for i, st in enumerate(states):
        ref_p = os.path.join(ref_dir, st["name"] + ".png")
        if i >= len(stills) or not os.path.exists(ref_p):
            continue
        ref = load(ref_p)
        ours = load(os.path.join(stills_dir, stills[i]))
        a = np.asarray(ref, dtype=np.float32)
        b = np.asarray(ours, dtype=np.float32)
        d = np.abs(a - b)
        report[st["name"]] = {
            "mae_window": round(float(d.mean()), 2),
            "mae_header": round(float(d[:HEADER].mean()), 2),
            "mae_body": round(float(d[HEADER:].mean()), 2),
        }
        side = Image.new("RGB", (W * 2 + 20, H + 40), (20, 20, 20))
        side.paste(ref, (0, 40))
        side.paste(ours, (W + 20, 40))
        dr = ImageDraw.Draw(side)
        dr.text((10, 10), f"REAL EDITOR (RC f984c9a)  {st['name']}", fill=(255, 255, 255))
        dr.text((W + 30, 10), f"FILM PLATE ({tag})", fill=(255, 255, 255))
        side.resize((side.width // 2, side.height // 2), Image.LANCZOS).save(os.path.join(out_dir, f"{tag}-{st['name']}-side.png"))
        Image.blend(ref, ours, 0.5).save(os.path.join(out_dir, f"{tag}-{st['name']}-blend.png"))
        Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, f"{tag}-{st['name']}-diff.png"))
    with open(os.path.join(out_dir, f"{tag}-report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
