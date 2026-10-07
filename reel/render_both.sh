#!/usr/bin/env bash
# Burn the static two-trail overlay onto the clean Reel clip, then save
# check frames at 1s/7s/14s. Audio is stream-copied untouched.
# Usage: reel/render_both.sh input.mp4 [output.mp4]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
in="$1"
out="${2:-$here/reel-both-trails.mp4}"

IFS=, read -r w h fps < <(ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate -of csv=p=0 "$in")
echo "input: ${w}x${h} @ ${fps} fps"

python3 "$here/make_overlay_both.py"  # 1080x1920 master: overlay-both-trails.png
overlay="$here/overlay-both-trails_${w}x${h}.png"
python3 "$here/make_overlay_both.py" "$w" "$h" "$overlay" >/dev/null

ffmpeg -v error -y -i "$in" -i "$overlay" \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -preset slow -crf 18 -profile:v high \
  -r "$fps" -c:a copy -movflags +faststart "$out"

for t in 1 7 14; do
  ffmpeg -v error -y -ss "$t" -i "$out" -frames:v 1 -q:v 2 "${out%.mp4}_frame_${t}s.jpg"
done
ffprobe -v error -show_entries format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration "$out"
