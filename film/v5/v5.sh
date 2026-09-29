#!/usr/bin/env bash
# Commands for the v5 portrait films (1080x1920, 60 fps). Outputs go under $V5_OUT
# (default /home/user/build/v5), never the repo.
#
#   film/v5/v5.sh prep                                 data dirs, symlinks, available.json (run by every command)
#   film/v5/v5.sh stills <name> <t1,t2,...|every:0.5> [main|tiktok]   PNG stills + contact sheets in $OUT/stills/<name>
#   film/v5/v5.sh frames <name> <t0> <t1> [main|tiktok]               a still at EVERY frame of [t0, t1] (sync checks)
#   film/v5/v5.sh preview <name> [from] [to] [main|tiktok]            half-size MP4 in $OUT/out/<name>.mp4
#   film/v5/v5.sh render <name> [from] [to] [main|tiktok]             final MP4 in $OUT/out/<name>.mp4
#   film/v5/v5.sh check <t1,t2,...> [main|tiktok]                     determinism check (two browsers, three seek orders)
#
# The composition is main (film/v5/main.html, 0 s = the master's first sample) or tiktok
# (film/v5/tiktok.html, its own data dir and audio). Audio: $OUT/master_v5.wav for main,
# $OUT/tiktok_v5.wav for tiktok, muxed when present. WORKERS defaults to 2 (4 shared CPUs).
# Open a composition in a browser with ?safe=1 to see the safe-zone guides (never in renders).

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${V5_OUT:-/home/user/build/v5}"   # V5_OUT (FILM_OUT belongs to the 16:9 film)
FILM_DATA="${FILM_DATA:-/home/user/build/film/data}"   # the 16:9 film's prepared GUI slices and clip frames
WORKERS="${WORKERS:-2}"

comp_of() { case "${1:-main}" in main) echo film/v5/main.html ;; tiktok) echo film/v5/tiktok.html ;; *) echo "unknown composition: $1" >&2; exit 2 ;; esac; }
data_of() { case "${1:-main}" in main) echo "$OUT/data" ;; tiktok) echo "$OUT/data-tiktok" ;; esac; }
audio_of() { case "${1:-main}" in main) echo "$OUT/master_v5.wav" ;; tiktok) echo "$OUT/tiktok_v5.wav" ;; esac; }
mounts_of() { echo --mount /art/rc=/home/user/choroboros-rc/Assets --mount /art/site=/home/user/kaizendsp/public --mount "/data=$(data_of "$1")"; }

prep_one() {
  local which="$1" data; data="$(data_of "$which")"
  mkdir -p "$data" "$OUT/out" "$OUT/stills"
  # The GUI slices and clip frames are shared with the 16:9 film (prepared by film/film.sh gui|frames).
  if [[ ! -f "$FILM_DATA/gui/index.json" ]]; then FILM_OUT="$(dirname "$FILM_DATA")" "$REPO/film/film.sh" gui; fi
  for d in gui frames; do
    if [[ -e "$FILM_DATA/$d" ]]; then ln -sfn "$FILM_DATA/$d" "$data/$d"; fi
  done
  # Scope data from the v5 audio build, when it exists: $V5_SCOPE, else $OUT/audio/scope[-tiktok].
  # If the audio build writes straight into $data/scope (a real directory), it is used as it is.
  local suffix=""; [[ "$which" == tiktok ]] && suffix="-tiktok"
  local scope_src="${V5_SCOPE:-$OUT/audio/scope$suffix}"
  if [[ -d "$data/scope" && ! -L "$data/scope" ]]; then
    :
  elif [[ -f "$scope_src/index.json" && "$(realpath -m "$scope_src")" != "$(realpath -m "$data/scope")" ]]; then
    ln -sfn "$scope_src" "$data/scope"
  elif [[ -L "$data/scope" && ! -f "$data/scope/index.json" ]]; then
    rm -f "$data/scope"
  fi
  python3 - "$data" <<'PY'
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
out = {"gui": os.path.isfile(os.path.join(data, "gui", "index.json")), "scope": bool(stems), "scopeStems": stems, "frames": frames,
       "measured": os.path.isfile(os.path.join(scope, "measured.json")), "meter": os.path.isfile(os.path.join(scope, "meter.json"))}
with open(os.path.join(data, "available.json"), "w") as f:
    json.dump(out, f, indent=1)
print(os.path.basename(data), "available:", json.dumps(out))
PY
}

prep() { prep_one main; prep_one tiktok; }

stills() {
  local name="$1" at="$2" which="${3:-main}"
  prep_one "$which" >/dev/null
  # shellcheck disable=SC2046
  cd "$REPO" && node tools/stills.mjs --comp "$(comp_of "$which")" --at "$at" --out "$OUT/stills/$name" --workers "$WORKERS" --no-sheet $(mounts_of "$which")
  python3 "$REPO/film/tools/sheet.py" "$OUT/stills/$name" "${SHEET_PER:-12}" "${SHEET_COLS:-6}" "${SHEET_W:-270}" sheet
}

# A still at every frame from t0 to t1 inclusive (frame times f/60), for frame-accuracy checks.
frames() {
  local name="$1" t0="$2" t1="$3" which="${4:-main}"
  local at; at="$(python3 -c "import math,sys; a,b=float(sys.argv[1]),float(sys.argv[2]); print(','.join(f'{f/60:.6f}' for f in range(math.ceil(a*60-1e-9), math.floor(b*60+1e-9)+1)))" "$t0" "$t1")"
  stills "$name" "$at" "$which"
}

preview() {
  local name="$1" from="${2:-}" to="${3:-}" which="${4:-main}"
  prep_one "$which" >/dev/null
  local range=(); [[ -n "$from" ]] && range+=(--from "$from"); [[ -n "$to" ]] && range+=(--to "$to")
  local audio=(); [[ -f "$(audio_of "$which")" ]] && audio=(--audio "$(audio_of "$which")")
  # shellcheck disable=SC2046
  cd "$REPO" && node tools/render.mjs --comp "$(comp_of "$which")" --out "$OUT/out/$name.mp4" --preview --workers "$WORKERS" "${range[@]}" "${audio[@]}" $(mounts_of "$which")
}

render() {
  local name="$1" from="${2:-}" to="${3:-}" which="${4:-main}"
  prep_one "$which" >/dev/null
  local range=(); [[ -n "$from" ]] && range+=(--from "$from"); [[ -n "$to" ]] && range+=(--to "$to")
  local audio=(); [[ -f "$(audio_of "$which")" ]] && audio=(--audio "$(audio_of "$which")")
  # shellcheck disable=SC2046
  cd "$REPO" && node tools/render.mjs --comp "$(comp_of "$which")" --out "$OUT/out/$name.mp4" --workers "$WORKERS" "${range[@]}" "${audio[@]}" $(mounts_of "$which")
}

check() {
  local at="$1" which="${2:-main}"
  prep_one "$which" >/dev/null
  # shellcheck disable=SC2046
  cd "$REPO" && node tools/render.mjs --comp "$(comp_of "$which")" --out "$OUT/stills/determinism-$which" --check-determinism "$at" $(mounts_of "$which")
}

cmd="${1:-}"; shift || true
case "$cmd" in
  prep|stills|frames|preview|render|check) "$cmd" "$@" ;;
  *) sed -n '2,17p' "$0"; exit 1 ;;
esac
