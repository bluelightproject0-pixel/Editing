#!/usr/bin/env bash
# Corte maestro: extrae cada rango con micro-fades de 30 ms y concatena sin re-codificar.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=assets/source_1080.mp4
if [ "${VARIANT:-long}" = short ]; then
  OUT=edit-short/assets/cut.mp4; TMP=build/segs-short
  RANGES="0.00-5.15 12.75-15.53 34.72-40.45 42.05-63.30 93.80-108.12 123.62-125.92 133.45-138.95"
else
  OUT=edit/assets/cut.mp4; TMP=build/segs
  RANGES="0.00-5.15 12.75-40.45 42.05-86.40 93.85-109.75 111.25-112.10 117.32-120.20 122.75-138.95"
fi
rm -rf $TMP; mkdir -p $TMP $(dirname $OUT)
i=0; : > $TMP/list.txt
for r in $RANGES; do
  a=${r%-*}; b=${r#*-}; d=$(python3 -c "print(round($b-$a,3))"); fo=$(python3 -c "print(round($b-$a-0.03,3))")
  f=$TMP/s$i.mp4
  ffmpeg -v error -y -ss $a -i $SRC -t $d -map 0:v:0 -map 0:a:0 \
    -c:v libx264 -preset fast -crf 17 -g 30 -keyint_min 30 -pix_fmt yuv420p -r 30000/1001 \
    -af "afade=t=in:st=0:d=0.03,afade=t=out:st=$fo:d=0.03" -c:a aac -b:a 256k -ar 48000 $f
  echo "file 's$i.mp4'" >> $TMP/list.txt
  ffprobe -v error -select_streams v -show_entries stream=duration -of csv=p=0 $f | xargs echo "seg$i $a-$b vdur"
  i=$((i+1))
done
ffmpeg -v error -y -f concat -safe 0 -i $TMP/list.txt -c copy -movflags +faststart $OUT
ffprobe -v error -show_entries stream=codec_type,duration -of compact $OUT
