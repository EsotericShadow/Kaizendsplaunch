#!/usr/bin/env bash
# Render helpers for the Still Life film. Outputs go under /home/user/build/film, never the repo.
#
#   film/film.sh prep                                  write /data/available.json (run by every command)
#   film/film.sh gui                                   slice the plugin filmstrips into /data/gui (once, ~15 s)
#   film/film.sh frames                                extract the Fold and Echolalia clip windows to frames
#   film/film.sh stills <name> <t1,t2,...> [comp]      PNG stills + contact sheets (12 per sheet) in $OUT/stills/<name>
#   film/film.sh preview <name> [from] [to] [comp]     half-size preview MP4 in $OUT/out/<name>.mp4 (with the master audio if it exists)
#   film/film.sh render <name> [from] [to] [comp]      final MP4 (adds the master audio if it exists)
#   film/film.sh check <t1,t2,...> [comp]              determinism check (two browsers, three seek orders)
#   film/film.sh gallery                               stills of the component gallery
#
# comp defaults to film/main/index.html. WORKERS (default 2) sets the browser count.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${FILM_OUT:-/home/user/build/film}"
DATA="$OUT/data"
WORKERS="${WORKERS:-2}"
MOUNTS=(--mount /art/rc=/home/user/choroboros-rc/Assets --mount /art/site=/home/user/kaizendsp/public --mount "/data=$DATA")

ffmpeg_bin() {
  if [[ -n "${FFMPEG:-}" ]]; then echo "$FFMPEG"; return; fi
  python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
}

# Tell the page what generated data exists, so it never requests a missing file (a 404 fails a render).
gui() {
  FILM_GUI_OUT="$DATA/gui" python3 "$REPO/film/tools/prep_gui.py"
}

prep() {
  mkdir -p "$DATA/scope" "$DATA/frames" "$OUT/out" "$OUT/stills"
  # (Re)slice when the index is missing or predates the 2x close-up plates.
  grep -q '"lit1x"' "$DATA/gui/index.json" 2>/dev/null || gui
  python3 - "$DATA" <<'PY'
import json, os, sys
data = sys.argv[1]
scope = os.path.join(data, "scope")
idx = os.path.join(scope, "index.json")
stems = []
if os.path.isfile(idx):
    with open(idx) as f:
        j = json.load(f)
    s = j.get("stems") or j.get("files") or {}
    names = [x if isinstance(x, str) else (x.get("name") or x.get("stem")) for x in s] if isinstance(s, list) else list(s)
    for n in names:
        info = s[n] if isinstance(s, dict) else {}
        fn = (info or {}).get("file") or (info or {}).get("path") or f"{n}.i16"
        if os.path.isfile(os.path.join(scope, fn)):
            stems.append(n)
frames = {}
fdir = os.path.join(data, "frames")
if os.path.isdir(fdir):
    for d in sorted(os.listdir(fdir)):
        p = os.path.join(fdir, d)
        if os.path.isdir(p):
            frames[d] = len([x for x in os.listdir(p) if x.startswith("frame-")])
out = {"gui": os.path.isfile(os.path.join(data, "gui", "index.json")), "scope": bool(stems), "scopeStems": stems, "frames": frames}
with open(os.path.join(data, "available.json"), "w") as f:
    json.dump(out, f, indent=1)
print("available:", json.dumps(out))
PY
}

# Clip windows: clip_in/clip_out from the cue sections when present, else the treatment's windows.
# Frames are extracted at 60 fps with a 0.5 s margin each side; frame 0 is clip time (in - 0.5).
frames() {
  prep >/dev/null
  local ff; ff="$(ffmpeg_bin)"
  python3 - "$REPO/film/cues.json" <<'PY' | while read -r name src tin tout; do
import json, sys
c = json.load(open(sys.argv[1]))
defaults = {"fold": ("public/fold/fold-motion-sound.mp4", 1.00, 3.25), "echolalia": ("public/film/echolalia/time-sound-preview.mp4", 9.50, 11.75)}
for s in c["sections"]:
    if s["name"] in defaults:
        src, a, b = defaults[s["name"]]
        src = s.get("clip_src", src)
        a = s.get("clip_in", a)
        b = s.get("clip_out", b)
        print(s["name"], src.replace("public/", "", 1), a, b)
PY
    local dir="$DATA/frames/$name"
    rm -rf "$dir"; mkdir -p "$dir"
    local start; start=$(python3 -c "print(max(0.0, $tin - 0.5))")
    local dur; dur=$(python3 -c "print(($tout + 0.5) - max(0.0, $tin - 0.5))")
    echo "frames: $name  $src  $start + $dur s -> $dir"
    "$ff" -nostdin -hide_banner -loglevel error -ss "$start" -i "/home/user/kaizendsp/public/$src" -t "$dur" \
      -vf "fps=60,setsar=1" -c:v libwebp -quality 92 -compression_level 4 -start_number 0 "$dir/frame-%04d.webp"
    local count; count=$(ls "$dir" | grep -c '^frame-')
    printf '{"source": "%s", "start": %s, "fps": 60, "count": %s, "clip_in": %s, "clip_out": %s}\n' "$src" "$start" "$count" "$tin" "$tout" > "$dir/meta.json"
  done
  prep
}

stills() {
  local name="$1" at="$2" comp="${3:-film/main/index.html}"
  prep >/dev/null
  # Contact sheets are made with PIL: the renderer's in-browser sheet runs out of memory past ~40 stills.
  cd "$REPO" && node tools/stills.mjs --comp "$comp" --at "$at" --out "$OUT/stills/$name" --workers "$WORKERS" --no-sheet "${MOUNTS[@]}"
  python3 "$REPO/film/tools/sheet.py" "$OUT/stills/$name" 12 4 480 sheet
}

preview() {
  local name="$1" from="${2:-}" to="${3:-}" comp="${4:-film/main/index.html}"
  prep >/dev/null
  local range=(); [[ -n "$from" ]] && range+=(--from "$from"); [[ -n "$to" ]] && range+=(--to "$to")
  local audio=(); [[ -f "$OUT/audio/master.wav" ]] && audio=(--audio "$OUT/audio/master.wav")
  cd "$REPO" && node tools/render.mjs --comp "$comp" --out "$OUT/out/$name.mp4" --preview --workers "$WORKERS" "${range[@]}" "${audio[@]}" "${MOUNTS[@]}"
}

render() {
  local name="$1" from="${2:-}" to="${3:-}" comp="${4:-film/main/index.html}"
  prep >/dev/null
  local range=(); [[ -n "$from" ]] && range+=(--from "$from"); [[ -n "$to" ]] && range+=(--to "$to")
  local audio=(); [[ -f "$OUT/audio/master.wav" ]] && audio=(--audio "$OUT/audio/master.wav")
  cd "$REPO" && node tools/render.mjs --comp "$comp" --out "$OUT/out/$name.mp4" --workers "$WORKERS" "${range[@]}" "${audio[@]}" "${MOUNTS[@]}"
}

check() {
  local at="$1" comp="${2:-film/main/index.html}"
  prep >/dev/null
  cd "$REPO" && node tools/render.mjs --comp "$comp" --out "$OUT/stills/determinism" --check-determinism "$at" "${MOUNTS[@]}"
}

gallery() {
  stills gallery "${1:-0.5,1.25,1.75,2.25,2.75,3.25,3.75,4.45,5.42,6.3,7.4}" film/gallery/index.html
}

cmd="${1:-}"; shift || true
case "$cmd" in
  prep|gui|frames|stills|preview|render|check|gallery) "$cmd" "$@" ;;
  *) sed -n '2,14p' "$0"; exit 1 ;;
esac
