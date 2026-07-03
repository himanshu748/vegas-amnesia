#!/bin/bash
# Demo composite v2: recorded gameplay segments + designed HTML-rendered cards.
# Segments get their caption chip overlaid (fade in); intro/outro are full cards.
set -euo pipefail
cd "$(dirname "$0")/.."

RAW=$(ls docs/demo-raw/*.webm | head -1)
TMP=docs/demo-tmp; rm -rf $TMP; mkdir -p $TMP

seg() { # seg <out> <start> <end> <chip>
  local out=$1 ss=$2 to=$3 chip=$4
  ffmpeg -y -loglevel error -i "$RAW" -loop 1 -t 30 -i "docs/cards/$chip.png" -filter_complex \
    "[0:v]trim=start=${ss}:end=${to},setpts=PTS-STARTPTS[v];[1:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1[c];[v][c]overlay=0:0:shortest=1" \
    -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 "$TMP/$out.mp4"
  echo "file '$out.mp4'" >> $TMP/list.txt
}

card() { # card <out> <png> <dur>
  ffmpeg -y -loglevel error -loop 1 -t $3 -i "docs/cards/$2.png" \
    -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=$(echo "$3-0.5" | bc):d=0.5" \
    -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 "$TMP/$1.mp4"
  echo "file '$1.mp4'" >> $TMP/list.txt
}

: > $TMP/list.txt
card intro intro 3.8
seg s1 1.0 9.2 cap1          # boot log + tutorial card
seg s2 11.9 17.0 cap2        # inspect safe note + FILE IT
seg s3 44.0 52.0 cap3        # graph pops in (3D)
seg s3b 57.0 63.0 cap3       # second filing lands
seg s4 76.3 83.0 cap4        # chad reply + speech bubble
seg s5 94.5 100.5 cap5        # recall answer + citation pulse
seg s6 107.3 113.6 cap6      # memify purple inferences
seg s7 113.8 118.6 cap7      # herring modal
seg s7b 128.3 136.8 cap7     # forget fade
seg s8 148.2 154.2 cap8      # ending screen
seg s9 154.0 159.6 cap9      # debug overlay
card outro outro 4.2

ffmpeg -y -loglevel error -f concat -safe 0 -i $TMP/list.txt -c copy docs/demo.mp4
rm -rf $TMP
ffprobe -v error -show_entries format=duration -of csv=p=0 docs/demo.mp4
ls -la docs/demo.mp4

# ---------- cognee-deep-dive.mp4 (same segments, lifecycle-focused cut) ----------
TMP=docs/demo-tmp2; rm -rf $TMP; mkdir -p $TMP
: > $TMP/list.txt
DIVE() { # reuse seg with the dive list
  local out=$1 ss=$2 to=$3 chip=$4
  ffmpeg -y -loglevel error -i "$RAW" -loop 1 -t 30 -i "docs/cards/$chip.png" -filter_complex \
    "[0:v]trim=start=${ss}:end=${to},setpts=PTS-STARTPTS[v];[1:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1[c];[v][c]overlay=0:0:shortest=1" \
    -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 "$TMP/$out.mp4"
  echo "file '$out.mp4'" >> $TMP/list.txt
}
ffmpeg -y -loglevel error -loop 1 -t 3.6 -i docs/cards/intro.png -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=3.1:d=0.5" -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 $TMP/i.mp4
echo "file 'i.mp4'" >> $TMP/list.txt
DIVE d1 11.9 17.0 cap2
DIVE d2 44.0 52.0 cap3
DIVE d3 94.5 100.5 cap5
DIVE d4 107.3 113.6 cap6
DIVE d5 128.3 136.8 cap7
DIVE d6 154.0 159.6 cap9
ffmpeg -y -loglevel error -loop 1 -t 4 -i docs/cards/outro.png -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" -c:v libx264 -crf 20 -pix_fmt yuv420p -r 25 $TMP/o.mp4
echo "file 'o.mp4'" >> $TMP/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i $TMP/list.txt -c copy docs/cognee-deep-dive.mp4
rm -rf $TMP
