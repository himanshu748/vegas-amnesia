#!/bin/bash
# Neural VO clips for the demo, one per segment, timed to the composite.
# Segment starts (s): intro=0.4 s1=4.3 s2=12.1 s3=17.3 s3b=25.3 s4=31.3
#                     s5=38.0 s6=44.1 s7=50.4 s7b=55.2 s8=63.8 s9=69.8 outro=75.2
set -euo pipefail
cd "$(dirname "$0")/.."
TTS=.venv/bin/edge-tts
V="en-US-AndrewMultilingualNeural"
OUT=docs/vo; rm -rf $OUT; mkdir -p $OUT

say() { $TTS --voice "$V" --rate=+6% --text "$2" --write-media "$OUT/$1.mp3"; }

say intro "Vegas Amnesia. A detective game built on the Cognee Cloud memory lifecycle."
say s1    "You are HAL 9001. Your owner had a wild night. Your memory graph was wiped. And Priya lands at noon."
say s2    "Step one: remember. File the evidence you trust, and it becomes real memory in Cognee."
say s3    "Watch it grow. A living 3D knowledge graph. One Cognee dataset per investigation."
say s3b   "Entities. Relationships. Sources. Extracted automatically."
say s4    "Interrogate the witnesses. They're LLM driven, and they know exactly what your graph knows."
say s5    "Step two: recall. Ask HAL anything. Every answer cites its source nodes."
say s6    "Step three: memify. Connect the dots, and HAL derives brand new inferences. The purple ones."
say s7    "But not everything you find is true."
say s7b   "Step four: forget. False memories get deleted for real. Watch the red herring die."
say s8    "Solve the night. The timeline rebuilt, and scored against ground truth."
say s9    "And every Cognee call? On the record."
say outro "Vegas Amnesia. Play it now."

for f in $OUT/*.mp3; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  echo "$(basename $f) ${d}s"
done
