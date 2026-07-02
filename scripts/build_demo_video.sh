#!/bin/bash
# Cuts the raw playthrough recording into two edits:
#   docs/demo.mp4              (~80s full demo, lifecycle captions)
#   docs/cognee-deep-dive.mp4  (~40s, endpoint-level captions for the judges)
set -euo pipefail
cd "$(dirname "$0")/.."

RAW=$(ls docs/demo-raw/*.webm | head -1)
FONT="/System/Library/Fonts/Menlo.ttc"
CYAN="0x22e6ff"; PINK="0xff2e88"; PURPLE="0xb26bff"; AMBER="0xffb545"

seg() { # seg <start> <end> <caption> <color>
  local ss=$1 to=$2 text=$3 color=$4
  echo "[0:v]trim=start=${ss}:end=${to},setpts=PTS-STARTPTS,drawtext=fontfile=${FONT}:text='${text}':fontsize=30:fontcolor=${color}:x=(w-text_w)/2:y=h-70:box=1:boxcolor=black@0.65:boxborderw=14"
}

card() { # card <dur> <line1> <line2> <color1>
  local dur=$1 l1=$2 l2=$3 c1=$4
  echo "color=c=0x0a0812:s=1600x900:d=${dur},drawtext=fontfile=${FONT}:text='${l1}':fontsize=76:fontcolor=${c1}:x=(w-text_w)/2:y=(h/2)-70,drawtext=fontfile=${FONT}:text='${l2}':fontsize=28:fontcolor=0xd8d4e8:x=(w-text_w)/2:y=(h/2)+40"
}

# ---------- demo.mp4 ----------
ffmpeg -y -i "$RAW" -filter_complex "
$(card 3.5 'VEGAS AMNESIA' 'an AI detective game on the Cognee Cloud memory lifecycle' $PINK)[intro];
$(seg 5.5 10.5 'HAL-9001 boots with a wiped memory graph' $CYAN)[s1];
$(seg 37.8 48.5 '1/4 REMEMBER — evidence becomes graph memory' $CYAN)[s2];
$(seg 54.0 60.0 'every discovery grows the live memory graph' $CYAN)[s3];
$(seg 79.0 85.3 'characters are LLM-driven — they react to what your graph knows' $AMBER)[s4];
$(seg 92.4 98.5 '2/4 RECALL — Ask HAL cites its source nodes' $CYAN)[s5];
$(seg 107.0 113.5 '3/4 MEMIFY — consolidation derives purple inferences' $PURPLE)[s6];
$(seg 122.5 134.5 '4/4 FORGET — right-click prunes red herrings for real' $PINK)[s7];
$(seg 143.0 150.0 'SOLVE — the night, reconstructed with citations' $AMBER)[s8];
$(seg 150.5 156.0 'every Cognee call on the record — press backtick' $PURPLE)[s9];
$(card 4 'play it now' 'vegas-amnesia.vercel.app        WeMakeDevs x Cognee — The Hangover Part AI' $CYAN)[outro];
[intro][s1][s2][s3][s4][s5][s6][s7][s8][s9][outro]concat=n=11:v=1:a=0[v]
" -map "[v]" -c:v libx264 -crf 22 -pix_fmt yuv420p -movflags +faststart docs/demo.mp4

# ---------- cognee-deep-dive.mp4 ----------
ffmpeg -y -i "$RAW" -filter_complex "
$(card 3.5 'HOW WE USE COGNEE CLOUD' 'remember - recall - memify - forget — all four, live' $PURPLE)[intro];
$(seg 37.8 46.0 'POST /api/v1/remember — one data item per fact, auto-cognified' $CYAN)[s1];
$(seg 92.4 98.5 'POST /api/v1/recall + includeReferences — answers cite chunks' $CYAN)[s2];
$(seg 107.0 113.5 'memify = cognify re-run w/ inference prompt + derived facts' $PURPLE)[s3];
$(seg 128.0 134.5 'POST /api/v1/forget dataId — graph nodes actually deleted' $PINK)[s4];
$(seg 150.5 156.0 'the receipts — every lifecycle call, timed, in-game' $AMBER)[s5];
$(card 4 'per-session datasets - graph deltas - citations' 'github.com/…/vegas-amnesia        vegas-amnesia.vercel.app' $CYAN)[outro];
[intro][s1][s2][s3][s4][s5][outro]concat=n=7:v=1:a=0[v]
" -map "[v]" -c:v libx264 -crf 22 -pix_fmt yuv420p -movflags +faststart docs/cognee-deep-dive.mp4

ls -la docs/*.mp4
