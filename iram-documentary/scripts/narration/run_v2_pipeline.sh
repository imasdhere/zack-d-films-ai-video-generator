#!/usr/bin/env bash
# Version 2 production chain: cloned narration -> QA -> assembly and mix -> picture (4 parallel renders) -> export -> QC.
# Resumable: finished narration chunks are skipped. Run from anywhere; logs go to /home/user/iram-work/logs/v2_*.log.
set -uo pipefail
P="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$P"
PY=/home/user/iram-work/venvs/ml/bin/python; LOG=/home/user/iram-work/logs
step() { echo "== $(date +%H:%M:%S) $*"; }
fail() { echo "PIPELINE_FAILED: $*"; exit 1; }

step plan;            $PY -m audio_engine.synthesis_manager plan                         || fail plan
step narration-en;    $PY -m audio_engine.synthesis_manager generate --lang en           || fail narration-en
step narration-ar;    $PY -m audio_engine.synthesis_manager generate --lang ar           || fail narration-ar
step qa;              $PY -m audio_engine.synthesis_manager qa --regenerate              || fail qa
step quranic;         $PY -m audio_engine.synthesis_manager quranic                      || echo "quranic review candidates failed (not part of the film)"
step assemble-mix;    $PY -m audio_engine.audio_assembler all                            || fail assemble
step render
jobs=("4 --part 1/2" "4 --part 2/2" "5" "3 --part 1/2" "3 --part 2/2" "6" "2" "1" "7" "0")
printf '%s\n' "${jobs[@]}" | xargs -P 4 -I{} sh -c "$PY scripts/editing/edit.py video --chapter {} > $LOG/v2_render_\$(echo {} | tr -c '0-9' '_').log 2>&1 || echo RENDER_FAILED {}"
for c in 3 4; do
  printf "file '%s'\nfile '%s'\n" "$P/renders/chapters/chapter_${c}_part1of2.mp4" "$P/renders/chapters/chapter_${c}_part2of2.mp4" > $LOG/ch${c}_concat.txt
  ffmpeg -y -loglevel error -f concat -safe 0 -i $LOG/ch${c}_concat.txt -c copy renders/chapters/chapter_${c}.mp4 || fail concat-$c
  rm -f renders/chapters/chapter_${c}_part1of2.mp4 renders/chapters/chapter_${c}_part2of2.mp4
done
step export;          bash scripts/export/export_final.sh                                 || fail export
step qc;              $PY scripts/quality_control/qc.py && $PY scripts/quality_control/write_qc_report.py || fail qc
step final-report;    $PY -m audio_engine.write_reports final                            || fail final-report
echo PIPELINE_DONE
