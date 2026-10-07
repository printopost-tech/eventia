#!/usr/bin/env bash
# Burn the static overlay onto a Reel. Audio is stream-copied untouched.
# Usage: reel/render.sh input.mp4 [output.mp4]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
in="$1"
out="${2:-${in%.*}_overlay.mp4}"

command -v ffmpeg >/dev/null || { sudo apt-get update && sudo apt-get install -y ffmpeg; }

IFS=, read -r w h fps < <(ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate -of csv=p=0 "$in")
echo "input: ${w}x${h} @ ${fps} fps, duration $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")s"

overlay="$here/overlay.png"
[ "${w}x${h}" = "1080x1920" ] || overlay="$here/overlay_${w}x${h}.png"
python3 "$here/make_overlay.py" "$w" "$h" "$overlay"

ffmpeg -y -i "$in" -i "$overlay" \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -preset slow -crf 18 -profile:v high \
  -r "$fps" -c:a copy -movflags +faststart "$out"

echo "output:"
ffprobe -v error -show_entries format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration "$out"
