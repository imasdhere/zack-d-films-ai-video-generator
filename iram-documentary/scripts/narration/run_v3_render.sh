#!/usr/bin/env bash
# Version 3, picture only (after the narration and mix are done): re-voiced English narration (paragraph chunks, Arabic pronunciation of Iram and ʿĀd) -> QA -> mix ->
# 1440p picture (2560x1440, resumable parts, 4 in parallel) -> export -> QC -> reports. Re-run it after an interruption.
set -uo pipefail
P="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$P"
export IRAM_WORK=${IRAM_WORK:-/home/user/iram-work}
PY=${IRAM_PY:-$IRAM_WORK/venvs/ml/bin/python}; LOG=$IRAM_WORK/logs; mkdir -p $LOG; JOBS=${IRAM_JOBS:-4}
step() { echo "== $(date +%H:%M:%S) $*"; }
fail() { echo "PIPELINE_FAILED: $*"; exit 1; }
export IRAM_SCALE=${IRAM_SCALE:-1.3333334} IRAM_CRF=${IRAM_CRF:-18} IRAM_CHAPTER_DIR=${IRAM_CHAPTER_DIR:-renders/chapters_1440} IRAM_MASTER_NAME=${IRAM_MASTER_NAME:-iram_lost_city_documentary_1440p}
mkdir -p $IRAM_CHAPTER_DIR

step render
PLAN="3:3 4:4 5:2 6:2 2:2 1:2 7:1 0:1"
jobs=()
for cp in $PLAN; do c=${cp%%:*}; n=${cp##*:}
  if [ "$n" = 1 ]; then jobs+=("$c"); else for i in $(seq 1 $n); do jobs+=("$c --part $i/$n"); done; fi
done
printf '%s\n' "${jobs[@]}" | xargs -P $JOBS -I{} sh -c "$PY scripts/editing/edit.py video --chapter {} > $LOG/v3_render_\$(echo {} | tr -c '0-9' '_').log 2>&1 || echo RENDER_FAILED {}"
step join
for cp in $PLAN; do c=${cp%%:*}; n=${cp##*:}; [ "$n" = 1 ] && continue
  : > $LOG/v3_ch${c}_concat.txt
  for i in $(seq 1 $n); do
    f="$P/$IRAM_CHAPTER_DIR/chapter_${c}_part${i}of${n}.mp4"
    ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" > /dev/null 2>&1 || fail "missing or incomplete $f"
    echo "file '$f'" >> $LOG/v3_ch${c}_concat.txt
  done
  ffmpeg -y -loglevel error -f concat -safe 0 -i $LOG/v3_ch${c}_concat.txt -c copy $IRAM_CHAPTER_DIR/chapter_${c}.mp4 || fail join-$c
  rm -f $IRAM_CHAPTER_DIR/chapter_${c}_part*of${n}.mp4        # free disk at once
done
for c in 0 1 2 3 4 5 6 7; do
  d=$(ffprobe -v error -show_entries format=duration:stream=width,height -of csv=p=0 $IRAM_CHAPTER_DIR/chapter_$c.mp4 | tr '\n' ' ') || fail "chapter $c unreadable"
  echo "chapter $c: $d"
done

step export;       bash scripts/export/export_final.sh                                        || fail export
step qc;           $PY scripts/quality_control/qc.py > $LOG/v3_qc.log 2>&1 && $PY scripts/quality_control/write_qc_report.py || fail qc
step final-report; $PY -m audio_engine.write_reports final                                    || fail final-report
echo PIPELINE_DONE
