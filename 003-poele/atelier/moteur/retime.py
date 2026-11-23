"""Aère une voix calée : ralentit (optionnel) puis allonge les silences entre phrases et entre étapes.
usage: retime.py SRC_DIR DST_DIR speed intra_add intra_min para_min"""
import sys, json, os, shutil, subprocess, numpy as np, soundfile as sf
src, dst, speed, intra_add, intra_min, para_min = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
T = json.load(open(src + '/timeline.json')); S = T['sents']
wav = src + '/audio/voice_el.wav'
os.makedirs(dst + '/audio', exist_ok=True)
tmp = dst + '/audio/_speed.wav'
if abs(speed - 1) > 1e-3:
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-af', 'rubberband=tempo=%g:formant=preserved:pitchq=quality' % speed, tmp], check=True)
else: shutil.copy(wav, tmp)
a, sr = sf.read(tmp); k = 1 / speed
def sc(x): return x * k
for s in S:
    s['t0'], s['t1'] = sc(s['t0']), sc(s['t1']); s['breaks'] = [[b[0], sc(b[1]), sc(b[2])] for b in s['breaks']]
total = sc(T['total'])
pieces = []; shift = 0.0; last = 0
for i in range(len(S) - 1):
    g0, g1 = S[i]['t1'], S[i + 1]['t0']; gap = g1 - g0
    want = max(para_min, gap) if S[i + 1]['p'] != S[i]['p'] else max(intra_min, gap + intra_add)
    add = max(0.0, want - gap); cut = int(round((g0 + gap / 2) * sr))
    pieces.append(a[last:cut]); pieces.append(np.zeros((int(round(add * sr)),) + a.shape[1:])); last = cut
    S[i]['_shift'] = shift; shift += add
S[-1]['_shift'] = shift; pieces.append(a[last:])
cum = 0.0
for i, s in enumerate(S):
    sh = s.pop('_shift'); s['t0'] += sh; s['t1'] += sh; s['breaks'] = [[b[0], b[1] + sh, b[2] + sh] for b in s['breaks']]
out = np.concatenate(pieces); sf.write(dst + '/audio/voice_el.wav', out, sr, subtype='PCM_16'); os.remove(tmp)
T['total'] = total + shift
json.dump(T, open(dst + '/timeline.json', 'w'), ensure_ascii=False, indent=1)
import re
words = sum(len(re.findall(r"[\wÀ-ÿ'’-]+", s['text'])) for s in S); speech = S[-1]['t1'] - S[0]['t0']
print('words', words, 'speech %.1f' % speech, 'total %.2f' % T['total'], 'wpm %.1f' % (words / speech * 60), 'video ≈ %.1f s' % (T['total'] + 2.3 + 5.6))
