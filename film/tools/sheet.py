#!/usr/bin/env python3
"""Contact sheets from a stills folder: sheet.py <dir> <per_sheet> <columns> <thumb_w> [prefix]"""
import glob, os, re, sys
from PIL import Image, ImageDraw, ImageFont

d, per, cols, tw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
prefix = sys.argv[5] if len(sys.argv) > 5 else "sheet"
files = sorted(glob.glob(os.path.join(d, "still-*.png")))
th = round(tw * 9 / 16)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14)
except Exception:
    font = ImageFont.load_default()
for s in range(0, len(files), per):
    chunk = files[s:s + per]
    rows = (len(chunk) + cols - 1) // cols
    W = cols * (tw + 8) + 8
    H = rows * (th + 26) + 8
    sheet = Image.new("RGB", (W, H), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    for i, f in enumerate(chunk):
        m = re.search(r"-t([0-9.]+)-f(\d+)", f)
        im = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
        x = 8 + (i % cols) * (tw + 8)
        y = 8 + (i // cols) * (th + 26)
        sheet.paste(im, (x, y))
        dr.text((x + 2, y + th + 4), f"{m.group(1)} s  f{int(m.group(2))}", fill=(235, 235, 235), font=font)
    out = os.path.join(d, f"{prefix}-{s // per:02d}.png")
    sheet.save(out)
    print(out)
