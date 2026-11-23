#!/bin/bash
# usage: audit.sh VIDEO OUTDIR STEP
V=$1; O=$2; ST=${3:-5}; rm -rf $O; mkdir -p $O
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $V)
python3 - "$V" "$O" "$ST" "$DUR" <<'PY'
import sys, subprocess
from PIL import Image
v, o, st, dur = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
ts = [round(0.8 + k * st, 1) for k in range(int((dur - 1) / st) + 1)]
for t in ts: subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', v, '-frames:v', '1', '-vf', 'scale=270:480', '%s/f_%06.1f.jpg' % (o, t)])
import glob
fs = sorted(glob.glob(o + '/f_*.jpg'))
for n in range(0, len(fs), 9):
    c = Image.new('RGB', (9 * 274, 500), (40, 40, 40))
    from PIL import ImageDraw; d = ImageDraw.Draw(c)
    for k, p in enumerate(fs[n:n + 9]): c.paste(Image.open(p), (k * 274, 20)); d.text((k * 274 + 4, 3), p.split('_')[-1][:-4], fill=(255, 255, 0))
    c.save('%s/sheet_%02d.jpg' % (o, n // 9), quality=80)
print(len(fs), 'frames')
PY
