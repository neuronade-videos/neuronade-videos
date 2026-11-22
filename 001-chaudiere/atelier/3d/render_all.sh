#!/bin/bash
cd /home/claude/b3d
for s in hook1:1.5 hook2:1.25 ign:1.25 cond:1.25 gauge:1.25; do
  n=${s%%:*}; sc=${s##*:}
  python3 boiler.py $n 28 $sc > log_$n.txt 2>&1
  cp shot_$n.png final_$n.png
  echo "$n done $(date +%T)" >> progress.txt
done
echo ALL >> progress.txt
