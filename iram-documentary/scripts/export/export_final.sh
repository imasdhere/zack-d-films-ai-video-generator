#!/usr/bin/env bash
# Concatenate chapter renders, mux the mastered mix and soft subtitles, make the review copy and thumbnail.
set -euo pipefail
P="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$P"
OUT=renders/final; mkdir -p $OUT
CH=${IRAM_CHAPTER_DIR:-renders/chapters}; NAME=${IRAM_MASTER_NAME:-iram_lost_city_documentary}
# the handoff archive carries the mix as FLAC (lossless); turn it back into mix.wav when needed
[ -f $OUT/mix.wav ] || { [ -f $OUT/mix.flac ] && ffmpeg -y -loglevel error -i $OUT/mix.flac -c:a pcm_s24le $OUT/mix.wav; }
ls $CH/chapter_{0,1,2,3,4,5,6,7}.mp4 | sed "s|^|file '$P/|; s|$|'|" > $OUT/concat.txt
# picture length = sum of the chapter files; mux straight from the concat list (no 3.7 GB intermediate file)
VDUR=$(for f in $CH/chapter_{0,1,2,3,4,5,6,7}.mp4; do ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"; done | awk '{s+=$1} END {printf "%.3f", s}')
# trim audio to picture; never -shortest (subtitles end early)
ffmpeg -y -loglevel error -f concat -safe 0 -i $OUT/concat.txt -i $OUT/mix.wav -i assets/subtitles/iram_lost_city_documentary.en.srt \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -c:s mov_text \
  -metadata title="The Lost City of Iram — In Search of the People of the Pillars" -metadata:s:a:0 language=eng -metadata:s:s:0 language=eng \
  -t "$VDUR" -movflags +faststart $OUT/$NAME.mp4
ffmpeg -y -loglevel error -i $OUT/$NAME.mp4 -map 0:v -map 0:a -map 0:s -vf scale=960:540:flags=lanczos \
  -c:v libx264 -preset medium -crf 27 -pix_fmt yuv420p -c:a aac -b:a 128k -c:s mov_text -movflags +faststart $OUT/${NAME}_review_540p.mp4
echo EXPORT_DONE
