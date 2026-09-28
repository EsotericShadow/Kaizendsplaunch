#!/usr/bin/env python3
"""Slice the Choroboros filmstrip sheets into one image per frame, for the film's GUI plate.

A page that references the whole sheets makes Chromium decode several 3132 px and 7552 px images
per plate and evict them again, so every frame re-decodes gigabytes. One small file per frame keeps
the decoded footprint tiny. Frames are copied 1:1 (no resampling), so the pixels are the plugin's.

Reads the release-candidate art and writes outside the repo (the art is proprietary):
  /home/user/choroboros-rc/Assets  ->  /home/user/build/film/data/gui/<set>/<sheet>/<NNN>.png
Sets: green, blue, red, purple, black (rate_off ... width_on, mix, switch), white (main, mix),
shared (switch_a). Writes gui/index.json last; re-running skips finished sheets.
"""

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

from PIL import Image

SRC = os.environ.get("CHORO_ASSETS", "/home/user/choroboros-rc/Assets")
DST = os.environ.get("FILM_GUI_OUT", "/home/user/build/film/data/gui")

# (frame size, first frame offset, step, columns, frame count)
MAIN = (300, 12, 312, 10, 100)
MIX = (512, 64, 576, 13, 156)
WHITE_MIX = (150, 12, 162, 10, 100)
SWITCH = (512, 0, 512, 5, 18)

ENGINES = ["green", "blue", "red", "purple", "black"]
KNOBS = [("rate", 1), ("depth", 2), ("offset", 3), ("width", 4)]


def jobs():
    for e in ENGINES:
        for name, n in KNOBS:
            for state in ("off", "on"):
                yield (f"{e}/{name}/{e}_{n}_{state}.png", f"{e}/{name}_{state}", MAIN)
        yield (f"{e}/{e}_mix_knob_spritesheet.png", f"{e}/mix", MIX)
        yield (f"{e}/{e}_switch_spritesheet.png", f"{e}/switch", SWITCH)
    yield ("MIX/white_main_knob_spritesheet.png", "white/main", MAIN)
    yield ("MIX/white_mix_knob_spritesheet.png", "white/mix", WHITE_MIX)
    yield ("switch_a_spritesheet.png", "shared/switch_a", SWITCH)


def slice_sheet(job):
    src, dst, (size, off, step, cols, count) = job
    out = os.path.join(DST, dst)
    done = os.path.join(out, ".done")
    if os.path.exists(done):
        return dst, count, "skip"
    os.makedirs(out, exist_ok=True)
    im = Image.open(os.path.join(SRC, src))
    im.load()
    for f in range(count):
        r, c = divmod(f, cols)
        x, y = off + c * step, off + r * step
        im.crop((x, y, x + size, y + size)).save(os.path.join(out, f"{f:03d}.png"), compress_level=3)
    with open(done, "w") as fh:
        fh.write(src + "\n")
    return dst, count, "ok"


def main():
    workers = int(os.environ.get("PREP_WORKERS", "2"))
    todo = list(jobs())
    index = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for dst, count, status in ex.map(slice_sheet, todo):
            index[dst] = count
            print(f"{status:4s} {dst} ({count})", flush=True)
    with open(os.path.join(DST, "index.json"), "w") as fh:
        json.dump({"source": SRC, "sheets": index}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
