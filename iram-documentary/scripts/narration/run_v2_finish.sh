#!/usr/bin/env bash
# Version 2, second half: picture render (small resumable parts, 4 in parallel) -> chapter joins -> export -> QC -> reports.
# Re-run it after an interruption: parts that are complete and up to date are skipped (scripts/editing/edit.py).
set -uo pipefail
P="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$P"
PY=/home/user/iram-work/venvs/ml/bin/python; LOG=/home/user/iram-work/logs
step() { echo "== $(date +%H:%M:%S) $*"; }
fail() { echo "PIPELINE_FAILED: $*"; exit 1; }
# chapter:parts (1 = whole chapter). Chapter 3 keeps 2 parts, chapter 4 uses 4: each part is 40-130 s of film.
PLAN="3:2 4:4 5:2 6:2 2:2 1:2 7:1 0:1"

step render
jobs=()
for cp in $PLAN; do c=${cp%%:*}; n=${cp##*:}
  if [ "$n" = 1 ]; then jobs+=("$c"); else for i in $(seq 1 $n); do jobs+=("$c --part $i/$n"); done; fi
done
printf '%s\n' "${jobs[@]}" | xargs -P 4 -I{} sh -c "$PY scripts/editing/edit.py video --chapter {} > $LOG/v2_render_\$(echo {} | tr -c '0-9' '_').log 2>&1 || echo RENDER_FAILED {}"

step join
for cp in $PLAN; do c=${cp%%:*}; n=${cp##*:}; [ "$n" = 1 ] && continue
  : > $LOG/ch${c}_concat.txt
  for i in $(seq 1 $n); do
    f="$P/renders/chapters/chapter_${c}_part${i}of${n}.mp4"
    ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" > /dev/null 2>&1 || fail "missing or incomplete $f"
    echo "file '$f'" >> $LOG/ch${c}_concat.txt
  done
  ffmpeg -y -loglevel error -f concat -safe 0 -i $LOG/ch${c}_concat.txt -c copy renders/chapters/chapter_${c}.mp4 || fail join-$c
done
for c in 0 1 2 3 4 5 6 7; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 renders/chapters/chapter_$c.mp4) || fail "chapter $c unreadable"
  echo "chapter $c: $d s"
done

step export;       bash scripts/export/export_final.sh                                        || fail export
step qc;           $PY scripts/quality_control/qc.py > $LOG/v2_qc.log 2>&1 && $PY scripts/quality_control/write_qc_report.py || fail qc
step final-report; $PY -m audio_engine.write_reports final                                    || fail final-report
step eval-report;  $PY -m audio_engine.evaluate_engines score > $LOG/v2_score.log 2>&1 && $PY -m audio_engine.write_reports evaluation || echo "evaluation report failed"
for cp in $PLAN; do c=${cp%%:*}; n=${cp##*:}; [ "$n" = 1 ] || rm -f renders/chapters/chapter_${c}_part*of${n}.mp4; done
echo PIPELINE_DONE
