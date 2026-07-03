#!/bin/bash
# Adds sound to the demos: timed neural VO + a synthesized dark-noir ambient
# bed (A-minor drone stack, license-free). Run after build_demo_v2.sh +
# make_narration.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

DUR=63
VO=docs/vo

# --- ambient bed: detuned A1 drone + fifth + slow swell + vinyl-ish texture ---
ffmpeg -y -loglevel error \
  -f lavfi -i "sine=frequency=55:duration=$DUR" \
  -f lavfi -i "sine=frequency=55.4:duration=$DUR" \
  -f lavfi -i "sine=frequency=82.4:duration=$DUR" \
  -f lavfi -i "sine=frequency=110.2:duration=$DUR" \
  -f lavfi -i "anoisesrc=color=pink:duration=$DUR:amplitude=0.028" \
  -filter_complex "\
    [0:a]volume=0.50[a0];[1:a]volume=0.44[a1];[2:a]volume=0.22[a2];\
    [3:a]volume=0.14,tremolo=f=0.13:d=0.75[a3];\
    [4:a]lowpass=f=320,tremolo=f=0.11:d=0.6[a4];\
    [a0][a1][a2][a3][a4]amix=inputs=5,volume=4.5,\
    lowpass=f=900,aecho=0.7:0.6:60:0.25,volume=0.9,\
    afade=t=in:st=0:d=2,afade=t=out:st=$(echo "$DUR-3" | bc):d=3[bed]" \
  -map "[bed]" -ac 2 docs/vo/bed.wav

# --- timed VO track (starts in seconds) ---
starts=(intro:0.3 s1:4.3 s2:12.3 s3:20.3 s5:27.3 s6:34.3 s7b:41.3 s8:48.3 s9:54.3 outro:59.3)
inputs=(); filters=""; mix=""
i=0
for pair in "${starts[@]}"; do
  name=${pair%%:*}; at=${pair##*:}
  ms=$(echo "$at * 1000 / 1" | bc)
  inputs+=(-i "$VO/$name.mp3")
  filters+="[$i:a]adelay=${ms}|${ms},apad=whole_dur=${DUR}[v$i];"
  mix+="[v$i]"
  i=$((i+1))
done

ffmpeg -y -loglevel error "${inputs[@]}" -filter_complex \
  "${filters}${mix}amix=inputs=$i,volume=$(echo "$i * 1.4" | bc)[vo]" \
  -map "[vo]" -ac 2 -t $DUR docs/vo/vo_track.wav

# --- final mixes ---
ffmpeg -y -loglevel error -i docs/demo.mp4 -i docs/vo/vo_track.wav -i docs/vo/bed.wav \
  -filter_complex "[2:a]volume=0.55[b];[1:a][b]amix=inputs=2,volume=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest docs/demo-sound.mp4
mv docs/demo-sound.mp4 docs/demo.mp4

# deep-dive gets the bed only (first 44s), faded
DDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 docs/cognee-deep-dive.mp4)
ffmpeg -y -loglevel error -i docs/cognee-deep-dive.mp4 -i docs/vo/bed.wav \
  -filter_complex "[1:a]atrim=0:${DDUR},afade=t=out:st=$(echo "$DDUR-2.5" | bc):d=2.5,volume=0.8,loudnorm=I=-18:TP=-1.5[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -shortest docs/dd-sound.mp4
mv docs/dd-sound.mp4 docs/cognee-deep-dive.mp4

ffprobe -v error -select_streams a -show_entries stream=codec_name,duration -of csv=p=0 docs/demo.mp4
ls -la docs/*.mp4
