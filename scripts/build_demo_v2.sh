#!/bin/bash
# Composite the current-UI playthrough into demo.mp4 with designed caption chips.
# Windows are VIDEO-time (the raw webm is variable-rate, so beats.json wall-clock
# doesn't map linearly — these were located visually).
set -euo pipefail
cd "$(dirname "$0")/.."

RAW=$(ls docs/demo-raw/*.webm | head -1)
TMP=docs/demo-tmp; rm -rf $TMP; mkdir -p $TMP; : > $TMP/list.txt

seg() { # seg <out> <src_start> <dur> <chip>
  local out=$1 ss=$2 dur=$3 chip=$4
  ffmpeg -y -loglevel error -ss "$ss" -t "$dur" -i "$RAW" -loop 1 -t 30 -i "docs/cards/$chip.png" -filter_complex \
    "[0:v]setpts=PTS-STARTPTS[v];[1:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1[c];[v][c]overlay=0:0:shortest=1" \
    -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 "$TMP/$out.mp4"
  echo "file '$out.mp4'" >> $TMP/list.txt
}
card() { # card <out> <png> <dur>
  ffmpeg -y -loglevel error -loop 1 -t "$3" -i "docs/cards/$2.png" \
    -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=$(echo "$3-0.5"|bc):d=0.5" \
    -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 "$TMP/$1.mp4"
  echo "file '$1.mp4'" >> $TMP/list.txt
}

card intro intro 4
seg s1 6   8 cap1     # scene beauty shot (full-width current UI)
seg s2 44  8 cap2     # REMEMBER: graph reveal, nodes appear
seg s3 108 7 cap3     # living 3D graph, full of nodes
seg s5 116 7 cap5     # RECALL: Ask HAL
seg s6 127 7 cap6     # MEMIFY: purple inferences
seg s7 145 7 cap7     # FORGET: the memory log
seg s8 356 6 cap8     # SOLVE: win screen + confetti + citations
seg s9 362 5 cap9     # the receipts: live Cognee call log
card outro outro 4

ffmpeg -y -loglevel error -f concat -safe 0 -i $TMP/list.txt -c copy docs/demo.mp4
rm -rf $TMP
echo "demo.mp4:" $(ffprobe -v error -show_entries format=duration -of csv=p=0 docs/demo.mp4)"s"
