#!/usr/bin/env bash
# Rebuild the whole "Still Life" soundtrack (main film and vertical cutdown).
# Heavy outputs go to /home/user/build/film (not committed); logs to audio/logs.
# The Choroboros renderer is used by path (/home/user/build/choro-render/build/choro-render
# or $CHORO_RENDER) and is never copied into this repository.
#
# Usage: audio/film/run_all.sh [--no-vertical] [--no-sweep]
set -euo pipefail
cd "$(dirname "$0")"
VERTICAL=1
SWEEP="--sweep"
for a in "$@"; do
  case "$a" in
    --no-vertical) VERTICAL=0 ;;
    --no-sweep) SWEEP="" ;;
  esac
done
t0=$(date +%s)
echo "== 1/8 compose dry mono stems"
python3 compose.py
echo "== 2/8 Choroboros renders R01-R12 + R09ref (Purple pre-roll sweep, meta checks)"
python3 render_dsp.py $SWEEP --jobs 2
echo "== 3/8 level matching (BS.1770 per bar) -> audio/logs/level-match.json"
python3 levelmatch.py
echo "== 4/8 product clips (Fold, Echolalia bend check, Stovetop downbeat)"
python3 clips.py
echo "== 5/8 mix and master"
python3 mix.py
echo "== 6/8 scope data"
python3 scope.py
echo "== 7/8 QC -> audio/logs/qc.json"
python3 qc.py
if [ "$VERTICAL" = 1 ]; then
  echo "== 8/8 vertical cutdown (compose, renders, level match, mix, scope, QC)"
  python3 vertical.py
fi
echo "done in $(( $(date +%s) - t0 )) s"
