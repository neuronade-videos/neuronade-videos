#!/bin/bash
# usage: build.sh DIR SFXSCRIPT BRANDMOD  -> DIR/final.mp4
set -e
D=$1; SFX=$2; BR=$3; cd $D
python3 $SFX > /dev/null; python3 music_st.py > /dev/null
python3 - <<PY
import sys, json, os; sys.path.insert(0, '$D')
import holo8 as H8
FPS = H8.FPS; V = H8.V
times = [H8.INTRO + f0 / FPS for k, f0, s, nm in H8.EVF] + [H8.INTRO + V.NF / FPS + H8.OUTRO_EV]
durs = [(nm + 2) / FPS for k, f0, s, nm in H8.EVF] + [(H8.msg_frames(H8.LORE['outro']['text']) + 2) / FPS]
os.makedirs('$D/audio', exist_ok=True)
json.dump(dict(times=times, durs=durs), open('$D/audio/glitch_times.json', 'w'))
import $BR as BRM
BRM.sonic(BRM.INTRO + BRM.MAIN + BRM.OUTRO)
print('glitch', [round(x, 1) for x in times])
PY
python3 glitch_audio.py > /dev/null; bash mix_final.sh 2>&1 | grep -E "I:|Peak:" | tail -2
python3 - <<PY
import sys, os; sys.path.insert(0, '$D')
import holo8 as H8
from multiprocessing import Pool
ks = [k for k in range((H8.V.NF + 149) // 150) if not os.path.exists('$D/seg/seg_%03d.mp4' % k)]
with Pool(2) as p:
    for r in p.imap_unordered(H8.render_seg, ks): pass
import brand as B
p = '$D/seg/z_outro.mp4'
if not os.path.exists(p): H8.encode(p, (H8.outro8(i / H8.FPS) for i in range(int(round(B.OUTRO * H8.FPS)))))
print('segs', len(ks))
PY
(echo "file 'seg/a_intro.mp4'"; for f in seg/seg_*.mp4; do echo "file '$f'"; done; echo "file 'seg/z_outro.mp4'") > concat.txt
ffmpeg -y -v error -f concat -safe 0 -i concat.txt -c copy video_raw.mp4
ffmpeg -y -v error -i video_raw.mp4 -i audio/master.wav -map 0:v -map 1:a -c:v libx264 -preset medium -crf 20 -maxrate 4400k -bufsize 8800k -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart final.mp4
ls -la final.mp4; ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
